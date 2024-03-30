---
layout: post
title: tcp状态TIME_WAIT_用户层面
category: kernel
typora-root-url: ../../..
---

# 什么是 TIME_WAIT

我们都知道，TCP 关闭连接时，[主动关闭]连接一方会在接收到[被动关闭]连接一方的 FIN 包时，将会进入 TIME_WAIT 状态，再等待 2MSL 之后，再进入到 Closed 状态，以下是在 TCP 四次挥手的状态迁移图：

![tcp-close](../../../assets/tcp%E7%8A%B6%E6%80%81TIME_WAIT_%E7%94%A8%E6%88%B7%E5%B1%82%E9%9D%A2/tcp_close.png)

<!--more-->

> MSL : Max segment lifetime ，报文最大生存时间，是指任何报文在网络上存在的最长时间，超过这个时间报文将会被丢弃。在 Linux 系统中，MSL 被定义成 30 秒， 2MSL 就是 60 秒。

MSL 的定义可以参考linux (内核代码)[https://github.com/torvalds/linux/blob/c839682c719f0e3dc851951c9e2eeb8a41cd9609/include/net/tcp.h#L120]

```
#define TCP_TIMEWAIT_LEN (60*HZ) /* how long to wait to destroy TIME-WAIT
				  * state, about 60 seconds	*/
```

# 为什么要设计 TIME_WAIT 这个状态

假设没有 TIME_WAIT 这个状态的设计，也就意味着[主动关闭]的一方直接进入到 CLOSED 状态，这会导致出现如下的问题：

* 防止前一个连接【一个连接是指五元组，source ip|source port|dest ip|dest port|protocol】上发生延迟或者丢失重传的数据包，被后面的新的连接错误的接收。

![why-time-wait-1](../../../assets/tcp%E7%8A%B6%E6%80%81TIME_WAIT_%E7%94%A8%E6%88%B7%E5%B1%82%E9%9D%A2/why-time-wait-1.png)

上述图示中：SEQ = 3 的数据包被再次重传到新打开的连接上，数据被错误的接收了。

* 确保连接方能在时间范围内，关闭自己的连接。

![why-time-wait-2](../../../assets/tcp%E7%8A%B6%E6%80%81TIME_WAIT_%E7%94%A8%E6%88%B7%E5%B1%82%E9%9D%A2/why-time-wait-2.png)

[主动关闭]连接的一方最后一次回复 ACK 时，由于网络不可靠的原因，导致 ACK 丢失，那么[被动关闭]连接的一方停留在 LAST_ACK 状态。假设没有 TIME_WAIT 状态，或者没有等待 2MSL ，或者 MSL 的时间很短，下一个新建立的连接恰好是同一个五元组，由于之前的连接被动关闭的一方还停留在 LAST_ACK 状态，在接收到新打开连接的 SYN 包时，则会认为是一个错误的包，直接回复 RST ，**导致新的连接无法正常的建立**。

# TIME_WAIT 过多造成的影响

## socket 端口数量在 2MSL 时间段内被耗尽

从前文中我们可以分析出，在 2MSL 时间周期之内（也就是一分钟之内），同一个五元组的连接无法被使用。

我们假设一个高并发的互联网系统中，每一秒钟会建立 1000 个短连接，在 2MSL 的等待时间（一分钟）之内就会创建 60000 个连接，这意味着在 1 分钟之内都会处在 TIME_WAIT 状态，这些短连接都不会被释放。 而在默认的情况下，linux 内核允许打开的端口数量大约 30000 左右。这意味着，如果我们不调整默认的端口数量，将无法支撑单台服务器每秒钟 1000 个短链接的请求。

```
cat /proc/sys/net/ipv4/ip_local_port_range
32768   61000
```

## 一定程度的内存和 CPU 消耗

Linux 内核当中会有一个 hash table 保存当前的所有 socket 连接，在这个 hash table 中既有 TIME_WAIT 状态的连接，也包含其它状态的连接。可以通过如下命令去查看当前系统 hash table 的大小设置：

```
dmesg | grep "TCP established hash table"
[    0.285124] TCP established hash table entries: 8192 (order: 4, 65536 bytes)
```

除此之外，还有一个 hash table 用来保存所有的 bound ports ，主要可以快速的找到一个可用的端口或者随机端口：

```
dmesg | grep "TCP bind hash table"
[    0.285147] TCP bind hash table entries: 8192 (order: 5, 131072 bytes)
```

从占用内存的角度上来看， entries : 8192 个连接也就占用了 65536 bytes ，平均一个连接也才 8 byte ，实际的内存消耗非常非常少。

## how to trace TIME_WAIT status ?

利用 `ss` 工具可以轻松跟踪 TIME_WAIT 状态。

查看一台服务器上 TIME_WAIT 的总体数量：

```
ss -tan state time-wait | wc -l
```

如果数量较多，我们可能会关心到底是哪些进程，或者哪些服务产生了过多的 TIME_WAIT，比如如下的命令能够显示出服务器上 443 （https）端口的 TIME_WAIT 情况 ：

```
ss -o state time-wait '( sport = :443 )'
```

如果你还关心除了 time-wait 之外的其它状态的情况，可以结合 awk 进行统计：

```
ss -ant | awk '
    NR>1 {++s[$1]} END {for(k in s) print k,s[k]}
'
```

可以通过如下的方式统计出一台 server 上， 指定的端口服务连接了哪些 IP，连接了多少次 :

```
ss -tan 'sport = :443' | awk '{print $(NF)" "$(NF-1)}' | sed 's/:[^ ]*//g' | sort | uniq -c

1
1 * *
1 119.6.99.248 120.24.36.47
1 Address Peer
```

更多信息，可以参考：https://www.cyberciti.biz/tips/linux-investigate-sockets-network-connections.html

## 到底出现多少的 TIME_WAIT 状态的连接需要进行优化

一般的情况下，如果一台服务器上 TIME_WAIT 的连接数只有 20000 以下，笔者认为根本不需要过多关注。网络上有很多文章都在讨论过多的 TIME_WAIT 状态下的调优，但是我认为常规的情况下不应该打破 TCP 状态协议的规范。

如果一台服务器处理已经由于太多的 TIME_WAIT 导致无法正常的建立连接了，个人可以从如下几个层面考虑优化：

* 服务内核参数调整：
可以先看看 `ip_local_port_range` 能否还能再设置大一些，以便可以使用开启更多的端口（如何修改可以参考[这里](https://ma.ttias.be/linux-increase-ip_local_port_range-tcp-port-range/)）。

* 增加服务器：
既然一台机器已经无法承载更多的连接了，加服务器是最快捷和合理的方案。

* 尽量不要让服务器端成为主动关闭连接的一方：
设置服务器端的 KeepAlive ，尽可能不让服务器端主动关闭连接，而是让客户端连接，这样就不会出现 TIME_WAIT 过多的问题。


## 关于 tcp_timestamps、tcp_tw_reuse、tcp_tw_recycle、tcp_max_tw_buckets

如果你在 google 中搜索 `too many time_wait state connections` ，基本上都给出针对上述 3 个参数调优的方法。

我们首先来看看这 3 个参数的具体含义

### net.ipv4.tcp_timestamps

tcp_timestamps 是一个 TCP option （选项字段），它由一共 8 个字节表示时间戳，其中第一个 4 字节字段用来保存发送该数据包的时间，第二个 4 字节字段用来保存最近一次接收对方发送到达数据的时间。

### net.ipv4.tcp_tw_reuse

> tcp_tw_reuse - BOOLEAN
> Allow to reuse TIME-WAIT sockets for new connections when it is
> safe from protocol viewpoint. Default value is 0.
> It should not be changed without advice/request of technical
> experts.

ref by ： https://www.kernel.org/doc/Documentation/networking/ip-sysctl.txt

从字面上大概描述的意思是：允许在 `安全的情况`，让新的连接能够重用 TIME_WAIT 状态的 socket 连接，默认值为 0 。最后还增加了一个警告提示：请不要在没有专家指导的情况下去调整该参数。

关键在于：`safe from protocol viewpoint` 的定义是什么？什么样的情况下会重用链接了？可以参考如下的 Linux 内核的[代码](https://elixir.bootlin.com/linux/v3.2.99/source/net/ipv4/tcp_ipv4.c#L115)：

```
int tcp_twsk_unique(struct sock *sk, struct sock *sktw, void *twp)
{
	const struct tcp_timewait_sock *tcptw = tcp_twsk(sktw);
	struct tcp_sock *tp = tcp_sk(sk);

	/* With PAWS, it is safe from the viewpoint
	   of data integrity. Even without PAWS it is safe provided sequence
	   spaces do not overlap i.e. at data rates <= 80Mbit/sec.

	   Actually, the idea is close to VJ's one, only timestamp cache is
	   held not per host, but per port pair and TW bucket is used as state
	   holder.

	   If TW bucket has been already destroyed we fall back to VJ's scheme
	   and use initial timestamp retrieved from peer table.
	 */
	if (tcptw->tw_ts_recent_stamp &&
	    (twp == NULL || (sysctl_tcp_tw_reuse &&
			     get_seconds() - tcptw->tw_ts_recent_stamp > 1))) {
		tp->write_seq = tcptw->tw_snd_nxt + 65535 + 2;
		if (tp->write_seq == 0)
			tp->write_seq = 1;
		tp->rx_opt.ts_recent	   = tcptw->tw_ts_recent;
		tp->rx_opt.ts_recent_stamp = tcptw->tw_ts_recent_stamp;
		sock_hold(sktw);
		return 1;
	}

	return 0;
}
EXPORT_SYMBOL_GPL(tcp_twsk_unique);
```

重用 TIME_WAIT 连接的条件：
* 设置了 tcp_timestamps = 1，即开启状态。
* 设置了 tcp_tw_reuse = 1，即开启状态。
* 新连接的 timestamp 大于 之前连接的 timestamp 。
* 在处于 TIME_WAIT 状态并且持续 1 秒之后。`get_seconds() - tcptw->tw_ts_recent_stamp > 1` 。

重用的连接类型：仅仅只是 Outbound (Outgoing) connection ，对于 Inbound connection 不会重用。

安全指的是什么：
* TIME_WAIT 可以避免重复发送的数据包被后续的连接错误的接收，由于 timestamp 机制的存在，重复的数据包会直接丢弃掉。
* TIME_WAIT 能够确保被动连接的一方，不会由于主动连接的一方发送的最后一个 ACK 数据包丢失（比如网络延迟导致的丢包）之后，一直停留在 LAST_ACK 状态，导致被动关闭方无法正确地关闭连接。为了确保这一机制，主动关闭的一方会一直重传（ retransmit ） FIN 数据包。

### net.ipv4.tcp_tw_recycle

> tcp_tw_recycle - BOOLEAN
> Enable fast recycling TIME-WAIT sockets. Default value is 0. It should not be changed without advice/request of technical experts.

同样的，上述描述有几个问题：
* 与 2MSL 相比，fast recycling 有多快？
* 打开了该选项之后会产生什么问题？

内核代码可以参考[这里](https://elixir.bootlin.com/linux/v3.18.96/source/net/ipv4/tcp_minisocks.c#L266)

```
/*
 * Move a socket to time-wait or dead fin-wait-2 state.
 */
void tcp_time_wait(struct sock *sk, int state, int timeo)
{
	struct inet_timewait_sock *tw = NULL;
	const struct inet_connection_sock *icsk = inet_csk(sk);
	const struct tcp_sock *tp = tcp_sk(sk);
	bool recycle_ok = false;

	if (tcp_death_row.sysctl_tw_recycle && tp->rx_opt.ts_recent_stamp)
		recycle_ok = tcp_remember_stamp(sk);

	if (tcp_death_row.tw_count < tcp_death_row.sysctl_max_tw_buckets)
		tw = inet_twsk_alloc(sk, state);

	if (tw != NULL) {
		struct tcp_timewait_sock *tcptw = tcp_twsk((struct sock *)tw);
		const int rto = (icsk->icsk_rto << 2) - (icsk->icsk_rto >> 1);
		struct inet_sock *inet = inet_sk(sk);

		tw->tw_transparent	= inet->transparent;
		tw->tw_rcv_wscale	= tp->rx_opt.rcv_wscale;
		tcptw->tw_rcv_nxt	= tp->rcv_nxt;
		tcptw->tw_snd_nxt	= tp->snd_nxt;
		tcptw->tw_rcv_wnd	= tcp_receive_window(tp);
		tcptw->tw_ts_recent	= tp->rx_opt.ts_recent;
		tcptw->tw_ts_recent_stamp = tp->rx_opt.ts_recent_stamp;
		tcptw->tw_ts_offset	= tp->tsoffset;

#if IS_ENABLED(CONFIG_IPV6)
		if (tw->tw_family == PF_INET6) {
			struct ipv6_pinfo *np = inet6_sk(sk);

			tw->tw_v6_daddr = sk->sk_v6_daddr;
			tw->tw_v6_rcv_saddr = sk->sk_v6_rcv_saddr;
			tw->tw_tclass = np->tclass;
			tw->tw_flowlabel = be32_to_cpu(np->flow_label & IPV6_FLOWLABEL_MASK);
			tw->tw_ipv6only = sk->sk_ipv6only;
		}
#endif

#ifdef CONFIG_TCP_MD5SIG
		/*
		 * The timewait bucket does not have the key DB from the
		 * sock structure. We just make a quick copy of the
		 * md5 key being used (if indeed we are using one)
		 * so the timewait ack generating code has the key.
		 */
		do {
			struct tcp_md5sig_key *key;
			tcptw->tw_md5_key = NULL;
			key = tp->af_specific->md5_lookup(sk, sk);
			if (key != NULL) {
				tcptw->tw_md5_key = kmemdup(key, sizeof(*key), GFP_ATOMIC);
				if (tcptw->tw_md5_key && !tcp_alloc_md5sig_pool())
					BUG();
			}
		} while (0);
#endif

		/* Linkage updates. */
		__inet_twsk_hashdance(tw, sk, &tcp_hashinfo);

		/* Get the TIME_WAIT timeout firing. */
		if (timeo < rto)
			timeo = rto;

		if (recycle_ok) {
			tw->tw_timeout = rto;
		} else {
			tw->tw_timeout = TCP_TIMEWAIT_LEN;
			if (state == TCP_TIME_WAIT)
				timeo = TCP_TIMEWAIT_LEN;
		}

		inet_twsk_schedule(tw, &tcp_death_row, timeo,
				   TCP_TIMEWAIT_LEN);
		inet_twsk_put(tw);
	} else {
		/* Sorry, if we're out of memory, just CLOSE this
		 * socket up.  We've got bigger problems than
		 * non-graceful socket closings.
		 */
		NET_INC_STATS_BH(sock_net(sk), LINUX_MIB_TCPTIMEWAITOVERFLOW);
	}

	tcp_update_metrics(sk);
	tcp_done(sk);
}
```

通过 `const int rto = (icsk->icsk_rto << 2) - (icsk->icsk_rto >> 1);` 和 `tw->tw_timeout = rto;` ，可以分析出处在 TIME_WAIT 的等待时间是 3.5 * RTO 。那么 RTO （ Retransmission timeout ）是什么了? 具体可以参考[这篇文章](http://www.orczhou.com/index.php/2011/10/tcpip-protocol-start-rto/) ，简而言之就是会通过与 RTT 想结合的动态算法，动态计算出的一个时间，用于 TCP 判断在多久之后需要重传数据包。我们可以通过 `ss --info` 去查看对应连接的 RTO ，比如下面这个连接的 RTO 为 216 ，单位是 ms 。

```
ss -4 --info

Netid  State      Recv-Q Send-Q                                      Local Address:Port                                                       Peer Address:Port
tcp    ESTAB      0      0                                               127.0.0.1:55996                                                         127.0.0.1:mysql
         cubic wscale:7,7 rto:216 rtt:16/20.25 ato:40 mss:22400 cwnd:10 send 112.0Mbps lastsnd:2803099 lastrcv:2803099 lastack:2803059 rcv_rtt:1 rcv_space:43690
```

Linux 内核当中写死了 MIN RTO = 200 ms ，MAX RTO = 120 s。 一般场景下，在局域网范围内 RTO 的大小大概为 200 ms， 3.5 * 200 = 700 ms ，因此它是远远小于 2MSL （1 秒）时间的。

下面我们来讨论一下，设置快速回收了之后会产生什么问题。假设我们一台阿里云云服务器上部署了测试环境的 nginx ，并且在这台服务器上打开了 tw_recycle 的设置， 如果客户端连接服务器端处在一个 NAT 网络中（例如，我们工作的办公室中的，所有的 PC 电脑都是通过**同一个公网 IP** 访问 internet 的）, 就可能导致在一个 3.5 个 RTO 之内，在 NAT 环境中所有客户端，只能有其中的一个能够成功连接成功（因为时间戳小的数据包会被直接丢弃）。

因此我们建议不要开启 tw_recycle 配置。事实上，在 linux 内核 4.12 版本，已经去掉了 net.ipv4.tcp_tw_recycle 参数了，参考[这里](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/commit/?id=4396e46187ca5070219b81773c4e65088dac50cc)


### tcp_max_tw_buckets

> tcp_max_tw_buckets - INTEGER
> Maximal number of timewait sockets held by system simultaneously.
> If this number is exceeded time-wait socket is immediately destroyed
> and warning is printed. This limit exists only to prevent
> simple DoS attacks, you _must_ not lower the limit artificially,
> but rather increase it (probably, after increasing installed memory),
> if network conditions require more than default value.

设置 TIME_WAIT 最大数量。目的为了阻止一些简单的DoS攻击，平常不要人为的降低它。如果缩小了它，那么系统会将多余的TIME_WAIT删除掉，日志里会显示：「TCP: time wait bucket table overflow」。


# 参考文章

https://vincent.bernat.im/en/blog/2014-tcp-time-wait-state-linux
https://huoding.com/2012/01/19/142
https://mp.weixin.qq.com/s?__biz=MzI4MjA4ODU0Ng==&mid=402415747&idx=1&sn=2458ba4fe1830eecdb8db725d3f395fa&scene=1&srcid=0317kixDKODOMBEMqjenW4Jb