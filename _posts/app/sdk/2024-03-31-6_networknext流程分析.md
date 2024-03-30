---
layout: post
title: 6_networknext流程分析
category: app
typora-root-url: ../../..
---

## 前言

networknext, 官方定义是独立于互联网的另一种网络. 这个网络中会负责为连接的两端选择最优质的线路, 取得丢包, 延迟, 抖动都最低的效果. 其实现猜测大致如下:

1. 客户端和服务端都需要通过调用sdk才能收发包: 这样方便对数据包做封装, 定制
2. 需要先向`udp.v2.networknext.com`对接申请接入网络
3. 接入时使用基于域名的就近接入方案, 该方案利用limelight提供的CDN网络实现

networknext网络的实现, 关键在于其SDK. 有了SDK对于收发包的封装, 数据包的转发, 加密, 接入SDN网络等方面都会很好做. 这样的方式应该会成为趋势, 有助于网络的构建和DDos防护.

该SDK官方已开源, 需要申请成为开发者才github可见. SDK使用文档在:

https://next.readthedocs.io/en/latest/integrate.html#client-integration

本文基于networknext提供的4.20.4版本代码进行分析，目标是理解networknext的设计，设计一套sdk用于公司业务接入自研sdn网络系统。

## 客户端

通过分析`examples/simple_client.cpp`，`examples/upgraded_client.cpp`，客户端提供的主要功能接口及调用流程是：

1. next_init()：初始化环境，可以根据参数或环境变量传入配置信息。

2. next_client_create()：主要是创建socket，并绑定本地地址、传入收包回调函数。追踪源码可以看到这里使用的统一都是udp协议的socket！调用流程：
   ```shell
   next.cpp::next_client_create()
     next.cpp::next_client_internal_create()
       next_linux.cpp::next_platform_socket_create()
         socket(..., SOCK_DGRAM, IPPROTO_UDP )
         bind()
     # 另起线程，使用next_client_internal_thread_function处理收包
     next.cpp::next_platform_thread_create(..., next_client_internal_thread_function, ...)
   ```

3. next_client_internal_thread_function()：收包处理函数，在另一个线程中阻塞调用。收包流程如下：

   ```shell
   next.cpp::next_client_internal_thread_function()
     next.cpp::next_client_internal_block_and_receive_packet()
       #获取到数据包
       next_linux.cpp::next_platform_socket_receive_packet()
       #如果不是NEXT_PASSTHROUGH_PACKET类型，为经过networknext的非直连包、或者服务端的升级路由包、或状态变更，解包使用：
       next.cpp::next_client_internal_process_network_next_packet()
         #依次处理各类包，形成事件
         ...
         #入事件队列
         next.cpp::next_queue_push()
       #否则，为直连包，解包使用：
       next.cpp::next_client_internal_process_raw_direct_packet()
         #直接处理收到的直连包，形成NEXT_CLIENT_NOTIFY_PACKET_RECEIVED事件
         #入事件队列
         next.cpp::next_queue_push()
   ```

4. next_client_open_session()：主要是将目标地址记录起来（此处称为session，鸡连接信息

5. next_client_update()：每次先处理客户端事件队列中的事件，主要有：

   - NEXT_CLIENT_NOTIFY_PACKET_RECEIVED：收包处理。会回调传入的收包函数。
   - NEXT_CLIENT_NOTIFY_UPGRADED：收到服务端通知升级网络路由
   - NEXT_CLIENT_NOTIFY_STATS_UPDATED：状态变更
   - NEXT_CLIENT_NOTIFY_READY：客户端就绪；next_client_ready()用于检查该标记

6. next_client_send_packet()：执行发包。需要注意的是，发包会判断客户端所处的状态，是经过networknext转发（upgraded），或者直连。发包流程如下：

   ```shell
   next.cpp::next_client_send_packet()
     #若是直连，调用：
     next.cpp::next_client_send_packet_direct()
     	next_linux.cpp::next_platform_socket_send_packet()
     #否则，先获取到下一条地址（在上文，由networknext通过服务端的升级路由包下发的），并组装好经过networknext网络格式的包
     next.cpp::next_route_manager_prepare_send_packet(..., &next_to, ...)
     #然后发送经过networknext网络格式的包到该下一跳地址
     next_linux.cpp::next_platform_socket_send_packet(..., &next_to, ...)
   ```

7. next_client_destroy()：销毁创建的连接资源

8. next_destroy()：销毁sdk相关资源

可以看到这个设计很简洁明了，下面我们来看下服务端的处理过程。

## 服务端

通过分析`examples/simple_server.cpp`，`examples/upgraded_server.cpp`，服务端端提供的主要功能接口及调用流程是：

1. next_init()：略

2. next_server_create()：主要是创建socket，并绑定本地地址server_address、传入收包回调函数。这一系列流程和客户端基本一样，不做展开。

3. next_server_internal_thread_function()：收包处理函数，和客户端基本一样，不做展开。

4. next_server_update()：处理各类事件队列中的事件，主要有：

   - NEXT_SERVER_NOTIFY_PACKET_RECEIVED：收包处理。会回调传入的收包函数。
   - NEXT_SERVER_NOTIFY_SESSION_UPGRADED：将某个链接（session）升级为走networknext网络方式
   - NEXT_SERVER_NOTIFY_PENDING_SESSION_TIMED_OUT：状态变更超时情况处理
   - NEXT_SERVER_NOTIFY_SESSION_TIMED_OUT：某个链接超时处理
   - NEXT_SERVER_NOTIFY_FAILED_TO_RESOLVE_HOSTNAME：域名解析失败
   - NEXT_SERVER_NOTIFY_READY
   - NEXT_SERVER_NOTIFY_FLUSH_FINISHED

5. next_server_send_packet()：执行发包。除了区分是否经过networknext网络发包，需要注意的是这里还有多发送一个`send_upgraded_direct`用于通知客户端升级使用networknext网络的包：

   ```c
   if ( send_upgraded_direct )
   {
       // [255][session sequence][packet sequence](payload) style packet direct to client
   
       uint8_t buffer[NEXT_MAX_PACKET_BYTES];
       uint8_t * p = buffer;
       next_write_uint8( &p, NEXT_DIRECT_PACKET );
       next_write_uint8( &p, open_session_sequence );
       next_write_uint64( &p, send_sequence );
       memcpy( buffer+10, packet_data, packet_bytes );
       next_platform_socket_send_packet( server->internal->socket, to_address, buffer, size_t(packet_bytes) + 10 );
   }
   ```

6. next_server_flush()：在准备退出前，确保将所有待发送的数据发送完毕

7. next_server_destroy()：销毁创建的连接资源

8. next_destroy()：销毁sdk相关资源

## 总结

networknext的sdk主要封装了连接创建、数据包收发的功能。客户端和服务端初始的连接是直连，后续如果发生网络波动，数据链路的切换依赖于持续调用`next_xxx_update()`函数对连接状态和服务端事件做监控，然后由服务端下发`session_upgrade`消息通知客户端切换到networknext网络接入点，实现按需改善传输链路的功能。

那么我们自己实现sdk要适用于公司业务接入自研sdn网络系统，需要实现的主要功能预期是：

1. 提供常规的sdk初始化和sdk释放接口
2. 提供连接创建销毁接口，创建时只需指定服务端地址（可以是ip:port，也可以是已注册的服务器编号）、接受消息回调函数。连接创建的动作，是先请求获取代理列表，然后建立自定协议的连接（可以是kcp协议），并进行测评。
3. 提供连接发送函数，并对交互包做监控，当发现链路出现卡顿时，自动触发一次多线路测评。如果可以切换，则触发进行线路切换。上层业务则继续调用收发函数并且无感。

其他设计抉择：

1. Q：是否由服务端提供直连地址，并由服务端控制是否网络升级？
   A：不这么做。大部分服务端不具备集群能力，如果直接暴露直连地址，对于单服的业务不友好；另外服务端控制是否网络升级，对于服务端开发增加了负担。
2. Q：如何穿越代理后仍能获取客户端真实ip？
   A：预计全网使用kcp协议传输数据包，预留一个协议头部字段保存客户端真实IP；网络入口点对客户端真实IP进行设置，若没有设置则认为对端直连。
3. Q：是否需要确保客户端合法？比如确定真实IP有效？
   A：不需要。客户端可以通过后续的协议进一步验证，比如使用协商好的rsa签名等；按功能分层思想，nnet专注于高效转发与普适性，上层具体业务相关的安全性又业务做保障。
4. Q：是否支持p2p？
   A：可以支持，但p2p的模型存在打洞失败情况；打洞失败时，还需要继续走中转服完成转发。

## 开发计划

一阶段：

* [ ] 实现nnet服务端sdk，先注册ID到xxmygw，然后创建监听；nnet服务端sdk析构时，则主动注销ID到xxmygw。
* [ ] 实现nnet客户端sdk，获取xxmygw代理，并使用ID连接，成功收发包
* [ ] 实现基于收发包的需要判定网络故障
* [ ] 实现网络故障时，无感切换到另一条xxmygw代理

二阶段：

* [ ] 【非必须】xxmygw代理点实现发布-订阅模式，订阅nnet服务端sdk注册的ID信息
* [ ] 【非必须】xxmygw代理转发识别nnet客户端sdk发送的数据包，自动匹配ID信息来动态建立转发规则，并固化到内核态或网卡驱动，无需固定配置。（主要是解决代理转发支持的服务端上限问题）
* [ ] xxmygw考虑提供统一的中转服，使用nnet服务端sdk接入xxmygw，客户端在p2p连接失败后，均需要连上中转服后进行中转。
