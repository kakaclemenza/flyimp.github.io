---
layout: post
title: flyos_plan
category: flyos
---

### plan
* 参照 thor-os, OS67
* TODO:   
(1) 取消交叉编译环境的限制   
(2) 进程调度

### flyos 安装方法
```
make create_hdd						# 按规格制作镜像文件
make bochs							# 编译内核, 写入hdd.img
sudo dd if=hdd.img of=/dev/sdb		# 将hdd.img写入USB设备, 这里假定为 /dev/sdb
# 这样USB启动盘就制作好了
```

### flyos 提交与合并规范
* 确保每一次提交, flyos 都应该是**可运行**状态
* 提交信息规范同 AngularJS 
* dev 分支进行开发, 每有重大进步, 需要合并 master:   
(1) 在分支修改 VERSION 文件, 增加新版本号及备注说明, 提交如:   
`V1.0.1: micro_kernel in cpp`   
(2) 切换到 master, 合并分支, 合并信息注明"merge: update version vx.x.x", 命令:  
`git merge --no-ff dev`  
(3) 合并完成, 切换到 dev, 执行:   
`git rebase master`


### 参考目标的编译注意事项   
* thor-os:   
	见**移动硬盘**中的成功备份文件  
	如果编译是出现类似某些头文件找不到的错误, 是因为thor-os使用了cpp.d类型的文件, 需要:  
	`make clean`   
	一下就可以了
* OS67:   
	见**移动硬盘**中的成功备份文件

### 常用命令:
* virtualbox 使用 img 做启动硬盘:  
1) VBoxManage convertdd  file.img file.vdi  
2) VBoxManage convertfromraw -format VDI ${source_img} ${destination_vdi}  

* virtualbox 使用 U 盘启动
1) VBoxManage internalcommands createrawvmdk -filename ~/.VirtualBox/VDI/UsbDisk.vmdk -rawdisk /dev/sdc 
2) 使用转换好的vmdk格式文件作为virtualbox启动硬盘

* losetup 操作 img 文件
1) sudo /sbin/losetup -o1048576 /dev/loop0 hdd.img   
2) sudo losetup -d /dev/loop0 卸载   

### bochs 调试总结
```
# 查看接下来要执行的 20 行
u /20
# 设置断点
b 0x9aa
# 设置跟踪寄存器信息, 则每次执行到断点会打印寄存器信息
trace-reg on
# 查看断点
blist
# 删除断点, num 是 blist 查到的断点号
b [num]
# 禁用/启用断点
bpd|bpe [num]
# 显示内存地址内容
x /4 0x9aa		# 显示线性地址后 4 字节内容
xp /4			# 显示物理地址后 4 字节内容
# 查看堆栈
print-stack
# 打印寄存器
r
# 更多...后续按需上网搜
```

### 未知问题搜集:
* [dev b0f0925]: 修改 CPP\_FLAGS 选项 -O1 为 -Os, 发现编译出来的内核 kernel.bin 变小了很多, 并且运行过程中也没有了错误. 之前则一直有 `set_diskette_current_cyl(): drive > 1` 错误, 经过 bochs 调试发现是读取 kernel.bin 时读到无法读取的 sectors 导致了报错.
* 
