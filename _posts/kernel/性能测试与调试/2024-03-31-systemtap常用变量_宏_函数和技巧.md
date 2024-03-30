---
layout: post
title: systemtap常用变量_宏_函数和技巧
category: kernel
typora-root-url: ../../..
---

# SystemTap—-常用变量、宏、函数和技巧[转]

发表于[2020年3月30日](https://xmsg.org/wordpress/2020/03/systemtap-常用变量、宏、函数和技巧转/)由[xmsg](https://xmsg.org/wordpress/author/messageloop/)

一、宏



\1. kderef

从指定的地址处读取指定大小的值

格式为：

kderef(size, address);

其中address为要读取的地址值，size是要是读取的值的大小，返回值就是所读取的值。

2.kread

在嵌入的C代码中安全地读取指针值

格式为：

kread(&(address))

 

二、函数

1.execname()

获取当前进程的名称，即可执行文件的名称

\2. pid()

获取当前进程的PID

3.pp()

获取当前的probe点。例如 probe process.syscall,process.end { /* scripts */},在块中调用pp()可能会返回”process.syscall”和”process.end”。

4.probefunc()

获取当前probe的函数名称。例如probe sys_read函数，在probe块中调用该函数就会返回sys_read。注意这个函数的返回值是从pp()返回的字符串中解析得到的。

5.tid()

获取当前线程的ID

6.cpu()

获取当前CPU的ID

7.gettimeofday_s()

获取当前Unix时间

8.get_cycles()

获取处理器周期数

9.ppfunc()

获取当前probe的函数名称。在probe指定文件中的函数中时非常有用，可以知道当前的probe位于哪个函数。

10.print_backtrace()

打印内核调用栈信息

11.print_ubacktrace()

打印用户态调用栈信息

12.thread_indent()

输出当前线程的信息，格式为“相对时间 程序名称(线程id)：（空格)”，如果当前probe的函数执行的次数约到，空格的数量也就越多。这个函数还有一个参数，用来控制空格的数量。如果参数值越大，则空格的数量越多。相对时间是当前的时间（以微秒为单位）减去指定线程第一次执行thread_indent时的时间。

13.target()

获取当前脚本针对的目标进程ID。需要配置stap的-c或-x命令使用。

 

三、技巧

[1.@cast](mailto:1.@cast)()操作

如果将一个获取的值（可能是一个类型的地址值）存储到SystemTap中定义的变量，但是在读取的时候需要根据特定的类型去读取，此时，可以使用@cast()操作来读取。

其格式为

@cast(p, “type_name”[,”module”])->member

在systemtap中使用cast来将指定的地址值转换为C语言中的类型，并且可以去获取相应的值（例如结构体成员）示例如下

function is_tcp_packet:**long**(iphdr) {
protocol = @cast(iphdr, “iphdr”)->protocol
**return** (protocol == %{ IPPROTO_TCP %}) /* <– expression */ }

如果是在probe内，还可以直接使用$ptr来获取成员的值，例如：

```
probe begin {
printf(“SystemTap Scripts start…..\n”);
}

probe kernel.function(“tcp_v4_rcv”) {
printf(“skb->len = %d\n”, $skb->len);
}
```

@cast()操作中还可以指定类型所在的头文件，示例如下：

```
@cast(tv, “timeval”, “<sys/time.h>”)->tv_sec
@cast(task, “task_struct”, “kernel<linux/sched.h>”)->tgid
```

2.在使用嵌入C代码作为函数体的辅助函数中获取参数和设置返回值

如果版本是1.8或更新的，则使用STAP_ARG_(参数名)来获取参数，例如STAP_ARG_arg，其中arg是参数名。设置返回值的形式是STAP_RETVALUE=value。

如果版本是1.7或更老的，则使用THIS->（参数名）来获取参数，例如THIS->arg，其中arg是参数名。设置返回值的形式是THIS->__retvalue=value。

3.获取probe函数的参数

如果带debuginfo，即DWARF probes，则可以直接使用参数的名称加’$’即可，例如sys_read()中的第一个参数fd，就可以通过$fd来获取其值。

如果缺少debuginfo，即DWARF-less probing，则需要通过uint_arg(),pointer_arg()和ulong_arg()等来获取，这些函数都需要指定当前要获取的参数是第几个参数，编号从1开始。例如asmlinkage ssize_t sys_read(unsigned int fd, char __user * buf, size_t count)中，uint_arg(1)获取的是fd的值，pointer_arg(2)获取的是buf的地址值，ulong_arg(3)获取的是count参数。更多的获取参数的函数参见[man page index](http://sourceware.org/systemtap/man/index.html)。

如果是通过process.syscall、process(“PATH”).syscall或者process(PID).syscall来probe系统调用，则可以通过$syscall来获取系统调用号，通过$arg1,$arg2等来获取相应的参数值。

在probe用户程序，系统调用或内核函数时，可以通过parms来获取所有的参数（是字符串，不是具体的值）。在使用“probesyscall.名称”来probe系统调用时，可以使用argstr来获取参数列表，和parms来获取所有的参数（是字符串，不是具体的值）。在使用“probesyscall.名称”来probe系统调用时，可以使用argstr来获取参数列表，和parms显示格式不同，直接显示对应的值。

4.”.”字符窜连接符

如果想将一个函数返回的字符串和一个常量字符串拼接，则在两者之间加入”.”即可，例如probefunc().”123″。

“.”运算符还支持”.=”，即拼接后赋值。

5、获取stap命令行参数

如果要获取命令行参数准确的值，则使用$1、$2….$<NN>来获取对应的参数。如果想将命令行参数转换为字符串，则使用@1、@2…@<NN>来获取参数对应的字符串。

6、next操作

如果在probe函数中，发现某个条件没有满足，则结束本次probe的执行，等待下次事件的到来。示例如下：

```
global i

probe begin {
printf(“SystemTap Scripts start…..\n”);
}

probe kernel.function(“sys_read”) {
++i;
**if** (i % 2) {
next;
}
printf(“i = %d\n”, i);
}
```

7、$$vars

如果合适的话，可以通过$$vars获取当前所有可见的变量列表。如果列表中某些成员的值显示”？”，则表示当前这些变量尚未初始化，还不能访问。

8、call和inline后缀的区别

如果加上call后缀，只有在当前probe的函数是非内联函数时才会触发事件。例如，如果在内联函数pskb_may_pull()的probe点加上call后缀，则事件不会被触发。对于非内联函数的probe点，不能加上inline后缀，否则编译时会报错。如果想触发内联函数的probe事件，一定不能加上call后缀。如果call和inline后缀都不加，则内核函数和非内联函数的probe事件都会触发。

9、输出”%”字符

在systemtap中使用转义字符来输出”%”没有效果，在编译时会报错，可以使用”%%”来输出”%”。