---
layout: post
title: mac_ios中的vpn编程
category: net
typora-root-url: ../../..
---

## mac使用

mac上相对简单，使用golang编译工具编译出`.a`静态库，然后使用lipo工具将各平台静态库打包到一起即可。

mac上程序调用静态库，执行VPN隧道创建工作。注意程序需要使用管理员权限来运行。

## IOS使用

### 编译

IOS上，vpn sdk可以使用gomobile编译为`xcframework`类型，然后打包成zip进行发布，如：

```shell
gomobile bind -target=ios -o build/Vpn.xcframework ./sdk/cmd/mobile &&\
cd ./build &&\
zip -r Vpn.xcframework.zip Vpn.xcframework
```

注意，对于新版gomobile（[v0.0.0-20221110043201-43a038452099](https://pkg.go.dev/golang.org/x/mobile@v0.0.0-20221110043201-43a038452099/cmd/gomobile)以来），只能编译出`.xcframework`结尾的库文件，而无法编译`.framework`文件；如果**命名写错**，则会报错。

### 使用

> 可以参考wireguard如何开发ios平台应用：
>
> https://github.com/WireGuard/wireguard-go
>
> https://github.com/WireGuard/wireguard-apple
>
> 官方demo：
>
> https://developer.apple.com/library/archive/samplecode/SimpleTunnel/Introduction/Intro.html

要开发IOS上的VPN应用，需要具备前提：

* IOS8只允许创建ipsec VPN；IOS 9及以上系统，才开放新的api，即`NETunnelProviderManager`和`NEPacketTunnelProvider`，可以让开发者开发自己的私密协议的VPN。所以最低可以支持设备为iPhone4s，并且该设备需要升级到IOS9。

  | 手机型号 | 发布时间 | 最低iOS版本 | 最高iOS版本 |
  | -------- | -------- | ----------- | ----------- |
  | iPhone 4	    | 10年6月7日	| iOS 4	      | iOS 7，但是很勉强    |
  | iPhone 4s	    | 11年10月4日	| iOS 5	      | iOS 9，不支持iOS 10  |
  | iPhone 5	    | 12年9月20日	| iOS 6	  	  |                      |
  | iPhone 5c	    | 13年9月10日	| iOS 7	  	  |                      |
  | iPhone 5s	    | 13年9月10日	| iOS 7	  	  |                      |
  | iPhone 6	    | 14年9月10日	| iOS 8	  	  |                      |
  | iPhone 6 P	| 14年9月10日	| iOS 8	       |                     |
  | iPhone 6s	    | 15年9月10日	| iOS 9	  	   |                     |
  | iPhone 6s P	| 15年9月10日	| iOS 9	  	   |                     |
  | iPhone SE	    | 16年3月21日	| iOS 9.3	   |	                 |
  | iPhone 7	    | 16年9月8日	| iOS 10	   |	                 |
  | iPhone 7 P    | 16年9月8日	| iOS 10	   |	                 |
  
* 需要有付费的开发者账号，在Apple ID中设置添加Network Extension和Personal VPN，这样才能在Xcode中进行开发。

* Xcode项目中要加入VPN功能，需要“File-New-Target...”加入“Network Extension”这个target，用作在当前项目中加入VPN功能，然后当前项目和Target中设置“Capabilities”中也需要开启“Network Extensions”，参考：https://github.com/wlixcc/VPNClient/

由于本人没有苹果开发者账号，这里只是记录一下开发思想，主要使用`NEPacketTunnelProvider`：

1. 创建的“Network Extension”这个target中，有个继承自`NEPacketTunnelProvider`的类`PacketTunnelProvider`
2. 我们的任务就是实现其中的`startTunnelWithOptions()`和`stopTunnelWithReason()`方法；
   * `startTunnelWithOptions()`用于配置vpn信息（包括路由、对端地址、本段地址、网卡配置等）并启用vpn开始监听数据包；最后需要调用`completionHandler(nil);`来让IOS内部建立vpn连接。
   * `stopTunnelWithReason()`用于关闭vpn连接
3. 创建好vpn连接后，是使用NEPacketTunnelProvider对象的packetFlow来完成数据包的收发

xxxvpn与这种方式的结合，就是：

* 首先ios上利用`NEPacketTunnelProvider`封装好接口，**构造一个对象vpnBuilder，实现xxxvpn中的xxxvpnBuilder**
* 将vpnBuilder传递给`xxxvpnInitSdk()`用于后续创建或销毁vpn连接
* 后续调用`xxxvpnAccel()`，内部就会通过vpnBuilder来调用ios代码中的相关VPN接口，实现VPN连接。

