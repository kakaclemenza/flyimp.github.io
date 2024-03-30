---
typora-root-url: ../..
ref: https://www.cnblogs.com/zhaoyixin96/p/12582449.html
---

### 安装运行

部署集群目标: 两个master, 两个worker, **每个master上都要部署keepalived+haproxy实现主备及负载均衡**

下面是安装kubenet的过程

```shell
#1. 在所有节点安装 Docker 和 kubeadm, 使用root执行
apt-get update && apt-get install -y apt-transport-https
curl https://mirrors.aliyun.com/kubernetes/apt/doc/apt-key.gpg | apt-key add -
cat > /etc/apt/sources.list.d/kubernetes.list << EOF
deb https://mirrors.aliyun.com/kubernetes/apt/ kubernetes-xenial main
EOF
curl -fsSL https://mirrors.ustc.edu.cn/docker-ce/linux/debian/gpg | sudo apt-key add -
cat > /etc/apt/sources.list << EOF
deb [arch=amd64] https://mirrors.ustc.edu.cn/docker-ce/linux/debian stretch stable
EOF
apt-get update
# 在安装 kubeadm 的过程中，kubeadm 和 kubelet、kubectl、
# kubernetes-cni 这几个二进制文件都会被安装好
apt-get install -y docker-ce kubeadm
# kubenet新版要求禁用swap以提高效率
swapoff -a
sed 's/.*swap.*/#&/' /etc/fstab


#2. Master节点部署
# 打印本次部署的 kubernetes 的版本信息
kubeadm config print init-defaults
# 根据上面信息, 编写初始化使用的yaml文件
cat > ./kubeadm.yaml << EOF
apiVersion: kubeadm.k8s.io/v1beta2
imageRepository: registry.aliyuncs.com/google_containers
kind: ClusterConfiguration
controllerManager:
    extraArgs:
        horizontal-pod-autoscaler-use-rest-clients: "true"
        horizontal-pod-autoscaler-sync-period: "10s"
        node-monitor-grace-period: "10s"
apiServer:
    extraArgs:
        runtime-config: "api/all=true"
kubernetesVersion: v1.18.0
EOF
# 初始化第一个Master节点. 初始化完成后, 会获得节点ip:port, token和cert-hash用于添加其他master或worker
kubeadm init --config kubeadm.yaml
# 将安全配置文件保存到~/.kube目录下, kubectl默认会使用这个目录下的授权信息访问 Kubernetes 集群
mkdir -p $HOME/.kube
cp -i /etc/kubernetes/admin.conf $HOME/.kube/config
chown $(id -u):$(id -g) $HOME/.kube/config
# 查看 nodes 状态, 这个时候 master 还处于 NotReady 状态, 因为还没有安装网络插件 Calico
kubectl get nodes
# 要让Kubernetes Cluster能够工作, 必须安装Pod网络插件, 否则Pod之间无法通信
# 网络插件 Calico 安装完之后稍等一会，再次查看 nodes 状态，应该已经变成 Ready
curl https://docs.projectcalico.org/v3.9/manifests/calico.yaml -O
kubectl apply -f calico.yaml
# 默认配置下Kubernetes不会将Pod调度到Master节点, 使用的是Taint标记. 如果希望Master节点也能作为Node使用, 
# 则使用如下命令去除Taint标记, 加'-'就意味着移除该键
kubectl taint nodes k8s-master node-role.kubernetes.io/master-
# 要恢复Master Only状态, 则使用'=""'添加该键:
kubectl taint nodes k8s-master node-role.kubernetes.io/master:NoSchedule


#3. 其他节点部署
将相关文件复制到其他
# 3.1 添加其他Master, 首先需要将相关文件复制到目标节点
ssh root@debian10master1 mkdir -p /etc/kubernetes/pki/etcd
scp /etc/kubernetes/admin.conf root@debian10master1:/etc/kubernetes
scp /etc/kubernetes/pki/{ca.*,sa.*,front-proxy-ca.*} root@debian10master1:/etc/kubernetes/pki
scp /etc/kubernetes/pki/etcd/ca.* root@debian10master1:/etc/kubernetes/pki/etcd
# 然后执行添加Master节点指令
kubeadm join 172.31.0.57:6443 --token xxx --discovery-token-ca-cert-hash xxx --control-plane
# 3.2 添加Worker
kubeadm join 172.31.0.57:6443 --token xxx --discovery-token-ca-cert-hash xxx
```

下面是部署kubernetes-dashboard, 

```shell
wget https://raw.githubusercontent.com/kubernetes/dashboard/v2.0.0-rc2/aio/deploy/recommended.yaml -o ./kubernetes-dashboard.yaml
# 部署dashboard
kubectl apply -f kubernetes-dashboard.yaml
# 访问service就可以访问到dashboard的webUI，但是默认生成的service访问类型是ClusterIP，
# 所以集群外部不能访问到. 这里需要修改成使用NodePort类型
kubectl edit svc kubernetes-dashboard -n kubernetes-dashboard
"""
...
spec:
  clusterIP: 10.107.159.204
  externalTrafficPolicy: Cluster
  ports:
  - nodePort: 30443
    port: 443
    protocol: TCP
    targetPort: 8443
  selector:
    k8s-app: kubernetes-dashboard
  sessionAffinity: None
  type: NodePort
...
"""
# 检查端口映射是否正确
kubectl get services -n kubernetes-dashboard
# 创建ServiceAccount类型角色(RBAC)
kubectl create serviceaccount mysa -n default
# 创建clusterrolebinding，然后将此sa绑定至集群中存在的clusterrole, 以具备admin的权限
kubectl create clusterrolebinding dashboard-admin --clusterrole=admin --serviceaccount=default:mysa
# 查看sa的secret, 里面就保存了token
kubectl get secret
kubectl describe secret mysa-token-gc8z5
```

部署前期需要做好配置, 如果配置不成功需要重新部署时, 使用

```shell
# 自动清理相关配置文件和挂载目录项, 清理后台进程
kubeadm reset -y

# 确认当强主机名, 必要时修改主机名
hostnamectl
hostnamectl set-hostname master1

# 调整hosts配置, 如配置"127.0.0.1 master1"
vi /etc/hosts

# 重新初始化, 之后的步骤和上文相同
kubeadm init --config kubeadm.yaml
```

错误`error execution phase preflight: couldn’t validate the identity of the API Server`: 这是因为使用旧的已过期的token和hash去添加节点. 需要重新生成新的token和hash

```shell
#得到token
kubeadm token create 
#得到discovery-token-ca-cert-hash
openssl x509 -pubkey -in /etc/kubernetes/pki/ca.crt | openssl rsa -pubin -outform der 2>/dev/null | openssl dgst -sha256 -hex | sed 's/^.* //'
```

关键术语:

* Pod: 
* Controller: 
  * deployment
  * daemonset
  * job
  * cronjob
* Service: 
* 

kubelet是唯一没有以容器形式运行的Kubernetes组件, 它是通过Systemd服务运行

### kubectl常用控制指令

```shell
# 查看所有pod的详细信息(状态, IP, 所在节点...)
kubectl get -A pod -o wide

# 将Master节点设置为可部署应用状态


# 部署/更新应用, 推荐尽量只使用部署文件+apply


# master上进入某个pod
kubectl exec -it <pod_name> -n <namespace> -- bash

# 查看内部pod的配置
kubectl edit -n kube-system pod kube-apiserver-k8s-master
```

### 组件原理

![](C:\Users\admin\fun\assets\ea2c62caf0c4172943a9833c45c661ebf1b52aee.png)

下面介绍一个Deployment的启动过程:

1. kubectl向APIServer发起创建deployment的请求
2. controller-manager
3. scheduler定时向apiserver获取自己感兴趣的数据, 其中包括待调度的Pod信息和可用的node, 然后进行计算得到调度信息通过apiserver写入etcd
4. Worker节点通过etcd发现有自己有需要部署的Pod, 于是进行Pod的启动操作, 启动完毕则更新etcd中该Pod的信息.

scheduler是k8s的调度模块，做的事情就是拿到pod之后在node中寻找合适的进行适配这么一个单纯的功能。scheduler作为一个客户端，从apiserver中读取到需要分配的pod，和拥有的node，然后进行过滤和算分，最后把这个匹配信息通过apiserver写入到etcd里面，供下一步的kubelet去拉起pod使用。

以v1.2.0版为主, 源码位置在:

* APIServer:
  * kubernetes/cmd/kube-apiserver/app/server.go
  * kubernetes/pkg/apiserver
* kube-scheduler
  * kubernetes/plugin/cmd/kube-scheduler/app/server.go
  * kubernetes/plugin/pkg/scheduler
* kube-controller-manager
  * kubernetes/cmd/kube-controller-manager/app/controllermanager.go
  * kubernetes/pkg/controller

#### 一. APIServer

APIServer是Kubernetes系统管理指令的统一入口. 对任何资源的增删改查操作都需要交给APIServer处理后才能提交etcd.

通过etcdctl连接etcd后台存储, 查看资源信息

```shell
# 首先要安装etcd-client
sudo apt-get install etcd

# 查看, APIServer的资源路径都从/registry开始
etcdctl ls /registry -recursive
```

#### 二. scheduler
