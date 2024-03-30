---
layout: post
title: PCI_COM串口与tty
category: kernel
typora-root-url: ../../../..
---

## PCI设备

### PCI是啥

PCI/PCI-E接口是主板上比较通用的一种接口标准，目前主要提供给需要直接与CPU进行通讯的设备使用，通常是为了扩展主板上没有支持的功能，比如扩展独立显卡等设备，目的是为平台输出更加强力的图形能力，弥补核显的不足.

PCI接口(插槽)最典型的就是主板上插着显卡或网卡的那种插口, 一般是白色的, 与内存插槽有区别. 另外, **PCI插槽都是等长的**，防呆口位置靠上，大部分都是纯白色。**PCIe插槽有大有小**，最小的x1，最大的x16，防呆口靠下. 

### PCI设备控制

nymph中引入PCI主要是**为了在网卡驱动中获取到网卡信息**, 对网卡进行操作.

PCI规范中, 单个系统(Linux中支持为单个PCI域)中, 拥有256个PCI总线(8bit), 每个总线支持32个设备(5bit), 每个设备可以是多功能版, 可接8种功能(3bit). 所以PCI外设以功能为单位. 每个功能正好可以用一个16位地址标识.

lspci查看到的标识`00:14.0`就是第00总线, 第20设备, 第0号功能; 对应/proc/bus/pci/devices中的`00a0`标识

PCI总线中的IO空间使用32位地址总线, 对其进行操作时使用in_dword()和out_dword(). 具体的代码操作是参考: https://wiki.osdev.org/PCI

这里, pci::ReadConfigDword()中的offset就是用于索引64字节设备无关的PCI地址空间(寄存器), 可以参考\<Linux设备驱动程序:P306\>. 



## COM串口

nymph中利用COM1口输出系统日志, 在外部可以通过qemu -serial导出到具体的目标中. 代码src/drivers/serial.cpp参考自https://wiki.osdev.org/Serial_Ports

注意这里Enable DLAB之后对于[COM1_PORT+0]和[COM1_PORT+1]的赋值是在设置 serial controller (UART)的时钟频率. Disable DLAB之后, [COM1_PORT+0]用于读写数据, [COM1_PORT+1]用于使能中断. nymph中只是利用COM口对外发数据, 所以**没有开启相关中断**



## TTY

待实现