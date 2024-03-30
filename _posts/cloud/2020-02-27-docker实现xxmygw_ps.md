---
layout: post
title: docker实现xxmygw_ps
category: cloud
typora-root-url: ../..
---

这个问题决定了xxmygw能否使用docker. 前提条件:

1. 模拟容器的实现, 在linux系统上是比较直接的, 无非是chroot+unshare+cgroup这三个命令的操作. chroot实现文件系统隔离(切换根文件系统), unshare实现各种命名空间隔离, cgroup则对容器使用的CPU/内存资源做限制. 这里简单使用一个命令即可创建一个容器:

```
#假设根文件系统在rootfs目录下, -p进行pid命名空间隔离, -n进行网络命名空间隔离. 详见man 1 unshare
unshare -p -n -f --mount-proc=./rootfs/proc chroot rootfs /bin/bash
```

有兴趣动动手的可以参见: <https://yq.aliyun.com/articles/628678>

2. 对于每个容器做网络命名空间的隔离, 即对于每个容器都有自己的一套协议栈的副本, 有自己的网络设备、路由选择表、邻接表、Netfilter表、网络套接字、网络procfs条目、网络sysfs条目和其他网络资源. 所以通过在容器中配置公网ip, 实现PS的容器化应该是有可能的, 可以进一步探索.

需求:

PS节点需要配置公网ip, 并将对该公网ip的30000-60000端口进行定制转发.

使用docker自带的端口映射方式, 一台主机上就不能运行多个docker进程了. 这样没有意义. 所以需要自定义网桥, 实现类似于虚拟机**"桥接"**的功能. PS上都配置公网ip, 即可实现容器化需求.

refs:
https://www.jianshu.com/p/5ba2078c23e0
https://blog.csdn.net/freewebsys/article/details/80428830

**docker自定义网桥实现"桥接"**

实验环境/规划环境:

* 宿主机(enp2s0f0)ip: 192.168.1.105/24; mac: b8:70:f4:7f:73:58
* 容器ip: 192.168.1.150/24; mac: e2:79:ce:2b:b1:e4
* 网桥(br0)mac: 4e:36:9e:ed:b8:08
* 测试机ip: 192.168.1.110/24
* 路由器ip: 192.168.1.1; mac: 20:dc:e6:79:5e:46

网络模型:

![docker桥接组网](/img/cloud/docker_diy_bridge.png)

创建过程:

{% raw %}

```shell
# 以--net=none方式启动容器, 这样docker就不会自动为容器配置网络
docker run -ti --rm --net=none debian:stretch /bin/sh
# 确保ip_forward处于启用状态. 同时注意观察iptables filter和nat表
sudo sysctl -w net.ipv4.ip_forward=1

# 找出容器的id. -l找到最近创建的容器, -q仅打印容器id
cont_id=$(docker container ls -lq)
# 以容器的进程id作为自定义网络命名空间的名字
cont_nsid=$(docker inspect -f '{ {.State.Pid}}' ${cont_id})
# 创建网络命名空间. 实质就是添加文件或连接在/var/run/netns/目录下
sudo mkdir -p /var/run/netns
sudo ln -s /proc/${cont_nsid}/ns/net /var/run/netns/${cont_nsid}

# 创建网桥br0
sudo ip link add br0 type bridge
# 将enp2s0f0的ip赋值给网桥
sudo ifconfig br0 192.168.1.105/24 up
sleep 0.1
# 将宿主机网卡加入网桥, 作为网桥中的一个端口. 到这里网桥就夺走了enp2s0f0
# 上分配ip, 并且在路由器上看到192.168.1.105对应的mac地址变成br0的mac
sudo ip l s enp2s0f0 master br0
sudo ifconfig enp2s0f0 0 up

# 建立veth pair虚拟网卡A和B
sudo ip l a A type veth peer name B
# 将一端A绑定到网桥作为一个端口
sudo brctl addif br0 A
sudo ip l s A up
sudo brctl show
# 将另一端放到容器的网络命名空间中, 并改名为eth0. 配置ip
sudo ip l s B netns $cont_nsid
sudo ip netns exec $cont_nsid ip l s dev B name eth0
sudo ip netns exec $cont_nsid ip l s dev eth0 up
sudo ip netns exec $cont_nsid ip a a 192.168.1.150/24 dev eth0
# 将容器的默认网关设置为宿主机
sudo ip netns exec $cont_nsid ip r a default via 192.168.1.105
```

{% endraw %}

如此创建完成, 在路由器上看到的arp地址对应关系:

* 192.168.1.105: 4e:36:9e:ed:b8:08

在测试机上可以ping通192.168.1.150和192.168.1.105; 测试机看到arp地址:

* 192.168.1.150: e2:79:ce:2b:b1:e4

### pipework配合compose实现编排下的自定义"桥接"

docker官方是不支持对于网桥过多的自定义配置的. 搜索网络下, 发现有pipework这个工具, 可以比较方便的实现类似上文的docker自定义网桥实现"桥接". 

不过这样局限于单个容器, 在编排上的话该怎么做呢. 官方给出的方法是编排时配合[dreamcat4/pipework](https://hub.docker.com/r/dreamcat4/pipework/)容器, 按配置设定环境变量, 即可实习编排下自定义"桥接"

```shell
# 获取dreamcat4/pipework镜像
docker pull dreamcat4/pipework
# 
```

refs:
https://github.com/dreamcat4/docker-images/blob/master/pipework/3.%20Examples.md
https://github.com/dreamcat4/docker-images/blob/master/pipework/4.%20Config.md

## 实现openvpn模拟网游加速器

https://github.com/kylemanna/docker-openvpn

**1、安装**

1.下载

```
docker pull kylemanna/openvpn
```

2.全局变量(方便设置)

```
OVPN_DATA="/root/ovpn-data"// 下面的全局变量换成你的服务器的外网ipIP="xxx.xxx.xxx.xxx"
```

3.创建文件目录

```
mkdir ${OVPN_DATA}
```

4.配置

```
docker run -v ${OVPN_DATA}:/etc/openvpn --rm kylemanna/openvpn ovpn_genconfig -u tcp://${IP}
```

5.初始化

```
docker run -v ${OVPN_DATA}:/etc/openvpn --rm -it kylemanna/openvpn ovpn_initpki

Enter PEM pass phrase: 输入123456（你是看不见的） 
Verifying - Enter PEM pass phrase: 输入123456（你是看不见的） 
Common Name (eg: your user, host, or server name) [Easy-RSA CA]:回车一下 
Enter pass phrase for /etc/openvpn/pki/private/ca.key:输入123456
```

5.创建用户

```
docker run -v ${OVPN_DATA}:/etc/openvpn --rm -it kylemanna/openvpn easyrsa build-client-full CLIENTNAME nopass

Enter pass phrase for /etc/openvpn/pki/private/ca.key:输入123456 
```

6.生成密钥

```
docker run -v ${OVPN_DATA}:/etc/openvpn --rm kylemanna/openvpn ovpn_getclient CLIENTNAME > ${OVPN_DATA}/CLIENTNAME.ovpn
```

7.生成docker容器

```
docker run --name openvpn -v ${OVPN_DATA}:/etc/openvpn -d -p 1194:1194 --privileged kylemanna/openvpn
```

**2. 撤销签署的证书(删除用户)**

进入docker

easyrsa revoke client1 easyrsa gen-crl cp /etc/openvpn/pki/crl.pem /etc/openvpn/crl.pem

编辑${OVPN_DATA}/openvpn.conf 

crl-verify /etc/openvpn/crl.pe

重启Docker
