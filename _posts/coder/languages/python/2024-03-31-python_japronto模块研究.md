---
layout: post
title: python_japronto模块研究
category: coder
typora-root-url: ../../../..
---

tornado是基于原生python代码实现的web框架, 效率过低. 所以无奈, 只能探寻更好的解决方案. 目前有:

* vibora: https://github.com/vibora-io/vibora
* japronto: https://github.com/squeaky-pl/japronto

两者都展示了很高的io, 本质上其实都是调用c写的libuv(直接调用的是cython封装的uvloop); 这里选择了"貌似"更强大的japronto!

迫于现有项目的要求, 需要深入源码进行理解, 然后调整代码, 使其与项目贴合. 这里就用来总结探究源码过程中遇到的问题吧. 可以发现自己对于python体系的了解还是不完整的 :)



### import是可以直接解析.so模块的

只要是按Python C接口编写的代码, 生成.so库, 就可以直接被python代码import; japronto里面对于C语言模块的依赖就是这样做的. 

japronto中/build.py中参照Cython.Distutils.build_ext, 自定义了build_ext方法, 然后在setup.py中使用build_ext方法对C语言模块进行构建.



### setup.py打包原理

