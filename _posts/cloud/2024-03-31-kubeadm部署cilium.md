---
layout: post
title: kubeadm部署cilium
category: cloud
typora-root-url: ../..
---

## cilium安装

系统要求：

* kernel >= 5.10
* 安装 k8s 时，使用--skip-phases=addon/kube-proxy 选项来跳过 kube-proxy 安装

cilium依托helm进行配置和部署，首先需要下载helm chart，这些chart获取地址在：

> https://github.com/cilium/charts/

我们使用cilium-1.12.7版本：

```shell
wget https://raw.githubusercontent.com/cilium/charts/master/cilium-1.12.7.tgz
tar xf cilium-1.12.7.tgz
#解压得到cilium chart配置文件
```

接下来需要配置cilium：

```shell
#更换镜像下载地址为国内dockerhub源地址
sed -i "s/quay.io/hub-mirror.c.163.com/g" cilium/values.yaml

#通过helm template渲染出yaml文件
#--set debug.enabled=true ：开启debug模式
#--set kubeProxyReplacement=strict ：使用完全替代kube-proxy模式
#--set hubble.ui.enabled=true ：开启hubble ui界面
helm template --namespace kube-system \
     --set debug.enabled=true \
     --set kubeProxyReplacement=strict \
     --set bpf.masquerade=true \
     --set hubble.relay.enabled=true \
     --set hubble.ui.enabled=true \
     --set prometheus.enabled=true \
     --set operator.prometheus.enabled=true \
     --set hubble.enabled=true \
     --set hubble.metrics.enabled="{dns,drop,tcp,flow,port-distribution,icmp,http}" \
	 --set k8sServiceHost=192.168.56.110 \
	 --set k8sServicePort=6443 \
     cilium/ > cilium_1.12.7.yaml
     
# 这里pod间转发使用的是vxlan隧道模式，其他模式：
# 1. Cilium Host Routing Enabled with BPF Mode[Native Routing]
#        --set tunnel=disabled \
#        --set autoDirectNodeRoutes=true \
#        --set nativeRoutingCIDR=172.21.0.0/20 \
#        --set loadBalancer.mode=hybrid \
# 
# 2. Direct Server Return (DSR)
#        --set tunnel=disabled \
#        --set autoDirectNodeRoutes=true \
#        --set nativeRoutingCIDR=172.21.0.0/20 \
#        --set loadBalancer.mode=dsr \
```

需要提一下Cilium在kubernetes中有2种运行模式，一种是完全替换kube-proxy， 如果底层 Linux 内核版本低，可以替换kube-proxy的部分功能，与原来的 kube-proxy 共存

* kubeProxyReplacement=strict：Cilium完全替代所有kube-proxy功能。 Cilium代理启动并运行后，将负责处理类型为ClusterIP，NodePort，ExternalIP和LoadBalancer的Kubernetes服务。
* kubeProxyReplacement=probe：此选项适用于混合设置，即kube-proxy在Kubernetes集群中运行，其中Cilium部分替换并优化了kube-proxy功能。一旦Cilium agent启动并运行，它就会在基础内核中探查所需BPF内核功能的可用性，如果不存在，则依靠kube-proxy补充其余的Kubernetes服务处理，从而禁用BPF中的部分功能。
* kubeProxyReplacement=partial：与探针类似，此选项用于混合设置，即kube-proxy在Kubernetes集群中运行，其中Cilium部分替换并优化了kube-proxy功能。与探查基础内核中可用的BPF功能并在缺少内核支持时自动禁用负责BPF kube-proxy替换的组件的探针相反，该部分选项要求用户手动指定应替换BPF kube-proxy的组件。

接下来构建k8s集群时，使用：

```shell
kubeadm init \
    --image-repository=registry.aliyuncs.com/google_containers \
    --pod-network-cidr=10.244.0.0/16 \
    --apiserver-advertise-address=192.168.56.110 \
    --skip-phases=addon/kube-proxy  #注意这里指定不部署kube-proxy
```

如果对于已经部署了kube-proxy的集群，需要删掉`kube-proxy`相关的`daemonset`、`configmap`、`iptables`规则和`ipvs`规则。参考：

```shell
# 删除掉kube-proxy这个daemonset
kubectl -n kube-system delete ds kube-proxy

# 删除掉kube-proxy的configmap，防止以后使用kubeadm升级K8S的时候重新安装了kube-proxy（1.19版本之后的K8S）
kubectl -n kube-system delete cm kube-proxy

# 在每台机器上面使用root权限清除掉iptables规则和ipvs规则
iptables-save | grep -v KUBE | iptables-restore
ipvsadm -C
```

后续添加node等配置，可以参考[kubeadm部署k8s新版]()

接下来可以部署cilium：

```shell
kubectl apply -f cilium_1.12.7.yaml
```

配置hubble-ui可以被外部访问需要使用NodePort模式，编辑`hubble-ui-svc.yaml`：

```yaml
kind: Service
apiVersion: v1
metadata:
  namespace: kube-system
  name: hubble-ui-svc
spec:
  selector:
    k8s-app: hubble-ui
  ports:
    - name: http
      port: 8081  #注意：这个版本的hubble-ui使用nginx进行代理的，nginx端口是8081
      nodePort: 30010
  type: NodePort
```

然后执行 `kubectl apply -f hubble-ui-svc.yaml`就可以通过任意节点的30010端口打开hubble-ui界面。

hubble-ui展示的是各个pod间数据通信图，分为上下两个部分，上半部分是数据流向图，默认情况下可以自动发现基于网络 3 层和 4 层的访问依赖路径。下半部分是每条数据流路径的详细描述。

### 检查cilium-agent状态：

可以直接登录到cilium-agent，使用bash进行操作：`kubectl -n kube-system exec -ti cilium-9jlhx -- bash`

```shell
# 查看状态
cilium status
# 查看cilium负责的svc
cilium service list
# cilium monitor 抓包分析
cilium monitor
cilium monitor -vv
#获取ciilum bpf map信息
cilium map list
cilium map get cilium_ipcache -o json | jq
```



## 部署测试

### 通过hubble-ui观察



### 通过cilium-cli观察

cilium提供cilium-cli命令行工具，可以方便观察cilium状态，下载地址:

> https://github.com/cilium/cilium-cli/releases

下载解压到PATH路径下，然后执行：

```shell
# 检查cilium状态
cilium status

# 检查cilium 系统日志
cilium sysdump

# 连通性测试：会部署一系列deployment到k8s，需要能联网获取镜像
cilium connectivity test

# 其他
cilium help
```

