#!/usr/bin/env python3
"""Read Android UI labels and coordinates without taking a screenshot."""

import argparse
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET


def controls(xml):
    result = []
    for node in ET.fromstring(xml).iter("node"):
        attrs = node.attrib
        if attrs.get("password") == "true" or attrs.get("visible-to-user") == "false":
            continue
        match = re.fullmatch(r"\[(-?\d+),(-?\d+)\]\[(-?\d+),(-?\d+)\]", attrs.get("bounds", ""))
        if not match:
            continue
        left, top, right, bottom = map(int, match.groups())
        if min(left, top) < 0 or right <= left or bottom <= top:
            continue
        label = attrs.get("text") or attrs.get("content-desc") or attrs.get("resource-id")
        if not label:
            continue
        result.append({
            "text": label,
            "id": attrs.get("resource-id", ""),
            "center": [(left + right) // 2, (top + bottom) // 2],
            "enabled": attrs.get("enabled") == "true",
            "clickable": attrs.get("clickable") == "true",
        })
    return result


def dump_controls():
    bridge = Path(__file__).with_name("android-shell.sh")
    # Android and chroot must share this path; never store UI data in the repo.
    with tempfile.TemporaryDirectory(prefix="android-ui-", dir="/data/local/tmp") as directory:
        output = Path(directory) / "window.xml"
        completed = subprocess.run(
            ["sh", str(bridge), "-c", 'exec uiautomator dump "$1"', "android-ui", str(output)],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=30,
        )
        if completed.returncode or not output.is_file():
            raise RuntimeError("uiautomator 未生成界面文件，请检查服务权限和临时目录映射。")
        return controls(output.read_bytes())


def main():
    parser = argparse.ArgumentParser(description="读取控件文字和中心坐标；不截图、不点击。")
    parser.add_argument("--text", default="", help="按文字包含匹配")
    parser.add_argument("--id", default="", help="按 resource-id 包含匹配")
    parser.add_argument("--json", action="store_true", help="同时输出 ID、可用和可点击状态")
    args = parser.parse_args()
    try:
        rows = [row for row in dump_controls()
                if args.text.casefold() in row["text"].casefold() and args.id in row["id"]]
    except (OSError, RuntimeError, ET.ParseError, subprocess.TimeoutExpired) as error:
        message = str(error) if isinstance(error, RuntimeError) else type(error).__name__
        print(f"读取界面失败：{message}", file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps(rows, ensure_ascii=False))
    else:
        for row in rows:
            x, y = row["center"]
            state = " [不可用]" if not row["enabled"] else ""
            print(f'{json.dumps(row["text"], ensure_ascii=False)}\t({x}, {y}){state}')
    if not rows:
        print("没有匹配的控件。", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
