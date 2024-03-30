---
layout: post
title: 使用ebpf替代iptables
category: net
typora-root-url: ../../..
---

## 资源综述

项目：[xnat](https://gitee.com/xxf2015/xnat)

依赖：

* 

参考：

* [XDP-Forwarding](https://github.com/gamemann/XDP-Forwarding/)

* [beewall](https://github.com/mmat11/beewall)



## 原理解析





## 后续优化思路

1. [TODO] 当前直接对换mac地址；需要将根据路由选择源IP，以及源、目标mac地址

2. [TODO] 当前源端口选择策略比较暴力；需要参考MASQUERADE策略选择源PORT，参考[SNAT的MASQUERADE地址选择与端口选择](https://segmentfault.com/a/1190000041260378)
   另外，也可以参考cilium的snat，允许尝试32次，如果超过仍未找到合适的tuple，就报错。

3. [TODO] 可能受限于BPF程序无法使用for遍历；参考: https://github.com/gamemann/XDP-Forwarding/tree/master/patches