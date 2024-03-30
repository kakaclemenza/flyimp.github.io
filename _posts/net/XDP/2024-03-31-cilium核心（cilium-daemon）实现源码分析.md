---
layout: post
title: cilium核心（cilium-daemon）实现源码分析
category: net
typora-root-url: ../../..
---

> 转自：[Cilium eBPF实现机制源码分析](https://www.cnxct.com/how-does-cilium-use-ebpf-with-go-and-c/)



## Cilium实现源码分析

# 目的

本文面向eBPF开发者，旨在研究学习高质量开源产品设计思路、编码规范，学习更好得使用eBPF方法经验。内容比较干燥，谨慎阅读。

本文涉及cilium代码版本为2021-08-17的[1695d9c59a](https://github.com/cilium/cilium/commit/1695d9c59a)版本

# Cilium产品介绍

Cilium是由革命性内核技术eBPF驱动，用于提供、保护和观察容器工作负载（云原生）之间的网络连接的网络组件。
Cilium使用eBPF的强大功能来加速网络，并在Kubernetes中提供安全性和可观测性。现在 Cilium将eBPF的优势带到了Service Mesh的世界。Cilium服务网格使用eBPF来管理连接，实现了服务网格必备的流量管理、安全性和可观测性。

# 项目理解

从Cilium的架构图来看，位于容器编排系统和Linux Kernel之间，使用eBPF技术来控制容器网络的转发行为以及安全策略执行。其使用的eBPF功能包括宿主机网卡流量控制，容器container功能管理等。与系统交互的模块是`Cilium Daemon`，负责eBPF字节码生成、字节码注入到linux kernel，并进行数据读取等。

![img](../../../assets/cilium%E6%A0%B8%E5%BF%83%EF%BC%88cilium-daemon%EF%BC%89%E5%AE%9E%E7%8E%B0%E6%BA%90%E7%A0%81%E5%88%86%E6%9E%90/cilium-arch.png)
所以，本文重点将放在`Cilium Daemon`实现上。

`Cilium Daemon`模块在源码里对应`https://github.com/cilium/cilium/tree/master/daemon`目录，从`main.go`主文件开始阅读即可。但在阅读之前，先对cilium项目的目录结构做一个认识。

# 目录结构：

当前目标是理解分析cilium的eBPF应用，故笔者在总结时，只列出eBPF相关代码。

按照cilium官方的文档介绍[github.com/cilium/cilium](https://docs.cilium.io/en/latest/contributing/development/codeoverview/)，从目录结构中，摘录了eBPF相关的目录。

顶级目录

1. bpf : eBPF datapath收发包路径相关代码，eBPF源码存放目录。
2. daemon : 各node节点上运行的cilium-agent代码，也是跟内核做交互，处理eBPF相关的核心代码。
3. pkg : 项目依赖的各种包。
   1. pkg/bpf ： eBPF运行时交互的抽象层
   2. pkg/datapath datapath交互的抽象层
   3. pkg/maps eBPF map的描述定义目录
   4. pkg/monitor eBPF datapath 监控器抽象

# 源码阅读

## cilium C语言eBPF源码

### 源码功能分类

bpf目录下有很多eBPF实现的源码，文件列表如下

1. bpf_alignchecker.c C与Go的消息结构体格式校验
2. bpf_host.c 物理层的网卡tc ingress\egress相关过滤器
3. bpf_lxc.c 容器上的网络环境、网络流量管控等
4. bpf_network.c 网络控制相关
5. bpf_overlay.c 叠加网络控制代码
6. bpf_sock.c sock控制相关，包含流量大小控制、TCP状态变化控制
7. bpf_xdp.c XDP层控制相关
8. sockops 目录下有多个文件，用于sockops相关控制，流量重定向等性能优化。
9. cilium-probe-kernel-hz.c probe测试的，忽略

### 作用解释

关于上面eBPF文件源码的作用，在官网也有文档[eBPF Datapath Introduction](https://docs.cilium.io/en/v1.8/concepts/ebpf/intro/)解释，笔者稍做整理。

在详细阐述每个模块源码之前，我们先来复习一下linux kernel的网络栈

![img](../../../assets/cilium%E6%A0%B8%E5%BF%83%EF%BC%88cilium-daemon%EF%BC%89%E5%AE%9E%E7%8E%B0%E6%BA%90%E7%A0%81%E5%88%86%E6%9E%90/Linux-kernel-network-stack-xdp-tc.png)
如图所示，入口网络流量在到达NIC后，依次经过XDP、TC、Netfilter、TCP、socket层。
cilium的ebpf相关程序，核心功能是针对pod宿主机、pod、容器几个角色之间的网络流量管控。那么其功能肯定是在这几个栈的对应部位做响应hook。

常用的nftables、iptables模块对应在Netfiliter层，站在安全的视角里，HOOK点如何选择，选在那一层，需要结合安全需求来确定。

#### XDP

XDP BPF hook 是网络驱动程序中最早的一关，可以在接收到数据包时触发BPF程序。在这里实现了最高效的数据包处理。这个HOOK非常适合运行过滤程序来处理恶意或意外流量，以及实现常见的 DDOS保护机制。

#### Traffic Control Ingress/Egress

显然，是附加到流量控制 (TC) Ingress HOOK的BPF程序，与XDP类似，区别是其在网络堆栈完成后，数据包初始处理后运行。此HOOK在内核整个网络堆栈的L3层之前运行，可以读取与数据包关联的大部分元数据。很适合进行本地节点处理，比如应用L3/L4端点策略进行流量重定向等。

容器场景常使用veth pair的虚拟设备，它充当容器与主机的虚拟网桥。通过attach到这个veth pair的宿主机的TC Ingress钩子，Cilium 可以监控管理容器的所有流量。

#### socket operations

sockops Hook是attach到特定的cgroup上，在TCP事件上一并运行。Cilium的实现是把BPF sockops程序attach到根cgroup上，来监视TCP状态转换，进行相关业务处理。

#### socket 发送/接收

该钩子在TCP socket执行的每个发送操作上运行。这个钩子可以对消息进行读取、删除、重定向到另一个socket。（PS：`笔者说一句，这个就很可怕，在安全场景里，这可以很简单得实现端口复用的后门程序。复用80端口，监听unix socket做木马后门，HIDS如何发现？`）

### cilium的eBPF场景应用

Cilium使用上面几个Hook与几个接口功能相结合,创建了以下几个网络对象。

1. 虚拟接口(cilium_host、cilium_net)
2. 可选接口(cilium_vxlan)
3. linux内核加密支持
4. 用户空间代理(Envoy)
5. eBPF Hooks

#### 预过滤器 prefilter

XDP层实现的网络流量过滤过滤器规则。比如，由Cilium agent提供的一组CIDR映射用于查找定位、处理丢弃等。

#### endpoint策略

Cilium endpoint来继承实现。使用映射查找与身份和策略相关的数据包，该层可以很好地扩展到许多端点。根据策略，该层可能会丢弃数据包、转发到本地端点、转发到服务对象或转发到 L7 策略对象以获取进一步的L7规则。这是Cilium数据路径中的主要对象，负责将数据包映射到身份并执行L3和L4策略。

#### Service

TC栈上的HOOK，用于L3/L4层的网络负载均衡功能。

#### L3 加密器

L3层处理IPsec头的流量加密解密等。

#### Socket Layer Enforcement

socket层的两个钩子，即sockops hook和socket send/recv hook。用来监视管理Cilium endpoint关联的所有TCP套接字，包括任何L7代理。

#### L7 策略

L7策略对象将代理流量重定向到Cilium用户空间代理实例。使用Envoy实例作为其用户空间代理。然后，根据配置的L7策略转发流量。

如上组件是Cilium实现的灵活高效的 datapath。下图展示端点到端点的进出口网络流量经过的链路，以及涉及的cilium相关网络对象。

![cilium的Datapath图](../../../assets/cilium%E6%A0%B8%E5%BF%83%EF%BC%88cilium-daemon%EF%BC%89%E5%AE%9E%E7%8E%B0%E6%BA%90%E7%A0%81%E5%88%86%E6%9E%90/cilium_bpf_endpoint.svg)

### 总结

综合C的代码，从数据流向来看，分为两类

1. 用户态向内核态发送控制指令、数据
2. 内核态向用户态发送数据

第一部分，cilium调用类bpftool工具来进行eBPF字节码注入。（具体实现的方式，go代码分析时会讲到）； LB部分，会直接向map写入数据内容。(lb.h)
第二部分是内核向用户态发送数据，而数据内容几乎都是其他eBPF的运行日志。尤其是`dbg.h`里定义的`cilium_dbg*` 方法，实现了`skb_event_output()`和`xdp_event_output()`两种函数输出，来代替`trace_printk()`函数，方便用户快速读取日志。两种函数对应的事件输出都是用了`perf buf`类型的map来实现，对应go代码里做了详细的实现，抽象的非常好，后面笔者会重点介绍。

## cilium go源码分析

### eBPF map初始化

上面提到`Cilium Daemon`是管理eBPF的模块，那么从这个模块的入口文件开始阅读。
ebpf map是在ebpf prog加载之前，预先初始化的，在`daemon/cmd/daemon.go`469行

```golang
err = d.initMaps()COPY
```

`initMaps`函数实现在`daemon/cmd/datapath.go`文件的272行。

```golang
// initMaps opens all BPF maps (and creates them if they do not exist). This
// must be done *before* any operations which read BPF maps, especially
// restoring endpoints and services.
func (d *Daemon) initMaps() error {
    lxcmap.LXCMap.OpenOrCreate()
    ipcachemap.IPCache.OpenParallel()
    metricsmap.Metrics.OpenOrCreate()
    tunnel.TunnelMap.OpenOrCreate()
    egressmap.EgressMap.OpenOrCreate()
    eventsmap.InitMap(possibleCPUs)
    signalmap.InitMap(possibleCPUs)
    policymap.InitCallMap() 
}COPY
```

initMaps函数中初始化了cilium的所有eBPF map，功能包括xdp、ct等网络对象处理。
eBPF maps作用博主rexrock在文章 `https://rexrock.github.io/post/cilium2/`中做个直观的图，见

![img](../../../assets/cilium%E6%A0%B8%E5%BF%83%EF%BC%88cilium-daemon%EF%BC%89%E5%AE%9E%E7%8E%B0%E6%BA%90%E7%A0%81%E5%88%86%E6%9E%90/post-2408-61b1c9fe40471.png)

本文挑选其中一个例子来讲。就是前提提到的events maps初始化，用于内核的ebpf字节码调试输出的日志，对应代码`eventsmap.InitMap(possibleCPUs)`。 代码文件在`pkg/map/eventsmap/eventsmap.go`的53行

```golang
eventsMap := bpf.NewMap(MapName,
        bpf.MapTypePerfEventArray,
        &Key{},
        int(unsafe.Sizeof(Key{})),
        &Value{},
        int(unsafe.Sizeof(Value{})),
        MaxEntries,
        0,
        0,
        bpf.ConvertKeyValue,
    )COPY
```

从代码中可以看到，map名字是`cilium_events`，类型是`MapTypePerfEventArray`。

### eBPF代码编译

回到`daemon/cmd/daemon.go`文件，接着往下看，在816行对eBPF应用场景进行初始化。

```golang
err = d.init()

//跳转到285行的init函数
// Remove any old sockops and re-enable with _new_ programs if flag is set
sockops.SockmapDisable()
sockops.SkmsgDisable()COPY
```

对新老map进行删除、替换。

在237行进行datapath的重新初始化加载。

```golang
if err := d.Datapath().Loader().Reinitialize(d.ctx, d, d.mtuConfig.GetDeviceMTU(), d.Datapath(), d.l7Proxy); err != nil {COPY
```

#### datapath初始化ebpf环境

`Reinitialize`函数是抽象的interface的函数，具体实现在`pkg/datapath/loader/base.go`的230行
该函数前半部分对启动参数进行整理汇总。核心逻辑在421行。

```
prog := filepath.Join(option.Config.BpfDir, "init.sh")
cmd := exec.CommandContext(ctx, prog, args...)
cmd.Env = bpf.Environment()
if _, err := cmd.CombinedOutput(log, true); err != nil {
    return err
}
```

是的，你没看错，调用了外部的shell命令进行ebpf代码编译。对应文件是`bpf/init.sh`，这个shell里会进行编译ebpf文件。

比如：`bpf_compile bpf_alignchecker.c bpf_alignchecker.o obj ""` ，生成eBPF字节码.o文件。后面将用于校验C跟GO的结构体对齐情况。
`bpf_compile`也是封装的`clang`的编译函数，依旧使用llvm\llc编译链接eBPF字节码文件。

### eBPF字节码加载

同样`bpf/init.sh`也会对`bpf/*.c`进行编译，再调用`tc`等命令，对编译生成的eBPF字节码进行加载。

其次，go代码里也有加载的地方，见`pkg/datapath/loader/netlink.go`的`replaceDatapath`函数内91行使用`ip` 或`tc` 命令对字节码文件进行加载，使内核加载新的字节码。完成新老字节码的注入替换。

#### C跟go结构体格式校验

430行，使用go代码，验证C跟G结构体对齐情况。

```
alignchecker.CheckStructAlignments(defaults.AlignCheckerName)
```

在pkg/alignchecker/alignchecker.go里，CheckStructAlignments函数会读取.o的eBPF字节码文件，按照elf格式进行解析，并获取DWARF段信息，查找`.debug_*`段或者`.zdebug_`段信息。
getStructInfosFromDWARF函数会按照elf里段内结构体名字与被检测结构体名字进行对比，验证类型，长度等等。

### ebpf编译加载的其他方式

在`pkg/datapath/loader/base.go`210行左右`reinitializeXDPLocked`函数
调用`compileAndLoadXDPProg`函数进行ebpf字节码编译与加载。

```
// compileAndLoadXDPProg compiles bpf_xdp.c for the given XDP device and loads it.
func compileAndLoadXDPProg(ctx context.Context, xdpDev, xdpMode string, extraCArgs []string) error {
    args, err := xdpCompileArgs(xdpDev, extraCArgs)
    if err != nil {
        return fmt.Errorf("failed to derive XDP compile extra args: %w", err)
    }

    if err := compile(ctx, prog, dirs); err != nil {
        return err
    }
    if err := ctx.Err(); err != nil {
        return err
    }

    objPath := path.Join(dirs.Output, prog.Output)
    return replaceDatapath(ctx, xdpDev, objPath, symbolFromHostNetdevEp, "", true, xdpMode)
}
```

函数中，先进行参数重组，在调用`pkg/datapath/loader/compile.go`的compile函数进行编译。该函数依旧是调用了`clang`进行编译。

其他代码细节不在赘述。

### go源码分析总结

1. 编译：直接或间接调用clang/llc命令进行编译链接。
2. 加载：调用外部bpftool\tc\ss\ip等命令加载。
3. MAP管理：调用外部命令或go cilium/ebpf库进行map删除、创建等
4. CORE兼容：会在每个endpoint上编译，没有使用eBPF CORE。
5. 更新：每次重新加载都会编译。

# 内核态与用户态数据交互

## 交互map

| 名字                    | 类型                          | 所属文件      | 数据流向 | 备注                                                      |
| :---------------------- | :---------------------------- | :------------ | :------- | :-------------------------------------------------------- |
| SIGNAL_MAP              | BPF_MAP_TYPE_PERF_EVENT_ARRAY | signal.h      | ？       |                                                           |
| LB4_REVERSE_NAT_SK_MAP  | BPF_MAP_TYPE_LRU_HASH         | bpf_sock.c    | ?        |                                                           |
| LB6_REVERSE_NAT_SK_MAP  | BPF_MAP_TYPE_LRU_HASH         | bpf_sock.c    | ?        |                                                           |
| CIDR4_HMAP_NAME         | BPF_MAP_TYPE_HASH             | bpf_xdp.c     | ?        |                                                           |
| CIDR4_LMAP_NAME         | BPF_MAP_TYPE_LPM_TRIE         | bpf_xdp.c     |          |                                                           |
| CIDR6_HMAP_NAME         | BPF_MAP_TYPE_HASH             | bpf_xdp.c     |          |                                                           |
| CIDR6_LMAP_NAME         | BPF_MAP_TYPE_LPM_TRIE         | bpf_xdp.c     |          |                                                           |
| bytecount_map           | BPF_MAP_TYPE_HASH             | bytecount.h   |          |                                                           |
| cilium_xdp_scratch      | BPF_MAP_TYPE_PERCPU_ARRAY     | xdp.h         |          |                                                           |
| EVENTS_MAP              | BPF_MAP_TYPE_PERF_EVENT_ARRAY | event.h       |          |                                                           |
| IPV4_FRAG_DATAGRAMS_MAP | BPF_MAP_TYPE_LRU_HASH         | ipv4.h        |          |                                                           |
| LB6_REVERSE_NAT_MAP     | BPF_MAP_TYPE_HASH             | lb.h          |          |                                                           |
| LB6_SERVICES_MAP_V2     | BPF_MAP_TYPE_HASH             | lb.h          |          |                                                           |
| ENDPOINTS_MAP           | BPF_MAP_TYPE_HASH             | maps.h        |          |                                                           |
| METRICS_MAP             | BPF_MAP_TYPE_PERCPU_HASH      | maps.h        |          |                                                           |
| POLICY_CALL_MAP         | BPF_MAP_TYPE_PROG_ARRAY       |               |          |                                                           |
| THROTTLE_MAP            | BPF_MAP_TYPE_HASH             |               |          |                                                           |
| EP_POLICY_MAP           | BPF_MAP_TYPE_HASH_OF_MAPS     | maps.h        | ?        | Map to link endpoint id to per endpoint cilium_policy map |
| POLICY_MAP              | BPF_MAP_TYPE_HASH             | maps.h        | ?        | Per-endpoint policy enforcement map                       |
| EVENTS_MAP              | BPF_MAP_TYPE_SOCKHASH         | bpf_sockops.h | ?        |                                                           |

太多了，而且比较偏向cilium的业务功能，偏离本文主题，不写了。后面会按照数据流向分三类，总结说明。

## map作用分类

### 内核态自用

常用与程序内部的临时缓存。比如`__section("cgroup/connect4")`时，TCP socket的状态每次变化，都需要将之前endpoint信息存储起来，下次状态变化时，再读取更改。 举个例子

```c
//bpf/sockops/bpf_sockops.c line 127 
__section("sockops")
int bpf_sockmap(struct bpf_sock_ops *skops)
{
    // 调用bpf_sock_ops_ipv4 函数
    sock_hash_update(skops, &SOCK_OPS_MAP, &key, BPF_NOEXIST);
}
//bpf/sockops/bpf_redir.c line 42
__section("sk_msg")
int bpf_redir_proxy(struct sk_msg_md *msg)
{
    msg_redirect_hash(msg, &SOCK_OPS_MAP, &key, flags);
}COPY
```

### 内核态写，用户态读

有个典型的场景，就是eBPF字节码运行日志的输出。以cilium events map为例，该map是内核态代码的日志输出map。

#### EVENTS_MAP map创建

```golang
MapName = "cilium_events" //eventsmap.go line 19
eventsMap := bpf.NewMap(MapName,
        bpf.MapTypePerfEventArray,
        &Key{},
        int(unsafe.Sizeof(Key{})),
        &Value{},
        int(unsafe.Sizeof(Value{})),
        MaxEntries,
        0,
        0,
        bpf.ConvertKeyValue,
    )COPY
```

map的路径会被拼接，最终全路径时`/sys/fs/bpf/tc/globals/cilium_events`，

```golang
// Path to where bpffs is mounted , /sys/fs/bpf
mapRoot = defaults.DefaultMapRoot

// Prefix for all maps (default: tc/globals)
mapPrefix = defaults.DefaultMapPrefix
m.path = filepath.Join(mapRoot, mapPrefix, name)
// 即 /sys/fs/bpf/tc/globals/cilium_eventsCOPY
```

拼接好map路径后，调用`os.MkdirAll`创建`/sys/fs/bpf/tc/globals`目录;调用`CreateMap`函数，使用`unix.Syacall`创建`BPF_MAP_CREATE`操作的FD；

```
ret, _, err := unix.Syscall(
    unix.SYS_BPF,
    BPF_MAP_CREATE,
    uintptr(unsafe.Pointer(&uba)),
    unsafe.Sizeof(uba),
)
```

调用objPin对map ID和cgroup path绑定，保存到`pkg/bpf/map_Register_linx.go`的`mapRegister Map`里，完成整个map的创建、关联。

#### map数据写入

map内数据写入是由`dbg.h`内`cilium_dbg*`相关函数写入，代码参见

```c
static __always_inline void cilium_dbg(struct __ctx_buff *ctx, __u8 type, __u32 arg1, __u32 arg2)
{
    struct debug_msg msg = {
        __notify_common_hdr(CILIUM_NOTIFY_DBG_MSG, type),
        .arg1   = arg1,
        .arg2   = arg2,
    };

ctx_event_output(ctx, &EVENTS_MAP, BPF_F_CURRENT_CPU,
             &msg, sizeof(msg));
}COPY
```

其中，写入的map名字是`EVENTS_MAP`常量，定义在`bpf/node_config.h`里，默认是`test_cilium_events`，需要总控远程下发这个头文件。方便由go这边统一控制map的名字。详细代码在`pkg/datapath/linux/config/config.go`里WriteNodeConfig函数部分。比如

```golang
cDefinesMap["EVENTS_MAP"] = eventsmap.MapName
cDefinesMap["SIGNAL_MAP"] = signalmap.MapName
cDefinesMap["POLICY_CALL_MAP"] = policymap.PolicyCallMapName
cDefinesMap["EP_POLICY_MAP"] = eppolicymap.MapName
cDefinesMap["LB6_REVERSE_NAT_MAP"] = "cilium_lb6_reverse_nat"
cDefinesMap["LB6_SERVICES_MAP_V2"] = "cilium_lb6_services_v2"COPY
```

回到`cilium_dbg`函数，是内核eBPF部分最底层的日志事件输出函数，map声明在`bpf/lib/events.h`

```c
struct bpf_elf_map __section_maps EVENTS_MAP = {
    .type       = BPF_MAP_TYPE_PERF_EVENT_ARRAY,
    .size_key   = sizeof(__u32),
    .size_value = sizeof(__u32),
    .pinning    = PIN_GLOBAL_NS,
    .max_elem   = __NR_CPUS__,
};COPY
```

调用的地方比较简单，不在一一赘述。

#### 小结

map名统一由go部分控制，起到统一管理作用，避免两端不一致。

事件日志/调试日志避开`trace_printk`函数输出，统一发送至用户态go部分，避免人工查看`/sys/kernel/debug/tracing/trace_pipe`，提升工作效率。

由go部分决策如何处理。比如发送给相关模块订阅的角色，或者统一上传到日志中心，便于大规模分析展示。这是个可以借鉴的好思路。

#### map数据读取

在monitor/agent/agent.go里，初始化时对map进行了pin操作。

> 笔者要吐槽的是cilium_events map名字的常量是`eventsMapName`，这跟创建map时用的`pkg/maps/eventsmap/eventsmap.go下的MapName`不是同一个，而是重新定义一个。影响代码分析。

```golang
path := oldBPF.MapPath(eventsMapName)
eventsMap, err := ebpf.LoadPinnedMap(path, nil)COPY
```

在handleEvents函数中进行事件读取，并对异常错误进行计数，用作数据完整性校对。（笔者还没细跟进）

```go
func (a *Agent) processPerfRecord(scopedLog *logrus.Entry, record perf.Record) {
    a.Lock()
    defer a.Unlock()

    if record.LostSamples > 0 {
        // 丢失数据大小统计
        a.MonitorStatus.Lost += int64(record.LostSamples) 
        // 通知所有内部消费者，告诉他们数据丢失部分大小
        a.notifyPerfEventLostLocked(record.LostSamples, record.CPU)

        // 存入外部订阅者队列，在队列的消费处，发送给所有监听者
        a.sendToListenersLocked(&payload.Payload{
            CPU:  record.CPU,
            Lost: record.LostSamples,
            Type: payload.RecordLost,
        })

    } 
    // ...
}COPY
```

这里的事件发送分为两种接受者

1. monitor进程内部的消费者，抽象为`consumer.MonitorConsumer`，比如数据丢失监控、事件处理dispather派发器等。对应`consumers`属性，使用`RegisterNewConsumer`函数来注册为消费者。
2. monitor进程外部的订阅者，抽象为`listener.MonitorListener`，比如与其交互的外部进程，远程数据数据库、中心事件处理总控等。对应`newListener`属性，使用`RegisterNewListener`函数注册，目前只支持自定义的`Version1_2`，方便以后扩展。

不管是`consumer`还是`listener`，都是一对多的关系，遍历多个`consumers\listener`进行发送。

cilium的配套可视化组件Hubble就是作为其中一个`consumer`来接收数据的。

对于事件的进程外部发送，cilium采用本地unix socket的方式，监听`/var/run/cilium/monitor1_2.sock`，来支持本机进程间数据通讯。

```go
func ServeMonitorAPI(monitor *Agent) error {
    listener, err := buildServer(defaults.MonitorSockPath1_2)
    if err != nil {
        return err
    }

    s := &server{
        listener: listener,
        monitor:  monitor,
    }

    log.Infof("Serving cilium node monitor v1.2 API at unix://%s", defaults.MonitorSockPath1_2)

    go s.connectionHandler1_2(monitor.Context())

    return nil
}COPY
```

#### 小结

对于内核态程序、稳定性质量做监控，结合内核态数据对服务更好的掌控。
事件的派发角色需要结合业务，进程内消费角色如何划分（对账、解码），进程间消费角色如何设计，多版本升级，通许协议如何设计等。
cilium在代码层面，角色功能上做了非常好的抽象，扩展性比较好。比如`MonitorListener`接口设计时，只规范了`Enqueue(pl *payload.Payload)`、`Version() Version`、`Close()`三个方法，实现的时候，可以随意扩展。

### 用户态写，内核态读

以XDP层的IP过滤为例，对应map path ： cilium_cidr_v4_dyn，来给大家讲一下这个场景。

事件触发是由HTTP接口接收控制指令触发的，在`daemon/cmd/prefilter.go`的55行附近，`patchPrefilter.Handle`函数接收HTTP request，读取策略文件中的CIDRs，准备调用`preFilter.Insert`写入到eBPF Maps中。

reFilter.Insert是接口函数，抽象的实现在`pkg/datapath/prefilter/prefilter.go`119行Insert函数中实现。

#### 打开

CIDRs写入到eBPF maps里之前，先进行map选择

```go
for _, cidr := range cidrs {
    ones, bits := cidr.Mask.Size()
    which := p.selectMap(ones, bits)
    if which == mapCount || p.maps[which] == nil {
        ret = fmt.Errorf("No map enabled for CIDR string %s", cidr.String())
        break
    }
    err := p.maps[which].InsertCIDR(cidr)
    if err != nil {
        ret = fmt.Errorf("Error inserting CIDR string %s: %s", cidr.String(), err)
        break
    } else {
        undoQueue = append(undoQueue, cidr)
    }
}COPY
```

循环遍历CIDRs，每个IP都判断是IPv4还是IPv6，选择对应的map，准备写入。写入的map在PreFilter.initOneMap函数里做了初始化读取。 先判断IP的类型`prefixesV4Dyn`、`prefixesV4Fix`、`prefixesV6Dyn`、`prefixesV6Fix`，再调用pkg/maps/cidrmap/cidrmap.go中147行`cidrmap.OpenMapElems`函数打开当前map。

打开map时，会先尝试创建`bpf.MapTypeLPMTrie`类型（也就是`BPF_MAP_TYPE_LPM_TRIE`类型）的map，若不支持，则改为`MapTypeHash`类型，来兼容低版本内核的linux。

#### 写入

PreFilter.Insert调用CIDRMap.InsertCIDR，再调用bpf.UpdateElement写入相应CIDRs。

#### 内核态读取

在`bpf/bpf_xdp.c`的`check_v4`函数中，`map_lookup_elem`函数查找`CIDR4_LMAP_NAME`eBPF map，若包含在内，则直接返回`CTX_ACT_DROP`丢弃包。

```c
#ifdef CIDR4_LPM_PREFILTER
    if (map_lookup_elem(&CIDR4_LMAP_NAME, &pfx))
        return CTX_ACT_DROP;
#endifCOPY
```

这段代码在`__section("from-netdev")`段运行，起到XDP层就可以过滤IP的作用。

`CIDR4_LMAP_NAME`常量就是对应的`cilium_cidr_v4_dyn` eBPF map ，老样子，也是由go层的代码生成的`filter_config.h`头文件，会把`CIDR4_LMAP_NAME`改为全路径的`cilium_cidr_v4_dyn`。

其中，go部分生成头文件的地方在`pkg/datapath/prefilter/prefilter.go`的59行`WriteConfig`函数里。

```go
fmt.Fprintf(fw, "#define CIDR4_LMAP_NAME %s\n", path.Base(p.maps[prefixesV4Dyn].String()))COPY
```

#### 小结

- eBPF map可以做内核态用户态数据交互
- 不同数据类型，选择不同的eBPF map类型，LPMTrie与HASH当前类库都支持。
- 在自己的项目中，也可以考虑内核态做基本的过滤策略，且策略内容可以动态下发。

# 总结

Cilium产品是面向微服务场景下的网络管理方案，涉及的安全也只是网络链路的可达性。对系统安全几乎没有涉猎。
但该产品是使用eBPF技术大规模应用的优秀项目之一，分析学习他的实现，可以帮助我们快速理解eBPF在go语言中的使用技巧。

通过笔者的分析学习，可以宏观的了解到Cilium在eBPF内核技术使用时，场景覆盖网络处理的XDP、TC、SOCKET等L3、L4、L7层，业务覆盖防火墙、网络路由、网络隔离、负载均衡等。通过集中式管理eBPF文件源码，下发到各endpoint分发式编译挂载。调试日志作为eBPF map事件统一收集处理。 支持用户态、内核态相互之间用eBPF map做双向通讯，实现策略下发与数据收集。具备数据对账、监控告警能力。

不足的地方在资源占用、熔断机制等功能。但考虑到cilium是宿主机上主要业务，CPU、内存等资源优先使用，对熔断机制需求不强烈。 这点不同于HIDS等安全防御产品，需要让资源给业务，严格控制自身资源使用。



## Cilium datapath加载流程

### cilium中ebpf map构成

![the maps of cilium](../../../assets/cilium%E6%A0%B8%E5%BF%83%EF%BC%88cilium-daemon%EF%BC%89%E5%AE%9E%E7%8E%B0%E6%BA%90%E7%A0%81%E5%88%86%E6%9E%90/1614297479000.png)

### 2.1 公共ebpf map的初始化

cilium有很多公用的ebpf map，这些map在ebpf prog加载前被创建：

```undefined
runDaemon() =>NewDaemon() =>Daemon.initMaps()
```

- **cilium_call_policy**，PROG_ARRAY，用来装“to-contaner”
- **cilium_ct4_global**，CT表，for tcp
- **cilium_ct_any4_global**，CT表，for non-tcp
- cilium_events，
- **cilium_ipcache**，ip+mask -> sec_label + VETP,如果是本地，则VETP为0
- cilium_ipv4_frag_datagrams
- cilium_lb4_affinity
- cilium_lb4_backends
- cilium_lb4_reverse_nat
- cilium_lb4_reverse_sk
- cilium_lb4_services_v2
- cilium_lb_affinity_match
- **cilium_lxc**，本地endpoint对应的netdev，ip -> NETDEV-INFO
- cilium_metrics
- cilium_nodeport_neigh4
- cilium_signals
- cilium_snat_v4_external
- **cilium_tunnel_map**，ip -> VETP，只记录非本地的ip

### 2.2 基础网络构建(init.sh)

#### 2.2.1 初始化参数

- LIB=/var/lib/cilium/bpf，bpf源码所在目录
- RUNDIR=/var/run/cilium/state，工作目录
- IP4_HOST=10.17.0.7，cilium_host的ipv4地址
- IP6_HOST=nil
- MODE=vxlan，网络模式
- **NATIVE_DEVS**=eth0，出口网卡，可以手动指定，没指定的话就看默认路由走那个口
- XDP_DEV=nil
- XDP_MODE=nil
- MTU=1500
- IPSEC=false
- ENCRYPT_DEV=nil
- HOSTLB=true
- HOSTLB_UDP=true
- HOSTLB_PEER=false
- CGROUP_ROOT=/var/run/cilium/cgroupv2
- BPFFS_ROOT=/sys/fs/bpf
- NODE_PORT=true
- NODE_PORT_BIND=true
- MCPU=v2
- NODE_PORT_IPV4_ADDRS=eth0=0xc64a8c0
- NODE_PORT_IPV6_ADDRS=nil
- NR_CPUS=64

#### 2.2.2 具体工作

1）创建了cilium_host和cilium_net；

2）如果是vxlan模式，添加并设置vxlan口cilium_vxlan；

3）编译并加载cilium_vxlan相关的prog和map；

> **2个map：**
>
> - cilium_calls_overlay_2，每个endpoint都有自己独立的tail call map，2是init.sh脚本固定写死的ID_WORLD；
> - cilium_encrypt_state
>
> **6个prog：**
>
> - from-container：bpf_overlay.c
> - to-container：bpf_overlay.c
> - cilium_calls_overlay_2【1】 = __send_drop_notify：lib/drop.h
> - cilium_calls_overlay_2【7】 = tail_handle_ipv4：bpf_overlay.c
> - cilium_calls_overlay_2【15】= tail_nodeport_nat_ipv4：lib/nodeport.h
> - cilium_calls_overlay_2【17】= tail_rev_nodeport_lb4：lib/nodeport.

4）删除出口网卡已经挂载的ebpf程序（from-netdev和to-netdev）

5）加载LB相关ebpf和map；

```load
tc exec bpf pin /sys/fs/bpf/tc/globals/cilium\_cgroups\_connect6 obj bpf\_sock.o type sockaddr attach\_type connect6 sec connect6
tc exec bpf pin /sys/fs/bpf/tc/globals/cilium\_cgroups\_post\_bind6 obj bpf\_sock.o type sock attach\_type post\_bind6 sec post\_bind6
tc exec bpf pin /sys/fs/bpf/tc/globals/cilium\_cgroups\_sendmsg6 obj bpf\_sock.o type sockaddr attach\_type sendmsg6 sec sendmsg6
tc exec bpf pin /sys/fs/bpf/tc/globals/cilium\_cgroups\_recvmsg6 obj bpf\_sock.o type sockaddr attach\_type recvmsg6 sec recvmsg6
tc exec bpf pin /sys/fs/bpf/tc/globals/cilium\_cgroups\_connect4 obj bpf\_sock.o type sockaddr attach\_type connect4 sec connect4
tc exec bpf pin /sys/fs/bpf/tc/globals/cilium\_cgroups\_post\_bind4 obj bpf\_sock.o type sock attach\_type post\_bind4 sec post\_bind4
tc exec bpf pin /sys/fs/bpf/tc/globals/cilium\_cgroups\_sendmsg4 obj bpf\_sock.o type sockaddr attach\_type sendmsg4 sec sendmsg4
tc exec bpf pin /sys/fs/bpf/tc/globals/cilium\_cgroups\_recvmsg4 obj bpf\_sock.o type sockaddr attach\_type recvmsg4 sec recvmsg4
```

6）XDP、FLANNEL、IPSEC相关初始化暂未研究

### 2.3 剩余的初始化工作

1）cilium_host的datapath

```python
tc[filter replace dev cilium_host ingress prio 1 handle 1 bpf da obj 554_next/bpf_host.o sec to-host]
tc[filter replace dev cilium_host egress prio 1 handle 1 bpf da obj 554_next/bpf_host.o sec from-host]
```

> **说明**：加载了2 + 5 个prog，1个PROG_ARRAY map，1个cilium_policy_00554 map
>
> - PROG：
>   from-host、to-host
> - PROG_ARRAY_MAP：
>   cilium_calls_hostns_00554（554是epid）
> - PROG IN PROG_ARRAY_MAP：
>   cilium_calls_hostns_00554【1】= __send_drop_notify
>   cilium_calls_hostns_00554【7】= tail_handle_ipv4_from_netdev => tail_handle_ipv4(ctx,false)
>   cilium_calls_hostns_00554【15】= tail_nodeport_nat_ipv4
>   cilium_calls_hostns_00554【17】= tail_rev_nodeport_lb4
>   cilium_calls_hostns_00554【22】= tail_handle_ipv4_from_host => tail_handle_ipv4(ctx, true)

2）cilium_net的datapath

```python
tc[filter replace dev cilium_net ingress prio 1 handle 1 bpf da obj 554_next/bpf_host_cilium_net.o sec to-host]
```

> - **说明**：加载了1 + 5个prog，1个PROG_ARRAY map
> - PROG：
>   to-host
> - PROG_ARRAY_MAP：
>   cilium_calls_netdev_00004（4是ifindex，ip link命令可以查看）
> - PROG IN PROG_ARRAY_MAP：
>   cilium_calls_netdev_00004【1】= __send_drop_notify
>   cilium_calls_netdev_00004【7】= tail_handle_ipv4_from_netdev => tail_handle_ipv4(ctx,false)
>   cilium_calls_netdev_00004【15】= tail_nodeport_nat_ipv4
>   cilium_calls_netdev_00004【17】= tail_rev_nodeport_lb4
>   cilium_calls_netdev_00004【22】= tail_handle_ipv4_from_host => tail_handle_ipv4(ctx, true)

3）eth0的datapath

```python
tc[filter replace dev eth0 ingress prio 1 handle 1 bpf da obj 554_next/bpf_netdev_eth0.o sec from-netdev]
tc[filter replace dev eth0 egress prio 1 handle 1 bpf da obj 554_next/bpf_netdev_eth0.o sec to-netdev]
```

> **说明：**加载了2+5个prog，1个PROG_ARRAY map
>
> - PROG：
>   from-netdev、to-netdev
> - PROG_ARRAY_MAP：
>   cilium_calls_netdev_00002（4是ifindex，ip link命令可以查看）
> - PROG IN PROG_ARRAY_MAP：
>   cilium_calls_netdev_00002【1】= __send_drop_notify
>   cilium_calls_netdev_00002【7】= tail_handle_ipv4_from_netdev => tail_handle_ipv4(ctx,false)
>   cilium_calls_netdev_00002【15】= tail_nodeport_nat_ipv4
>   cilium_calls_netdev_00002【17】= tail_rev_nodeport_lb4
>   cilium_calls_netdev_00002【22】= tail_handle_ipv4_from_host => tail_handle_ipv4(ctx, true)

4）lxc_health的datapath，**跟增加一个pod的datapath是完全一样的**

```python
tc[filter replace dev lxc_health ingress prio 1 handle 1 bpf da obj 908_next/bpf_lxc.o sec from-container]
```

> **说明**：加载了1+4+1个prog，1个PROG_ARRAY map，1个cilium_policy_00908 map
>
> - PROG：
>   from-container
> - PROG IN PROG_ARRAY_MAP：
>   cilium_calls_00908【1】= __send_drop_notify
>   cilium_calls_00908【6】= tail_handle_arp
>   cilium_calls_00908【15】= tail_nodeport_nat_ipv4
>   cilium_calls_00908【17】= tail_rev_nodeport_lb4
>   cilium_call_policy[908] = handle_policy(to-container好像已经废弃了)