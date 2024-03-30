---
layout: post
title: MASQUERADE源IP和源端口选择策略
category: kernel
typora-root-url: ../../..
---

## 源码分析

内核版本：5.10

调用流程：

```shell
/net/netfilter/xt_MASQUERADE.c::masquerade_tg_reg
  .target = masquerade_tg,
  /net/netfilter/xt_MASQUERADE.c::masquerade_tg()
    /net/netfilter/nf_nat_masquerade.c::nf_nat_masquerade_ipv4()
      # 查路由表获取到源地址
      #获取路由表
      rt = skb_rtable(skb);
      #获得下一跳的地址
      nh = rt_nexthop(rt, ip_hdr(skb)->daddr);
      #选择最合适的SNAT源地址
      newsrc = inet_select_addr(out, nh, RT_SCOPE_UNIVERSE);
      ...
      #设置可用的源地址和源端口范围
      newrange.min_addr.ip = newsrc;
      newrange.max_addr.ip = newsrc;
      newrange.min_proto   = range->min_proto;
      newrange.max_proto   = range->max_proto;
      ...
      #根据可用范围确定SNAT源地址，修改ct
      /net/netfilter/nf_nat_core.c::nf_nat_setup_info()
        #从可用范围中获取唯一的五元组
        /net/netfilter/nf_nat_core.c::get_unique_tuple()
        ...
        #修改conntrack中的回包的五元组
        /net/netfilter/nf_conntrack_core.c::nf_ct_invert_tuple();
        ...
        #将连接记录添加到bysource表中，用于get_unique_tuple()中查找最近SNAT的连接记录
        if (maniptype == NF_NAT_MANIP_SRC) {
          ...
          srchash = hash_by_src()
          ...
          hlist_add_head_rcu(&ct->nat_bysource, &nf_nat_bysource[srchash])
          ...
        }
```

下面我们重点分析一下`/net/netfilter/nf_nat_core.c::get_unique_tuple()`如何获取唯一的五元组：

```c
/* Manipulate the tuple into the range given. For NF_INET_POST_ROUTING,
 * we change the source to map into the range. For NF_INET_PRE_ROUTING
 * and NF_INET_LOCAL_OUT, we change the destination to map into the
 * range. It might not be possible to get a unique tuple, but we try.
 * At worst (or if we race), we will end up with a final duplicate in
 * __nf_conntrack_confirm and drop the packet. */
static void
get_unique_tuple(struct nf_conntrack_tuple *tuple,
         const struct nf_conntrack_tuple *orig_tuple,
         const struct nf_nat_range2 *range,
         struct nf_conn *ct,
         enum nf_nat_manip_type maniptype)
{
    const struct nf_conntrack_zone *zone;
    struct net *net = nf_ct_net(ct);


    zone = nf_ct_zone(ct);


    /* 1) If this srcip/proto/src-proto-part is currently mapped,
     * and that same mapping gives a unique tuple within the given
     * range, use that.
     *
     * This is only required for source (ie. NAT/masq) mappings.
     * So far, we don't do local source mappings, so multiple
     * manips not an issue.
     */
    /* 先尝试判断不做SNAT是否满足可用范围，或者在最近SNAT的连接记录中获取SNAT源地址 */
    if (maniptype == NF_NAT_MANIP_SRC &&
        !(range->flags & NF_NAT_RANGE_PROTO_RANDOM_ALL)) {
        /* SNAT和非随机端口会走到这里 */
        /* try the original tuple first */
        /* A. 不做SNAT判断是否满足可用范围 */
        if (in_range(orig_tuple, range)) {
            /* 判断五元组是否唯一 */
            if (!nf_nat_used_tuple(orig_tuple, ct)) {
                *tuple = *orig_tuple;
                return;
            }
        /* B. 根据源地址hash，在最近SNAT的连接记录中获取SNAT源地址 */
        } else if (find_appropriate_src(net, zone,
                        orig_tuple, tuple, range)) {
            pr_debug("get_unique_tuple: Found current src map\n");
            /* 判断五元组是否唯一 */
            if (!nf_nat_used_tuple(tuple, ct))
                return;
        }
    }

    /* 随机端口或者没有找到符合上面判断的五元组时会走到这里 */
    /* 2) Select the least-used IP/proto combination in the given range */
    *tuple = *orig_tuple;
    /* 从源地址范围中获取最合适的源IP */
    find_best_ips_proto(zone, tuple, range, ct, maniptype);

    /* Only bother mapping if it's not already in range and unique */
    /* 先不修改端口判断五元组是否满足范围 */
    if (!(range->flags & NF_NAT_RANGE_PROTO_RANDOM_ALL)) {
        if (range->flags & NF_NAT_RANGE_PROTO_SPECIFIED) {
            if (!(range->flags & NF_NAT_RANGE_PROTO_OFFSET) &&
                l4proto_in_range(tuple, maniptype,
                      &range->min_proto,
                      &range->max_proto) &&
                (range->min_proto.all == range->max_proto.all ||
                 !nf_nat_used_tuple(tuple, ct)))
                /* 非随机端口 && 设置了端口范围 && 端口满足范围 && 五元组唯一
                 * 会走到这里 直接返回确认的五元组*/
                return;
        } else if (!nf_nat_used_tuple(tuple, ct)) {
            /* 非随机端口 && 没有设置了端口范围 && 五元组唯一
             * 会走到这里 直接返回确认的五元组*/
            return;
        }
    }

    /* Last chance: get protocol to try to obtain unique tuple. */
    /* 3) 在可用范围中选择一个合适的端口（五元组唯一，端口在范围内） */
    nf_nat_l4proto_unique_tuple(tuple, range, maniptype, ct);
}
```

考虑普遍的一些情况，比如有以下规则：

```shell
sudo iptables -t nat -A PREROUTING -p tcp -d 1.1.1.1/32 --dport  12345 -j DNAT --to-destination 2.2.2.2:23456
sudo iptables -t nat -j MASQUERADE
```

客户端是 1.0.0.0:55555 ，经过转发后，连接概况如下：

> C->P ：1.0.0.0:55555 -> 1.1.1.1:12345
>
> P->S ：1.1.1.1:55555 -> 2.2.2.2:23456

则`get_unique_tuple()`匹配流程是：

* 1-A）不做SNAT判断是否满足可用范围：【不匹配】，因为此时传入的tuple是`10.0.0.0:55555 -> 2.2.2.2:23456`，即修改了目标地址后的tuple，不匹配传入的可用范围中的`IP == 1.1.1.1`
* 1-B）根据源地址hash，在最近SNAT的连接记录中获取SNAT源地址：【不匹配】，如果是新的ct连接，不会存在匹配的最近SNAT连接记录。
* 2）从源地址范围中获取最合适的源IP，先不修改端口判断五元组是否满足范围：【匹配】，源端口使用`orig_tuple`中的，即`10.0.0.0:55555`中的55555端口；源IP则使用`find_best_ips_proto()`进行修改；修改后tuple为`1.1.1.1:55555 -> 2.2.2.2:23456`，匹配传入的可用范围。**正常到这里就退出了**
* 3）在可用范围中选择一个合适的端口：【保底】，如果前面确定了源IP之后，还是无法找到唯一的五元组，这种情况比如：默认tuple中的源端口被占用了；则遍历可用范围来找到一个合适端口。



## 拓广

### SNAT区别

SNAT源码在`/net/netfilter/nf_nat_core.c::xt_snat_target_v0()`，它与MASQUERADE的区别仅在于**少了一个选择最合适源IP的步骤**

### 改变linux网关的NAT类型，提高p2p成功率

MASQUERADE实现决定了linux网关的NAT是`Symmetric NAT`类型NAT，只不过默认策略是尽量接近`Port Restricted Cone NAT`，但如上文分析如果源端口被占用了，还是会选择一个可用端口，导致p2p连接失败。

我们可以修改MASQUERADE实现，使得linux网关支持p2p连接，可行的方法如下：

1. **改为 FULL-CONE NAT**：将`get_unique_tuple()`选到的port对应到origin方向五元组，形成一个映射表；后续该port收到的数据包都发往固定的origin方向五元组；这样最多只能同时服务65535个连接，详细做法参考[p2p连接](/net/p2p连接.md)
2. **改为 Port Restricted Cone NAT**：修改`get_unique_tuple()`实现算法，使得相同客户端的源IP:源PORT，在已经匹配到固定代理服PORT时，后续的数据包使用相同代理服PORT

