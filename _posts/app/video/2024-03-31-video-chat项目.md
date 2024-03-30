---
layout: post
title: video-chat项目
category: app
typora-root-url: ../../..
---

### 聊天



### 私聊

ChatDialog 组件负责处理私聊

### 音视频通话

ChatDialog负责处理私聊, 那么音视频通话组件VideoArea就会添加到ChatDialog中来发起

在 A（呼叫者）和 B（被呼叫者）之间建立通信的机制如下：

1. A 使用 ICE 服务器配置创建 RTCPeerConnection 对象。
2. A 使用 RTCPeerConnection createOffer 方法创建一个 offer（SDP 会话描述）。
3. A 使用 offer 调用 setLocalDescription(offer) 方法。
4. A 使用信令机制（privateMessagePCSignaling）将 offer 发送给 B

B(被呼叫者)处理流程如下:

1. B 获得 offer 并使用 A 的 offer 调用 setRemoteDescription()（这样 B 的 RTCPeerConnection 就能知道 A 的设置了）。
2. B 使用 RTCPeerConnection createAnswer 方法创建 answer。
3. B 用 answer 调用 setLocalDescription(answer) 方法。
4. B 使用信令机制（privateMessagePCSignaling）将 answer 发回给 A。
5. A 使用 setRemoteDescription() 方法将 B 的 answer 设置为远程会话描述