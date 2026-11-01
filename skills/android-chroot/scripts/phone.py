#!/usr/bin/env python3
"""Device-probed Android helpers. Private records stay outside the project."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import struct
import subprocess
import sys
import tempfile
import time
import uuid

BRIDGE = Path(__file__).resolve().with_name("android-shell.sh")
STATE_DIR = Path.home() / ".local/state/android-chroot"
STATES = {0: "default-state", 1: "enable", 2: "disable", 3: "disable-user", 4: "disable-until-used"}
PACKAGE = re.compile(r"[A-Za-z][A-Za-z0-9_]*(?:\.[A-Za-z0-9_]+)*\Z")


def android(*args, timeout=30):
    # Every argument is passed through argv, never inserted into shell source.
    result = subprocess.run(["sh", str(BRIDGE), "-c", 'exec "$@"', "phone", *map(str, args)],
                            capture_output=True, timeout=timeout)
    if result.returncode:
        detail = (result.stderr or result.stdout).decode(errors="replace").strip()[-1200:]
        raise RuntimeError(f"{args[0]} 返回 {result.returncode}: {detail}")
    return result.stdout.decode(errors="replace")


def device():
    props = dict(re.findall(r"^\[([^]]+)\]: \[(.*)\]$", android("getprop"), re.M))
    serial = props.get("ro.serialno") or props.get("ro.boot.serialno")
    if not serial:
        raise RuntimeError("无法核对设备身份，停止创建或恢复状态记录。")
    return {
        "key": hashlib.sha256(serial.encode()).hexdigest(),
        "model": props.get("ro.product.model"),
        "build": props.get("ro.build.display.id"),
        "android": props.get("ro.build.version.release"),
    }


def package_names(user, disabled=False):
    args = ["pm", "list", "packages", "--user", str(user)]
    if disabled:
        args.append("-d")
    result = android(*args)
    if "Error" in result or "Exception" in result:
        raise RuntimeError(result.strip())
    return {line[8:].strip() for line in result.splitlines() if line.startswith("package:")}


def parse_packages(raw, user):
    packages = {}
    current = None
    in_packages = False
    for line in raw.splitlines():
        # Updated system apps also occur under "Hidden system packages".
        # Only the top-level Packages section describes the current install.
        if line and not line[0].isspace():
            in_packages = line.rstrip() == "Packages:"
            current = None
            continue
        if not in_packages:
            continue
        match = re.match(r"\s{2}Package \[([^]]+)\]", line)
        if match:
            current = match[1]
        match = re.match(rf"\s+User {user}:\s+(.+)", line)
        if current and match and "installed=" in match[1]:
            fields = dict(re.findall(r"(\w+)=([^\s]+)", match[1]))
            if fields.get("installed") != "true":
                continue
            enabled = int(fields["enabled"])
            if enabled not in STATES:
                raise RuntimeError(f"{current}: 未知 enabled 状态 {enabled}")
            packages[current] = {"enabled": enabled, **{
                key: fields.get(key) == "true" for key in ("stopped", "hidden", "suspended")}}
    return packages


def packages(user):
    names = package_names(user)
    if not names:
        raise RuntimeError(f"用户 {user} 没有可读取的应用；请核对用户及权限。")
    rows = parse_packages(android("dumpsys", "package", "packages", timeout=60), user)
    missing = names - rows.keys()
    if missing:
        raise RuntimeError(f"未能解析 {len(missing)} 个应用状态，停止操作。")
    disabled = package_names(user, disabled=True)
    return {name: {**rows[name], "disabled": name in disabled} for name in sorted(names)}


def package_state(name, user):
    rows = parse_packages(android("dumpsys", "package", name), user)
    if name not in rows:
        raise RuntimeError(f"用户 {user} 未安装 {name} 或状态不可读。")
    return rows[name]["enabled"]


def private_path(value=None, suffix=".json"):
    path = Path(value).expanduser().absolute() if value else STATE_DIR / (time.strftime("%Y%m%dT%H%M%S") + "-" + uuid.uuid4().hex[:8] + suffix)
    resolved = path.resolve()
    source = BRIDGE.parent.parent
    if resolved == source or source in resolved.parents or any((p / ".git").exists() for p in resolved.parents):
        raise RuntimeError("手机状态和截图须保存到仓库之外。")
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    return path


def save(path, data, create=False):
    content = (json.dumps(data, ensure_ascii=False, indent=2) + "\n").encode()
    if create:
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "wb") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
    else:
        fd, temporary = tempfile.mkstemp(dir=path.parent, prefix=".android-state-")
        try:
            with os.fdopen(fd, "wb") as stream:
                stream.write(content)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, path)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)


def snapshot(user):
    return {"schema": 1, "kind": "snapshot", "device": device(), "user": user,
            "boot_id": android("cat", "/proc/sys/kernel/random/boot_id").strip(),
            "time": time.time(), "packages": packages(user)}


def check_identity(record, user):
    if record.get("schema") != 1 or record.get("user") != user:
        raise RuntimeError("记录格式或 Android 用户不匹配。")
    if record.get("device", {}).get("key") != device()["key"]:
        raise RuntimeError("记录来自其他设备，停止操作。")


def compare(before, after):
    if before.get("kind") != "snapshot" or after.get("kind") != "snapshot":
        raise RuntimeError("需要两份应用快照。")
    if before["device"]["key"] != after["device"]["key"] or before["user"] != after["user"]:
        raise RuntimeError("两份快照的设备或用户不一致。")
    old, new = before["packages"], after["packages"]
    return {"rebooted": before["boot_id"] != after["boot_id"],
            "build_changed": before["device"]["build"] != after["device"]["build"],
            "added": sorted(new.keys() - old.keys()), "removed": sorted(old.keys() - new.keys()),
            "changed": {p: {"before": old[p], "after": new[p]} for p in sorted(old.keys() & new.keys()) if old[p] != new[p]}}


def disable(names, user, path):
    names = list(dict.fromkeys(names))
    if not all(PACKAGE.fullmatch(name) for name in names):
        raise RuntimeError("仅接受应用包名，不接受组件名或 shell 参数。")
    identity = device()
    original = {name: package_state(name, user) for name in names}
    record = {"schema": 1, "kind": "disable", "device": identity, "user": user,
              "time": time.time(), "entries": {name: {"before": state, "attempted": False} for name, state in original.items()}}
    save(path, record, create=True)
    print(f"恢复记录：{path}", flush=True)
    for name, entry in record["entries"].items():
        try:
            if package_state(name, user) != entry["before"]:
                raise RuntimeError("应用状态已改变，停止批次。")
            if entry["before"] != 3:
                entry["attempted"] = True
                save(path, record)  # Record intent before changing Android state.
                android("pm", "disable-user", "--user", user, name)
            entry["after"] = package_state(name, user)
            if entry["after"] != 3:
                raise RuntimeError("禁用后的状态验证失败。")
            save(path, record)
        except Exception as error:
            entry["error"] = str(error)
            save(path, record)
            raise
    return {"disabled": names, "record": str(path)}


def restore(path, user):
    # Read and atomically update the same file, not the symlink used to reach it.
    # Resolve once, before any device mutation, and recheck the storage location.
    path = private_path(Path(path).expanduser().resolve(strict=True))
    record = json.loads(path.read_text())
    check_identity(record, user)
    if record.get("kind") != "disable":
        raise RuntimeError("需要禁用操作生成的恢复记录。")
    entries = record["entries"]
    for name, entry in entries.items():
        if not PACKAGE.fullmatch(name) or type(entry.get("before")) is not int or entry["before"] not in STATES:
            raise RuntimeError("恢复记录含无效包名或状态。")
        if entry.get("attempted") and not entry.get("restored") and package_state(name, user) not in (3, entry["before"]):
            raise RuntimeError(f"{name} 已被其他操作改动，停止恢复。")
    restored = []
    for name, entry in entries.items():
        if not entry.get("attempted") or entry.get("restored"):
            continue
        current = package_state(name, user)
        if current not in (3, entry["before"]):
            raise RuntimeError(f"{name} 的状态已改变，停止恢复。")
        if current != entry["before"]:
            android("pm", STATES[entry["before"]], "--user", user, name)
        if package_state(name, user) != entry["before"]:
            raise RuntimeError(f"{name} 恢复验证失败。")
        entry["restored"] = True
        save(path, record)
        restored.append(name)
    return {"restored": restored, "record": str(path)}


def foreground():
    output = android("dumpsys", "activity", "activities")
    matches = re.findall(r"(?:topResumedActivity|mResumedActivity)[^\n]*?\bu(\d+)\s+([A-Za-z0-9_.$]+/[A-Za-z0-9_.$]+)", output)
    rows = [{"user": int(user), "component": component} for user, component in dict.fromkeys(matches)]
    if not rows:
        raise RuntimeError("未识别到前台 Activity；可能处于锁屏或系统输出格式不同。")
    return rows


def screenshot(path):
    result = subprocess.run(["sh", str(BRIDGE), "-c", "exec screencap -p"], capture_output=True, timeout=30)
    data = result.stdout
    if result.returncode or not data.startswith(b"\x89PNG\r\n\x1a\n") or len(data) < 24 or data[12:16] != b"IHDR":
        raise RuntimeError("截图失败：" + result.stderr.decode(errors="replace")[-500:])
    width, height = struct.unpack(">II", data[16:24])
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "wb") as stream:
        stream.write(data)
    return {"path": str(path), "width": width, "height": height,
            "note": "需查看图片确认画面；受保护页面可能黑屏。"}


def doctor():
    checks = {}
    commands = {"identity": ("id",), "model": ("getprop", "ro.product.model"),
                "build": ("getprop", "ro.build.display.id"), "android": ("getprop", "ro.build.version.release"),
                "user": ("am", "get-current-user"), "display": ("wm", "size"),
                "density": ("wm", "density"), "battery": ("dumpsys", "battery")}
    for name, command in commands.items():
        try:
            value = android(*command)
            if not value.strip() or "Can't find service" in value or "Permission Denial" in value:
                raise RuntimeError(value or "服务无输出")
            if name == "battery":
                level = re.search(r"^\s*level:\s*(\d+)", value, re.M)
                if not level:
                    raise RuntimeError("电池服务返回格式未识别")
                value = f"level={level[1]}"
            checks[name] = {"ok": True, "value": value.strip()}
        except (RuntimeError, OSError, subprocess.TimeoutExpired) as error:
            checks[name] = {"ok": False, "error": str(error)}
    try:
        current_user = int(android("am", "get-current-user").strip())
        checks["packages"] = {"ok": True, "count": len(packages(current_user))}
    except (ValueError, RuntimeError, OSError, subprocess.TimeoutExpired) as error:
        checks["packages"] = {"ok": False, "error": str(error)}
    try:
        with tempfile.NamedTemporaryFile(dir="/data/local/tmp", prefix="android-check-") as stream:
            marker = uuid.uuid4().hex
            stream.write(marker.encode())
            stream.flush()
            if android("cat", stream.name) != marker:
                raise RuntimeError("Android 与 chroot 临时目录映射不一致")
        checks["shared_tmp"] = {"ok": True}
    except (RuntimeError, OSError, subprocess.TimeoutExpired) as error:
        checks["shared_tmp"] = {"ok": False, "error": str(error)}
    try:
        from ui_controls import dump_controls
        checks["ui"] = {"ok": True, "controls": len(dump_controls())}
    except (RuntimeError, OSError, ValueError, subprocess.TimeoutExpired) as error:
        checks["ui"] = {"ok": False, "error": str(error)}
    return checks


def main():
    parser = argparse.ArgumentParser(description="Android 自检、应用状态与恢复、重启对比、前台查询和截图。")
    sub = parser.add_subparsers(dest="action", required=True)
    sub.add_parser("doctor")
    sub.add_parser("foreground")
    shot = sub.add_parser("screenshot")
    shot.add_argument("--output")
    for name in ("packages", "snapshot", "disable", "restore", "compare"):
        command = sub.add_parser(name)
        command.add_argument("--user", type=int, required=True)
        if name in ("packages", "disable"):
            command.add_argument("packages", nargs="+" if name == "disable" else "*")
        if name in ("snapshot", "disable"):
            command.add_argument("--output")
        if name in ("restore", "compare"):
            command.add_argument("record")
    args = parser.parse_args()
    try:
        if hasattr(args, "user") and args.user < 0:
            raise RuntimeError("请指定明确的非负 Android 用户编号。")
        if args.action == "doctor":
            result = doctor()
        elif args.action == "foreground":
            result = foreground()
        elif args.action == "screenshot":
            result = screenshot(private_path(args.output, ".png"))
        elif args.action == "packages":
            rows = packages(args.user)
            if any(p not in rows for p in args.packages):
                raise RuntimeError("所选包未安装于此用户。")
            result = {p: rows[p] for p in args.packages} if args.packages else rows
        elif args.action == "snapshot":
            path = private_path(args.output)
            data = snapshot(args.user)
            save(path, data, create=True)
            result = {"path": str(path), "packages": len(data["packages"])}
        elif args.action == "compare":
            old = json.loads(Path(args.record).expanduser().read_text())
            check_identity(old, args.user)
            result = compare(old, snapshot(args.user))
        elif args.action == "disable":
            result = disable(args.packages, args.user, private_path(args.output))
        else:
            result = restore(private_path(args.record), args.user)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 1 if args.action == "doctor" and any(not row["ok"] for row in result.values()) else 0
    except (OSError, ValueError, KeyError, TypeError, RuntimeError, subprocess.TimeoutExpired) as error:
        print(f"操作失败：{error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
