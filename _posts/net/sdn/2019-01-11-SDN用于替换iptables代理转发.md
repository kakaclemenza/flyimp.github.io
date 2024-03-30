---
layout: post
title: SDN用于替换iptables代理转发
category: net
tag: sdn
---

ref:

- [multipath](https://github.com/wildan2711/multipath)
- [Hedera](https://github.com/Huangmachi/Hedera)



### 实验环境说明

关键组件
* SDN控制器: opendaylight karaf-0.6.4
* 南向接口: OpenFlow
* 虚拟机: docker
* 虚拟网络: mininet

环境搭建说明:
待总结

```
feature:install odl-restconf odl-dluxapps-applications odl-l2switch-switch-ui odl-mdsal-apidocs odl-l2switch-switch
```
安装支持REST API的组件：feature：install odl-restconf
安装L2 switch和OpenFlow插件：feature:install odl-l2switch-switch-ui，feature：install odl-openflowplugin-flow- services-ui
安装基于karaf控制台的md-sal控制器功能，包括nodes、yang UI、Topology：feature：install odl-mdsal-all

安装DLUX功能：feature：install odl-dluxapps-applications

安装完成后，可以使用feature：list -i，来查看已安装功能

卸载已安装功能，必须关闭opendaylight，删除对应的数据目录，然后重启opendaylight


ref：https://blog.csdn.net/weixin_40610952/article/details/80378784


### mininet与流表操作
##### 确认实验环境正确
启动mininet, 连接到opendaylight控制器(opendaylight控制器可以做成集群, 这里目前只有单台). 
```
sudo mn --custom ./topo-2sw_2host.py --topo mytopo --controller=remote,ip=172.17.0.2,port=6633 --switch=ovsk,protocols=OpenFlow13
```
网络拓补使用如下脚本构建网络:
```
#Mininet OpenDayLight 2016/9/20 by Wasdns

"""Custom topology example
Two directly connected switches plus two hosts for each switch:
   host1 --- switch1 --- switch2 --- host3
               |            |
               |            |
             host2        host4
"""
from mininet.topo import Topo
 
class MyTopo( Topo ):
    "Simple topology example."
 
    def __init__( self ):
        "Create custom topo."
 
        # Initialize topology 
        Topo.__init__( self )
         
        # Add hosts and switches
        Host1 = self.addHost( 'h1' )
        Host2 = self.addHost( 'h2' )
        Host3 = self.addHost( 'h3' )
        Host4 = self.addHost( 'h4' )
        Switch1 = self.addSwitch( 's1' )
        Switch2 = self.addSwitch( 's2' )
    
        # Add links
        self.addLink( Host1, Switch1 )
        self.addLink( Host2, Switch1 )
        self.addLink( Switch2, Host3 )
        self.addLink( Switch2, Host4 )
        self.addLink( Switch1, Switch2 )
 
topos = { 'mytopo': ( lambda: MyTopo() ) }
```
测试环境可用
```shell
mininet> pingall
mininet> net
mininet> dump
mininet> h1 ping h2
mininet> h1 ifconfig
```
根据不同版本odl的差异, 如果出现节点间ping不通, 可能是没有安装`odl-switch`模块.

查看交换机s1上流表:
```
mininet> sh ovs-ofctl dump-flows s1
```
如果出现错误`version negotiation failed`, 是因为OpenFlow协议版本不匹配, 则使用如下命令指定协议:
```
mininet> sh ovs-ofctl -O Openflow13 dump-flows s1
 cookie=0x2b00000000000000, duration=8594.073s, table=0, n_packets=0, n_bytes=0, priority=100,dl_type=0x88cc actions=CONTROLLER:65535
 cookie=0x2a00000000000012, duration=155.125s, table=0, n_packets=1, n_bytes=42, idle_timeout=600, hard_timeout=300, priority=10,dl_src=00:00:00:00:00:02,dl_dst=00:00:00:00:00:01 actions=output:"s1-eth1"
 cookie=0x2a00000000000013, duration=155.125s, table=0, n_packets=0, n_bytes=0, idle_timeout=600, hard_timeout=300, priority=10,dl_src=00:00:00:00:00:01,dl_dst=00:00:00:00:00:02 actions=output:"s1-eth2"
 cookie=0x2b00000000000000, duration=8592.107s, table=0, n_packets=22, n_bytes=1680, priority=2,in_port="s1-eth2" actions=output:"s1-eth1",CONTROLLER:65535
 cookie=0x2b00000000000001, duration=8592.107s, table=0, n_packets=25, n_bytes=1806, priority=2,in_port="s1-eth1" actions=output:"s1-eth2",CONTROLLER:65535
 cookie=0x2b00000000000000, duration=8594.073s, table=0, n_packets=7, n_bytes=542, priority=0 actions=drop
```
由于我们实现执行了`pingall`, 所以流表里有对应的匹配规则. 关于流表的字段解析详见下节

##### 流表分析与操作



### load-balancing



### 决定使用GRE隧道连接各个节点

注意事项:

* 考虑MTU
* 考虑性能
* vxlan比较, 何时必须使用

### hub.spawn()

这个是基于eventlet的协程, 协程无需进行锁保护.

hub.sleep(5)会主动让出cpu 5秒



## SDN虚机测试环境搭建

#### 一. 基本思路

利用GRE隧道构建overlay网络, 每个虚机上不修改公网网卡接口, 直接利用公网地址映射与其他各节点的隧道. 

本地overlay网络ip地址直接配置在br0接口上. 由于是负责接入网络后进行选路, 所以underlay网络的ip只会利用一个ip, 如果机器上有多线, 则这里选择每个代理点上都有的**电信ip**作为underlay网络的ip

#### 二. 基础互联保证

(1) 虚机配置中的混杂模式无需开启

由于使用的隧道构建网络, 本机不会接收到mac地址不指向本机的数据包, 所以虚机无需特别开启混杂模式

(2) br0使用的fail-mode

这个参数决定了OVS在连接控制器异常时该如何操作，可选值为:

- standalone: OVS每隔`inactivity_probe`秒尝试连接一次控制器，重试三次，三次仍失败之后，OVS会转变为一个普通的MAC地址学习交换机。但是OVS仍会在后台尝试连接Controller，一旦连接成功，就会重新转变为OpenFlow交换机，依靠流表完成转发
- secure: 当Controller连接失败或没配置Controller时，OVS自身不会设置任何flow, **也不会改变任何已有的flow规则**, 它只会尝试重连Controller, 对于已有的flow规则则正常转发.

这里设置fail-mode: secure, 则一开始的时候网络间不通, 无法测试进行正确的连通性测试, 同时对br0抓包也不会抓到任何包. 所以如果测试连通性, 这里需要使用standalone模式.

standalone模式对于环形网络会引发广播风暴, 正式环境下不应该启用!



****