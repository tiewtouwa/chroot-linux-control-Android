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
- USB 网卡、地址、共享与 NAT 见 [网络配置](networking.md)；扫描、SSH、传输和抓包见 [远程与网络工具](remote-access.md)；硬件、通信与自动化见 [系统接口](device-interfaces.md)。
- 应用状态修改和恢复见 [应用管理](package-management.md)，界面定位、点击和截图见 [界面操作](ui-operations.md)。
- 滑动、按键用 `input`，启动应用用 `am`。先查看本机帮助并核对参数；有些系统的 `input --help` 不可用，直接运行无参数 `input` 可读取帮助。不要假设 `input text` 支持中文。
- 拍照、录音、定位等通过已有接口执行，仍受 Android 权限与后台限制；不能用来测试连通性。
- 震动命令先查 `cmd vibrator_manager help`；帮助输出的退出码可能非零。吞掉错误的旧通知脚本返回 0 不代表硬件生效。
- 改网络或重启前考虑当前连接；刷机不属于普通控制任务的附带操作。

## 进程查询

Android 应用进程用原生 `ps`、`pidof` 和 `top` 查询；chroot 内启动的 Linux 程序用 Debian 的 `ps`、`pgrep` 和 `top`。两者可能看到相同 PID，命令与列名却不同。包已安装、已启用不代表进程正在运行。

```sh
sh scripts/android-shell.sh -c 'ps -A -o PID,PPID,USER,STAT,RSS,NAME'
sh scripts/android-shell.sh -c 'pidof "$1"' phone com.example.app
sh scripts/android-shell.sh -c 'top -b -n 1 -m 10'
sh scripts/android-shell.sh -c 'cat "/proc/$1/status"' phone 12345
```

按本机查询得到的 PID 读取 `/proc`，不要复用旧 PID；进程可能退出或 PID 被重用。查询特定应用时留意 `:service` 等独立进程。`top` 使用单次采样，报告 CPU／内存时说明这是快照；仅在需要趋势时限定采样次数和间隔。输出只保留任务所需进程与字段，避免披露其他应用的命令行参数。
