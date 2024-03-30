---
layout: post
title: python包管理与virtualenv
category: coder
---

### python包管理

**python模块索引路径问题**

(1)解释器首先搜索具有该名称的内置模块

(2)如果没有找到, 将在变量 `sys.path` 给出的目录列表中搜索

这里sys.path按顺序取决于如下几个因素:

* 安装路径判断: python为了支持virtualenv, 会对运行python二进制文件所处的目录进行判断, 获得一个相对的sys.prefix代表python的安装路径. **这一点取决于目录结构, 和virtualenv的active脚本无关!** 而后就会根据sys.prefix构建sys.path, 所以即使在其他目录下运行到virtualenv下的python, 看到的sys.path还是相对于virtualenv目录下的. 添加路径会先是当前路径"", 然后就是一系列系统默认路径(编译配置时--prefix指定)
  ref: https://stackmirror.com/questions/897792

* 对于当前路径""的定义, 细节是这样的, 假设目录树如下:

  ```
  .
  ├── a
  │   ├── a.py
  │   ├── a.pyc
  │   ├── __init__.py
  │   ├── __init__.pyc
  │   ├── ryu.py
  │   └── ryu.pyc
  ├── b
  └── main.py
  ```

  main.py调用a, a调用ryu; 这里我的系统中是安装了ryu模块的, 我直接在main.py同级目录执行main.py, 但是a中调用的ryu还是a/ryu.py, 而不是/usr/local/lib/python3.7/dist-packages/ryu/\__init__.py!!!

* a

**一. 源码安装**

依赖于apt的安装的python和pip通常比较旧, 容易出现各种问题. 所以有必要能快速通过源码安装正确的python环境, 所有的python和pip都可以通过类似下面命令进行快速简单安装:

```shell
#!/bin/bash

# wget https://www.python.org/ftp/python/3.6.8/Python-3.6.8.tgz
apt-get install build-essential libreadline6-dev libssl-dev -y \
	&& tar xvf Python-3.6.8.tgz \
	&& cd Python-3.6.8 \
	&& ./configure --prefix=/usr/local/python36 --with-ssl \
	&& make all \
	&& make install
if [ $? -ne 0 ]; then
    echo "build python3.6 failed. exit..."
    exit 1
fi

ln -s /usr/local/python36/bin/pip3 /usr/local/bin/pip3 \
    && ln -s /usr/local/python36/bin/python3 /usr/local/bin/python3
if [ $? -ne 0 ]; then
    echo "unable to make soft link for pip3 and python3"
    exit 2
fi
```

会同时安装python3和pip3, 并开启ssl支持.

**二. pip包管理**

*正常安装*

```shell
pip install xxx
pip install -i http://mirrors.aliyun.com/pypi/simple --trusted-host mirrors.aliyun.com xxx
```

默认的源可以设置在~/.pip/pip.conf:

```
[global]
trusted-host=mirrors.aliyun.com
index-url=http://mirrors.aliyun.com/pypi/simple
```

*离线安装*

可以配合virtualenv, 下载目标软件包及相关依赖:

```shell
virtualenv -p python3 myenv
source myenv/bin/activate
mkdir ryu_pkg && cd ryu_pkg
pip3 download ryu==4.30
cd .. && tar cvf ryu_pkg.tar ryu_pkg/
```

安装

```shell
tar xvf ryu_pkg.tar
cd ryu_pkg
# --no-index: 不使用源来安装包
# -f ./: 依赖索引目录为 ./; 注意有些pip版本需要写绝对路经/path或file:///path
#pip3支持直接从py压缩包或.whl文件安装
pip3 install --no-index -f ./ pbr-5.1.3-py2.py3-none-any.whl
pip3 install --no-index -f ./ ryu-4.30.tar.gz
```



### virtualenv 是什么

这其实是python界大名鼎鼎的打包工具, 它的初衷在于**完全的打包**当前的项目环境. 这意味着需要打包的东西大致是:

* python, pip等二进制可执行文件
* 通过pip安装的一些依赖包

是的你没看错, 这里的第一点决定了 virtualenv **并不能很好的实现真正的环境隔离**. 二进制文件的执行依赖于系统相关的底层库或模块, 不同系统间微小的环境差别, 可以能导致virtualenv中某个依赖包无法正常导入, 甚至pip或python这样的二进制可执行文件也不能正常执行! 

这样, 可以解释为什么在使用 virtualenv 迁移环境过程中, 总会出现各种莫名奇妙的问题.

**docker 是正途**

想要真正的实现带环境的迁移, docker的做法才是正确的. 需要从操作系统层环境开始, 对整个项目做打包.
