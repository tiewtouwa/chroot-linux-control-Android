# chroot-linux-control-Android

让 Codex 在已 root 的 Android chroot Linux 中操作手机，支持系统命令、应用与屏幕操作，以及 Termux:API 接口。proot 仅作说明。

## 使用

将 `skills/android-chroot` 复制到 `~/.agents/skills/`，然后在 Codex 中输入：

```text
$android-chroot 读取手机电池状态
```

需要现有 root/chroot 环境及可用的 Android 接口，技能本身不会授予权限。

## 手机震动

- `sh scripts/vibrate.sh 500`：震动 500 毫秒；也可用于完成通知，Codex 通知会经过 `codex_notify_filter.py` 过滤子任务。
- `scripts/agy_vibrate_on_stop.sh`：agy 的 Stop hook，结束时震动。

脚本依赖 Android 的 `cmd vibrator_manager` 和相应权限。

提交前阅读 [隐私与提交规则](AGENTS.md)。许可证：[MIT](LICENSE)。
