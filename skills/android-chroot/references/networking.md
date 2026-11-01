# 网卡、地址与网络共享

适用于 USB 网卡、静态 IP、路由、DNS、USB／Wi-Fi／蓝牙共享，以及 NAT。扫描、SSH、文件传输、抓包见 [远程与网络工具](remote-access.md)。

从技能目录调用 Android 命令，可在当前 shell 定义：

```sh
android() { sh scripts/android-shell.sh -c 'exec "$@"' android "$@"; }
```

以下 `$IFACE`、`$CIDR`、`$GATEWAY` 等均来自本次设备检测和用户目标，不把示例值直接套在手机上。`ip` 等 Linux 工具与宿主机共享网络时，操作会直接影响手机连接。

## 1. 网卡与权限探测

- 查 `ip -j address show`、`ip -j link show`、`ip -j rule show`、`ip -j route show table all`；精简输出接口、地址、状态和相关路由，不输出完整硬件标识。
- USB 接入前后比较接口列表。不要固定假设叫 `eth0`、`usb0`、`rndis0` 或 `ncm0`。
- 查 `/sys/class/net/$IFACE/{operstate,carrier}`、`statistics/{rx_packets,tx_packets,rx_bytes,tx_bytes}`；有接口或设置了 `UP` 不等于有载波。
- `ethtool -i "$IFACE"` 查已绑定驱动，`ethtool "$IFACE"` 查链路。驱动目录里有 RTL8152/8153、ASIX 或 CDC 驱动不等于已接入的具体网卡可用。
- USB 角色区分：手机接 USB 网卡时是主机；手机把自己作为 USB 网卡共享给电脑时是外设。OTG、线材、供电和对端驱动需分别确认。
- UID 0 之外，还要确认本进程的 `CAP_NET_ADMIN`／`CAP_NET_RAW` 和实际命令权限。不要通过创建虚拟接口或修改规则来测试权限。

## 2. IP、掩码和 DHCP

先保存目标接口的地址、路由、规则及当前会话使用的路径到仓库外。只改用户指定的接口和地址。

```sh
ip address show dev "$IFACE"
ip address add "$CIDR" dev "$IFACE"
ip address del "$CIDR" dev "$IFACE"
```

- `add`／`del` 是操作模板，不连着执行；改地址通常先添加新地址、验证对端和回程，再按请求删除旧地址。不要 `ip addr flush`。
- Android 管理的 Wi-Fi／以太网优先用本机设置界面配置静态地址或 DHCP；直接用 `ip` 通常只改运行态，重新连接或系统网络服务可能覆盖。
- 不在已有 Android DHCP 管理的接口上额外启动 `dhclient`／DHCP 服务。需要手动 DHCP 时先确认当前管理者和工具是否存在。
- 验证新地址、连通性和返回路径，不能只看命令退出码；回滚只撤销本次添加项并恢复本次删除项。

## 3. 路由、DNS与代理

```sh
ip route get "$TARGET_IP"
ip rule show
ip route show table all
```

- Android 使用多张路由表、UID／fwmark 规则及可能存在的 VPN。主表没有默认路由不能直接判定手机没网；chroot 流量与 Android 应用／共享客户端的路径也可能不同。
- 修改前确定路由表、源地址、目标网段和出口。使用针对目标的 `ip route add/del ... table "$TABLE"`，不覆盖所有默认路由或清空规则。
- chroot 的 `/etc/resolv.conf` 与 Android 网络 DNS 是两套配置。先用 IP 连通性和 `getent ahosts "$HOSTNAME"` 区分路由与名称解析；Android 端通过本机 Wi-Fi／私人 DNS 设置处理，不能用修改 Linux resolv.conf 代替。
- `curl --connect-timeout 5 --max-time 15 --head "$URL"` 可验证指定 HTTP(S) 目标。代理只对明确指定的命令／应用配置，不假设系统代理覆盖全部协议。

## 4. USB 共享：手机向电脑或平板供网

按顺序验证，避免把开关状态当作联网成功：

1. `android svc usb getFunctions`；结合 `android dumpsys usb` 中当前 connected、configured、functions 字段确认 USB 枚举。部分命令把正常结果写到 stderr，要结合退出码与文本解释。
2. `android dumpsys tethering` 确认下游接口是 `TetheredState`、`lastError=0`，并识别实际上游。
3. 查下游地址、carrier、收发计数、`ip -4 neigh show dev "$IFACE"` 和 DHCP 客户端记录。输出省略 MAC、客户端标识和无关历史日志。
4. 对已识别的对端地址做有限次数 `ping -I "$IFACE" -c 3 -W 2 "$PEER_IP"`。不响应 ICMP 不等于无法联网；结合邻居、DHCP 和流量计数判断。
5. 由对端访问一个指定目标，再检查其 DNS、回程和共享流量；没有对端结果时明确只验证到了哪一层。

开启／关闭共享优先通过已观察到的系统“USB 网络共享”设置。`svc usb setFunctions rndis`／`ncm` 仅设置 USB 功能，不能单独建立 DHCP、DNS、转发和 NAT，不能替代共享服务。修改 USB functions 也可能中断 ADB；只在目标功能受支持且用户要求改变时操作。

USB 已 configured 而网络 carrier=0、收发包为零时，先排查对端主机角色、RNDIS／NCM 驱动和线材；不要反复换 IP 或 NAT 规则。安卓对端是否支持取决于其内核与 ROM，不能一概判断。

## 5. USB 反向供网：电脑向手机供网

先确定采用哪条路径：手机作为主机接 USB 网卡，或电脑作为主机通过 USB 网络接口为手机路由。后一种需要电脑端配置共享／路由，不能仅在手机上打开“USB 网络共享”。

- 获取两端接口与地址，确认电脑有可用上游，并有操作该电脑的通路。
- 按所选系统的共享方式配置电脑的地址分配、转发与 NAT；手机端核对目标路由和 DNS。Android 应用可能还需要网络服务识别该链路，Linux root 的 `curl` 成功不等于所有应用成功。
- 没有对端权限或兼容 USB 网络接口时，报告缺少的条件，不自动安装 VPN／ADB 桥接服务。

## 6. Wi-Fi 连接与热点

先读 `android cmd wifi help`。按需查看状态、已有网络、扫描结果；输出隐藏 SSID、BSSID 和凭据中与任务无关的部分。

- Wi-Fi 开关：本机帮助支持时使用 `android cmd wifi set-wifi-enabled enabled`／`disabled`。
- 连接网络：使用本机 `connect-network` 参数；密码不能写入仓库、命令日志或最终答复。优先复用已保存的网络或系统设置界面。
- Wi-Fi 热点：通过系统共享设置确认名称、认证、频段与上游，再启停并核对客户端。`start-softap` 可能只建立 AP；AP 启动不能单独证明 Internet 共享已建立。
- 扫描、连接、热点切换会影响当前连接，先确认当前会话路径；不把断网操作当作自检。

## 7. 蓝牙共享、NFC／定位／飞行模式开关

查本机 `cmd bluetooth_manager help`、`cmd nfc help`、`cmd location help`、`cmd connectivity help`。

- 蓝牙开关与蓝牙 PAN 网络共享是两回事；PAN 配对和共享走系统设置，核对对端以及是否生成网络接口。
- NFC／定位／飞行模式只修改用户指定项，记录旧值，读取结果。开启定位开关不等于获取了位置。
- 不自动打开调试模式或授予通知监听、辅助功能等权限作为捷径。

## 8. 防火墙、NAT 和转发

优先通过原生 Android 命令只读检查：

```sh
android iptables -S
android iptables -t nat -S
android ip6tables -S
android cat /proc/sys/net/ipv4/ip_forward
```

chroot 的 `iptables` 可能默认使用内核不支持的 nft 后端，legacy 也可能缺少 Android 的 `quota2` 等扩展。此时先尝试原生命令，不全局修改 alternatives，不以 `nft flush ruleset` 或 `iptables -F` 排障。

用户需要自定义转发／NAT 时，先确定源网段、入／出口、协议、端口、上游和返回路径。仅添加能明确定位和撤销的本次规则；避免重复添加，不改系统已有的 tethering、VPN、计费链。修改转发值前保存原值；回滚时确认没有其他共享服务正在依赖它。IPv4 NAT 不代表 IPv6 已处理。

验证规则命中计数、客户端双向通信和 DNS；只读查询成功仅证明可查看规则，不证明修改权限或共享结果。
