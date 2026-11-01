# 扫描、SSH、传输和网络诊断

使用 chroot 中的 Linux 工具；USB 共享、IP、路由和防火墙见 [网络配置](networking.md)。下面变量必须来自用户指定目标和本次网络检测。示例中的操作只在对应任务已授权时执行。

## 工具发现与依赖

```sh
command -v ip ss nmap ssh scp sftp sshd rsync curl wget tcpdump ethtool ping traceroute mtr iperf3 socat nc tailscale wg
```

不要假设之前安装过的工具在另一手机也存在。缺少 nmap、iperf3 等时先说明缺项；用户要求使用该功能时，按当前发行版包管理方式安装必要依赖。仅盘点或编写技能不安装软件、不启动服务。

## 主机发现和端口扫描

先明确单个地址或已授权网段，从 USB DHCP／邻居或用户输入取得目标，不自动扩大到 Wi-Fi、VPN、全部私网或公网。

```sh
ip -4 neigh show dev "$IFACE"
nmap -sn -e "$IFACE" "$AUTHORIZED_CIDR"
nmap -sT -Pn -p "$PORTS" "$TARGET_IP"
```

- `-sn` 做主机发现；`-sT` 做 TCP 连接扫描。`-Pn` 仅用于已明确的目标，不据此把无回应主机判作在线。
- 默认有限目标和端口；仅在用户需要服务识别时用 `-sV`。不要自动追加 `-A`、全端口、漏洞脚本、密码尝试或高并发扫描。
- 找 SSH 可先查指定目标的 22／8022 或用户给定端口；没有开放端口不能靠反复扫描建立 SSH 服务。
- 报告 open、closed、filtered 和无响应的区别，不把发现一个 IP 当作确认设备身份。

## SSH 登录电脑

`PORT` 使用用户指定的 SSH 服务端口；未指定时先从 `ssh -G "$SSH_TARGET"` 读取配置中的端口。登录、隧道和传输使用同一个值。

```sh
ssh -G -p "$PORT" "$SSH_TARGET"
ssh -o ConnectTimeout=5 -p "$PORT" "$SSH_TARGET" 'uname -s; id'
```

`SSH_TARGET` 是确认过的 `user@host` 或已有 SSH alias。复用现有 config、agent、密钥和 known_hosts；不输出私钥或密码。先核对 `ssh -G` 的主机、端口、用户及身份文件，输出不要带无关代理凭据。

已知主机密钥改变时核对原因，不删除记录或关闭主机校验。首次连接需要核对可信指纹；不要把 `StrictHostKeyChecking=no` 当作默认。无凭据或对端未开 SSH 时只说明缺项，不猜账号和密码。连接测试只运行已授权的只读命令。

远端命令会经过远端 shell；不能把文件名或用户输入拼入命令字符串。复杂远端脚本用明确的脚本文件或固定代码加经过正确编码的参数，避免多层引号失效。

## 手机提供 SSH 服务

先查 `ss -ltnp`、已有 sshd 进程及配置，不重复启动服务器。用户要求开放服务时，确认监听地址、端口和认证方式，复用已有主机密钥。

```sh
SSHD_BIN=$(command -v sshd) &&
SSHD_BIN=$(realpath "$SSHD_BIN") &&
"$SSHD_BIN" -t -f "$CONFIG" &&
"$SSHD_BIN" -D -e -f "$CONFIG"
```

`sshd` 必须用绝对路径启动；先定位并规范化路径，配置检查成功后才启动实例。

配置放仓库外；监听目标 USB／局域网地址，使用用户已有公钥认证。不要默认为所有接口开放 root 密码登录，也不顺带设置开机启动。长期运行需使用本机实际存在的服务管理方式并保留停止方法；没有 systemd 时不要假定 `systemctl` 能用。

验证配置、监听地址、进程和对端连接。退出时只停止本次启动的实例，不杀所有 sshd 或关闭当前唯一管理通路。

## 文件传输与目录同步

- `sftp -P "$PORT" "$SSH_TARGET"`：交互上传、下载，适合路径包含特殊字符时使用。
- `scp -P "$PORT" ...`：复制明确源和目标；核对远端路径处理和客户端版本，不插入 shell 源码。
- `rsync -an ...`：先预览需要同步的变化，确认方向后再去掉 `n`。`--delete` 仅用于明确要求镜像删除的任务。
- 复制后核对文件大小，必要时校验哈希。不要把手机数据、录音、照片或密钥传入代码仓库。

## SSH 隧道与 SOCKS 代理

```sh
ssh -N -p "$PORT" -o ExitOnForwardFailure=yes -L "127.0.0.1:$LOCAL_PORT:$DEST_HOST:$DEST_PORT" "$SSH_TARGET"
ssh -N -p "$PORT" -o ExitOnForwardFailure=yes -R "127.0.0.1:$REMOTE_PORT:$DEST_HOST:$DEST_PORT" "$SSH_TARGET"
ssh -N -p "$PORT" -o ExitOnForwardFailure=yes -D "127.0.0.1:$LOCAL_PORT" "$SSH_TARGET"
```

先核对两端端口是否占用。`-L` 的目标从远端访问，`-R` 的目标从手机端访问；`-D` 是本地 SOCKS。端口监听成功不等于目的服务可达，要测试实际目标请求。只绑定任务需要的地址，不自动使用 `-g`、`0.0.0.0` 或修改远端 GatewayPorts。记录本次进程以便停止。

`socat`／`nc` 也可用于明确的 TCP/UDP 测试或转发；先确认已安装，不用它们默认开放任意监听。Tailscale／WireGuard 属于额外 VPN 部署，需要相应客户端、配置和用户目标；不能因 SSH 失败就自动改现有 VPN。

## 连通性、DNS、速度与网卡状态

```sh
ping -c 3 -W 2 "$TARGET_IP"
ip route get "$TARGET_IP"
getent ahosts "$HOSTNAME"
curl --connect-timeout 5 --max-time 15 --head "$URL"
traceroute "$TARGET_IP"
mtr --report --report-cycles 5 "$TARGET_IP"
ethtool "$IFACE"
```

- ICMP 被过滤时结合 TCP／HTTP 结果判断，不直接宣称断网。网卡协商速率不等于实际吞吐。
- `iperf3 -c "$PEER_IP" -t 10` 要求指定对端已运行 iperf3 服务；反向测试按需加 `-R`。不要向任意公网主机测速或擅自启服务。
- 结果注明出口、目标、方向和测量窗口，不把手机自身成功访问当作共享客户端也能访问。

## 抓包

先确认目标接口、协议／主机过滤条件和停止条件：

```sh
# FILTER 是单个参数，例如只针对已确认对端的协议；不要用 eval 展开。
tcpdump -i "$IFACE" -nn -c 50 "$FILTER"
```

优先只输出必要包头和计数；保存时使用仓库外的唯一文件，限制抓包时间、数量和文件大小，避免无限运行。需要 tshark 解析时再检查依赖。不要默认抓取所有接口、应用正文或解密内容；捕获文件可能包含凭据，按手机数据处理。后台捕获必须记录进程，结束后确认停止。
