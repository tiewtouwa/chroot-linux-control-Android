# 手机操作

以下相对路径从技能目录运行。只执行用户任务需要的命令，这些例子不是批量执行清单。先用 `--check` 确认通路，再按需查看目标命令帮助。

## 只读查询

```sh
sh scripts/android-shell.sh -c 'cmd -l'
sh scripts/android-shell.sh -c 'dumpsys battery'
sh scripts/android-shell.sh -c 'wm size; wm density'
sh scripts/android-shell.sh -c 'am get-current-user'
sh scripts/android-shell.sh -c 'cmd package help'
```

仅输出任务相关结果，不为检测接口运行完整 getprop、全量应用数据转储或截图。

## 传参与路径

把变量作为 shell 位置参数传入，避免嵌入 `-c` 源码：

```sh
sh scripts/android-shell.sh -c 'test -e "$1"' android-phone '/sdcard/Download/example.txt'
```

`android-phone` 是 `$0`，后续参数从 `$1` 开始。文件名带空格或 shell 特殊字符时仍保持双引号。Android 服务与 chroot 看到的路径可能不同，先验证映射。

## 屏幕和应用

用户要求截图时可将 PNG 通过 stdout 写入 chroot 的任务目录：

```sh
sh scripts/android-shell.sh -c 'screencap -p' > /tmp/android-screen.png
```

检查命令退出码和图片有效性后再交付；避免覆盖已有文件。受保护页面可能黑屏，不能声称截图包含其内容。截图不提交到技能仓库。

点击、滑动、按键用系统 `input`，先看帮助并依据当前截图坐标执行。系统 `am`/`cmd package` 可启动或查询应用；先确认真实包名、启动组件和 Android 用户，不猜包名后直接启动、停用或卸载。

应用冻结/解冻与设置更改先记录原状态，核对具体 user 后操作并重新查询。主用户、工作资料和分身中的同名应用是不同操作对象。

## 硬件和通知

已有 Termux 通路可调用电量、音量、亮度、震动、传感器等接口，先检查帮助与返回值。录音、拍照、位置等仍依赖应用权限和前后台限制，真实 root 不代表任意状态下都能成功。

Android 的 `cmd vibrator_manager`、音频和显示服务参数随版本变化，先查该设备帮助。现有脚本若吞掉错误或总返回 0，不能以其退出码证明硬件生效。

## 网络和系统

使用现有 Android 工具核对网络状态。启停网络、改路由、防火墙或重启可能切断会话，执行前确认任务要求、目标和恢复通路。不把桌面 Linux 的 systemctl、NetworkManager 或 iptables 用法直接当作 Android 管理方式。

刷机、boot 分区、bootloader、内核模块和系统分区写入需要专门的设备与版本核对，不作为普通手机控制的附带步骤。
