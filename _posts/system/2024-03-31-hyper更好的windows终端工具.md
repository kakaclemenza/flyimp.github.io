---
typora-root-url: ../..
---





### 为什么使用hyper

xshell收费, secureCRT比较老旧, 功能补全.

VNCViewer(tightVNC等系列)基本能满足需求, 但是本机在vim编辑是延迟巨大, 且vncconfig在处理clipboard时总有bug. 

经过多方尝试, 比较好用的是hyper和cmder, 这里选择了比较活跃的hyper



### 问题解决记录: 

* 回车会出现`%`, 设置: 

  ```shell
  env: {LANG:'en_US.UTF-8', TERM:'cygwin'},
  ```

* 字体:

  ```shell
  fontSize: 16,
  fontFamily: '"DejaVu Sans Mono"',
  ```

* 配色问题导致vim显示异常: 关闭vim上对于256色的支持

  ```shell
  vi ~/.vim/vim-init/init/init-style.vim
  """
  ...
  "set t_Co=256
  ...
  """
  ```

* 1



### 设置git bash与ssh自动登录

首先安装gitbash, 然后设置hyper:

```shell
shell: 'C:\\Program Files\\Git\\git-cmd.exe',
shellArgs: ['--command=usr/bin/bash.exe', '-l', '-i'],
env: {LANG:'en_US.UTF-8', TERM:'cygwin'},
```

设置好后重启hyper, 就可以看到使用了git-bash. 

下面配置ssh自动登录, git-bash的主目录在C:\Users\admin\下, 执行

```shell
cat ~/.ssh/id_rsa.pub | ssh xiaofeng@10.17.17.37 "mkdir -p ~/.ssh; cat >> ~/.ssh/authorized_keys"
```



### go语言内网开发vim+youcompleteme

##### 1. 利用gitee下载并配置youcompleteme

> step2、使用[git](http://blog.fpliu.com/it/software/git)下载`YouCompleteMe`源代码
>
> | 源   | https://github.com/Valloric/YouCompleteMe                    |
> | ---- | ------------------------------------------------------------ |
> | 镜像 | https://gitee.com/mirrors/youcompletemehttps://gitee.com/YouCompleteMe/YouCompleteMe |
>
> 示例：
>
> ```bash
> git -C ~/.vim/bundle clone https://gitee.com/mirrors/youcompleteme.git
> ```
>
> step3、进入`YouCompleteMe`源代码根目录
>
> ```bash
> cd ~/.vim/bundle/youcompleteme
> ```
>
> step4、查看`YouCompleteMe`的源代码根目录中的内容
>
> ![img](/img/system/YouCompleteMe-installation-via-source-ls.png)
>
> **注：**`install.py`就是安装脚本。后面会用到。
>
> step5、使用[git](http://blog.fpliu.com/it/software/git)下载`子模块`的代码
>
> ```bash
> git submodule update --init
> ```
>
> **注意：**请不要画蛇添足的加上`--recursive`参数，后面会知道原因。
>
> step6、将`third_party/ycmd/.gitmodules`中的`go.googlesource.com`字符串替换为`github.com/golang`
>
> ```bash
> sed -i".bak" "s@go.googlesource.com@github.com/golang@g" ./third_party/ycmd/.gitmodules
> ```
>
> step7、将`third_party/ycmd/build.py`中的`download.eclipse.org`字符串替换为`mirrors.ustc.edu.cn/eclipse`
>
> ```bash
> sed -i".bak" "s@download.eclipse.org@mirrors.ustc.edu.cn/eclipse@g" ./third_party/ycmd/build.py
> ```
>
> step8、设置[go get](http://blog.fpliu.com/it/software/GoToolchain/bin/go#get)的代理
>
> ```bash
> export GO111MODULE=on
> export GOPROXY=https://goproxy.io
> ```
>
> [golang](http://blog.fpliu.com/it/software/development/language/golang)的很多模块在`https://golang.org/x`下，国内是无法访问的，`Google`在[GitHub](http://blog.fpliu.com/it/open-source/software/project-hosting/GitHub)上也创建了对应的仓库， 奈何这些模块太多了，我们总不能一个一个去替换吧，我们也不知道它会用哪些模块，所以用代理服务器解决。`https://goproxy.io`是`https://golang.org/x`的代理，它的服务器在中国香港， 我们可以访问，速度也是相当的快。
>
> step9、继续下载剩余的`子模块`的代码
>
> ```bash
> git submodule update --init --recursive
> ```

这一步参考http://blog.fpliu.com/it/software/vim/plugin/YouCompleteMe

**如果之前已经下载配置过, 可以直接打包youcompleteme.zip, 拷贝进内网, 解压到~/.vim/bundle/youcompleteme, 就不需要重新下载和配置了**

##### 2. 内网安装

我的内网虚拟机由于做了比较多实验, python环境会比较复杂, 所以一定要注意. 这里使用的目标python3是在 /usr/local/python36/bin/python3 , **要先将/usr/bin/python3, /usr/local/bin/python3等做软链指向目标python3**

然后, 进入~/.vim/bundle/youcompleteme/, 执行编译安装:

```shell
python3 install.py --clang-completer --js-completer --ts-completer --java-completer --go-completer
```

编译过程中报错, python3是静态编译的, youcompleteme注入需要python3动态编译, 于是重新编译python3:

```shell
./configure --prefix=/usr/local/python36 --enable-shared
make -j4 all
sudo make install
```

再运行python3, 报错找不到动态库, 于是修改ld.so.conf并使生效:

```shell
echo "/usr/local/python36/lib" >> /etc/ld.so.conf.d/libc.conf
sudo ldconfig /etc/ld.so.conf
```

之后python3运行正常.

vim-init使用外网配置好的环境, 直接拷贝进来, init-basic.vim文件注意修改python3路径配置:

```shell
...
let g:ycm_server_python_interpreter = '/usr/local/bin/python3'
...
```

配置好了, vim中需要执行`:PlugInstall`安装插件, 在安装结果中会出现`youcompleteme`, 则安装成功了.

之后我们配置下.ycm_extra_conf.py

> `.ycm_extra_conf.py`是`YouCompleteMe Client`的配置文件。
>
> 在`YouCompleteMe Client`启动后，会从当前路径开始向上层路径寻找`.ycm_extra_conf.py`，找到后，会询问你要不要加载它， 如果没有找到，就加载`~/.vim/bundle/YouCompleteMe/.ycm_extra_conf.py`。
>
> `~/.vim/bundle/YouCompleteMe/.ycm_extra_conf.py`是全局配置，我们一般不做修改。
>
> 一般，我们会复制一个到`${HOME}`目录或者到自己的项目目录下，然后在此基础上做适合自己的修改。
>
> 在`~/.vim/bundle/YouCompleteMe`目录及其子目录下有很多的`.ycm_extra_conf.py`样例。你可以根据自己的需要复制。
>
> ```bash
> cp ~/.vim/bundle/YouCompleteMe/third_party/ycmd/.ycm_extra_conf.py ~
> ```



### 3. 检查是否正常工作. 问题解决

vi编辑一个go文件, 看看功能是否正常. <u></u>

**问题一**: 底行没报错, 但是vim中只有语法检查, 没有自动补全. 

结合`/system/2017-11-13-vim其他技巧总结.md`一文, 我们直到vim自动补全是依赖python3运行的服务, 于是`ps aux | grep python3`发现python3并没有运行. 经查证, 原因是此时/usr/bin/python3没有指向编译用的目标python3. 修改后问题解决.

**问题二**: 底行报错: `YouCompleteMe unavailable : invalid syntax (vimsupport.y, line 184)`

这个查网上github issue, 说是vim版本过低, 不支持python3.6以上注入. 所以需要升级vim到8.1以上, 单纯的源码编译安装比较难(国外源很慢). 于是**使用apt源方式强制安装, 在我本机Debian9上/etc/apt/sources.list加入Debian10的源**, 然后:

```shell
sudo apt-get update
# 查看有什么版本, 发现候选版本就是一个8.1的, 于是直接更新即可
sudo apt-cache policy vim
sudo apt-get install vim -y
```

更新完后, 再运行vim, 就能正常补全了. 记得删掉Debian10的源, 避免安装其他包时出现问题.



