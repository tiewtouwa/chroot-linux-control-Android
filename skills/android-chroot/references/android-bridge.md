# 连接排障

- 自检失败先看原始错误，确认当前确实在目标手机的 chroot 内。
- 文件存在却无法执行：检查 Android linker、`/apex`、`/vendor` 等挂载。Android Bionic 与 Linux glibc 不能混用；包装脚本只在子进程清理动态库变量。
- shell 可用而服务失败：检查 Binder、UID、SELinux 和目标服务权限。不自动改挂载、关闭 SELinux 或递归 chmod。
- chroot 的 `/usr/bin/su` 不一定是 Android 的 Magisk/KernelSU `su`，先确认实现。
- Termux:API 需要兼容安装的应用、命令行包及 Android 权限。先检查命令和应用，再用有限超时的电池查询测试现有通路；root 直接运行 `termux-*` 可能因 UID、广播或套接字限制失败，但不要预先判定一定不可用。调用 Android／Termux 程序前在子进程清理 Linux 动态库变量，不修改整个会话环境。
- Termux 文件路径须同时能被 API 应用访问；chroot 可写的 `/root` 目录不一定对应用可见。超时或空输出保留原始错误，先核对操作是否已经执行，不盲目重试。
- 网络命令可用不代表已连通：USB 要区分枚举、网卡 carrier、DHCP、对端和上游；具体顺序见 [网络配置](networking.md)。Android 的策略路由不能只看 main 表。
- chroot 的 nft 后端可能不兼容内核，legacy 可能缺 Android 扩展；先用 Android 原生 iptables 只读检查，不清空规则或全局替换后端。SSH、扫描与抓包依赖见 [远程与网络工具](remote-access.md)。
- 只有当前通路不可用或用户指定时才用已有 ADB 连接。多设备须指定 `adb -s SERIAL`；`unauthorized` 需要设备侧授权。

接口说明：[Termux:API](https://github.com/termux/termux-api)。
