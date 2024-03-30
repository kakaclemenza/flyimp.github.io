---
layout: post
title: android bug定位与调试
category: app
typora-root-url: ../../../..
---

# 基本调试步骤

1. 看日志：应用日志、崩溃报告bugreport
2. 找共性：平台类型、cpu架构、发生时间、发生条件
3. 尝试稳定复现：有些bug，需要运行长时间才能复现。于是需要申请真机或测试机长时间跑。
4. 加日志定位
5. 借助调试工具：ASAN，lldb，adb crash log

java层的调试相对简单，而且我对java不熟悉，就不介绍了。由于这边编写的是c/c++库，这里主要介绍native层的调试。

## 查日志

### 应用日志

应用日志不多说，按程序设计不同而不同，日志应该分级别，并在关键分支打上日志。

### 崩溃报告bugreport

android应用崩溃的时候，系统会保存一个tombstone文件到/data/tombstones目录，bugly系统上的崩溃信息应该也是取自这里。使用下面命令会导出最近的crash相关信息：

```shell
# 将崩溃信息保存到E盘
adb bugreport E:\
```

导出的信息是zip包，解压后如下：

![img](../../../assets/1460468-2ae2a88222d17058.png)

其中tombstone_xx就是近10次崩溃的信息记录。依次查找到我们应用程序的对应崩溃日志，大致如下：

![img](../../../assets/1460468-612b6c69d14984f4.png)

然后就可以配合some-abi-addr2line.exe工具（一般在${NDK_ROOT}/toolchains/llvm/prebuild/windows-x86_64/bin/目录下）查具有调试信息的native库来定位崩溃具体行号，如：

```
i686-linux-android-addr2line.exe -Cfe .\xxx.so 0010e48c
```

一般bugreport中报告的问题特征关键词记录如下：

* 应用无响应/死锁：am_anr
* 查看处于聚焦状态的 Activity：am_focused_activity
* 查看进程启动事件：Start proc
* 设备是否发生系统崩溃：am_proc_died
* 内存不足：am_low_memory



## 找共性

一般接入bugly系统，即可看到多次崩溃的共性特征。利用共性特征设置模拟环境，才能方便复现bug

## adb crash log

复现bug后，我们就可以在本地查找具体原因。使用adb crash log能打印出崩溃堆栈，减少干扰。

```
adb logcat -b crash
```

本质上这上面的信息和tombstone没有差别，也可以使用some-abi-addr2line.exe配合具有调试信息的库来定位具体崩溃点。



## 调试工具ASAN

### 基本原理

**程序申请的每 8bytes 内存映射到 1byte 的 shadown 内存上。**

因为 malloc 返回的地址都是基于8字节对齐的，所以每8个字节实际可能有以下几个状态：

**case 1：**8 个字节全部可以访问，例如`char* p = new char[8];` 将0写入到这8个字节对应的1个字节的shadow内存。

**case 2：**前 1<=n<8 个字节可以访问, 例如`char* p = new char[n]`, 将数值n写入到相应的1字节的shadow内存，尽管这个对象实际只占用5bytes，malloc的实现里[p+5, p+7]这尾部的3个字节的内存也不会再用于分配其他对象，所以通过指针p来越界访问最后3个字节的内存也是被允许的。

**asan还会在程序申请的内存的前后，各增加一个redzone区域（n \* 8bytes），用来解决overflow/underflow类问题。**

free对象时，**asan不会立即把这个对象的内存释放掉，而是写入1个负数到该对象的shadown内存中，即将该对象成不可读写的状态， 并将它记录放到一个隔离区(book keeping)中**, 这样当有野指针或use-after-free的情况时，就能跟进shadow内存的状态，发现程序的异常；一段时间后如果程序没有异常，就会再释放隔离区中的对象。

**编译器在对每个变量的load/store操作指令前都插入检查代码**，确认是否有`overflow、underflow、use-after-free`等问题。

### 使用范围

ASan 可以检测到内存错误类型如下：

- Stack and heap buffer overflow/underflow 栈和堆缓冲区上溢/下溢；
- Heap use after free 堆内存被释放之后还在使用其指针；
- Stack use outside scope 在某个局部变量的作用域之外，使用其指针；
- Double free/wild free 指针重复释放的情况。

ASan 支持 arm 和 x86 平台，使用 ASan 时，APP 性能会变慢且内存占用会飙升。针对 arm64 平台，Android 官方推荐使用 HWASan

### as接入方式

参考: https://developer.android.com/ndk/guides/asan#cmake

#### 修改配置文件

CMake APP 下面的 build.gradle 添加：

```text
android {
    defaultConfig {
        externalNativeBuild {
            cmake {
                # ANDROID_STL也可以设置为"system"或"none"
                arguments "-DANDROID_ARM_MODE=arm", "-DANDROID_STL=c++_shared"
            }
        }
    }
    buildTypes {
    	debug {
    		# 告诉Android系统本程序允许调试。否则调试器是连接不到这个程序上去的
    		debuggable true
    	}
    }
    
    packagingOptions {
    	# 对于第三方引入的so库, 不进行调试信息裁剪
    	doNotStrip "**.so"
    	jniLibs.useLegacyPackaging = true
    }
    
    sourceSets {
    	main {
    		jniLibs.srcDirs = ['jni/libs']
    		resources.srcDir = 'jni/resources'
    	}
    }
}
```

CMakeLists.txt 脚本添加:

```text
target_compile_options(${libname} PUBLIC -fsanitize=address -fno-omit-frame-pointer)
set_target_properties(${libname} PROPERTIES LINK_FLAGS -fsanitize=address)
```

#### 添加wrap.sh和asan库

1.  ASan 运行时库添加到应用模块的 `jni/libs` 中

2. 将包含以下内容的 `wrap.sh` 文件添加到 `jni/resources/lib` 目录中的每个目录。目录路径在上面build.gradle中通过`resources.srcDir`指定

   ```
   #!/system/bin/sh
   HERE="$(cd "$(dirname "$0")" && pwd)"
   export ASAN_OPTIONS=log_to_syslog=false,allow_user_segv_handler=1
   ASAN_LIB=$(ls $HERE/libclang_rt.asan-*-android.so)
   if [ -f "$HERE/libc++_shared.so" ]; then
       # Workaround for https://github.com/android-ndk/ndk/issues/988.
       export LD_PRELOAD="$ASAN_LIB $HERE/libc++_shared.so"
   else
       export LD_PRELOAD="$ASAN_LIB"
   fi
   "$@"
   ```

最终目录结构：

> ```txt
> jni
>  ├── libs
>  │   ├── arm64-v8a
>  │   │   └── libclang_rt.asan-aarch64-android.so
>  │   ├── armeabi-v7a
>  │   │   └── libclang_rt.asan-arm-android.so
>  │   ├── x86
>  │   │   └── libclang_rt.asan-i686-android.so
>  │   └── x86_64
>  │       └── libclang_rt.asan-x86_64-android.so
>  └── resources
>  	└── lib
>         ├── arm64-v8a
>         │   └── wrap.sh
>         ├── armeabi-v7a
>         │   └── wrap.sh
>         ├── x86
>         │   └── wrap.sh
>         └── x86_64
>             └── wrap.sh
> ```

#### 运行

配置好如上设置，再编译出apk，就是具备ASAN功能的apk了，具体崩溃时就会打印出出更详细的崩溃原因

## 调试工具lldb

对于AS管理的代码，可以使用AS自带的调试工具进行完整调试，十分方便。但是对于引入的第三方库，由于没有源码AS无法正常进行调试，这时候就需要借助lldb工具。

### 确保第三方库具有调试信息

Change `build.gradle` as follows.

**NOTE:** If your ndk is used in a library, then change your *library*'s gradle file instead of your *main application*'s.

```
android {
  defaultConfig {
    packagingOptions {
      doNotStrip '**.so'     // ADD THIS! #1
    }
    externalNativeBuild {
      cmake {
        cppFlags "-Wl,--build-id -g"     // ADD THIS! #2
      }
    }
  }
}
```

Step2: Build the project (for me it is `flutter build apk --debug`, but for native Android projects you know it).

Step3: Now your `.so` with symbols is here: (This is *sample* location, where the library name is vision_utils and my .so file name is libvision_utils.so)

```
./build/vision_utils/intermediates/cmake/debug/obj/arm64-v8a/libvision_utils.so
```

or

```
./build/vision_utils/intermediates/stripped_native_libs/debug/out/lib/arm64-v8a/libvision_utils.so
```

Bonus1: If you want the "actual" .so file in apk, find it like `unzip -p ./build/app/outputs/apk/debug/app-debug.apk lib/arm64-v8a/libvision_utils.so > ./build/temp-libvision_utils.so`.

Bonus2: If you are using [bloaty](https://github.com/google/bloaty), you can run your command like: `bloaty ./build/temp-libvision_utils.so --debug-file=./build/vision_utils/intermediates/stripped_native_libs/debug/out/lib/arm64-v8a/libvision_utils.so -d compileunits`

附注：对于Android.mk编译的库，同样需要调整编译选项加入`-g`参数，输出的带调试信息的库放在`{project}/obj/local/armeabi/`目录下

### 配置lldb-server

首先，android模拟器需要是获得root权限的。

根据设备的cpu类型，选择对应的lldb-server，上传到android模拟器：

```shell
adb push ${NDK_ROOT}/toolchains/llvm/prebuilt/windows-x86_64/lib64/clang/9.0.8/lib/linux/i386/lldb-server /data/local/tmp/
```

这边是i386架构，其他架构要使用对应目录下的lldb-server。

然后运行lldb-server

```shell
# adb shell登陆后执行：
cd /data/local/tmp/
chmod 777 ./lldb-server
./lldb-server platform --server --listen unix-abstract:///data/local/tmp/debug.sock
```

### lldb连接服务器

windows下不能安装lldb，只能再linux下或者mac下进行操作，这里可以使用windows上跑linux虚拟机，然后linux虚拟机安装lldb来连接windows上的android模拟器的方式，实现调试：

```shell
#linux虚拟机安装lldb
apt install lldb
#连接到android模拟器的adb服务器，这里监听的tcp地址为192.168.59.101:5555
adb connect 192.168.59.101:5555
#lldb运行前，需要使用adb connect先连上模拟器
lldb
> platform select remote-android
> platform connect unix-abstract-connect:///data/local/tmp/debug.sock
# 假设要调试的应用pid为1835；attach完成后该进程就被暂停了
# 查pid： adb shell ps -ef | grep demo
> attach -p 1835
# 按文件行号打断点：`xxx.cpp:1358`
> br set -f xxx.cpp -l 1359
# 按方法名设置断点
> br set -n TestFunc
# 继续执行
> c
```

### lldp常用操作指令

1. breakpoint调试断点：

   ```shell
   #指定文件和行号设置断点
   breakpoint set --file abort.c --line 12
   breakpoint set -f syscall.S -l 12
   
   #指定函数名称设置断点
   breakpoint set --name abort
   breakpoint set -n assert
   
   #指定函数名规则匹配：
   breakpoint set --func-regex abort
   
   #指定地址：
   breakpoint set --address 0xf2dbd03e
   breakpoint set -a 0xf2dbd03e
   
   #指定库
   breakpoint set --shlib liblog.so --name _log
   
   #查看已经设置的断点，注意看输出信息包含断点是否成功命中、是否enable、进程中有多少个位置命中断点：
   breakpoint list
   
   #禁用、启用、删除断点：
   breakpoint disable 1 # 对断点1进行操作
   breakpoint enable 1
   breakpoint delete 1
   breakpoint delete all # 删除所有断点
   ```

   

2. thread线程操作/backtrace/bt

   ```shell
   thread list
   thread backtrace
   bt # 上一条命令的简写
   thread backtrace all
   thread select n # 选择指定的线程号
   
   thread continue/continue/c
   thread step-over/next/n
   thread step-into/step/s
   thread step-out/finish
   thread return 10
   ```

   

3. frame栈帧操作

   ```
   frame info
   frame select n # 选择栈帧
   frame up # 向上一层栈帧
   frame down
   frame variable # 打印当前栈帧的变量
   ```

   

4. image镜像操作

   ```shell
   #列出进程加载的库
   image list
   
   #查找指定的地址信息
   image lookup --type
   image lookup -t
   image lookup --name
   image lookup -n
   image lookup --address
   image lookup -a
   
   #通过函数名或符号名查找对应的地址
   image lookup -r -n <FUNC_REGEX> # 有符号时使用
   image lookup -r -s <FUNC_REGEX> # 无符号时使用
   
   #dump
   image dump sections
   image dump sym
   ```

5. watchpoint调试断点

   ```shell
   #针对变量、内存地址进行设置：
   watchpoint set variable valName # 代码中的变量名
   watchpoint set variable self->_dataArray
   watchpoint set expression 0x14AD6A70
   
   #在此基础上添加条件（Read、Write）：
   watchpoint set expression -w read -- 0x16aabbcc # 内存地址 注意--
   watchpoint set expression -w write -- 0x16aabbcc
   
   #条件断点：
   watchpoint modify -c '*(int *)0x10aabbcc == 1'
   
   #操作
   watchpoint list
   watchpoint delete i
   watchpoint delete all
   ```

6. 流程控制

   ```shell
   r     # run
   run   # 运行程序
   c     # process continue
   process continue      # 继续
   process interupt      # 暂停
   s     # strp
   step    # 源码级别的单步执行/进入函数
   stepi   # 汇编指令级别的单步执行/进入函数
   next    # 同step但不进入函数
   nexti   # 同stepi但不进入函数
   finish  # 完成执行当前函数（执行完成当前函数的所有剩余指令并退出到上一级）
   return  # 直接退出当前函数，可以指定返回值
   f       #显示当前所处代码行
   l       #列出源代码
   ```

7. memory内存操作

   ```shell
   #memory read [起始地址 结束地址]/寄存器 -outfile 输出路径（内存操作）
   # Memory操作比较复杂，建议直接查看官方手册或Cheat Sheet
   memory read $pc
   ```

8. disassemble：显示汇编代码

   ```shell
   disassemble -b
   disassemble --frame
   disassemble --name func_name
   disassemble -a address
   disassemble -s address
   d # 这三行都是等价简写
   di
   dis
   ```

   

9. register寄存器操作

   ```shell
   #读写寄存器：
   register read
   register read r0
   register write r10 1 # 寄存器名称 写入值
   ```

10. expression/print打印、执行表达式打印结果

    ```shell
    expr (int) strlen(testVar)
    ```

    

11.  display变量观察列表：类似IDE提供的watch list。每次单步执行后都会打印出指定的表达式的值。

    ```shell
    display expr
    display list
    undisplay n
    ```

12. help

    ```
    help
    help frame
    ```

    



## bug经验总结

### arm结构体强转导致崩溃

这类问题比较难查，需要涉及到汇编代码，具体原因是结构体发生强制转换，转换后数据对齐信息没有同步过去。再arm中某些指令如`STMIA/LDMIA`在处理非对齐数据时，会直接崩溃。



