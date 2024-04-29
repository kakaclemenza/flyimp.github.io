---
layout: post
title: sdwan_frr构建bgp网络
category: net
typora-root-url: ../../..
---

## BGP

BGP全称是Border Gateway Protocol, 对应中文是边界网关协议。这个名字比较抽象，而维基中文的[解释](https://link.zhihu.com/?target=https%3A//zh.wikipedia.org/zh-cn/%E8%BE%B9%E7%95%8C%E7%BD%91%E5%85%B3%E5%8D%8F%E8%AE%AE)我觉得比较好（维基英文甚至都没有类似的解释）。BGP是互联网上一个*核心的去中心化自治路由协议*。从这个解释来看，首先这是一个用于互联网（Internet）上的路由协议。它的地位是核心的（目前是最重要的，互联网上唯一使用的路由协议），它的目的是去中心化，以达到各个网络自治。不过还是有点抽象？

先看看几个相关的概念：

- AS（Autonomous system）：自治系统，指在一个（有时是多个）组织管辖下的所有IP网络和路由器的全体，它们对互联网执行共同的路由策略。也就是说，对于互联网来说，一个AS是一个独立的整体网络。而BGP实现的网络自治也是指各个AS自治。每个AS有自己唯一的编号。
- IGP（Interior Gateway Protocol）：内部网关协议，在一个AS内部所使用的一种路由协议。一个AS内部也可以有多个路由器管理多个网络。各个路由器之间需要路由信息以知道子网络的可达信息。IGP就是用来管理这些路由。代表的实现有RIP和OSPF。
- EGP（Exterior Gateway Protocol）：外部网关协议，在多个AS之间使用的一种路由协议，现在已经淘汰，被BGP取而代之。

由于BGP就是为了替换EGP而创建，它的地位与EGP相似。但是BGP也可以应用在一个AS内部。因此BGP又可以分为IBGP（Interior BGP ：同一个AS之间的连接）和EBGP（Exterior BGP：不同AS之间的BGP连接）。既然EGP已经被替代了，那EBGP的存在比较好理解，但是IGP协议都还活得好好的（这里指的是OSPF），那IBGP的意义何在？IGP的协议是针对同一个AS网络来设计的，一个自治网络的规模一般都不大，所以设计的时候就没有考虑大规模网络的情况。而当一个自治网络足够大时，OSPF存在性能瓶颈（后面会说明）。BGP本身就是为了在Internet工作，其设计就是为了满足大型网络的要求，所以大型私有IP网络内部可以使用IBGP。总的来说，这几类路由协议，小规模私有网络IGP，大规模私有网络IBGP，互联网EBGP。

> BGP是互联网的骨架！

## frr构建bgp网络

我们可以使用docker-comopse直接在本地以容器方式运行整个bgp网络，这样做实验会方便很多。

复杂的网络例子：

```dockerfile
# 复杂的集群结构:
#
#             /--- pe1(10.100.0.11, 10.100.1.11) --- ce1(10.100.1.12)
#            /
#  pe2(10.100.0.12, 10.100.10.12, 10.100.2.11) ----- ce2(10.100.2.12)
#                         \
#                          \__ pe3(10.100.10.13, 10.100.3.11) --- ce3(10.100.3.12)

version: '2.2'
services:
  pe1:
    image: frrouting/frr:v8.3.0
    privileged: true
    cap_add:
      - NET_BIND_SERVICE
      - NET_RAW
      - NET_ADMIN
      - SYS_ADMIN
    volumes:
      - ./conf/repositories:/etc/apk/repositories
      - ./conf/daemons:/etc/frr/daemons
      - ./conf/vtysh.conf:/etc/frr/vtysh.conf
      - ./conf/frr_pe1.conf:/etc/frr/frr.conf
    networks:
      - pe1-ce1
      - penet12
    networks:
      pe1-ce1:
        ipv4_address: 10.100.1.11
      penet12:
        ipv4_address: 10.100.0.11
  pe2:
    image: frrouting/frr:v8.3.0
    cap_add:
      - NET_BIND_SERVICE
      - NET_RAW
      - NET_ADMIN
      - SYS_ADMIN
    volumes:
      - ./conf/repositories:/etc/apk/repositories
      - ./conf/daemons:/etc/frr/daemons
      - ./conf/vtysh.conf:/etc/frr/vtysh.conf
      - ./conf/frr_pe2.conf:/etc/frr/frr.conf
    networks:
      pe2-ce2:
        ipv4_address: 10.100.2.11
      penet12:
        ipv4_address: 10.100.0.12
      penet23:
        ipv4_address: 10.100.10.12
  pe3:
    image: frrouting/frr:v8.3.0
    cap_add:
      - NET_BIND_SERVICE
      - NET_RAW
      - NET_ADMIN
      - SYS_ADMIN
    volumes:
      - ./conf/repositories:/etc/apk/repositories
      - ./conf/daemons:/etc/frr/daemons
      - ./conf/vtysh.conf:/etc/frr/vtysh.conf
      - ./conf/frr_pe3.conf:/etc/frr/frr.conf
    networks:
      pe3-ce3:
        ipv4_address: 10.100.3.11
      penet23:
        ipv4_address: 10.100.10.13
  ce1:
    image: frrouting/frr:v8.3.0
    #command: python app.py
    cap_add:
      - NET_BIND_SERVICE
      - NET_RAW
      - NET_ADMIN
      - SYS_ADMIN
    volumes:
      - ./conf/repositories:/etc/apk/repositories
    networks:
      pe1-ce1:
        ipv4_address: 10.100.1.12
    command: sh -c '
      ip r d default
      && ip r a default via 10.100.1.11
      && /usr/lib/frr/docker-start
      '
  ce2:
    image: frrouting/frr:v8.3.0
    cap_add:
      - NET_BIND_SERVICE
      - NET_RAW
      - NET_ADMIN
      - SYS_ADMIN
    volumes:
      - ./conf/repositories:/etc/apk/repositories
    networks:
      pe2-ce2:
        ipv4_address: 10.100.2.12
    # 覆盖默认运行时的命令，将ce的默认网关改到pe
    command: sh -c '
      ip r d default
      && ip r a default via 10.100.2.11
      && /usr/lib/frr/docker-start
      '
  ce3:
    image: frrouting/frr:v8.3.0
    cap_add:
      - NET_BIND_SERVICE
      - NET_RAW
      - NET_ADMIN
      - SYS_ADMIN
    volumes:
      - ./conf/repositories:/etc/apk/repositories
    networks:
      pe3-ce3:
        ipv4_address: 10.100.3.12
    # 覆盖默认运行时的命令，将ce的默认网关改到pe
    command: sh -c '
      ip r d default
      && ip r a default via 10.100.3.11
      && /usr/lib/frr/docker-start
      '

networks:
  penet12:
    driver: bridge
    ipam:
      config:
      - subnet: 10.100.0.0/24
        gateway: 10.100.0.1
  penet23:
    driver: bridge
    ipam:
      config:
      - subnet: 10.100.10.0/24
        gateway: 10.100.10.1
  pe1-ce1:
    driver: bridge
    ipam:
      config:
      - subnet: 10.100.1.0/24
        gateway: 10.100.1.1
  pe2-ce2:
    driver: bridge
    ipam:
      config:
      - subnet: 10.100.2.0/24
        gateway: 10.100.2.1
  pe3-ce3:
    driver: bridge
    ipam:
      config:
      - subnet: 10.100.3.0/24
        gateway: 10.100.3.1
```

bgp网络状态定位与问题排查：

```shell
#vtysh控制台
# show ip route 输出；可以看到`B`开头的是bgp协议添加的路由项；如果没有可能有异常
...
K>* 0.0.0.0/0 [0/0] via 10.100.1.1, eth0, 00:00:40
C>* 10.100.0.0/24 is directly connected, eth1, 00:00:40
C>* 10.100.1.0/24 is directly connected, eth0, 00:00:40
B>* 10.100.2.0/24 [20/0] via 10.100.0.12, eth1, weight 1, 00:00:36
B>* 10.100.3.0/24 [20/0] via 10.100.0.12, eth1, weight 1, 00:00:36
B>* 10.100.10.0/24 [20/0] via 10.100.0.12, eth1, weight 1, 00:00:36

# show ip bgp summary 输出；
# 如果`State/PfxRcd`一栏为“Active”状态，说明建立bgp协议的tcp连接失败，可能是因为没有设置默认路由或网关，或端口被关闭；
# 如果`State/PfxRcd`一栏为“(Policy)”状态，需要指定ebgp policy，或设置`no bgp ebgp-requires-policy`
# 以下是一个成功的示例：
...
Neighbor        V         AS   MsgRcvd   MsgSent   TblVer  InQ OutQ  Up/Down State/PfxRcd   PfxSnt Desc
10.100.0.12     4       1002         7         7        0    0    0 00:01:20            4        5 N/A
...

# show ip bgp 输出最终bgp协议确定的路由项；
...
   Network          Next Hop            Metric LocPrf Weight Path
*  10.100.0.0/24    10.100.0.12              0             0 1002 i
*>                  0.0.0.0                  0         32768 i
*> 10.100.1.0/24    0.0.0.0                  0         32768 i
*> 10.100.2.0/24    10.100.0.12              0             0 1002 i
*> 10.100.3.0/24    10.100.0.12                            0 1002 1003 i
*> 10.100.10.0/24   10.100.0.12              0             0 1002 i
...
```

热重启更新，重启

```shell
# 热重启更新
/usr/lib/frr/frr reload

# 重启
/usr/lib/frr/frr restart
# 部分服务重启
pkill -x bgpd
/usr/lib/frr/bgpd -d -F traditional -A 127.0.0.1 --log file:/var/log/frr/bgpd.log
```

frr配置文件说明：https://docs.nvidia.com/networking-ethernet-software/cumulus-linux-41/Layer-3/Border-Gateway-Protocol-BGP/Basic-BGP-Configuration/

数据中心架构模拟：https://docs.nvidia.com/networking-ethernet-software/cumulus-linux-41/Layer-3/Border-Gateway-Protocol-BGP/Configuration-Example/