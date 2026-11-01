#!/usr/bin/env python3
"""Locate current Android controls and optionally tap one verified target."""
import argparse
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import time
import xml.etree.ElementTree as ET

from phone import android


def bounds(value):
    match = re.fullmatch(r"\[(-?\d+),(-?\d+)\]\[(-?\d+),(-?\d+)\]", value)
    if not match:
        return None
    left, top, right, bottom = map(int, match.groups())
    if min(left, top) < 0 or right <= left or bottom <= top:
        return None
    return [left, top, right, bottom]


def center(box):
    return [(box[0] + box[2]) // 2, (box[1] + box[3]) // 2]


def contains(box, point):
    return box[0] <= point[0] < box[2] and box[1] <= point[1] < box[3]


def controls(xml):
    result = []
    nodes = []
    candidates = []

    def visit(node, path=(), touch_parent=None, private=False):
        attrs = node.attrib
        if attrs.get("visible-to-user") == "false":
            return
        private = private or attrs.get("password") == "true"
        box = bounds(attrs.get("bounds", ""))
        # A disabled container can still dispatch touches to enabled children.
        enabled = attrs.get("enabled") == "true"
        clickable = attrs.get("clickable") == "true"
        long_clickable = attrs.get("long-clickable") == "true"
        info = {"path": path, "bounds": box, "enabled": enabled,
                "clickable": clickable, "long_clickable": long_clickable,
                "id": attrs.get("resource-id", ""),
                "package": attrs.get("package", "")}
        nodes.append(info)
        # Keep the closest touch-consuming ancestor even if disabled/invalid:
        # skipping it would incorrectly redirect the touch to an outer control.
        target = info if clickable or long_clickable else touch_parent
        label = attrs.get("text") or attrs.get("content-desc") or attrs.get("resource-id")
        if box and label and not private:
            row = {
                "text": label, "description": attrs.get("content-desc", ""),
                "id": attrs.get("resource-id", ""), "package": attrs.get("package", ""),
                "bounds": box, "center": center(box), "enabled": enabled,
                "clickable": clickable, "long_clickable": long_clickable, "tap_center": None,
                "checked": attrs.get("checked") == "true", "selected": attrs.get("selected") == "true",
            }
            result.append(row)
            candidates.append((row, target))
        for index, child in enumerate(node):
            visit(child, path + (index,), target, private)

    try:
        visit(ET.fromstring(xml))
    except ET.ParseError as error:
        raise RuntimeError(f"界面 XML 解析失败：{error}") from error

    # Check against clickable and long-clickable nodes, including unlabeled, disabled and
    # password nodes. Their text is never exposed by the blocker check.
    for row, target in candidates:
        if not row["enabled"]:
            row["tap_error"] = "所选节点自身不可用"
            continue
        if target is None or not target["enabled"] or target["bounds"] is None:
            row["tap_error"] = "实际点击目标缺失、不可用或范围不明"
            continue
        if not target["clickable"]:
            row["tap_error"] = "最近的触摸接收节点仅支持长按，不能跳过它点击外层控件"
            continue
        point = center(target["bounds"])
        for other in nodes:
            if not (other["clickable"] or other["long_clickable"]):
                continue
            # The target and its ancestors are on the same event path;
            # siblings and touch-consuming descendants can intercept the landing point.
            if target["path"][:len(other["path"])] == other["path"]:
                continue
            if other["bounds"] is None or contains(other["bounds"], point):
                row["tap_error"] = "落点可能被其他可点击或可长按控件接收，拒绝猜测"
                break
        else:
            row["tap_center"] = point
            row["tap_target"] = target
    return result


def dump_controls():
    with tempfile.TemporaryDirectory(prefix="android-ui-", dir="/data/local/tmp") as directory:
        output = Path(directory) / "window.xml"
        message = android("uiautomator", "dump", str(output), timeout=30)
        if not output.is_file():
            raise RuntimeError("uiautomator 未生成界面文件，请核对权限和目录映射：" + message.strip()[-500:])
        return controls(output.read_bytes())


def matching(rows, text="", resource_id="", exact=False):
    def match(value, query):
        return not query or (value == query if exact else query.casefold() in value.casefold())
    return [r for r in rows if match(r["text"], text) and match(r["id"], resource_id)]


def wait_for(text, resource_id, exact, seconds):
    deadline = time.monotonic() + seconds
    while True:
        rows = dump_controls()
        selected = matching(rows, text, resource_id, exact)
        if selected or time.monotonic() >= deadline:
            return rows, selected
        time.sleep(min(0.5, max(0, deadline - time.monotonic())))


def unique_target(rows):
    if len(rows) != 1:
        raise RuntimeError(f"匹配到 {len(rows)} 个控件；请用文字和 ID 缩小到唯一目标。")
    target = rows[0]
    if not target["enabled"] or target["tap_center"] is None:
        raise RuntimeError(target.get("tap_error", "目标不可用，或未找到可点击控件及父控件。"))
    return target


def tap(args, selected):
    target = unique_target(selected)
    # Re-read immediately before the only tap. Never retry a sent tap.
    fresh = dump_controls()
    current = unique_target(matching(fresh, args.text, args.id, args.exact))
    if current != target:
        raise RuntimeError("目标在点击前发生变化，未点击；请重新观察页面。")
    expected_before = matching(fresh, args.expect_text, args.expect_id, args.exact) if (args.expect_text or args.expect_id) else []
    if expected_before:
        raise RuntimeError("预期结果在点击前已存在，无法用于验证本次操作；请换一个结果条件。")
    try:
        android("input", "tap", *current["tap_center"])
    except (OSError, RuntimeError, subprocess.TimeoutExpired) as error:
        raise RuntimeError(f"点击命令失败或超时，可能已执行；先观察页面，不要直接重试：{error}") from error
    try:
        if args.expect_text or args.expect_id:
            after, expected = wait_for(args.expect_text, args.expect_id, args.exact, args.wait)
            verified = bool(expected)
        else:
            after, expected = dump_controls(), []
            verified = False
    except (OSError, RuntimeError, subprocess.TimeoutExpired) as error:
        return {"tap_sent": True, "target": current, "verified": False,
                "error": str(error), "note": "点击已发送，后续读取失败；先观察页面，不要直接重试。"}
    return {"tap_sent": True, "target": current, "ui_changed": after != fresh,
            "verified": verified, "expected_matches": len(expected),
            "note": "已满足预期界面条件" if verified else "点击已发送但结果未验证；先观察页面，不要直接重试。"}


def main():
    parser = argparse.ArgumentParser(description="读取界面控件；可按唯一目标点击并检查预期结果。")
    parser.add_argument("--text", default="", help="按文字匹配")
    parser.add_argument("--id", default="", help="按 resource-id 匹配")
    parser.add_argument("--exact", action="store_true", help="文字和 ID 精确匹配")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--wait", type=float, default=0, help="等待匹配的秒数，0–60；单次界面读取另有 30 秒超时")
    parser.add_argument("--click", action="store_true", help="重新定位后点击唯一目标一次")
    parser.add_argument("--expect-text", default="", help="点击后应新出现的文字")
    parser.add_argument("--expect-id", default="", help="点击后应新出现的 ID")
    args = parser.parse_args()
    if not 0 <= args.wait <= 60:
        parser.error("--wait 必须在 0–60 之间")
    if args.click and not (args.text or args.id):
        parser.error("点击必须指定 --text 或 --id")
    if (args.expect_text or args.expect_id) and not args.click:
        parser.error("预期结果参数需要 --click")
    try:
        _, rows = wait_for(args.text, args.id, args.exact, args.wait)
        if args.click:
            result = tap(args, rows)
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return 0 if result["verified"] else 3
        if args.json:
            print(json.dumps(rows, ensure_ascii=False))
        else:
            for row in rows:
                state = " [不可用]" if not row["enabled"] else ""
                print(f'{json.dumps(row["text"], ensure_ascii=False)}\t{tuple(row["center"])}{state}')
        if not rows:
            print("没有匹配的控件。", file=sys.stderr)
            return 1
        return 0
    except (OSError, RuntimeError, subprocess.TimeoutExpired) as error:
        print(f"界面操作失败：{error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
