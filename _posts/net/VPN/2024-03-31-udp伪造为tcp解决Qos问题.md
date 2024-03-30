---
layout: post
title: udp伪造为tcp解决Qos问题
category: net
typora-root-url: ../../..
---

> 转自：[聊聊运营商对UDP的QoS限制和应对](https://blog.csdn.net/dog250/article/details/113706995)
>
> by dog250大神

### UDP和运营商有什么关系？

这个问题有点大且突兀。只要不是在三大运营商上班的，其实我们都是端到端用户，而端到端用户对于网络的认知必然是盲目的，我们不知道路由器对我们的流量做了什么，我们更没有能力去控制它们，我们只能猜测。

本来一个技术范畴的讨论一旦涉及到了猜测，就不是技术讨论了，而是社会学讨论，这往往会带来无休止的辩论，争吵，在此其中，独占鳌头的往往不是靠技术实力，而是靠口才和措辞，或者还有夹杂着各种手势的抑扬顿挫。

我是极其讨厌充斥着此类调调的场合的，我在这种场合往往会选择闭嘴，然后离开。

人们无休止地讨论如何针对CC(Congestion Control)进行调优，其实每个人心里都没底，说出来的貌似令人信服的话靠的无非就是自信和强势，然后结论会瞬间打脸这种信口开河。

摘录一段深信服白皮书上的话：

> 如上图所示，刚好与传统 TCP“慢上升、快下降”相对，HTP 快速传输协议对于数据传输为“快上升、慢下降”。当网络吞吐允许的情况下以最短的时间将传输速度提高到吞吐量所允许的最高；

搞得好像真的一样，但其实这简直就是扯淡！

很多人都说QUIC其实不如TCP，这个结论我至今都不知道从哪个 “权威” 那里得到的，就好像人们人云亦云地诟病Netfilter/iptales一样。可是当你测试的时候，却发现 并不是每次 QUIC都不如TCP。

人们很少去深入探究中间网络，就好像开着个跑车在闹市区依然总觉得自己能起飞一样，说起运营商和TCP/UDP的关系，人们总是避而不谈，结论往往就两种：

* 你傻X啊，运营商和TCP/UDP毫无关系。
* 你想多了(或者就是脑子是个好东西…)，运营商会深度解析你的每一个数据包的。

说的跟真事儿一样，就好像他们无所不知的样子。我不明白这些懂点儿网络的人为什么总是学不会懂礼貌，其实我脾气也不好，我心里早就一万个XXX了。

但如果哪一天我也想聊聊这种话题，我会从一个具体的事情开始。嗯，今天就是，2021年春节前最后的一个周末。

我不能理解的一个问题是 一个UDP socket为什么不能多次bind不同的端口。 UDP本身就是无状态无连接的，它想发数据的时候，随时抓一个和其它五元组不冲突的端口使用即可，但事实上在一个UDP socket的生命周期内，它的源端口是不会变的，这看起来对UDP施加了更紧的约束，我觉得这是不合理的，这种约束也太不UDP了。

我们看下面的代码：

```python
#!/usr/bin/python3

import socket
#import sys

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

server_address = ('192.168.56.101', 1234)
message = str.encode('aaaaaaaaaaaaaaaaaaaaa')
sport = 4321

while True:
        sent = sock.sendto(message, server_address)
        sock.bind(('192.168.56.102', sport))
        sport = sport + 1
```

当你执行的时候，你会得到下面的报错：

```
Traceback (most recent call last):
  File "./udpsender.py", line 14, in <module>
    sock.bind(('192.168.56.102', sport))
OSError: [Errno 22] Invalid argument
```


至少在Linux上是这样的。

这是因为Linux禁止double bind：

```
int __inet_bind(struct sock *sk, struct sockaddr *uaddr, int addr_len,
		bool force_bind_address_no_port, bool with_lock)
{
	...
	/* Check these errors (active socket, double bind). */
	err = -EINVAL;
	if (sk->sk_state != TCP_CLOSE || inet->inet_num)
		goto out_release_sock;
	...
}
```


OK，既然我这么笃信这是不合理的，改了它便是了，执行下面的脚本：

```
#!/usr/bin/stap -g

%{
#include <net/inet_sock.h>
%}

function alter(ssk:long)
%{
	struct sock *sk = (struct sock *)STAP_ARG_ssk;
	struct inet_sock *inet = inet_sk(sk);
	sk->sk_prot->unhash(sk);
	inet->inet_num = 0;
%}

probe kernel.function("__inet_bind")
{
	alter($sk);
}
```


现在再来执行上面的python脚本试试看。

我们主要应该关注的是如果UDP socket每次发包都换一个不同的源端口，这将会在短时间内创造大量的五元组。这个事实会影响运营商的决策。

传统的状态防火墙，状态NAT会用一个 五元组 来追踪一条 连接 。如果连接过多，就会对这些保存状态的设备造成很大的压力，这种压力主要体现在两个方面：

- 存储压力：设备不得不配置大量的内存来保存大量的连接。
- 处理器压力：设备不得不在数据包到来的时候花更多的时间来匹配到一条连接。

由于UDP的无状态特征，没有任何报文指示一条连接什么时候该创建什么时候该销毁，设备必须有能力自行老化已经创建的UDP连接，且不得不在权衡中作出抉择：

- 如果老化时间过短，将会破坏正常通信但通信频率很低的UDP连接。
- 如果老化时间过长，将会导致已经无效的UDP连接消耗大量的内存，这将为DDoS攻击创造一个攻击面。

攻击者只需要用不同的UDP五元组构造报文使其经过状态设备即可，由于UDP报文没有任何指示连接创建销毁的控制信息，状态设备不得不平等对待任何新来的五元组，即为它们创建连接，并且指定相同的老化时间。TCP与此完全不同，由于存在syn，fin，rst等控制信息，状态设备便可以针对不同状态的TCP连接指定不同的老化时间，ESTABLISHED状态的连接显然要比其它状态的连接老化时间长得多。

这导致使用TCP来实施同样的攻击会困难很多。

为什么，为什么快速构造不同的TCP五元组达不到UDP同样的效果？

- 如果你只是盲目的用不同源端口发送syn，在没有真正的对端回应的情况下，这种状态的连接将会很快老化掉(10秒以内，甚至更短)。
- 如果你构造使用不同端口的大量真正的TCP连接，那么在状态设备受到伤害的同时，你自己也必须付出巨大的代价来维持住这些连接。
- …

你发起一个TCP连接，为了让状态设备保存这条连接，你自己也不得不保存这条连接，除非你通过海量的反射主机同时发起真连接，否则在单台甚至少量的主机上，这种攻击很难奏效。

办法也不是没有，如果你能在三次握手成功创建连接后迅速关掉它们，同时阻止任何rst，fin报文的发出，攻击可能会简单一些。

![在这里插入图片描述](../../../assets/udp%E4%BC%AA%E9%80%A0%E4%B8%BAtcp%E8%A7%A3%E5%86%B3Qos%E9%97%AE%E9%A2%98/20210207092436391.png)

在S上执行下面的命令：

```
while true; do telnet 172.18.0.1 22;done
```


刷一波之后，在Midbox上查看conntrack条目：

```
# conntrack -L -p tcp src 172.16.0.1|grep ESTABLISHED |wc -l
conntrack v1.4.5 (conntrack-tools): 14118 flow entries have been shown.
14117
```

而此时，S和D上均早已经看不见任何连接了：

```
# netstat -antp|grep 172.16.0.1 |wc -l
0
```

此外，不通过协议栈，构造raw报文来进行TCP握手进行攻击，本地不保存任何TCP连接信息显然是一种 更佳 的方法，因为我懒得去写那么多代码，也不想折腾scapy这种东西，就只能用上述iptables/stap的方式模拟了。

然而无论怎样，TCP做类似的攻击依然达不到UDP快速构建连接损害状态设备的效果，至少效率损失个3倍(需要三次握手)起跳吧。

好了，结束对状态设备的讨论。现在问题又来了，如果是非状态设备呢？

既然是无状态设备，我们便不必再纠结五元组连接的保持了。但是UDP短期构造海量五元组的能力仍然会影响无状态设备包分类算法的正常运行。基于包分类算法的优先级队列，缓存管理几乎也是通过五元组计算来完成的，UDP的特征将会使无状态设备对其做流量管控变得困难。其结果就是，眼睁睁任凭UDP流量挤满各级队列缓存却没有办法将其精确识别出来，即便是BBR遇到了UDP流量，也只能自降pacing rate而兴叹，在它看来，瓶颈带宽是真的减小了，运营商设备本应该做的更多，然而它却无能为力。

运营商(特别是国内运营商)显然没有能力和精力根据TCP和UDP的不同去深度定制不同的QoS策略，一刀切显然是最便捷的手段。

当然，国内运营商的带宽套餐超卖可能会导致下面的事情的发生(本人从不同非技术渠道获知，用技术手段确认)：

* 自然月月初，为了给套餐用户极佳的体验，会在高峰期对几乎所有UDP流量进行限制，包括丢包，低优先级队列，限速等等。
* 自然月月末，很多套餐用户流量已经超限，会适当放开对UDP流量的管制来实现自然限速。

这就是我为什么总是提倡 “在自然月月初的时候把你的UDP流量的UDP头换成TCP头，接收端再换回来” 的原因。

当我说这个话的时候，我听到过两种意思截然相反的反对声音：

- 运营商的设备根本不会去检测每一个报文到底是TCP还是UDP，更不会做深度包解析，这会严重影响性能。所以换头这个方法几乎没用。
- 运营商的设备会检查每一个经过的报文，很容易发现你这个假的TCP头，这么做更容易导致你的报文被丢弃。所以换头这个方法几乎没用。

我不知道这些人出于什么目的，我和他们并不熟识，只是单纯的讨论技术而已，在我要求他们给出理论分析或者至少给出测试数据的时候，他们便再也不回复了，我不知道他们是出于什么心态处处反驳，大概是为了彰显一下自己？不得而知。为了怼而怼没有意义，还是要亲自试一下。

当我需要亲自试一下的时候，又有人出来怼了，大概是说，即便真的要这么做，何必换头，直接修改掉IP头的protocol字段即可。很多人煞有其事地告诉我，直接改个字段就行：

```
...
if (iph->protocol == IPPROTO_TCP) {
	iph->protocol = IPPROTO_UDP;
	ip_send_check(iph);
	udph->check = 0;
} else if (iph->protocol == IPPROTO_UDP) {
	iph->protocol = IPPROTO_TCP;
	ip_send_check(iph);
}
```


我敢保证他们绝对没有真的试过，因为当你真正去这么尝试的时候，就会发现，丢包率大大增加了，甚至根本无法通信！这个事实难道没有从反面证明换头操作会影响运营商的QoS策略吗？

下面是我测试这种情况的一个代码片段，它是一个udpping程序，每次发给对端一个随机的字符串，等待对端echo回来。首先在对端部署仅仅修改IP头protocol字段的逻辑，并且执行socat：

```
socat -v UDP-LISTEN:4321,fork PIPE
```


发送端同样部署上述的IP头换protocol字段的逻辑，执行发送的代码片段如下：

```
while True:
	payload= random_string(20)
	sock.sendto(payload.encode(), (IP, PORT))
	...
	recv_data,addr = sock.recvfrom(65536)
	if addr[0]==IP and addr[1]==PORT:
		rtt=((time.time()-time_of_send)*1000)
		print("Reply from",IP,"seq=%d"%count, "time=%.2f"%(rtt),"ms")
	...
```


很遗憾，结果如下：

```
# 地址和rtt为伪造，真实测试链路为上海到日本。
Reply from 123.123.123.123 seq=97 time=25.41 ms
Request timed out
Request timed out
Request timed out
Reply from 123.123.123.123 seq=101 time=25.41 ms
Request timed out
Reply from 123.123.123.123 seq=103 time=25.44 ms
Reply from 123.123.123.123 seq=104 time=25.39 ms
Request timed out
Request timed out
Request timed out
Reply from 123.123.123.123 seq=108 time=25.40 ms
Reply from 123.123.123.123 seq=109 time=25.43 ms
```

由于发包程序发送的是random字符串，它们将会被解析成TCP头超过UDP头大小的部分，抓包可以一窥究竟，它可以分别被解析成下面的样子：

```
IP (tos 0x20, ttl 64, id 60168, offset 0, flags [DF], proto TCP (6), length 128)
    111.111.111.111.1234 > 123.123.123.123.4321: Flags [FSRPUE], cksum 0x5651 (incorrect -> 0x1bba), seq 7108832:7108912, win 17975, urg 19510, options [[bad opt]
...
IP (tos 0x20, ttl 64, id 60969, offset 0, flags [DF], proto TCP (6), length 128)
    111.111.111.111.1234 > 123.123.123.123.4321:  tcp 96 [bad hdr length 12 - too short, < 20]
...
IP (tos 0x20, ttl 64, id 63113, offset 0, flags [DF], proto TCP (6), length 128)
    111.111.111.111.1234 > 123.123.123.123.4321: Flags [RE], cksum 0x5430 (incorrect -> 0x8e6e), seq 7108832:7108920, win 20022, length 88 [RST+ lCufDCd5oRmJCW02dV6coRDKCGVmJc]
```


嗯，结果大概就是这个样子。

仅仅修改IP头的protocol字段，仅仅将TCP修改成UDP为什么不行？

因为运营商状态设备确实会检查TCP报文中的syn，ack，fin，rst等标志(否则它们如何创建连接呢？)，如果状态设备确实检查了这些标志，那么它就会在内部维护一个TCP连接的状态机，至少大概是这样，如果你的TCP报文序列严重违反了TCP状态机，结果可想而知。

> 如果只是设置了syn而没有设置ack，并且这个伪造的TCP报文还携带数据，在我的测试环境中则是被100%丢弃。

如果你只是修改了IP头的protocol字段，比方说改成了TCP，那么运营商设备就会将后面的UDP头解析成TCP头，由于UDP头只有8个字节，而TCP头的flag字段在8字节以外，因此运营商设备会将UDP的payload解析成TCP头的flag字段，而UDP payload几乎可以是任意的。

> 感谢TCP头和UDP头的前两个字段是一致的！

因此，如果要执行UDP头换TCP头的操作，并不是如那些信口开河之人想象的那样简单的。至少我测试下来，需要做的是：

不要带syn标志，因为运营商设备可能会检查syn标志和payload的互斥性(即不允许fastopen)。
保持一个单调递增的的Seq Number以及一个单调递增的Ack Number。
没有必要非要发送伪造的syn和syn/ack，这个类似Linux nf_conntrack的nf_conntrack_tcp_loose配置，网络允许路由的不对称，因此loose是宽松的。
下面的代码片段将UDP换成TCP头，为了不妨碍Netfilter深度检测报文，这个代码要在POSTROUTING的最后执行：

```c
struct iphdr *iph = ip_hdr(skb), ihdr;
struct dst_entry *dst = NULL;
static unsigned int seq = 1239876;
static unsigned int ack_seq = 2345;

udph = (struct udphdr *)start;
ihdr = *iph;
uhdr = *udph;

if (iph->protocol != IPPROTO_UDP)
	goto out;

ihdr.protocol = IPPROTO_TCP;
oldlen = ntohs(ihdr.tot_len);
ihdr.tot_len = htons(oldlen + delta);

if ((dst = skb_dst(skb)) == NULL)
	goto out;

// 假TCP不支持TSO/GSO，因此由于新增了12字节的TCP和UDP头长差之后超过MTU的包不予换头。
if (oldlen + delta +  LL_RESERVED_SPACE(dst->dev) > dst_mtu(dst))
	goto out;

if (pskb_expand_head(skb, delta, 0, GFP_ATOMIC))
	goto out;

iph = (struct iphdr *)skb_push(skb, delta);
	*iph = ihdr;

skb_reset_network_header(skb);
skb_set_transport_header(skb, iph->ihl*4);

ip_send_check(iph);

tcph = (struct tcphdr *)skb_transport_header(skb);
tcph->source = uhdr.source;
tcph->dest = uhdr.dest;
tcph->seq = htonl(seq);
seq += 1000;
tcph->ack_seq = ack_seq;
tcph->syn = 0;
tcph->doff = 5;
tcph->ack = 1;
tcph->urg = 1;
tcph->rst = 0;
tcph->fin = 0;
tcph->window = htons(1000);
// 无需计算TCP校验和，因为我会在接收端将它换回UDP并且取消校验和检查，以实现真正的尽力而为的弱校验。
```


将UDP头换成TCP头之后，在另一端，我们需要执行相反的操作，将伪造的假TCP头再换回UDP，这个要更容易些，至少不需要expand_head了。

下面的代码在PREROUTING的raw之后conntrack之前执行，这是因为需要在iptables的raw表中对需要转换的数据包进行识别，并且要保证恢复UDP头之后不影响后续可能存在的nf_conntrack操作：

```c
struct iphdr *iph = ip_hdr(skb), ihdr;
struct dst_entry *dst = NULL;

udph = (struct udphdr *)start;
ihdr = *iph;
uhdr = *udph;

if (iph->protocol != IPPROTO_TCP)
	goto out;

ihdr.protocol = IPPROTO_UDP;
oldlen = ntohs(ihdr.tot_len);
ihdr.tot_len = htons(oldlen - delta);

iph = (struct iphdr *)skb_pull(skb, delta);
*iph = ihdr;

skb_reset_network_header(skb);
skb_set_transport_header(skb,  iph->ihl*4);

ip_send_check(iph);

udph = (struct udphdr *)skb_transport_header(skb);
udph->source = thdr.source;
udph->dest = thdr.dest;
udph->len = htons(ntohs(iph->tot_len) - sizeof(struct iphdr));
// 取消校验和，补偿下换头操作带来的额外延迟。
udph->check = 0;
```


下面是一个iperf测试中换头功能切换前后的抓包效果：

```
23:37:25.951045 IP 192.168.56.101.1234 > 192.168.56.102.4321: UDP, length 1000
23:37:25.957493 IP 192.168.56.101.1234 > 192.168.56.102.4321: UDP, length 1000
23:37:25.968388 IP 192.168.56.101.1234 > 192.168.56.102.4321: UDP, length 1000
23:37:25.973226 IP 192.168.56.101.1234 > 192.168.56.102.4321: UDP, length 1000
23:37:25.988933 IP 192.168.56.101.1234 > 192.168.56.102.4321: UDP, length 1000
23:37:25.988933 IP 192.168.56.101.1234 > 192.168.56.102.4321: UDP, length 1000
23:37:26.009427 IP 192.168.56.102.4321 > 192.168.56.101.1234: UDP, length 1000
23:39:03.572431 IP 192.168.56.101.1234 > 192.168.56.102.4321: Flags [.UEW], seq 8934678:8935678, ack 3458334720, win 1000, urg 43727, length 1000
23:39:03.580616 IP 192.168.56.101.1234 > 192.168.56.102.4321: Flags [.UEW], seq 1000:2000, ack 1, win 1000, urg 35592, length 1000
23:39:03.587336 IP 192.168.56.101.1234 > 192.168.56.102.4321: Flags [.UEW], seq 2000:3000, ack 1, win 1000, urg 28841, length 1000
23:39:03.597182 IP 192.168.56.101.1234 > 192.168.56.102.4321: Flags [.UEW], seq 3000:4000, ack 1, win 1000, urg 19029, length 1000
23:39:03.603321 IP 192.168.56.101.1234 > 192.168.56.102.4321: Flags [.UEW], seq 4000:5000, ack 1, win 1000, urg 12785, length 1000
23:39:03.610564 IP 192.168.56.101.1234 > 192.168.56.102.4321: Flags [.UEW], seq 5000:6000, ack 1, win 1000, urg 5600, length 1000
23:39:03.618043 IP 192.168.56.101.1234 > 192.168.56.102.4321: Flags [.UEW], seq 6000:7000, ack 1, win 1000, urg 63666, length 1000
```


好漂亮的序列。

关于重算IP头校验和的问题，很多人是很反感，总觉得这里会增加额外的处理延时。实际上这种校验和计算开销是可以忽略不计的。

校验和是一种非常弱的校验算法，它本质上就是就是将数据序列按照16bits拆分，然后将这些16bits数据加到一起，从这个基本原理可以看出，用 **加法交换律** 很容易实现 **修改数据而不改变校验和** 以及 **校验和增量重新计算** 。

下面的代码展示了通过修改IP头的id字段来弥补protocol字段和tot_len字段的的改变从而不改变原始的校验和：

```c
unsigned short old1 = *(unsigned short *)&iph->ttl; // ttl和protocol合体作为16bits参与计算
unsigned short old2 = *(unsigned short *)&iph->tot_len; // 换头后总长会改变
unsigned short *pID;

...// 修改protocol和总长
pID = (unsigned short *)&iph->id;
*pID -= *(unsigned *)&iph->ttl - old1;
*pID -= *(unsigned *)&iph->tot_len - old2;
```

我个人倾向于采用同时修改IPID和原始IP校验和的方式，因为这样可以应对中间设备对IPID的分布进行扫描：

- 同一台主机发出报文的IPID字段呈现伪递增趋势。
- 如果同一个源IP的IPID是乱序的，中间设备会认为这是被NAT的不同主机发出的，进而可能给出不同的排队优先级。

下面的代码实现了校验和的增量计算：

```
unsigned short old1 = *(unsigned short *)&iph->ttl; // ttl和protocol合体作为16bits参与计算
unsigned short old2 = *(unsigned short *)&iph->tot_len; // 换头后总长会改变

... // 修改protocol和总长
iph->check = ~iph->check + *(unsigned *)&iph->ttl - old1 + *(unsigned *)&iph->tot_len - old2;
iph->check = ~iph->check;
```

其实，由于IP头本身就很小，一共才10个bits，因此即便是重新全部计算一遍也不会有多大开销。而诸如TCP，UDP这种连带载荷一起计算的校验和才能算得上开销。慢载MSS的报文差不多需要700多次的计算。因此一般比如在做了NAT之后需要对TCP/UDP重新计算校验和的时候，会用增量计算，只计算改变的量，而IP头的校验和，无所谓咯。

> TCP校验和太弱了，以至于我们完全不可信任它，交换payload的两个16bits不会影响检验和的正确性，因此在我们下载文件的时候，一般会顺手下载一个MD5文件用来自行校验。

有点跑题，OK，言归正传。

我在公网上进行了测试，同样的上海到日本的链路，换头操作之后丢包率小幅降低但不是很明显，等哪天我找一条国内的链路在流量高峰期测试一把再看效果。

行文至此，可以看到，首先，运营商真的会根据UDP和TCP标志做区分对待，其次，UDP头换成TCP头传输在技术上是可行的。现在，我想最后聊一下这种技术适合做什么，不能做什么。

显然，TCP换头有个前提，你必须能控制两端，换句话说这是一个双边操作，这和IP/GRE/TCP/UDP/VXX等隧道技术非常相似，简直就是同一类东西。当你可以控制两端时，你才有能力去搭建一条隧道。那么隧道里封装什么呢？

在我看来，任何东西都可以封装在这个伪造的假TCP隧道里，当然，包括皮鞋和真丝的领带。

现在，让我们忽略隧道的概念。我可以把遇到的任意UDP头换成TCP头吗？比如DNS的流量？

当然可以！并且我建议你这么做！只要你能卡住该UDP流量必经路径上的两个点，你就可以在这两个点之间将UDP头换成TCP头，我的理由如下：

- 不要误会，我的TCP不会带来任何TCP意义上的开销，不保存连接，无重传，不保序，这是个假的TCP，只是一个TCP头罢了。
- 本来UDP就是尽力而为的，换成伪造的假TCP并不会让事情变得更糟糕。
- 运营商对TCP更加友好，对UDP不友好，但却无力深度检测TCP连接的真实性。