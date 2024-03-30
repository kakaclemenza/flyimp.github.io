---
layout: post
title: ulimit设置与coredump文件
category: coder
typora-root-url: ../../../..
---

在linux下开发时，如果程序突然崩溃了，也没有任何日志。这时可以查看core文件。从core文件中分析原因，通过gdb看出程序挂在哪里，分析前后的变量，找出问题的原因。

### Core Dump

当程序运行的过程中异常终止或崩溃，操作系统会将程序当时的内存状态记录下来，保存在一个文件中，这种行为就叫做Core Dump（中文有的翻译成“核心转储”)。我们可以认为 core dump 是“内存快照”，但实际上，除了内存信息之外，还有些关键的程序运行状态也会同时 dump 下来，例如寄存器信息（包括程序指针、栈指针等）、内存管理信息、其他处理器和操作系统状态和信息。core dump 对于编程人员诊断和调试程序是非常有帮助的，因为对于有些程序错误是很难重现的，例如指针异常，而 core dump 文件可以再现程序出错时的情景。

### 相关设置

如果没有进行core dump 的相关设置，默认是不开启的。可以通过```ulimit -c```查看是否开启。如果输出为```0```，则没有开启，需要执行```ulimit -c unlimited```开启core dump功能。

#### ulimit

```ulimit```命令用来限制系统用户对shell资源的访问。限制 shell 启动进程所占用的资源，支持以下各种类型的限制：所创建的内核文件的大小、进程数据块的大小、Shell 进程创建文件的大小、内存锁住的大小、常驻内存集的大小、打开文件描述符的数量、分配堆栈的最大大小、CPU 时间、单个用户的最大线程数、Shell 进程所能使用的最大虚拟内存。同时，它支持硬资源和软资源的限制。

ulimit相关选项如下：

```
-a：显示目前资源限制的设定；
-c <core文件上限>：设定core文件的最大值，单位为区块；
-d <数据节区大小>：程序数据节区的最大值，单位为KB；
-f <文件大小>：shell所能建立的最大文件，单位为区块；
-H：设定资源的硬性限制，也就是管理员所设下的限制；
-m <内存大小>：指定可使用内存的上限，单位为KB；
-n <文件数目>：指定同一时间最多可开启的文件数；
-p <缓冲区大小>：指定管道缓冲区的大小，单位512字节；
-s <堆叠大小>：指定堆叠的上限，单位为KB；
-S：设定资源的弹性限制；
-t <CPU时间>：指定CPU使用时间的上限，单位为秒；
-u <程序数目>：用户最多可开启的程序数目；
-v <虚拟内存大小>：指定可使用的虚拟内存上限，单位为KB。
```

#### core文件的名称和生成路径：

> 可直接参考`man 5 core`

没有进行设置的话，默认生成的core文件不带其它任何扩展名称，全部命名为core。新的core文件生成将覆盖原来的core文件 。 可对core文件的名称和生成路径进行相关配置，如下：

- ```/proc/sys /kernel/core_uses_pid```可以控制core文件的文件名中是否添加pid作为扩展。文件内容为1，表示添加pid作为扩展名，生成的 core文件格式为core.xxxx；为0则表示生成的core文件同一命名为core。 


- ```proc/sys/kernel/core_pattern```可以控制core文件保存位置和文件名格式。 

以下是参数列表: 

```c
%p - insert pid into filename 添加pid 
%u - insert current uid into filename 添加当前uid 
%g - insert current gid into filename 添加当前gid 
%s - insert signal that caused the coredump into the filename 添加导致产生core的信号 
%t - insert UNIX time that the coredump occurred into filename 添加core文件生成时的unix时间 
%h - insert hostname where the coredump happened into filename 添加主机名 
%e - insert coredumping executable name into filename 添加命令名 
```

