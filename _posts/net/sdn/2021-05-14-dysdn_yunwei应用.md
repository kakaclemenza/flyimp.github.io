---
layout: post
title: xxxsdn_yunwei应用
category: net
typora-root-url: ../../..
---

### 一. xxmysdn优势

1. 软件自动控制, 自动监控
2. 实现任意两个ovs之间传输路径实时最优, 动态规避传输网络故障
3. 组建大二层网络, 支持纯私网虚机跨机房迁移



### 二. 难点问题解决

#### 1. 接入网络的主机发现

* 新接入网络的主机, 无论是迁移/新建, 都需要通过**无偿ARP报文**向网络声明其存在.
* ovs对于无法处理的arp报文, 上送控制器决策
* 控制器记录该主机所属ovs机房关系, 做出响应, 并设置更新ovs自动响应后续arp请求.

至于控制器是否需要广播该**无偿ARP报文**到其他机房, 需要后续实验验证广播代价与影响范围后决定

#### 2. BUM报文抑制

控制器对记录过的mac所属ovs机房关系, 会下发自动应答arp请求给相关ovs, 抑制报文跨机房广播.

#### 3. 跨机房包动态最优路径决策

xxmysdn的主要工作就是实现任意两个ovs之间传输路径实时最优. 如果应用在运维大二层网络, 则会面临以下新的问题:

* 每个公网网段需要部署一个ovs节点, ovs数量急剧上升, 控制器决策可能不堪重负. 假设有100个网段, 则ovs数量为 100, 隧道连接数为 100*(100+1)/ 2 = 5050
* 某个机房发出的到其他机房的报文, 目标mac地址需要按机房整合, 再通过组表匹配下一跳. 流表项会和整个网络中接入的机器数目成正比, 流表匹配性能需要测试清楚. 所幸ovs实现是十分高性能的, 有测试表明其查询复杂度不受流表项数目影响, 流表项数目则取决于内存大小

#### 4. 纯私网接入?

正常接入, 只要二层广播报文可达ovs二层网关, 即可正常跨机房

#### 4. 云代理/合作资源接入?

考虑vxlan方式接入



### 三. 流表设计

流表设计主要通过分表方式, 将不同功能的流表组织在一起, 实现增量修改. 主要包含如下两类设计:

* arp报文流表设计
* 转发路径流表设计

#### 1. arp报文流表设计



#### 2. 转发路径流表设计

大二层网络中, 为了不限制上层应用的自由度, 我们无法给二层包做任何假定, 如:

* 假定mac地址能按机房有规律的配置
* 假定vlan字段能按机房区分不同值, 或在入口ovs上标注vlan识别目标机房, 等等

所以我们唯一能判断数据包转发路径的字段只有`dl_dst`字段, 这意味着我们的流表项与整个网络中的机器数量级别相同. 我们这样设计转发路径流表, 以分离`dl_dst`字段匹配与路径转发规则, 如下

| 功能说明     | priority | match                                                        | action              |
| ------------ | -------- | ------------------------------------------------------------ | ------------------- |
| lldp包统计   | 65535    | "dl_dst": "01:80:c2:00:00:0e", "dl_type": 35020              | "OUTPUT:CONTROLLER" |
|              | 65535    | "dl_dst": "<其他机房的虚机mac>"                              | 广播到其他端口      |
|              | 65534    | "dl_dst": "ff:ff:ff:ff:ff:ff", "dl_type": 2054               | 发给LOCAL端口       |
| 支持vrrp组播 | 65535    | "in_port": "LOCAL", "dl_dst": "01:00:5E:00:00:12", "ip_proto": 112 | 发到组表0           |
|              | 65534    | "dl_dst": "01:00:5E:00:00:12", "ip_proto": 112               | 发给LOCAL端口       |
| 选路流表     | 1        | ...                                                          | ...                 |



### 四. 其他问题

#### 1. QoS限速



### 五. 方案设计

#### 方案一: vlan+mac地址 

说明: 对某个机房而言, 其发出的所有数据包将被ap修改: 使用vlan域来标识数据包来自的源机房, 目标mac通过流表发到目标机房.

sdn overlay使用gre, 额外包头为: 14+20+4 = 38Bytes

缺点: 

1. 限制了底层更改vlan的自由
2. 流表项依然巨大, 数目为: 机房数 x 整个网络主机数目

#### 方案二: 基于三层网络

说明: 按机房划分私网网段, 跨机房间传输需要通过某个机房部署的网关.

sdn overlay使用gre, 额外包头为: 14+20+4 = 38Bytes

缺点: 

1. 所有同机房的vm, 需要将私网网关指向ap节点私网ip
2. 由于不是大二层, 不支持跨机房迁移机器
3. ap点需要vrrp协议漂移ip, 保证高可用

#### 方案三: vxlan多封装一次

说明: 某个机房要发往其他机房的数据包, 首先由ap节点的fdb表+arp表进行代答arp报文. 当数据包发往ap节点, ap先从vx0接口发出vxlan封装的数据包. 数据包通过br0发出回到ovs上, 再经过gre封装发到其他ap节点.

sdn overlay使用vxlan+gre, 额外包头为: 14+20+4 + 14+20+8+8 = 88Bytes

缺点: 

1. 多了50Bytes额外包头
2. fdb表和arp表需要被控制器准实时修改.



### 方案三实现



虚机模拟网络结构如下:

```
                        宿主机充当路由器
                 +------------------------+
                 |                        |
                 +-------+        +-------+
           +-----+56.1/24|  宿主机 |57.1/24+------+
           |     +-------+        +-------+      |
           |     |                        |      |
           |     +------------------------+      |
           |                                     |
           |                                     |
   +-------+------+                      +-------+------+
   | host_only sw |                      | host_only sw |
   +---+------+---+                      +---+------+---+
       |      |                              |      |
   +---+      +----+                     +---+      +----+
   |               |                     |               |
+--+--+         +--+--+               +--+--+         +--+--+
|  A  |         |  B  |               |  C  |         |  D  |
+-----+         +-----+               +-----+         +-----+

```

这里A和B, C和D分属不同网段, 相互之间通信要经过宿主机进行路由转发. 这样可以模拟真实中的跨机房网络. 后续我们的实现就可以基于**B<->C**隧道来构建SDN网络, 使得A, B, C, D在同一大二层网络中. 然后通过**A<->D**之间互ping, 验证跨机房大二层网络的可行性.

虚拟机B, C充当二层网关, 其上ovs各端口情况如下. 

```
+--------------------+
|                    |
+------+       +-----+
| eth0 |       | br0 |
+------+       +-----+
|                    |
|              +-----+
|              | vx0 |
|              +-----+
|                    |
|              +-----+
|              | t2  |
|              +-----+
|                    |
|              +-----+
|              | t.. |
|              +-----+
|                    |
+--------------------+
```



注意点:

1. 宿主机充当路由器, 需要允许路由转发, 开启方法如:

   ```shell
   # 将 HKEY_LOCAL_MACHINE\SYSTEM\CurrentControlSet\Services\Tcpip\Parameters\IPEnableRoute设为1
   reg add HKLM\SYSTEM\CurrentControlSet\Services\Tcpip\Parameters /v IPEnableRouter /D 1 /f
   
   # 将 Routing and Remote Access 服务的启动类型更改为自动并启动服务
   sc config RemoteAccess start= auto
   sc start RemoteAccess
   ```

2. 虚拟机B, C由于需要充当二层网关, 所以它上面eth0网卡必须设置**开启混杂模式**, 使得它能接收到mac地址不是eth0网卡的数据包. 这样也会导致与eth0相连的物理交换机设备要取消限制mac->port的多对一关系, 确保能由eth0响应跨机房的arp请求.

3. 通过虚机软件vmware了解到, 对主机进行混杂模式设置, eth0会收到同虚拟交换机下目标地址是其他主机的icmp包. virtualbox对此还未找到太具体的说明, 不过这是正常现象, 因为混杂模式允许收到同网络下所有的数据包.



### 问题解决收集

#### 将eth0的ip和相关路由移动到br0

在将eth0加入br0前, 我们通常需要手动将eth0的ip和路由配置到br0上, 使得eth0加入后能立即可用. 这里记录下移动ip和路由的脚本:

```shell
# Usage: transfer_addrs src dst
# Copy all IP addresses (including aliases) from device $src to device $dst.
transfer_addrs () {
    local src=$1
    local dst=$2
    # Don't bother if $dst already has IP addresses.
    if ip addr show dev ${dst} | egrep -q '^ *inet ' ; then
        return
    fi
    # Address lines start with 'inet' and have the device in them.
    # Replace 'inet' with 'ip addr add' and change the device name $src
    # to 'dev $src'.
    ip addr show dev ${src} | egrep '^ *inet ' | sed -e "
s/inet/ip addr add/
s@\([0-9]\+\.[0-9]\+\.[0-9]\+\.[0-9]\+/[0-9]\+\)@\1@
s/${src}/dev ${dst}/
" | sh -e
    # Remove automatic routes on destination device
    ip route list | sed -ne "
/dev ${dst}\( \|$\)/ {
  s/^/ip route del /
  p
}" | sh -e
}

# Usage: transfer_routes src dst
# Get all IP routes to device $src, delete them, and
# add the same routes to device $dst.
# The original routes have to be deleted, otherwise adding them
# for $dst fails (duplicate routes).
transfer_routes () {
    local src=$1
    local dst=$2
    # List all routes and grep the ones with $src in.
    # Stick 'ip route del' on the front to delete.
    # Change $src to $dst and use 'ip route add' to add.
    ip route list | sed -ne "
/dev ${src}\( \|$\)/ {
  h
  s/^/ip route del /
  P
  g
  s/${src}/${dst}/
  s/^/ip route add /
  P
  d
}" | sh -e
}
```



### 讨论记录

#### 讨论: arp应答抢占



#### 大包dropped与mtu设置问题



#### 下一步工作：

link测速统计重构:

(1) 修改ovs内核代码, 对于lldp转发记录前后延迟, 上送控制器自动就知道延迟如何.

(2) 使用udp测速模式, 代替lldp包探测逻辑(初级探测, 精度损失大)