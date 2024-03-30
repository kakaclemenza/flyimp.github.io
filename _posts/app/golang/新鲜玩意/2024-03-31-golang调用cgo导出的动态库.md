---
layout: post
title: golang调用cgo导出的动态库
category: app
typora-root-url: ../../../..
---

## 需求

1. 需要开发一个golang写的动态库给C调用，所以使用cgo导出
2. 测试程序本来是用c写的，但是后续测试比较复杂，希望使用golang写

于是就用了golang调用c动态库的需求，包括：**需要传入golang的回调函数**

## 实现

本质上，这是可以实现的，不过目前发现只有linux上能正常支持，win上使用mingw32编译正常，但是运行时会报错`0xc0000005`，暂没找到合适的解决办法

下面记录下实现方式：

1. 源码目录：

   ```shell
   .
   ├── Makefile
   ├── lib				#库文件
   │   └── add.go
   ├── cfuncs.go        # go层回调函数C风格化接口
   └── main.go			# go调用C库示例代码
   ```

2. `./lib/add.go`

   ```go
   package main
   
   /*
   #include<stdlib.h>
   typedef void (*LogCb)(char *s);
   static void callLogCb(LogCb cb, char *s) {
           cb(s);
   }
   */
   import "C"
   import (
           "fmt"
           "unsafe"
   )
   
   //export Add
   func Add(a, b int, cb C.LogCb) {
           msg := fmt.Sprintf("%d + %d = %d", a, b, a+b)
           cMsg := C.CString(msg)
           C.callLogCb(cb, cMsg)
           C.free(unsafe.Pointer(cMsg))
   }
   
   func main() {
   }
   ```

3. `./cfuncs.go`

   ```go
   package main
   
   /*
   void MyLogCb_cgo(char *s) {
           void MyLogCb(char*);
           MyLogCb(s);
   }
   */
   import "C"
   ```

   

4. `./main.go`

   ```go
   package main
   
   /*
   #cgo CFLAGS: -I ./
   #cgo LDFLAGS: -L. -ladd -Wl,-rpath=.
   
   #include <stdlib.h>
   #include "libadd.h"
   void MyLogCb_cgo(char *s);
   */
   import "C"
   
   import (
           "fmt"
           "unsafe"
   )
   
   //export MyLogCb
   func MyLogCb(msg *C.char) {
           fmt.Printf("LogCb msg:%s\n", C.GoString(msg))
   }
   
   func main() {
           C.Add(1, 2, (C.LogCb)(unsafe.Pointer(C.MyLogCb_cgo)))
   }
   ```

   

5. `./Makefile`
   这里需要编译出来的程序使用相对目录查找动态库，添加连接选项`-Wl,-rpath.*`；这些选项因为go编译器安全考虑，默认被禁用，所以需要使用`CGO_LDFLAGS_ALLOW="-Wl,-rpath.*"`来启用（参考：https://pkg.go.dev/cmd/cgo）

   ```go
   main: clean
           go build --buildmode=c-shared -o ./libadd.so lib/add.go
           CGO_LDFLAGS_ALLOW="-Wl,-rpath.*" go build -o main *.go
   
   clean:
           rm -rf ./main ./libadd*
   ```

   


