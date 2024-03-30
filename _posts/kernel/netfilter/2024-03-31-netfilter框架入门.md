---
layout: post
title: netfilter框架入门
category: kernel
typora-root-url: ../../..
---

### netfilter框架与各模块

这里以linux3.2版本内核为例, linux4.1之后netfilter各结构命名有较大改动, 需要重新看代码梳理, 不过整体的设计思路是没有变动的.

#### netfilter框架主要功能

netfilter框架的主要工作是: 

1. 定义`nf_hooks[NFPROTO_NUMPROTO][NF_MAX_HOOKS]`, 为不同协议定义不同的hook点.
2. 不同功能模块可以通过`nf_register_hooks()`等函数来向特定协议和特定hook点注册
3. 在协议栈的不同点上(例如 arp_rcv(), ip_rcv(), ip6_rcv(), br_forward()等)放置 NF_HOOK() 函数, 当数据包经过了某个协议栈(NF_PROTO)的某个点( NF_HOOK)时, 该协议栈会通过 `NF_HOOK()->nf_hook_slow()` 函数调用对应钩子链表(`nf_hooks[NF_PROTO][NF_HOOK]`)中注册的每一个钩子项来处理该数据包
4. netfilter 为每个钩子函数提供返回值

   * NF_DROP(0): 数据包被丢弃. 即不被下一个钩子函数处理, 同时也不再被协议栈处理, 并释放掉该数据包. 协议栈将处理下一个数据包.
   * NF_ACCEPT(1): 数据包允许通过. 即交给下一个钩子函数处理、或交给协议栈继续处理(okfn()).
   * NF_STOLEN(2): 数据包被停止处理. 即不被下一个钩子函数处理, 同时也不被协议栈处理, 但也不释放数据包. 协议栈将处理下一个数据包.
   * NF_QUEUE(3): 将数据包交给 nf_queue 子系统处理. 即不被下一个钩子函数处理, 同时也不被协议栈处理, 但也不释放数据包. 协议栈将处理下一个数据包.
   * NF_REPEAT(4): 数据包将被该返回值的钩子函数再次处理一遍.
   * NF_STOP(5): 数据包停止被该 HOOK 点的后续钩子函数处理, 并交给协议栈继续处理(okfn())

netfilter框架代码的初始化过程如下: 

```c
net/socket.c::core_initcall(sock_init)
  sock_init()
    net/netfilter/core.c::netfilter_init()
```

其他设计:

* 每个hook代码都分为两部分, 即hook函数和xx_finish()函数, 这样做, 是因为编译内核时可以选择不编译netfilter模块, xx_finish函数的内容是即使没有netfilter模块, 内核也要必须对数据包做的事情.
* netfilter可以指定一个优先级, 低于这个优先级的hook函数不被执行, nf_hook_thresh(..., int thresh, int cond)函数的thresh参数就是优先级. 同时还可以通过cond参数(取0或1)更干脆的取消整个链的遍历.
* 我们发现遍历hook的代码都放在函数的最后, 如下面代码中的ip_forward_finish函数, NF_HOOK(PF_INET, NF_INET_FORWARD, skb, skb->dev,rt->u.dst.dev, ip_forward_finish); 这样的话, ip_forward_finish函数即使不被声明为inline, 其执行效率也挺高, 因为GNU C有一个尾部过程调用的优化, 省去了函数返回的开销

#### 关键功能模块的代码查找

这里如何找到注册的模块呢? 其实做法比较简单, 我们知道基于netfilter框架实现的功能, 必须调用函数`nf_register_hooks()`在hook点注册函数, 那我们就全局搜索下调用该函数的代码即可. 我们比较关注的功能有如下:

* 连接跟踪功能
* nat转发功能
* iptables包过滤功能

这三个主要功能所注册的hook点函数位置如下图:

![img](/img/kernel/netfilter_hook_points.png)

上图是IPv4协议中每个hook点上注册的hook函数(虚线框中的函数, 按照箭头方向的优先级顺序被调用), 注意, 图中假设security/mangle/raw这三个表中没有规则, 所以没有相应的hook函数. netfilter的入口点为ip_rcv()函数. 图中有四种hook函数:

1. 紫色的两个函数用来对分片包进行重组
2. 蓝色的四个函数用来实现数据包的连接跟踪(conntrack)模块
3. 绿色的三个函数用来用来进行数据包的过滤(查找filter表中的规则)
4. 粉色的四个函数用来实现NAT地址转换(查找NAT表中的规则)

下文会依次介绍其实现



### 连接跟踪功能模块的注册实现

#### nf_conntrack连接跟踪模块

nf_conntrack模块为其他具体协议模块**提供连接跟踪相关的全局资源和通用操作**. 该模块所处理的核心元素就是连接跟踪表项: `struct nf_conn`. 

1. 与连接跟踪相关的全局资源放在了 net->ct 网络命名空间中, 它的类型是 struct netns_ct
2. 连接跟踪通过 nf_conn 结构进行描述, 其状态标志ct->status定义在`enum ip_conntrack_status`, 
3. 连接跟踪对数据包在用户空间可以表现的状态, 由 enum ip_conntrack_info 表示, 被设置在 skb->nfctinfo 中
4. 连接跟踪里使用了两个全局 spin_lock 锁( nf_conntrack_lock、 nf_nat_lock)和一个局部 spin_lock 锁( ct->lock)
   * nf_conntrack_lock
     (1) ct 从 ct_hash[]表中添加/删除时使用该锁, 在 ct_hash 表中查找 ct 时使用 RCU 锁.
     (2) ct 从 unconfirmed 链上添加/删除时使用该锁, 在该 unconfirmed 链上的 ct 不需要查找.
     (3) ct 从 dying 链上添加/删除时使用该锁, 在该 dying 链上的 ct 不需要查找.
     (4) ct 通过 expect 与 mct 关联时使用该锁, 目的是防止 mct 被移动或删除.
     (5) expect 从 expect_hash[]表中添加/删除/查找时使用该锁. 因为 expect 与 ct 紧密关联, 所以共用一把锁. expect 仅在初试化连接时被查找.
   * nf_nat_lock
     (1) ct 从 nat_bysource[]中添加/删除/查找时使用该锁. nat_bysource[]在初始化连接时被使用.
     (2) 注册/注销 nf_nat_protos 协议时使用该锁.
   * ct->lock
     (1) 修改某个 ct 的数据时使用该 ct 自己的锁
5. 扩展连接跟踪结构( nf_conn)利用 nf_conntrack_extend.c 文件
6. 处理一个连接的子连接协议, 利用 nf_conntrack_helper.c 文件
7. 三层协议( IPv4/IPv6)利用 nf_conntrack_proto.c 文件中的 nf_conntrack_l3proto_register(struct nf_conntrack_l3proto *proto)和nf_conntrack_l3proto_unregister(struct nf_conntrack_l3proto *proto)在 nf_ct_l3protos[]数组中注册自己的三层协议处理函数
8. 四层协议( TCP/UDP)利用 nf_conntrack_proto.c 文件中的nf_conntrack_l4proto_register(struct nf_conntrack_l4proto *l4proto)和nf_conntrack_l4proto_unregister(struct nf_conntrack_l4proto *l4proto)在 nf_ct_protos[]数组中注册自己的四层协议处理函数
9. 建立连接跟踪结构( nf_conn)利用 nf_conntrack_core.c 文件中的 nf_conntrack_in()函数进行构建的. nf_conntrack_core.c 文件中还包括其它相应的处理ct表项函数

下面列出nf_conntrack模块的初始化过程:

```c
net/netfilter/nf_conntrack_standalone.c::nf_conntrack_standalone_init()
  nf_conntrack_net_init()
    net/netfilter/nf_conntrack_core.c::nf_conntrack_init()
      nf_conntrack_init_init_net()
        nf_conntrack_proto_init() //将nf_ct_l3protos[]全初始化为默认操作
        nf_conntrack_helper_init()
        nf_ct_extend_register()
      nf_conntrack_init_net() // 为相关哈希表, 链表初始化分配空间
```



#### IPv4 利用 nf_conntrack 进行链接跟踪

这个模块(nf_conntrack_l3proto_ipv4_init)实现对ipv4协议族连接跟踪功能的注册, 直接看模块的初始化操作:

```c
net/ipv4/netfilter/nf_conntrack_l3proto_ipv4.c::module_init(nf_conntrack_l3proto_ipv4_init)
  nf_conntrack_l3proto_ipv4_init()
    nf_conntrack_l4proto_register(&nf_conntrack_l4proto_tcp4)
    nf_conntrack_l4proto_register(&nf_conntrack_l4proto_udp4)
    nf_conntrack_l4proto_register(&nf_conntrack_l4proto_icmp)
    nf_conntrack_l3proto_register(&nf_conntrack_l3proto_ipv4)
    nf_register_hooks(ipv4_conntrack_ops, ...)
```

这里代码主要做两件事:

1. 为 ipv4 协议族注册了的 3 层协议 IPv4 协议处理函数, 和 IPv4 相关的三个 4 层协议 TCP、 UDP、 ICMP; 这里注册的协议相关函数, 不仅会用于链接跟踪功能, 也会被nat功能和包过滤功能间接调用到.
2. 注册了实现连接跟踪的钩子函数

这里ipv4_conntrack_ops所注册的钩子函数如下:

* `ipv4_conntrack_in()`: 挂载在 NF_IP_PRE_ROUTING 点上. 该函数**主要功能是创建链接**, 即创建 struct nf_conn 结构, 同时填充 struct nf_conn 中的一些必要的信息, 例如链接状态、引用计数、 helper 结构等.
* `ipv4_confirm()`: 挂载在 NF_IP_POST_ROUTING 和 NF_IP_LOCAL_IN 点上. 该函数**主要功能是确认一个链接**. 对于一个新链接, 在 ipv4_conntrack_in()函数中只是创建了 struct nf_conn 结构, 但并没有将该结构挂载到链接跟踪的 Hash 表中, 因为此时还不能确定该链接是否会被 NF_IP_FORWARD 点上的钩子函数过滤掉, 所以将挂载到 Hash 表的工作放到了 ipv4_confirm()函数中. 同时, 子链接的 helper 功能也是在该函数中实现的.
* `ipv4_conntrack_local()`: 挂载在 NF_IP_LOCAL_OUT 点上. 该函数功能与 ipv4_conntrack_in()函数基本相同, 但其用来处理本机主动向外发起的链接



### nat转发功能: IPv4 利用 nf_conntrack 进行 NAT 转换

nat功能初始化包括两个部分:

1. 连接跟踪部分
2. iptables转发部分

#### nat功能的连接跟踪部分初始化

```c
net/ipv4/netfilter/nf_nat_core.c::module_init(nf_nat_init)
  nf_nat_init()
    net/netfilter/nf_conntrack_extend.c::nf_ct_extend_register()
    nf_nat_net_init()
    //=> 之后初始化nf_nat_protos[]数组
```

链接跟踪部分初始化工作主要有:

1. 调用 nf_ct_extend_register() 注册一个连接跟踪的扩展功能
2. 调用 register_pernet_subsys() --> nf_nat_net_init() 创建 net->ipv4.nat_bysource 的 HASH 表
3. 初始化 nf_nat_protos[]数组, 为 TCP、 UDP、 ICMP 协议指定专用处理结构, 其它协议都指向默认处理结构
4. 设置一些全局变量l3proto等

#### nat功能的iptables转发部分初始化

```c
net/ipv4/netfilter/nf_nat_standalone.c::module_init(nf_nat_standalone_init)
  nf_nat_standalone_init()
    net/ipv4/netfilter/nf_nat_rule.c::nf_nat_rule_init()
      nf_nat_rule_net_init()
        ipt_register_table(..., &nat_table, ...)
      xt_register_target(&ipt_snat_reg)
      xt_register_target(&ipt_dnat_reg)
    nf_register_hooks(nf_nat_ops, ...)
```

iptables转发部分初始化工作有:

1. 调用 nf_nat_rule_init() --> nf_nat_rule_net_init()在 iptables 中注册一个 NAT 表 (通过 `ipt_register_table()`函数)
2. 调用 nf_nat_rule_init() 注册 SNAT target 和 DNAT target (通过`xt_register_target()`函数)
3. 调用 nf_register_hooks() 挂载 NAT 的 HOOK 函数

这里nf_nat_ops所注册的钩子函数, 最终都调用了nf_nat_fn()来实现nat转换逻辑, 但又略有不同, 如下:

* `nf_nat_in()`: 挂载在NF_IP_PRE_ROUTING点上, nf_nat_fn()做完nat转换逻辑后, 会判断skb的目标地址是否改变, 如果目标地址改变了, 则会将skb->_ref_dst置为NULL, 回到ip_rcv_finish()函数发现skb没有dst, 就会重新查询路由系统, 数据包会走ip_forward()逻辑
* `nf_nat_out()`: 挂载在NF_IP_POST_ROUTING点上, 功能基本等同于nf_nat_fn()
* `nf_nat_local_fn()`: 挂载在NF_IP_LOCAL_OUT点上, 和nf_nat_in()类似, 在调用nf_nat_fn()做完nat转换逻辑后, 如果判断到ct的目标地址发生了改变, 就会调用`ip_route_me_harder()`进行重新路由
* `nf_nat_fn()`: 挂载在NF_IP_LOCAL_IN点上

这里提几个注意点: 

1. nf_nat_fn()函数主要实现了nat转换逻辑, 其函数逻辑这里不详细分析, 直接看代码是最准确的. 如果觉得代码比较难懂, **推荐使用systemtap工具逐行最终关键变量和数据结构的变化**, 这种方式非常有效. 后续有时间再考虑写下使用systemtap分析具体代码的文章.

2. nf_nat_fn()函数中, 可以看到只用skb->ctinfo为IP_CT_NEW状态, 且ct没有打过IPS_SRC_NAT_DONE或IPS_DST_NAT_DONE标记, 才会调用**nf_nat_rule_find()**去查找iptables表规则. 这体现出了iptables表规则对于一个连接只会查找一遍, 后续连接的数据包都使用ct进行转发, 保证了转发的高效性.

3. 如果是需要查找iptables表规则, nf_nat_rule_find()查找和作用到连接跟踪表项的过程如下:

   ```c
   nf_nat_rule_find()
     ipt_do_table()	//规则匹配成功, 假如target匹配是SNAT
       ipt_snat_target()	//执行nf_nat_standalone初始化的target
         nf_nat_setup_info()
     alloc_null_binding()	//规则匹配失败
       nf_nat_setup_info()
   ```

   可以看到无论是查找成功和失败, 最终都会调用nf_nat_setup_info()将nat结果记录到ct, 并更新ct状态.



### iptables filter包过滤功能实现

iptables是用户态配置工具, 它通过setsockopt()和getsockopt()接口与内核态ip_tables模块交互, ip_tables模块将指令进行翻译存入xtable模块规则链表中. netfilter框架中执行到相应hook点时就会查找xtables规则链表并执行相关操作.

#### x_tables模块

struct xt_af xt[]结构数组: 该数组用于**挂载各个协议族的 match 和 target 资源**, 用户态的iptables命令传入的match和target在内核都要有对应xt[]中注册的match和target. find_check_entry()函数中可以看到内核如何根据用户态传过来的规则中match和target的name来匹配内核支持的match和target. struct xt_match 和struct xt_target结构都有name成员, **用户态传入的name必须是内核已注册的, 才能找到对应项添加到一条规则中去**.例如, iptables命令想要使用DNAT这个target, 则内核中必须要定义了对应“DNAT”的target函数. xt[]相关操作有:

* xt_register_match() 和  xt_unregister_match() : 用于注册对应协议可用的match
* xt_register_target() 和 xt_unregister_target() : 用于注册对应协议可用的target
* xt_find_match() 和 xt_find_target() : 用于在 xt[]数组中查找对应协议的 match 或 target 与对应规则相关联, 并增加 match 和 target 所在模块的引用计数

net.xt.tables[]网络命名空间协议链表: 该命名空间协议链表用于将不同协议族的 xt_table 结构表项挂到对应协议链表中

* xt_register_table() 和 xt_unregister_table() : 将 xt_table 挂入 net.xt.table[table->af] 链表中或取出
* xt_hook_link() 和 xt_hook_unlink() : 主要是利用 xt_table 结构和钩子函数构造出 nf_hook_ops 钩子项, 然后调用nf_register_hooks()或 nf_unregisgter_hooks()函数来注册或注销 ipv4 协议对应点的钩子函数 

初始化xtables资源的代码在:

```c
net/netfilter/x_tables.c::module_init(xt_init)
  xt_init()
    INIT_LIST_HEAD(&xt[i].target)	// 初始化各协议族的target
    INIT_LIST_HEAD(&xt[i].match)	// 初始化各协议族的match
      xt_net_init()
        INIT_LIST_HEAD(&net->xt.tables[i])	// 初始化net.xt.tables[]各协议族的 xt_table 表链表
```

注册规则链表的结构, 以ipv4(NFPROTO_IPV4=2)为例:

![img](/img/kernel/iptables_rules_structure.jpg)

1. net->xt.tables[2]为链表头, 将net->xt.tables[2]->next转型为xt_table结构实例, 依次遍历, 找到xt_table->name == "filter"的表结构
2. 将xt_table->private成员转为xt_table_info结构, xt_table_info结构用于存储该表中的所有信息, 包括按每个cpu保存相同一份规则集的entries列表, 以及指明每个链在entries中边界的hook_entry[]偏移数组和underflow[]偏移数组.
3. 通过`net/ipv4/netfilter/ip_tables.c::get_entry()`可以将xt_table_info->entries和xt_table_info->hook_entry[1]拼凑出ipt_entry结构, 代表一条iptables规则.
4. 每个ipt_entry可以包含多个xt_entry_match和一个xt_entry_target, 他们都保存在ipt_entry->elems柔性数组空间中, 其中xt_entry_target会放在最后. 匹配时, ipt_entry结构主要保存标准匹配的内容, ipt_entry_match结构主要保存扩展匹配的内容, ipt_entry_target结构主要保存规则的动作

下面我们编写个systemtap脚本来打印出实际的结构体的值, 来更直观确定结构体间关系, 脚本如下:

```c
#! /usr/bin/env stap

probe begin {
	print ("x_tables_trace begin...\n\n\n")
}

probe module("x_tables").function("xt_find_table_lock") {
# ipv4协议族NFPROTO_IPV4=2
  printf("net->xt.tables[2]==> %s\n\n", @cast($net->xt->tables[2]->next - (& @cast(0, "struct xt_table")->list), "struct xt_table")$$)

  xt_table_info_ptr = @cast($net->xt->tables[2]->next - (& @cast(0, "struct xt_table")->list), "struct xt_table")->private
  entries_ptr = @cast(xt_table_info_ptr, "struct xt_table_info")->entries
# NF_INET_LOCAL_IN=1
  hook_entry_input_offset = @cast(xt_table_info_ptr, "struct xt_table_info")->hook_entry[1]
  printf("xt_table_info==> %s\n\n", @cast(xt_table_info_ptr, "struct xt_table_info")$$);
  printf("ipt_entry==> %s\n\n", @cast(entries_ptr + hook_entry_input_offset, "struct ipt_entry", "kernel<linux/netfilter_ipv4/ip_tables.h>")$$);

  ipt_entry_elems_ptr = @cast(entries_ptr + hook_entry_input_offset, "struct ipt_entry", "kernel<linux/netfilter_ipv4/ip_tables.h>")->elems
  ipt_entry_target_offset = @cast(entries_ptr + hook_entry_input_offset, "struct ipt_entry", "kernel<linux/netfilter_ipv4/ip_tables.h>")->target_offset
  printf("xt_entry_target==> %s\n\n", @cast(ipt_entry_elems_ptr + ipt_entry_target_offset, "struct xt_entry_target", "kernel<uapi/linux/netfilter/x_tables.h>")$$);
}
```

运行脚本后, 执行触发xt_find_table_lock()函数:

```shell
iptables -D INPUT 1
```

输出如下:

```shell
x_tables_trace begin...


net->xt.tables[2]==> {.list={.next=0xffffffff8a8dd230, .prev=0xffffffff8a8dd230}, .valid_hooks=14, .private=0xffff9705f8820000, .me=0xffffffffc05df080, .af='\002', .priority=0, .table_init=0xffffffffc05dd0a0, .name="filter"}

xt_table_info==> {.size=632, .number=4, .initial_entries=4, .hook_entry=[4294967295, ...], .underflow=[4294967295, ...], .stacksize=1, .jumpstack=0xffff9705faab0680, .entries=""}

ipt_entry==> {.ip={.src={.s_addr=0}, .dst={.s_addr=0}, .smsk={.s_addr=0}, .dmsk={.s_addr=0}, .iniface="", .outiface="", .iniface_mask="", .outiface_mask="", .proto=0, .flags='\000', .invflags='\000'}, .nfcache=0, .target_offset=112, .next_offset=152, .comefrom=2, .counters={.pcnt=7829, .bcnt=502047}, .elems="("}

xt_entry_target==> {.u={.user={.target_size=0, .name="", .revision='\000'}, .kernel={.target_size=0, .target=0x0}, .target_size=0}, .data=""}

...
```

另外, 关于用户用iptables命令创建自定义的子链, 子链中的规则实际上作为一条普通的ipt_entry实例插入到原有entries列表的最后面, 并不会实际新增一种链的类型. 这里也可以通过systemtap观察插入前后hook_entry[]和underflow[]的改变进行验证



#### ip_tables 利用 x_tables 初始化 filter 表

ip_tables模块利用x_tables模块的资源, 注册ipv4协议族相关的match和target, 并提供内核态iptables规则的相关操作函数, 初始化代码在:

```c
net/ipv4/netfilter/ip_tables.c::module_init(ip_tables_init)
  //注册一些默认的target和match
  xt_register_targets(ipt_builtin_tg, ...)
  xt_register_matches(ipt_builtin_mt, ...)
  //注册两个函数用于用户态查询或修改iptables规则
  nf_register_sockopt(&ipt_sockopts)
```

初始化主要是注册了与用户态通信的接口. 这个模块提供的三个关键操作函数为:

* ipt_register_table() 和 ipt_unregister_table() : 该函数是 iptables 为 filter、 nat、 mangle 模块提供用于注册相应表结构的接口. 它根据当前表要被挂入的 HOOK 点来构建上图所示的 xt_table_info 初始规则表, 并调用 xt_register_table()函数将 filter 表的 xt_table 和 xt_table_info 结构挂入 net.xt.table[IPV4]链表中
* ipt_do_table() : 该函数是 iptables 为 filter、 nat、 mangle 模块提供用于对数据包匹配各表中规则的接口. 它根据表对应的 xt_table_info 结构中的信息, 找到相应的规则, 对数据包进行逐一匹配
* do_replace() : 该函数是 iptables 为 filter、 nat、 mangle 模块提供用于在对应表中**修改规则**的接口. 它根据用户传递过来的规则, 构建一个新的 xt_table_info 结构和规则, 并将它们与对应表的 xt_table->private 相关联. 它通过 xt_find_table_lock()和 xt_table_unlock()保证当前只有一个写者在操作该表. 通过 local_bh_disable()和 local_bh_enable()保证更换 table->private 指向新的 xt_table_info 结构时不被打断. 通过 get_counters()保证所有其它 CPU 都不再使用旧的 xt_table_info 结构, 安全释放旧的 xt_table_info 结构
  * translate_table() : 根据 ipt_replace 结构构建一个 xt_table_info 结构, 并做一些必要的检查(链是否环路等), 同时将表中的规则与相应的 match 和 target 相关联
  * xt_replace_table() : 为 newinfo 调用 xt_jumpstack_alloc(struct xt_table_info *i)初始化 stack 相关数据, 然后使 table->private 指向 newinfo, 并返回 oldinfo

初始化filter表的代码在:

```c
net/ipv4/netfilter/iptable_filter.c::module_init(iptable_filter_init)
  iptable_filter_init()
    iptable_filter_net_init()
      ipt_alloc_initial_table()
      ipt_register_table()
    	translate_table()
    	xt_register_table()
    xt_hook_link(&packet_filter, iptable_filter_hook)
      nf_register_hooks()	// 将packet_filter转为hook结构挂载, 并将hook处理函数置为iptable_filter_hook()
```

上面代码表明xt_hook_link()实际上会调用netfilter框架hook注册函数nf_register_hooks(), 注册的hook函数是iptable_filter_hook(), 该函数最终也会调用ipt_do_replace()进行iptables规则匹配.

raw表和mangle表的初始化也是类似的. 而对于nat表, 它的钩子函数注册方式不太一样, 上文已有描述, **它最终查询iptables规则的函数是nf_nat_rule_find(), 该函数最终也会调用ipt_do_replace()**.



#### 用户态iptables工具与内核态ip_tables模块交互

用户改变iptables规则时, 是通过ip_tables模块注册的ipt_sockopts中的set方法就是将用户空间传过来的ipt_replace来替换旧的iptables规则. 调用过程如下:

```c
用户态程序::setsockopt(IPT_SO_SET_REPLACE)
  net/ipv4/netfilter/ip_tables.c::do_ipt_set_ctl()
    do_replace()
      copy_from_user(&tmp, ...) //拷贝用户空间ipt_replace结构体
      xt_alloc_table_info(tmp.size)	//分配新的xt_table_info结构
      //将ipt_replace.entries的内容拷贝到新的xt_table_info->entries中
      copy_from_user(loc_cpu_entry, ...)
      translate_table()	//根据ipt_replace给新的xt_table_info赋值
      __do_replace()
        xt_find_table_lock(..., name) //查找到要更新的表
        xt_replace_table() //使用新的xt_table_info给赋值给xt_table->private
        //=> 后续对替换出来的旧的xt_table_info结构做清理
```





ref: http://bbs.chinaunix.net/thread-4082396-1-1.html
