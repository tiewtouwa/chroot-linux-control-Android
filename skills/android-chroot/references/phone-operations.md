# 其他系统操作

从技能目录运行，仅选择任务需要的命令：

```sh
sh scripts/android-shell.sh --check
sh scripts/android-shell.sh -c 'dumpsys battery'
sh scripts/android-shell.sh -c 'wm size; wm density'
sh scripts/android-shell.sh -c 'am get-current-user'
sh scripts/android-shell.sh -c 'test -e "$1"' phone '/sdcard/Download/example.txt'
```

- 参数示例中 `phone` 是 `$0`，文件路径是 `$1`。先确认 Android 与 chroot 的路径映射。
- 应用状态修改和恢复见 [应用管理](package-management.md)，界面定位、点击和截图见 [界面操作](ui-operations.md)。
- 滑动、按键用 `input`，启动应用用 `am`。先查看本机帮助并核对参数；有些系统的 `input --help` 不可用，直接运行无参数 `input` 可读取帮助。不要假设 `input text` 支持中文。
- 拍照、录音、定位等通过已有接口执行，仍受 Android 权限与后台限制；不能用来测试连通性。
- 震动命令先查 `cmd vibrator_manager help`；帮助输出的退出码可能非零。吞掉错误的旧通知脚本返回 0 不代表硬件生效。
- 改网络或重启前考虑当前连接；刷机不属于普通控制任务的附带操作。
