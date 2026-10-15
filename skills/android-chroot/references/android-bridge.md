# 连接与排障

## 本机 root/chroot

在 chroot 内看见 `/system` 不保证能执行其二进制：Android 使用 Bionic/linker，Linux 发行版通常使用 glibc，还可能缺少 `/apex`、`/vendor`、Binder、属性服务或合适的 SELinux 上下文。

先检查已有环境，不重新搭建或递归挂载整个 Android 文件系统：

```sh
uname -m
id
rg '^(Uid|Gid|CapEff|NoNewPrivs):' /proc/self/status
ls -l /system/bin/sh /system/bin/cmd /system/bin/getprop
sh scripts/android-shell.sh --check
```

文件存在却提示不存在时检查解释器/动态链接器和挂载；`Permission denied` 时检查执行权限和 SELinux；shell 成功而服务失败时检查 Binder/服务可见性、UID 和具体权限。优先复用用户已有、验证过的宿主执行入口。

不要假定 chroot 的 `/usr/bin/su` 是 Magisk/KernelSU 的 Android `su`；不要对未知实现套用参数。不要默认用 `nsenter`、`/proc/1/root` 或新挂载改变运行边界。只有任务要求修复 chroot 且目标已确认时才修改配置。

## Termux:API

常见位置是 `/data/data/com.termux/files/usr/bin`，应在当前环境检查。需要兼容来源/签名的 Termux 与 Termux:API 应用、Termux 中的 `termux-api` 软件包及相应运行时权限。参见 [Termux:API](https://github.com/termux/termux-api) 和 [命令行脚本](https://github.com/termux/termux-api-package)。

从 chroot 以 root 执行 Termux 脚本可能遭遇库、应用 UID、广播或套接字限制。通过已有 Termux shell/桥接执行，先验证非敏感查询如 `termux-battery-status`。不全局修改 PATH 或 LD_LIBRARY_PATH 来同时适配两套运行库，不为测试调用定位、录音或相机。

## 已有 ADB 连接

用 `adb devices -l` 确认在线设备；多个目标且无法从上下文确定时询问用户。后续均用 `adb -s SERIAL`。`unauthorized` 需要设备侧授权，不能声称已连接。无线配对使用用户给出的目标与配对流程，不扫描网络猜测设备。

ADB 的远端 shell 存在第二次解析，不能假设本地引用已足够。优先用脚本和文件传输减少多层插值；不把敏感文本放入日志或仓库。
