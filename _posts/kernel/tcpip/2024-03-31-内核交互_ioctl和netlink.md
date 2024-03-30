---
layout: post
title: 内核交互_ioctl和netlink
category: kernel
tag: tcpip
typora-root-url: ../../..
---

### ioctl通信方式

我们来分析一个操作的实现: `ifconfig -a`, 通过`sudo strace ifconfig -a`可以发现比较关键的调用如下:

```shell
...
socket(AF_INET, SOCK_DGRAM, IPPROTO_IP) = 4
...
ioctl(4, SIOCGIFCONF, &ifr)
```

ioctl系统调用是内核和应用程序交互配置的一种手段, 它是**同步**的, 即它的执行必定处于某个进程的上下文中. 这个系统调用是属于VFS的, 对于所有文件系统都可以使用, 这里假设操作的udp socket类型文件系统, 调用流程如下:

```shell
fs/ioctl.c::sys_ioctl()
  do_vfs_ioctl()
    vfs_ioctl()
      # file.f_op是在sock_map_fd()中alloc_file()赋值的
      # 指向net/socket.c::socket_file_ops
      filp->f_op->unlocked_ioctl => net/socket.c::sock_ioctl()
        # 通过cmd是否调用的设备驱动自身的.ndo_do_ioctl函数
        dev_ioctl()
        sock_do_ioctl()
          # sock->ops指向的是inet_dgram_ops
          sock->ops->ioctl => net/ipv4/af_inet.c::inet_ioctl()
            # SIOCADDRT等route相关
            net/ipv4/fib_frontend.c::ip_rt_ioctl()
            # SIOCGARP等arp相关
            net/ipv4/arp.c::arp_ioctl()
            # SIOCGIFADDR等设备相关
            net/ipv4/devinet.c::devinet_ioctl()
            # sk->sk_prot指向udp_prot
            sk->sk_prot->ioctl => net/ipv4/udp.c::udp_ioctl()
```

可以看到, 我们执行ifconfig, 只是借助了下SOCK_DGRAM类型的套接字, 来最终调用到协议族的inet_ioctl()而已, 而具体的信息查看或修改, 并不与具体的协议相关.

这里着重分析下devinet_ioctl()的实现, 它从用户接收cmd和arg两个参数, 其中arg是直接转成struct ifreq类型的结构, 包含要操作指令cmd对应的具体参数

```shell
net/ipv4/devinet.c::devinet_ioctl()
  inet_set_ifa()
    __inet_insert_ifa()
      inet_hash_insert()
      rtmsg_ifa()
        net/core/rtnetlink.c::rtnl_notify()
          net/netlink/af_netlink.c::nlmsg_notify()
            include/net/netlink.h::nlmsg_multicast()
              net/netlink/af_netlink.c::netlink_broadcast()
      blocking_notifier_call_chain(&inetaddr_chain, NETDEV_UP, ifa)
```

__inet_insert_ifa将ifa链入in_device结构, 将ifa加入inet_addr_lst哈希表. 然后就比较有意思, 它调用**rtmsg_ifa()**发送netlink消息, 下节会重点介绍. 同时对inetaddr_chain通知NETDEV_UP事件. 经过这么一番配置, in_ifaddr{}, net_device{}和 in_device{}的关系如下图:

![/img/tcpip/inet_set_ifa.png](/img/tcpip/inet_set_ifa.png)

### netlink通信方式

##### RTM_NEWLINK处理流程

我们仍然通过一个操作来追踪netlink, 使用`sudo strace ip a`, 可以发现比较关键的调用如下:

```shell
...
socket(AF_NETLINK, SOCK_RAW|SOCK_CLOEXEC, NETLINK_ROUTE) = 3
bind(3, ...)
sendto(3, { {..., type=RTM_GETLINK,...}, {...ifi_family=AF_UNSPEC,...}})
recvmsg(3, msg_iov=[{iov_base=[{ {..., type=RTM_NEWLINK, ...}}]}])
...
```

netlink是通过套接口标准的API来和内核通信的, 套接口的创建如下

```cpp
fd = socket(AF_NETLINK, SOCK_RAW, NETLINK_ROUTE);
```

这里的**protocol参数在AF_NETLINK协议族中指的是netlink family**, 比较常用的netlink family有以下几种

* NETLINK_ROUTE
* NETLINK_ARPD: 用户空间管理ARP表
* NETLINK_USERSOCK: 给应用程序发消息

可以看到family=AF_NETLINK, type=SOCK_RAW. 则我们要找的协议族是AF_NETLINK, 内核中在net/netlink/af_netlink.c中注册了AF_NETLINK协议族

```shell
net/netlink/af_netlink.c::core_initcall(netlink_proto_init)
  netlink_proto_init()
    proto_register(&netlink_proto, 0)
    sock_register(&netlink_family_ops)
    register_pernet_subsys(&netlink_net_ops)
    # rtnetlink是基本netlink协议的消息扩展, 对应NETLINK_ROUTE
    net/core/rtnetlink.c::rtnetlink_init()
      register_pernet_subsys(&rtnetlink_net_ops)
        net/core/rtnetlink.c::rtnetlink_net_init)_
          netlink_kernel_create(NETLINK_ROUTE...rtnetlink_rcv...)
            #内核创建一个轻量级socket结构, 最为内核netlink服务端
            sock_create_lite()
            #创建对应的sock结构
            __netlink_create()
            #这里绑定了rtnetlink在内核中的接收函数
            nlk_sk(sk)->netlink_rcv = rtnetlink_rcv
            #将sk插入到nl_table哈希表中, 注意这里设置了服务端pid=0
            netlink_insert(sk, net, 0)
            nlk->flags |= NETLINK_KERNEL_SOCKET
            nl_table[NETLINK_ROUTE].registered = 1
      # 注册rtnetlink_event()函数处理netdev_chain链事件
      register_netdevice_notifier(&rtnetlink_dev_notifier)
      rtnl_register(PF_UNSPEC, RTM_GETLINK, rtnl_getlink, ...)
```

则我们追溯系统调用, 如下

socket()调用

```shell
net/socket.c::socket()
  __sock_create()
    net/netlink/af_netlink.c::netlink_create()
      cb_mutex = nl_table[protocol].cb_mutex
      __netlink_create()
        sock->ops = &netlink_ops
        sk = sk_alloc(...PF_NETLINK,...,&netlink_proto)
        sk->sk_protocol = protocol
```

sendto()调用: 传递的是msghdr指针, 其中msghdr.msg_iov是指向nlmsghdr结构的指针

```shell
net/socket.c::sendto()
  sock_sendmsg()
    __sock_sendmsg_nosec()
      sock->ops->sendmsg => net/netlink/af_netlink.c::netlink_sendmsg()
        # 这里执行自动绑定. 会获得nlk->pid
        netlink_autobind()
          netlink_insert()
        skb = alloc_skb(len, GFP_KERNEL);
        netlink_unicast()
          # 由于dst_pid为0, 所以这里取到的sock结构就是内核netlink服务端
          netlink_getsockbypid()
            netlink_lookup()
          # 内核服务端netlink sock结构有设置NETLINK_KERNEL_SOCKET标志
          netlink_is_kernel()
          netlink_unicast_kernel()
            nlk->netlink_rcv => net/core/rtnetlink.c::rtnetlink_rcv()
              net/netlink/af_netlink.c::netlink_rcv_skb()
                # skb->data强制转型为nlmsghdr结构指针
                nlh = nlmsg_hdr(skb)
                cb() => net/core/rtnetlink.c::rtnetlink_rcv_msg()
                  # 注意这里family是传入的ifi_family=AF_UNSPEC, 
                  # type则是传入的type=RTM_GETLINK
                  doit = rtnl_get_doit(family, type)
                  doit() => rtnl_getlink()
                    # 构造回复包nskb
                    nskb = nlmsg_new()
                    # 为nskb填入查找到的信息
                    rtnl_fill_ifinfo(...RTM_NEWLINK,...)
                    rtnl_unicast()
```

这里sendto()主要就是创建一个skb, 然后找到用户态想将这个skb发送给哪个socket, 由于默认dst_pid为0, 且用户态也没有指定, 所以skb会发送给注册AF_NETLINK协议族时内核创建的轻量级netlink socket服务端. 具体就是直接调用netlink_unicast_kernel()完成后续工作.

##### RTM_NEWADDR处理

前面总结了RTM_NEWLINK等系列指令的处理流程, 但是我们没有看到有关于RTM_NEWADDR类型指令处理方式的注册. 全局搜索一下, 发现它是通过路由子系统初始化时, 调用devinet_init()进行注册的

```shell
net/ipv4/devinet.c::devinet_init()
  # 注册了ifi_family=PF_INET, type=RTM_NEWADDR的处理函数
  net/core/rtnetlink.c:: rtnl_register(PF_INET, RTM_NEWADDR, inet_rtm_newaddr, ...)
    net/ipv4/devinet.c::inet_rtm_newaddr()
      __inet_insert_ifa()
```

`__inet_inert_ifa()`的流程前面介绍ioctl通信方式时有详细讨论了.

### genetlink(Generic Netlink Family)

为什么会有这个? 其实我只所以需要彻底分析netlink通信机制, 是为了看懂fou隧道协议的处理方式, 该协议就是利用了genetlink通信方式来进行控制. 参见: /kernel/tcpip/fou协议源码解析.md

同样, 这里我们使用的操作是`sudo strace ip fou add port 5555 gue`, 可以发现比较关键的调用如下:

```shell
...
socket(AF_NETLINK, SOCK_RAW|SOCK_CLOEXEC, NETLINK_GENERIC) = 4
bind(4, {sa_family=AF_NETLINK, nl_pid=0, nl_groups=00000000}, 12) = 0
sendmsg(4, {msg_iov=[{iov_base={ {type=nlctrl, ...}, "\x03\x00\x00\x00\x08\x00\x02\x00\x66\x6f\x75\x00"}}]})
recvmsg(4, ...)
sendmsg(4, {msg_iov=[{iov_base={ {type=fou, ...}, "\x01\x01\x00\x00\x06\x00\x01\x00\x15\xb3\x00\x00\x05\x00\x04\x00\x02\x00\x00\x00\x06\x00\x02\x00\x02\x00\x00\x00"}}]})
recvmsg(4, ...)
...
```

可以看到, 创建socket时, 做法和netlink创建是一样的, 只是NETLINK_ROUTE变成了NETLINK_GENERIC. 这使得相关的调用函数有所变化, 比如sendto()调用中`nlk->netlink_rcv`就会指向`net/netlink/genetlink.c::genl_rcv()`.

我们先看看genetlink是怎么注册的

```shell
net/netlink/genetlink.c::subsys_initcall(genl_init)
  genl_init()
    genl_register_family_with_ops()
      # 将特殊的genl_family结构链入family_ht哈希表中
      genl_register_family()
      # 将代表协议操作集的genl_ops结构链入genl_family.ops_list
      genl_register_ops()
    register_pernet_subsys(&genl_pernet_ops)
      genl_pernet_init()
        netlink_kernel_create(...NETLINK_GENERIC...genl_rcv...)
    # 注册多播时使用的组
    genl_register_mc_group()
```

下面结合看看sendto()的实现, 这里直接从`nlk->netlink_rcv`指向的`net/netlink/genetlink.c::genl_rcv()`开始, 之前的调用逻辑和netlink是相同的

```shell
net/netlink/genetlink.c::genl_rcv()
  net/netlink/af_netlink.c::netlink_rcv_skb()
    # skb->data强制转型为nlmsghdr结构指针
    nlh = nlmsg_hdr(skb)
    cb() => net/netlink/genetlink.c::genl_rcv_msg()
      # 从family_ht哈希表中找到具体的genl_family结构
      # 这里nlh->nlmsg_type="nlctrl"
      family = genl_family_find_byid(nlh->nlmsg_type)
      genl_family_rcv_msg(family, ...)
        # 从genl_family.ops_list中找到具体的genl_ops结构, 
        # 这里hdr是nlmsghdr结构数据部分强制转为genlmsghdr结构, 从系统调用
        # 得知hdr->cmd=0x03, 即CTRL_CMD_GETFAMILY
        ops = genl_get_cmd(hdr->cmd, family)
        # 调用具体genl_ops结构注册doit()函数处理skb
        ops->doit() => ctrl_getfamily()
          #构建回复包skb
          ctrl_build_family_msg()
          genlmsg_reply()
```

ops->doit()随具体协议不同而不同, 从系统调用中来看, 第一次调用的是ctrl_getfamily(), 第二次调用的是fou_nl_cmd_add_port(), fou协议可继续参见: /kernel/tcpip/fou协议源码解析.md
