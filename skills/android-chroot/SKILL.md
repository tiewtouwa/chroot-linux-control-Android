---
name: android-chroot
description: 在真实 root 的 Android chroot 中控制手机、读取屏幕截图、调用系统命令和 Termux API、排查权限问题。不用于 proot 安装。
---

# Android chroot

用中文简短回复，复用现有 chroot，只执行用户要求的操作。

在技能目录执行：

```sh
sh scripts/android-shell.sh --check
sh scripts/android-shell.sh -c 'dumpsys battery'
```

- 首次连接先自检；Linux UID 0 不等于全部 Android 权限。
- 已保存的屏幕截图位于 `/sdcard/Pictures/Screenshots`；读取最新截图时按修改时间选择，并查看图片。旧截图不代表实时屏幕，图片不复制到仓库。
- 优先用现有 Android shell；Termux API 和 ADB 按需使用，不自动开放远程服务。
- 参数通过位置参数传递，不拼进 shell 源码。操作前核对设备、应用用户和路径，操作后验证结果。
- UI 操作先观察页面，逐步执行。修改设置记录旧值；不为排障关闭 SELinux 或扩大权限。
- 手机数据与凭据不进仓库；未验证的结果不声称成功。

按需阅读：[连接排障](references/android-bridge.md) · [操作示例](references/phone-operations.md)。
