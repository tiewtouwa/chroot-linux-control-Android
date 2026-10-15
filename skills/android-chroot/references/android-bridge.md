# 连接排障

- 自检失败先看原始错误，确认当前确实在目标手机的 chroot 内。
- 文件存在却无法执行：检查 Android linker、`/apex`、`/vendor` 等挂载。Android Bionic 与 Linux glibc 不能混用；包装脚本只在子进程清理动态库变量。
- shell 可用而服务失败：检查 Binder、UID、SELinux 和目标服务权限。不自动改挂载、关闭 SELinux 或递归 chmod。
- chroot 的 `/usr/bin/su` 不一定是 Android 的 Magisk/KernelSU `su`，先确认实现。
- Termux:API 需要兼容安装的应用、命令行包及 Android 权限。优先复用已有 Termux 通路；root 直接运行 `termux-*` 可能因 UID、广播或套接字限制失败。
- 只有当前通路不可用或用户指定时才用已有 ADB 连接。多设备须指定 `adb -s SERIAL`；`unauthorized` 需要设备侧授权。

接口说明：[Termux:API](https://github.com/termux/termux-api)。
