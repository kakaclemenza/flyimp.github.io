---
layout: post
title: vncserver安装方法
category: system
typora-root-url: ../..
---

### vncserver部署

首先是初始化:

```shell
#首先需要具备桌面环境
sudo apt install xfce4
#安装VNC服务器
sudo apt install tigervnc-standalone-server tigervnc-common
#创建初始配置并设置密码. 注意不要设置view-only password, 否则则用户将无法
# 使用鼠标和键盘与VNC实例进行交互. 创建密码文件将存储在~/.vnc目录下
vncserver
#   注意上面输出中主机名后的:1. 这表示正在运行vnc服务器的显示端口号. 初始化后
# 我们先停掉服务进程. 后面使用systemd方式来运行服务
vncserver -kill :1
```

配置VNC服务器, 现在服务器上同时安装了Xfce和TigerVNC, 我们需要配置TigerVNC以使用Xfce.

```shell
# 创建服务启动时配置脚本, 配置运行xfce4桌面
cat > ~/.vnc/xstartup << EOF
#!/bin/sh
unset SESSION_MANAGER
unset DBUS_SESSION_BUS_ADDRESS
export XMODIFIERS="@im=fcitx"
export QT_IM_MODULE="fcitx"
export GTK_IM_MODULE="fcitx"

exec startxfce4
EOF

# 添加执行权限
chmod u+x ~/.vnc/xstartup
# 创建systemd服务文件, 用户名xiaofeng要根据实际情况调整
sudo cat > /etc/systemd/system/vncserver@.service << EOF
[Unit]
Description=Remote desktop service (VNC)
After=syslog.target network.target

[Service]
Type=simple
User=xiaofeng
PAMName=login
PIDFile=/home/%u/.vnc/%H%i.pid
ExecStartPre=/bin/sh -c '/usr/bin/vncserver -kill :%i > /dev/null 2>&1 || :'
ExecStart=/usr/bin/vncserver :%i -geometry 1440x900 -alwaysshared -fg
ExecStop=/usr/bin/vncserver -kill :%i

[Install]
WantedBy=multi-user.target
EOF

# 通知systemd新的vncserver服务存在
sudo systemctl daemon-reload
# 启用服务. 如果当前linux上使用的是桌面环境, 一般:1显示端口都会被现有桌面占用
# 所以这里使用@2, 将5902绑定到:2显示端口
sudo systemctl enable vncserver@2.service
sudo systemctl start vncserver@2.service
sudo systemctl status vncserver@2.service
```

接下来就可以在windows下使用vncviewer客户端连接vnc服务了, 注意vncviewer会自动使用xfce下配置的分辨率, systemd配置文件中的1440x900只是个建议值, 在这里不会生效



### 其他问题收集

##### 1. win和debian之间无法复制粘贴

执行如下命令即可:

```shell
vncconfig -nowin&
```

为了方便起见, 这里把它添加到"Session and Startup"中, 加载xfce桌面后自动运行.

##### 2. 如何修改桌面的分辨率为910x1030

```shell
#直接在.config下查找关键字1920(当前分辨率是1920x1080)
grep -rn 1920 ~/.config
#修改具体配置文件
vi .config/xfce4/xfconf/xfce-perchannel-xml/displays.xml
#修改完毕, 注销重登即可生效
```

