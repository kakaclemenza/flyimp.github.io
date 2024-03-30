---
layout: post
title: kolla部署openstack_yoga版本
category: cloud
typora-root-url: ../..
---

## 〇、集群规划

当前使用的是openstack最新稳定版: yoga

本地环境我们使用最低配置，1台4核8G虚拟机；

```shell
192.168.56.108 openstack
```

我们使用的debian11.3虚拟机已经安装好docker环境，所以这里不需要再安装docker。

## 一、初始系统配置

首先设置新主机名：

```shell
hostnamectl set-hostname openstack
```

然后修改`/etc/hosts`，确保域名解析正确：

```shell
...
192.168.56.108 openstack
...
```

> 注意：如果没有修改/etc/hosts，使用`sudo`指令会由于解析不到master而超时报错

安装必要的依赖软件：

```shell
#ansible依赖sshpass; pip安装kolla-ansible, ansible等
apt install - python3-dev libffi-dev gcc libssl-dev ssh sshpass python3-pip
```

配置pip加速镜像源

```shell
mkdir ~/.pip
cat << EOF >  ~/.pip/pip.conf
[global]
index-url=http://apt.2980.com/pypi/simple
[install]
trusted-host=apt.2980.com
EOF
```

## 二、安装kolla-ansible

kolla-ansible依赖ansible，我们依次安装并配置

```shell
# ansible依赖pbr
pip install pbr
# yoga依赖ansible-core版本为2.11.x~2.12.x；对应ansible版本为4.x或5.x(参考ansible官网）
pip install ansible==5.2.0
pip install kolla-ansible
```

执行配置

```shell
#创建kolla的文件夹，后续部署的时候很多openstack的配置文件都会在这
mkdir -p /etc/kolla
chown $USER:$USER /etc/kolla
#复制ansible的部署配置文件
cp -v /usr/local/share/kolla-ansible/ansible/inventory/* /etc/kolla/.
#负责gloable.yml和password.yml到目录
cp -rv /usr/local/share/kolla-ansible/etc_examples/kolla/* /etc/kolla/.
#检查`etc/kolla`文件夹下的文件

#添加ansible补充配置(注意:默认配置已经有ansible内部实现,不需要再写入ansible.cfg)
mkdir -p /etc/ansible
cat << EOF > /etc/ansible/ansible.cfg
[defaults]
host_key_checking=False
pipelining=True
forks=100
EOF

#配置远程root登录
sed -i 's/localhost       ansible_connection=local/openstack ansible_user=root ansible_password=openstack ansible_become=true/' /etc/kolla/all-in-one

#配置kolla部署选项
cat << EOF > /etc/kolla/globals.yml
#选择下载的基础镜像
kolla_base_distro: "ubuntu"
#选择的安装方法，2选1。binary二进制安装，source源码安装
kolla_install_type: "binary"
#选择OpenStack的版本标签，
openstack_release: "yoga"
#OpenStack内部管理网络地址，通过该IP访问OpenStack Web页面进行管理。如果启用了高可用，需要设置为VIP（浮动IP）
kolla_internal_vip_address: "192.168.56.109"
#OpenStack内部管理网络地址的网卡接口
network_interface: "enp0s8"
#此网卡应该在没有IP地址的情况下处于活动，如果不是，那么OpenStack云平台中的云主机实例将无法访问外部网络。（存在IP时br-ex桥接就不成功）
neutron_external_interface: "enp0s9"
#关闭高可用
enable_haproxy: "no"
#关闭cinder（块存储）
#enable_cinder: "yes"
#enable_cinder_backend_lvm: "yes"
#指定nova-compute守护进程使用的虚拟化技术。（kvm好像有点问题，大家可以试试，看看你们能不能过nova下载）
#nova-compute>是一个非常重要的守护进程，负责创建和终止虚拟机实例，即管理虚拟机实例的生命周期。
nova_compute_virt_type: "qemu" #在物理机上部署时无需设置（默认kvm） ，仅在虚拟机中部署kolla-ansible-openstack时设置qemu
#配置docker pull镜像源加速
docker_registry: "hub.2980.com/dockerhub"
#设置docker镜像路径中间字段，即：hub.2980.com/dockerhub/<docker_namespace>/<image_name>
docker_namespace: "kolla"
EOF

#生成horizon(dashboard)的admin账号密码
kolla-genpwd
# 密码存储在/etc/kolla/password.yml的“keystone_admin_password”键中，可按需修改
sed -i '/^keystone_admin_password/c keystone_admin_password: admin' /etc/kolla/password.yml
```

## 三、部署openstack yoga

```shell
# 环境预检查 没问题直接next
kolla-ansible -i /etc//kolla/all-in-one prechecks
# 拉取镜像 时间有点长 大概15Minutes
kolla-ansible -i /etc/kolla/all-in-one pull
# 正式部署 大概15Minutes
kolla-ansible -i /etc/kolla/all-in-one deploy
# 验证部署, 并生成RC文件/etc/kolla/admin-openrc.sh，方便使用命令行控制
kolla-ansible -i /etc/kolla/all-in-one post-deploy
```

使用验证：

```shell
#安装opentack客户端
pip install python-openstackclient

#执行RC文件，添加环境变量
. /etc/kolla/admin-openrc.sh

#查看已启动的服务
openstack service list

# 查看endpoint
openstack endpoint list
```

使用dashboard登录验证(组件为horizon)

* 登录地址: `http://<vip>/auth/login`

* 帐号: admin

* 密码(前面有做过修改): admin

  ```shell
  #可以验证下我们的密码
  . /etc/kolla/admin-openrc.sh
  env | grep OS_PASSWORD
  ``` /etc/kolla/admin-openrc.sh
  env | grep OS_PASSWORD
  ```