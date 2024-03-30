---
layout: post
title: msys2替代gitbash
category: system
typora-root-url: ../..
---

## 背景

在win下使用linux命令行，目前是有比较多的选择了，这边尝试过的很多种，优缺点列举如下吧：

| 工具      | 优点                                                         | 缺点                                                         |
| --------- | ------------------------------------------------------------ | ------------------------------------------------------------ |
| mingw-w64 | * 提供了最原始的linux命令在win下的实现<br />* 跨平台编译依赖最直接的库 | * 缺乏维护，mingw已经停止维护，mingw-w64则很难更新<br />* 软件需要更新新装难 |
| cygwin    | * 和mingw-w64差不多<br />* 更新维护比较及时                  | * 软件需要更新新装不方便，需要在gui上操作<br />* 安装、迁移复杂 |
| WSL       | * 相当于微软做的linux独立内核虚拟机                          | 有点四不像，部分linux系统功能受限，windows开发又不方便       |
| msys2     | * 安装方便，一个exe安装完成<br />* 更新方便，使用pacman包管理器进行更新，可以方便使用国内源<br />* 可选使用mingw-w64、cygwin、clang进行跨平台编译 |                                                              |

如上，这边最终是使用了msys2作为win下的linux命令行进行工作。

以下介绍一下相关环境的部署过程，其实都挺简单的。

## 部署

1. 安装：到[MSYS2官网](https://www.msys2.org/)下载最新版本[msys2-x86_64-20221028.exe](https://github.com/msys2/msys2-installer/releases/download/2022-10-28/msys2-x86_64-20221028.exe)并安装

2. 打开安装后的`MSYS2 MSYS`程序，会出来mintty命令行窗口；接下来安装必备软件：默认镜像源中就有不少中国镜像，无需修改pacman就会选择好最优的源。直接安装所需的软件：

   ```shell
   # mingw-w64-x86_64-toolchain: gcc、g++、make等开发环境
   # zsh：替代bash
   # git、vim：必备工具
   # help2man man-db man-pages-posix：man手册
   pacman -Sy mingw-w64-x86_64-toolchain zsh git vim help2man man-db man-pages-posix 
   ```

3. 将msys2集成到windows terminal中使用：

   * 新建配置，命名为msys2，并将其设为”启动-默认配置文件“

   * 打开settings.json，修改`profiles.list`以下配置项，保持系统生成的guid，其他都改成如下：

     ```shell
     {
         "commandline": "D:/Program/msys64/msys2_shell.cmd -msys -defterm -no-start -use-full-path",
         "cursorShape": "filledBox",
         "icon": "D:/Program/msys64/msys2.ico",
         "name": "msys2",
         "startingDirectory": null
     }
     ```

     其中：`-msys -defterm -no-start`参数用于内嵌在命令行运行，`-use-full-path`用于合并windows中的PATH到msys2中，这样就可以执行windows下的指令了；比如windows下安装的golang，python3等。

4. 将msys2集成到vscode：修改settings.json如下即可

   ```shell
   {
   	...
       "terminal.integrated.defaultProfile.windows": "msys2",
       ...
       "terminal.integrated.profiles.windows": {
           ...
           "msys2": {
               "path": [
                   "D:\\Program\\msys64\\msys2_shell.cmd",
               ],
               "args": ["-msys", "-defterm", "-no-start", "-here", "-use-full-path"],
               "icon": "terminal-bash"
           }
       }
   }
   ```

   其中`-here`参数可以使msys2命令行打开时工作目录定位到工程目录下

5. 修改shell为zsh：编辑msys2_shell.cmd文件，调整`set "LOGINSHELL=bash"`为`set "LOGINSHELL=zsh"`

6. 其他优化：编辑`~/.zshrc.local`：

   ```shell
   #bigger history
   HISTSIZE=10000000
   
   prompt off
   autoload -U colors && colors
   # Customise the prompt yourself:
   PS1="%{$fg[magenta]%}▶ %{$reset_color%}"
   
   #设置取消ctrl+s, ctrl-q，防止不小心锁了命令行
   stty -ixon
   stty -ixoff
   
   #添加开发命令路径
   export PATH=$PATH:/mingw64/bin
   
   #别名，方法命令保持linux习惯
   alias vi=vim
   alias make=mingw32-make
   alias gcc=x86_64-w64-mingw32-gcc
   alias g++=x86_64-w64-mingw32-g++
   alias cc=x86_64-w64-mingw32-cc
   alias c++=x86_64-w64-mingw32-c++



参考文档：https://ttys3.dev/post/windows-terminal-msys2-mingw64-setup/
