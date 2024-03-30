---
layout: post
title: nymph中的网络arp_ip
category: flyos
tag: nymph
---

### nymph arp包测试正确做法

1. 虚拟机配置
   nymph 支持 arp 包解析之后, 需要构建测试环境对 nymph 发包. 虚拟机选择qemu, 参考命令如:
   
   ```
   qemu-system-x86_64  -serial file:kernel.log -netdev tap,helper=/usr/lib/qemu/qemu-bridge-helper,id=mynet0 -device rtl8139,netdev=mynet0,id=inet0 -vga std -hda /home/xiaofeng/hdd.img &
   ```
   
   其中 -netdev 选项就是利用 `qemu-bridge-helper` 工具, 利用本地桥接网卡接口 br0 创建给虚拟机使用的虚拟网卡接口 tap0. 这需要本地主机事先配置好 br0 接口. 

2. br0接口配置
   首先利用 `bridge-utils` 工具创建 br0 网卡接口:
   
   ```
   sudo apt install bridge-utils
   ```

sudo brctl addbr br0

```
配置 /etc/network/interfaces 增加如下配置:
```

auto br0
iface br0 inet static
    address 192.168.140.111
    broadcast 192.168.140.255
    netmask 255.255.255.0
    gateway 192.168.140.1
    bridge_ports tap0

```
最后重启网络管理设备, 是网卡配置生效
```

sudo systemctl restart networking.service
或
sudo systemctl restart network-manager

# 查看配置是否正确生效

ip a s

```
3. 向 tap0 接口发送 arp 包
配置完 br0, 启动 nymph 后, 就可以看到虚拟机自动在主机上创建了一个 tap0 网卡接口并桥接到 br0 接口上, 此时从 br0 网卡**广播** arp 数据包的话, 虚拟机 tap0 接口就应该能收到 arp 数据包了:
```

# 安装arp发包工具

sudo apt-get install arping

# 通过br0网卡广播arp包

arping -B -i br0

```
### traceroute原理

首先发送ttl=1的报文

路由不可达icmp报文 ---> 到达中间路由器, ttl需加一以到达下一跳

端口不可达icmp报文 ---> 到达目标主机



### ICMP回复包与ping回复包

**ICMP**

编码参见https://wiki.osdev.org/ICMP. 正确的ICMP请求包type=8, code=0; 正确的ICMP回复包type=0, code=0. 对于Payload没有要求

**ping**

ping是基于ICMP协议, 利用了payload字段. 如果ping包请求和回复包ICMP头部各个字段正确, 但是payload字段错误, 则ping命令会显示**"truncated"**. payload可能为32字节或56字节不等. ping回复包只要填入相同的payload即可. 参见: [wikipedia](https://en.wikipedia.org/wiki/Ping_(networking_utility))
```
