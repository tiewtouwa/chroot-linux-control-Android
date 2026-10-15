# 操作示例

从技能目录运行，仅选择任务需要的命令：

```sh
sh scripts/android-shell.sh -c 'dumpsys battery'
sh scripts/android-shell.sh -c 'wm size; wm density'
sh scripts/android-shell.sh -c 'am get-current-user'
sh scripts/android-shell.sh -c 'test -e "$1"' phone '/sdcard/Download/example.txt'
python3 scripts/ui-controls.py --text '设置' --json
```

- 参数示例中 `phone` 是 `$0`，文件路径是 `$1`。先确认 Android 与 chroot 的路径映射。
- `ui-controls.py` 调用 `uiautomator dump`，输出文字与中心坐标；不传筛选参数则列出全部有标签控件。数据临时存于 `/data/local/tmp`，读取后删除；密码控件不输出。游戏或自绘界面可能无控件信息。
- 按需用 `screencap -p` 截图，输出到未占用文件并检查图片；受保护页面可能黑屏。
- 点击/滑动用 `input`，应用操作用 `am` 或 `cmd package`。先查设备帮助，核对页面、包名和 Android 用户；不要假设 `input text` 支持中文。
- 拍照、录音、定位等通过已有接口执行，仍受 Android 权限与后台限制；不能用来测试连通性。
- 震动命令先查 `cmd vibrator_manager` 帮助；吞掉错误的脚本返回 0 不代表硬件生效。
- 改网络或重启前考虑当前连接；刷机不属于普通控制任务的附带操作。
