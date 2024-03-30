---
layout: post
title: 1_lsp_go_overview
category: coder
typora-root-url: ../../../..
---

本系列是基于阅读[Hands-On System Programming with Go]一书做的笔记. 

### go开发环境搭建

```shell
# 安装
sudo apt-get install golang
# 修改GOPATH
echo "export GOPATH=/home/xiaofeng/.golang" >> ~/.zshrc.local
```

推荐的开发环境是vscode+vscode-go插件

### go语言优缺点

go的优点比较多, 在用的时候慢慢体会就好了, 书中P94有列出一些

go语言目前为人所诟病的点主要有三点:

* 没有显式的错误处理机制
  
  > 最后不能忍的就是panic，recover和error了，一行一个if err != nil。弄到快吐

* 没有泛型
  
  >   接口继承是duck type，原则是你像一个什么东西你就是什么东西。这太恶心了。找父接口的时候要多难受有多难受。美其名曰高内聚低耦合，其实扯淡。
  > 
  >   类型断言就是一大败笔。要不就直接支持自动隐式转换，要不就泛型。也理解语言作者的意图，降低难度，规避泛型。但是确实不大友好。但是也还能忍。就是难看。
  > 
  > 作者：FredricZhu
  > 链接：https://www.jianshu.com/p/4bc5897d8cbf

* 没有依赖包的版本管理
  
  > 这点其实通过增加一些包管理工具后, 已经得到解决.

Go2.0版本已经在计划加入错误处理和泛型(截至2020.08).

### go中的切片和数组

* 切片拼接: 
  
  ```go
  s1 := []int{0, 1, 2, 3}
  s2 := []int{4, 5, 6, 7}
  s1 = append(s1, s2...)
  ```

* 切片拷贝给数组:
  
  ```shell
  # 数组可以用于map中的键, 但切片不能, 此时会需要切片拷贝给数组的做法
  copy(arr[:], someSlice)
  ```

* 1

* 

### go中的map

有些情况下, 我们需要自定义map中的键的类型, map中的key可以是任何的类型, 只要它的值能比较是否相等, Go的[语言规范](http://golang.org/ref/spec#Comparison_operators)已精确定义, Key的类型可以是：

- 布尔值
- 数字
- 字符串
- 指针
- 通道
- 接口类型
- 结构体
- 只包含上述类型的数组

但不能是：

- slice
- map
- function

注意这里的复合类型, 需要其中每个元素也是能比较相等的类型. 比如结构体中如果包含了slice类型的元素, 就不能作为key

### 通道与select

```go
for {
    var ok bool
    select {
    case ok = <-done:
        if ok {
            break
        }
    case num := <- numbers:
        fmt.Println(num)
    }
    if ok {
        break
    }
}
```

### go中的位运算

```shell
^     异或/按位取反
```
