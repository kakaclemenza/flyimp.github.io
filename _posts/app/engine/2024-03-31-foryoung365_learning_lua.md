---
layout: post
title: Lua语言学习笔记
category: development
tags: [Lua]
typora-root-url: ../../..
---

自学过Lua好多次，每次都因为长时间没用然后忘记了。这次决定做一下笔记，一方面加深印象，另一方面为了下次忘记能够快速“捡回来”做准备。

参考教程：[菜鸟教程之Lua教程](http://www.runoob.com/lua/lua-tutorial.html)

参考手册：[Lua5.3参考手册](http://www.runoob.com/manual/lua53doc/contents.html#contents)

*斜体部分为我个人的理解，可能不一定正确，只是帮助记忆。*

[TOC]

## 注释

### 单行注释

`--`是单行注释：

```lua
--这是单行注释
```

### 多行注释

`--[[]]--`是多行注释：

```lua
--[[
  这是多行注释的第一行
  这是多行注释的第二行
  ...
]]
```

## 标识符

*我喜欢称之为变量名*。规则同C/C++。字母或者下划线`_`开头，后面跟字母、数字或者下划线。

## 关键词

即系统保留关键字。一般约定，以下划线开头连接一串大写字母的名字（比如`_VERSION`）被保留用于Lua内部全局变量。

| and      | break | do    | else   |
| -------- | ----- | ----- | ------ |
| elseif   | end   | false | for    |
| function | if    | in    | local  |
| nil      | not   | or    | repeat |
| retrun   | then  | true  | until  |
| while    |       |       |        |

## 全局变量

在默认情况下，变量总是认为是全局的。（*好奇怪的设定*）

全局变量不需要声明，给一个变量复制后即创建了这个全局变量。访问一个没有初始化的全局变量也不会出错，只不过得到的结果是：nil。*（我的理解是全局变量默认初始化为nil。）*

```lua
print(b)    --nil
b = 10
print(b)    --10
```

如果你想删除一个全局变量，只需要将变量赋值为nil。

```lua
b = nil
print(b)    --nil
```

*简单的理解为，当且仅当一个变量不等于nil时，这个变量才存在。*

## 数据类型

Lua是动态类型语言，不需要指定变量类型。

| 数据类型     | 描述                                                                                                                                  |
| -------- | ----------------------------------------------------------------------------------------------------------------------------------- |
| nil      | 表示一个无效值（在条件表达式中相当于）                                                                                                                 |
| boolean  | 包含两个值：false和true。                                                                                                                   |
| number   | 表示双精度类型的实浮点数（*数值型全是double*）。                                                                                                        |
| string   | 字符串，由一对双引号或者单引号来表示。                                                                                                                 |
| function | 由C或Lua编写的函数                                                                                                                         |
| userdata | 表示任意存储在变量中的C数据结构。                                                                                                                   |
| thread   | 表示执行的独立线程，用于执行协同程序                                                                                                                  |
| table    | Lua中的表（table）其实是一个“关联数组”（associative arrays），数组的索引可以是数字或者是字符串(*说的这么复杂，其实就是一个map*)。在Lua里，table的创建是通过构造表达式来完成，最简单构造表达式是`{}`，用来创建一个空表。 |

我们可以使用type函数测试给定变量或者值的类型：

```lua
print(type("Hello world"))  --string
print(type(10.4*3))            --number
print(type(print))            --function
print(type(type))            --function
print(type(true))            --boolean
print(type(nil))            --nil
print(type(type(X)))        --string(type函数返回值为string)
```

### nil

nil类型表示一种没有任何有效值，它只有一个值——nil，例如打印一个没有赋值的变量，便会输出一个nil值：

```lua
print(type(a))        --nil
```

对于全局变量和table，nil还有一个删除作用，给全局变量或者table表里的变量赋一个nil值，等同于把它们删掉。

*可以理解为nil就是表示“不存在”。如果一个变量的值为nil，说明它不存在。把一个变量赋值为nil，意思就是这个变量被标记为不存在了。*

### boolean

boolean类型只有两个可选值：true和false，**Lua把nil和false看作是假**，**其他的都为真**。

### number

Lua默认只有一种number类型——double类型（默认类型可以修改luaconf.h）里的定义，以下几种写法都被看作是number类型：

```lua
a = 2
a = 2.2
a = 0.2
a = 2e+1
a = 0.2e-1
a = 7.8263692594256e-06
```

### string

字符串由一对双引号或者单引号表示。

```lua
string1 = "this is string1"
string2 = "this is string2"
```

也可以用2个方括号`[[]]`来表示“一块”字符串。

```lua
html = [[
  <html>
  <head></head>
  <body>
      <a href="foryoung365.github.io">苍月小筑</a>
  </body>
  </html>
]]
print(html)
```

在一个数字字符串上进行算术操作时，Lua会尝试将这个数字字符串转成一个数字：

```lua
print("2" + 6)            --8.0
print("-2e2" * "6")        -- -1200
```

如果该字符串无法转换为数字，将会报错。

字符串的连接使用的是`..`：

```lua
print("a" .. "b")        --ab
print(157 .. 428)        --157428
```

使用#来计算字符串的长度，放在字符串前面：

```
len = "foryoung365.github.io"
print(#len)                        --21
```

*转义字符和C/C++相同。*

#### 字符串操作

| 方法                                                      | 用法                                                                                        |
| ------------------------------------------------------- | ----------------------------------------------------------------------------------------- |
| string.upper(argument)                                  | 字符串全部转为大写字母。                                                                              |
| string.lower(argument)                                  | 字符串全部转为小写字母。                                                                              |
| string.gsub(MainString, FindString, ReplaceString, Num) | 在字符串中替换，MainString为要替换的字符串，FindString为被替换的字符串，ReplaceString要替换的字符串，num为替换次数（可以忽略，则全部替换）。  |
| string.strfind(str, substr, [init, [end]])              | 在一个指定的目标字符串中搜索指定的内容（第三个参数为索引），返回其具体位置。不存在则返回nil。`string.find("Hello Lua user", "Lua", 1)` |
| string.reverse(arg)                                     | 字符串反转                                                                                     |
| string.format(...)                                      | 返回一个类似print的格式化字符串。`string.format("the value is:%d", 4)`                                  |
| string.char(arg)和string.byte(arg[,int])                 | char将整型数字转成字符串并连接，byte转换字符为整数值（可以指定某个字符，默认第一个字符）。                                         |
| string.len(arg)                                         | 计算字符串的长度。                                                                                 |
| string.rep(string,n)                                    | 返回字符串string的n个拷贝。                                                                         |
| ..                                                      | 连接两个                                                                                      |

### table

在Lua里，table的创建是通过“构造表达式”来完成，最简单构造表达式是`{}`，用来创建一个空表。也可以在表里添加一些数据，直接初始化表：

```lua
--创建一个空表
local tbl = {}

--直接初始化表
local tbl2 = {"apple", "pear", "orange", "grape"}
```

Lua中的表(table)其实是一个map，索引可以是任意类型的值，但不能是nil。

```lua
a = {}
a["key"] = "value"
key = 10
a[key] = 22
a[key] = a[key] + 11
for k, v in pairs(a) do
    print(k .. ":" .. v)
end
```

执行结果为：

```
key ：value
10 : 33
```

不同于其他语言的数组把0作为数组的初始索引，**在Lua里标的默认初始索引一般以1开始**。

table不会固定长度大小，有新数据添加时table长度会自动增长，没初始化的table都是nil。

当我们为 table a 并设置元素，然后将 a 赋值给 b，则 a 与 b 都指向同一个内存。如果 a 设置为 nil ，则 b 同样能访问 table 的元素。如果没有指定的变量指向a，Lua的垃圾回收机制会清理相对应的内存（*我的理解是table的变量类似于指向table的智能指针，使用类似引用计数的方式管理，当引用被置0时，就会被Lua的垃圾回收机制回收掉*）。

#### table操作

| 方法                                          | 用途                                                             |
| ------------------------------------------- | -------------------------------------------------------------- |
| table.concat(table[, sep[, start[, end]]]); | 列出参数中指定table的数组部分，从start位置到end位置的所有元素，元素间以指定的分隔符(sep)隔开。       |
| table.insert(table, [pos,] value)           | 在table的数组部分指定位置(pos)插入值为value的一个元素，pos参数可选，默认为数组部分末尾。          |
| table.remove(table[, pos])                  | 返回table数组部分位于pos位置的元素，其后的元素会被前移。pos参数可选，默认为table长度，即从最后一个元素删起。 |
| table.sort(table[, comp])                   | 对给定的table进行升序排序。                                               |

### function

```lua
optional_function_scope function function_name( argument1, augument2, argument3..., argumentN )
    function_body
    return result_params_comma_separated
end
```

解析：

* optional_function_scope：该参数是可选的指定是全局函数还是局部函数，未设置该参数末尾为全局函数，使用local设置为局部函数。
* function_name：指定函数名称。
* argument1, augument2, argument3..., argumentN：函数参数，多个参数以逗号隔开，也可以不带参数。
* function_body：函数中需要执行的代码块。
* result_params_comma_separated：函数返回值，可以返回多个值，每个值以逗号隔开。

在Lua中，函数被看作是“第一类值（First-Class Value）”，函数可以存在变量里：

```lua
function factorial1(n)
    if n == 0 then
        return 1
    else
        return n * factorial1(n-1)
    end
end

print(factorial1(5))        --120
factorial2 = factorial1
print(factorial2(5))        --120
```

function可以作为参数，也以匿名函数的方式通过参数传递：

```lua
function anonymous(tab, fun)
    for k, v in pairs(tab) do
        print(fun(k, v))
    end
end
tab = { key1 = "val1", key2 = "val2" }
anonymous(tab, function(key, val)
      return key .. " = " .. val
  end)
```

执行结果为：

```
key1 = val1
key2 = val2
```

函数可以接受可变数目的参数，和C语言类似在函数参数列表中使用`...`表示函数有可变的参数。

lua将函数的参数放在一个叫arg的表中，#arg表示传入参数的个数。

```lua
function average(...)
    result = 0
    local arg={...}
    for i, v in ipairs(arg) do
        result = result + v
    end
    print("总共传入 ".. #arg " 个数")
    return result/#arg
end
```

### thread

在Lua里，最主要的线程是协同程序(coroutine)。它跟thread差不多，拥有自己的独立的栈、局部变量和指令指针，可以跟其他coroutine共享全局变量和其他大部分东西。

thread和coroutine的区别：thread可以同时多个运行，而coroutine任意时刻只能运行一个，并且处于运行状态的coroutine只有被suspend时才会暂停。

协程有点类似同步的多线程。在等待同一个线程锁的几个线程有点类似协程。

#### 基本语法

| 方法                                | 描述                                                                                                                                                                                                                                 |
| --------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| coroutine.create(f)               | 创建一个主体函数为 f 的新协程。 f 必须是一个 Lua 的函数。 返回这个新协程，它是一个类型为 "thread" 的对象。创建coroutine，返回coroutine， 参数是一个函数，当和resume配合使用的时候就唤醒函数调用                                                                                                            |
| coroutine.isyieldable()           | 如果正在运行的协程可以让出，则返回真。不在主线程中或不在一个无法让出的C函数中时，当前协程是可让出的。                                                                                                                                                                                |
| coroutine.resume(co[, val1, ...]) | 开始或继续协程 co 的运行。 当你第一次延续一个协程，它会从主体函数处开始运行。 val1, ... 这些值会以参数形式传入主体函数。 如果该协程被让出，resume 会重新启动它； val1, ... 这些参数会作为让出点的返回值。如果协程运行起来没有错误， resume 返回 true 加上传给 yield 的所有值 （当协程让出）， 或是主体函数的所有返回值（当协程中止）。 如果有任何错误发生， resume 返回 false 加错误消息。 |
| coroutine.yield(...)              | 挂起正在调用的协程的执行。传递给yield的参数都会转为resume的额外返回值。                                                                                                                                                                                          |
| coroutine.status(co)              | 以字符串形式返回协程co的状态：当协程正在运行（它就是调用status的那个），返回"running"；如果协程调用yield挂起或是还没有开始运行，返回"suspended"；如果协程是活动的，都并不在运行（即它正在延续其他协程），返回"normal"；如果协程运行完主体函数或因错误停止，返回"dead"。                                                                        |
| coroutine.wrap(f)                 | 创建一个主体函数为f的新协程。f必须是一个Lua的函数。返回一个函数，每次调用该函数都会延续该协程。传给这个函数的参数都会作为resume的额外参数。和resume返回相同的值，只是没有一个布尔量。如果发生任何错误，抛出这个错误。                                                                                                                |
| coroutine.running()               | 返回当前正在运行的协程加一个布尔量。 如果当前运行的协程是主线程，其为真。                                                                                                                                                                                              |

### userdata

userdata 是一种用户自定义数据，用于表示一种由应用程序或 C/C++ 语言库所创建的类型，可以将任意 C/C++ 的任意数据类型的数据（通常是 struct 和 指针）存储到 Lua 变量中调用。

## 变量

### 变量类型

Lua 变量有三种类型：全局变量、局部变量、表中的域。

Lua 中的变量全是全局变量，哪怕是语句块或是函数里，除非用 local 显示声明为局部变量。

局部变量的作用域为从声明位置开始到所在语句块结束。

变量的默认值均为 nil。

### 赋值语句

赋值是改变一个变量的值和改变表域的最基本的方法。

Lua可以对多个变量同时赋值，变量列表和值列表的各个元素用逗号分开，赋值语句右边的值会依次赋给左边的变量。(*这种奇怪方式还是不要用了*)

```lua
a, b = 10, 2*x       --a=10; b=2*x    
```

遇到赋值语句Lua会先计算右边所有的值然后再执行赋值操作，所以我们可以这样进行交换变量的值：

```lua
x, y = y, x                     -- swap 'x' for 'y'
a[i], a[j] = a[j], a[i]         -- swap 'a[i]' for 'a[j]'
```

当变量个数和值的个数不一致时，Lua会一直以变量个数为基础采取以下策略：

* 变量个数 > 值的个数            按变量个数补足nil
* 变量个数 < 值的个数                     多余的值会被忽略

多值赋值经常用来交换变量，或将函数调用返回给变量：

```
a, b = f()
```

f()返回两个值，第一个赋给a，第二个赋给b。

应该尽可能的使用局部变量，有两个好处：

1. 避免命名冲突。
2. 访问局部变量的速度比全局变量更快。

### 索引

对table的索引使用方括号`[]`。Lua也提供了`.`操作。

```
t[i]
t.i                        --当索引为字符串类型时的一种简化方法
gettable_event(t, i)    --采用索引访问本质上是一个类似这样的函数调用
```

## 循环

### while循环

*等价于C/C++中的while循环。*

```lua
while (condition) do
    statements
end
```

### for循环

*类似C/C++中的for循环，需要注意的是条件表达式只求值一次。*

#### 数值for循环

```lua
for var=exp1, exp2, exp3 do
    statements
end
```

var从exp1变化到exp2，每次变化以exp3为步长递增var，并执行一次”执行体“。exp3是可选的，如果不指定，默认为1。

for的三个表达式在循环开始前一次性求值，以后不再进行求值，其结果用在后面的循环中。

#### 泛型for循环

```lua
for i, v in ipairs(a) do
    statements
end
```

i是数组索引值，v是对应索引的数组元素值。ipairs是Lua提供的一个迭代器函数，用来迭代数组。

### repeat...until循环

 repeat...until 循环的条件语句在当前循环结束后判断。

*等价于C/C++中的`do...while`循环*

```lua
repeat
    statements
while( condition )
```

## 流程控制

### if

```lua
if ( condition ) then
    statements
end
```

### if...else

```lua
if ( condition ) then
    statements
else if ( condition ) then
    statements
else
    statements
end
```

## 运算符

常用的运算符大体上和C/C++差不多，这里就不说明了。只列出一些不同的。

设定A的值为10，B的值为20：

| 操作符 | 描述                                       | 实例                                                       |
| --- | ---------------------------------------- | -------------------------------------------------------- |
| ^   | 乘幂                                       | A^2输出结果100。                                              |
| ~=  | 不等于                                      | A~=B为true。                                               |
| and | 逻辑与                                      | (A and B)为false。                                         |
| or  | 逻辑或                                      | (A OR B)为true。                                           |
| not | 逻辑非                                      | not(A and B)为true。                                       |
| ..  | 字符串连接                                    | a..b，其中 a 为 "Hello " ， b 为 "World", 输出结果为 "Hello World"。 |
| #   | 一元运算符，返回字符串长度或表的长度（*类似C/C++中的sizeof(x)*） | `#"Hello"`返回5                                            |

### 运算符优先级

从高到低的顺序：

```lua
^
not        -(负号)
*        /
+        -
..
<    >    <=    >=    ~=    ==
and
or
```

除了^和..外所有的二元运算符都是左连接的。

## 模块与包

模块类似于一个封装库，从 Lua 5.1 开始，Lua 加入了标准的模块管理机制，可以把一些公用的代码放在一个文件里，以 API 接口的形式在其他地方调用，有利于代码的重用和降低代码耦合度。
Lua 的模块是由变量、函数等已知元素组成的 table，因此创建一个模块很简单，就是创建一个 table，然后把需要导出的常量、函数放入其中，最后返回这个 table 就行。

文件代码格式如下：

```lua
-- 文件名为 module.lua
-- 定义一个名为 module 的模块
module = {}

-- 定义一个常量
module.constant = "这是一个常量"

-- 定义一个函数
function module.func1()
    io.write("这是一个公有函数！\n")
end

local function func2()
    print("这是一个私有函数！")
end

function module.func3()
    func2()
end

return module
```

由上可知，模块的结构就是一个 table 的结构，因此可以像操作调用 table 里的元素那样来操作调用模块里的常量或函数。
上面的 func2 声明为程序块的局部变量，即表示一个私有函数，因此是不能从外部访问模块里的这个私有函数，必须通过模块里的公有函数来调用。

### require函数

Lua提供了一个名为require的函数用来加载模块。要加载一个模块，只需要简单地调用就可以了。例如：

```lua
require("<模块名>")
```

或者

```lua
require "<模块名>"
```

执行 require 后会返回一个由模块常量或函数组成的 table，并且还会定义一个包含该 table 的全局变量。

```lua
-- test_module.lua 文件
-- module 模块为上文提到到 module.lua
require("module")

print(module.constant)

module.func3()
```

以上代码执行结果为：

```
这是一个常量
这是一个私有函数！
```

或者给加载的模块定义一个别名变量，方便调用：

```lua
-- test_module2.lua 文件
-- module 模块为上文提到到 module.lua
-- 别名变量 m
local m = require("module")

print(m.constant)

m.func3()
```

以上代码执行结果为：

```
这是一个常量
这是一个私有函数！
```

### 加载机制

对于自定义的模块，模块文件不是放在哪个文件目录都行，函数 require 有它自己的文件路径加载策略，它会尝试从 Lua 文件或 C 程序库中加载模块。

require 用于搜索 Lua 文件的路径是存放在全局变量 package.path 中，当 Lua 启动后，会以环境变量 LUA_PATH 的值来初始这个环境变量。如果没有找到该环境变量，则使用一个编译时定义的默认路径来初始化。

如果找到目标文件，则会调用 package.loadfile 来加载模块。否则，就会去找 C 程序库。
搜索的文件路径是从全局变量 package.cpath 获取，而这个变量则是通过环境变量 LUA_CPATH 来初始。

搜索的策略跟上面的一样，只不过现在换成搜索的是 so 或 dll 类型的文件。如果找得到，那么 require 就会通过 package.loadlib 来加载它。

### C程序包

Lua和C是很容易结合的，使用C为Lua写包。

与Lua中写包不同，C包在使用以前必须首先加载并连接，在大多数系统中最容易的实现方式是通过动态连接库机制。

Lua在一个叫loadlib的函数内提供了所有的动态连接的功能。这个函数有两个参数:库的绝对路径和初始化函数。所以典型的调用的例子如下:

```lua
local path = "/usr/local/lua/lib/libluasocket.so"
local f = loadlib(path, "luaopen_socket")
```

loadlib函数加载指定的库并且连接到Lua，然而它并不打开库（也就是说没有调用初始化函数），反之他返回初始化函数作为Lua的一个函数，这样我们就可以直接在Lua中调用他。

如果加载动态库或者查找初始化函数时出错，loadlib将返回nil和错误信息。我们可以修改前面一段代码，使其检测错误然后调用初始化函数：

```lua
local path = "/usr/local/lua/lib/libluasocket.so"
-- 或者 path = "C:\\windows\\luasocket.dll"，这是 Window 平台下
local f = assert(loadlib(path, "luaopen_socket"))
f()  -- 真正打开库
```

一般情况下我们期望二进制的发布库包含一个与前面代码段相似的stub文件，安装二进制库的时候可以随便放在某个目录，只需要修改stub文件对应二进制库的实际路径即可。

将stub文件所在的目录加入到LUA_PATH，这样设定后就可以使用require函数加载C库了。

## 元表（metatable）

在 Lua table 中我们可以访问对应的key来得到value值，但是却无法对两个 table 进行操作。

因此 Lua 提供了元表(metatable)，允许我们改变table的行为，每个行为关联了对应的元方法。

例如，使用元表我们可以定义Lua如何计算两个table的相加操作a+b。

当Lua试图对两个表进行相加时，先检查两者之一是否有元表，之后检查是否有一个叫`__add`的字段，若找到，则调用对应的值。`__add`等即时字段，其对应的值（往往是一个函数或是table）就是"元方法"。

有两个很重要的函数来处理元表：

* setmetatable(table, metatable)：对指定table设置元表，如果元表中存在`__metatable`键值，setmetatable会失败。
* getmetatable(table)：返回对象的元表(metatable)。

### `__index`元方法

这是metatable最常用的键。

当你通过键来访问 table 的时候，如果这个键没有值，那么Lua就会寻找该table的metatable（假定有metatable）中的`__index `键。如果`__index`包含一个表格，Lua会在表格中查找相应的键。

如果__index包含一个函数的话，Lua就会调用那个函数，table和键会作为参数传递给函数。

`__index `元方法查看表中元素是否存在，如果不存在，返回结果为 nil；如果存在则由 `__index `返回结果。

```lua
mytable = setmetatable({key1 = "value1"}, {
  __index = function(mytable, key)
    if key == "key2" then
      return "metatablevalue"
    else
      return nil
    end
  end
})

print(mytable.key1,mytable.key2)
```

实例输出结果为：

```
value1    metatablevalue
```

__总结__

Lua查找一个表元素时的规则，其实就是如下3个步骤：

1. 在表中查找，如果找到，返回该元素，找不到则继续。
2. 判断该表是否有元表，如果没有元表，返回nil有元表则继续。
3. 判断元表有没有`__index`方法，如果`__index`方法为nil，则返回nil；如果`__index`方法是一个表，则重复1、2、3；如果`__index`方法是一个函数，则返回该函数的返回值。

### `__newindex`元方法

`__newindex`元方法用来对表更新，`__index`则用来对表访问。

当你给表的一个缺少的索引赋值，解释器就会查找`__newindex`元方法：如果存在则调用这个函数而不进行赋值操作。

```lua
mymetatable = {}
mytable = setmetatable({key1 = "value1"}, { __newindex = mymetatable })

print(mytable.key1)

mytable.newkey = "新值2"
print(mytable.newkey,mymetatable.newkey)

mytable.key1 = "新值1"
print(mytable.key1,mymetatable.key1)
```

以上实例执行输出结果为：

```
value1
nil    新值2
新值1    nil
```

以上实例中表设置了元方法` __newindex`，在对新索引键（newkey）赋值时（mytable.newkey = "新值2"），会调用元方法，而不进行赋值。而如果对已存在的索引键（key1），则会进行赋值，而不调用元方法` __newindex`。

### rawset和rawget

* rawset(table, index, value)：
  
  在不触发任何元方法的情况下 将 `table[index]` 设为 `value`。 `table` 必须是一张表， `index` 可以是 **nil** 与 NaN 之外的任何值。`value` 可以是任何 Lua 值。

* rawget(table, index)：
  
  在不触发任何元方法的情况下 获取 `table[index]` 的值。 `table` 必须是一张表； `index` 可以是任何值。

*我的理解是，rawset和rawget是为了绕过元方法而出现的，也就是相当于忽略元表执行操作。*

### 为表添加操作符

*有点类似C/C++中的操作符重载。*

| 模式       | 描述           |
| -------- | ------------ |
| __add    | 对应的运算符 '+'.  |
| __sub    | 对应的运算符 '-'.  |
| __mul    | 对应的运算符 '*'.  |
| __div    | 对应的运算符 '/'.  |
| __mod    | 对应的运算符 '%'.  |
| __unm    | 对应的运算符 '-'.  |
| __concat | 对应的运算符 '..'. |
| __eq     | 对应的运算符 '=='. |
| __lt     | 对应的运算符 '<'.  |
| __le     | 对应的运算符 '<='. |

### `__call`元方法

函数调用操作 `func(args)`。 当 Lua 尝试调用一个非函数的值的时候会触发这个事件 （即 `func` 不是一个函数）。 查找 `func` 的元方法， 如果找得到，就调用这个元方法， `func` 作为第一个参数传入，原来调用的参数（`args`）会依次排在后面。

### `__tostring`元方法

__tostring 元方法用于修改表的输出行为。

```lua
mytable = setmetatable({ 10, 20, 30 }, {
  __tostring = function(mytable)
    sum = 0
    for k, v in pairs(mytable) do
        sum = sum + v
    end
    return "表所有元素的和为 " .. sum
  end
})
print(mytable)
```

以上实例执行输出结果为：

```
表所有元素的和为 60
```

## 文件I/O

Lua I/O库用于读取和处理文件。分为简单模式（和C一样）、完全模式。

* 简单模式拥有一个当前输入文件和一个当前输出文件，并且提供针对这些文件相关的操作。
* 完全模式使用外部的文件句柄来实现。它以一种面对对象的形式，将所有的文件操作定义为文件句柄的方法。

简单模式在做一些简单的文件操作时较为合适。但是在进行一些高级的文件操作的时候，简单模式就显得力不从心。例如同时读取多个文件这样的操作，使用完全模式则较为合适。

打开文件操作语句如下：

```
file = io.open (filename [, mode])
```

mode 的值有：

| 模式  | 描述                                                                    |
| --- | --------------------------------------------------------------------- |
| r   | 以只读方式打开文件，该文件必须存在。                                                    |
| w   | 打开只写文件，若文件存在则文件长度清为0，即该文件内容会消失。若文件不存在则建立该文件。                          |
| a   | 以附加的方式打开只写文件。若文件不存在，则会建立该文件，如果文件存在，写入的数据会被加到文件尾，即文件原先的内容会被保留。（EOF符保留） |
| r+  | 以可读写方式打开文件，该文件必须存在。                                                   |
| w+  | 打开可读写文件，若文件存在则文件长度清为零，即该文件内容会消失。若文件不存在则建立该文件。                         |
| a+  | 与a类似，但此文件可读可写                                                         |
| b   | 二进制模式，如果文件是二进制文件，可以加上b                                                |
| +   | 号表示对文件既可以读也可以写                                                        |

### 简单模式

```lua
-- 以只读方式打开文件
file = io.open("test.lua", "r")

-- 设置默认输入文件为 test.lua
io.input(file)

-- 输出文件第一行
print(io.read())

-- 关闭打开的文件
io.close(file)

-- 以附加的方式打开只写文件
file = io.open("test.lua", "a")

-- 设置默认输出文件为 test.lua
io.output(file)

-- 在文件最后一行添加 Lua 注释
io.write("--  test.lua 文件末尾注释")

-- 关闭打开的文件
io.close(file)
```

以上实例中我们使用了 io."x" 方法，其中 io.read() 中我们没有带参数，参数可以是下表中的一个：

| 模式       | 描述                                           |
| -------- | -------------------------------------------- |
| "*n"     | 读取一个数字并返回它。例：file.read("*n")                 |
| "*a"     | 从当前位置读取整个文件。例：file.read("*a")                |
| "*l"（默认） | 读取下一行，在文件尾 (EOF) 处返回 nil。例：file.read("*l")   |
| number   | 返回一个指定字符个数的字符串，或在 EOF 时返回 nil。例：file.read(5) |

其他的 io 方法有：

- **io.tmpfile():**返回一个临时文件句柄，该文件以更新模式打开，程序结束时自动删除
- **io.type(file):** 检测obj是否一个可用的文件句柄
- **io.flush():** 向文件写入缓冲中的所有数据
- **io.lines(optional file name):** 返回一个迭代函数,每次调用将获得文件中的一行内容,当到文件尾时，将返回nil,但不关闭文件

### 完全模式

通常我们需要在同一时间处理多个文件。我们需要使用 file:function_name 来代替 io.function_name 方法。以下实例演示了如同同时处理同一个文件:

```lua
-- 以只读方式打开文件
file = io.open("test.lua", "r")

-- 输出文件第一行
print(file:read())

-- 关闭打开的文件
file:close()

-- 以附加的方式打开只写文件
file = io.open("test.lua", "a")

-- 在文件最后一行添加 Lua 注释
file:write("--test")

-- 关闭打开的文件
file:close()
```

read 的参数与简单模式一致。

其他方法:

- **file:seek(optional whence, optional offset):** 设置和获取当前文件位置,成功则返回最终的文件位置(按字节),失败则返回nil加错误信息。参数 whence 值可以是:
  
  - "set": 从文件头开始
  - "cur": 从当前位置开始[默认]
  - "end": 从文件尾开始
  - offset:默认为0
  
  不带参数file:seek()则返回当前位置,file:seek("set")则定位到文件头,file:seek("end")则定位到文件尾并返回文件大小

- **file:flush():** 向文件写入缓冲中的所有数据

- **io.lines(optional file name):** 打开指定的文件filename为读模式并返回一个迭代函数,每次调用将获得文件中的一行内容,当到文件尾时，将返回nil,并自动关闭文件。
  若不带参数时io.lines() <=> io.input():lines(); 读取默认输入设备的内容，但结束时不关闭文件。

## 错误处理

错误类型有：

* 语法错误：语法错误通常是由于对程序的组件（如运算符、表达式）使用不当引起的。
* 运行错误：运行错误是程序可以正常执行，但是会输出报错信息。

我们可以使用两个函数：`assert`和`error`来处理错误。

### assert函数

语法格式：

```lua
assert(v[, message])
```

如果其参数v的值为假（nil或false），它就调用error；否则，返回所有的参数。在错误情况时，message指哪个错误对象；如果不提供这个参数，参数默认为"assertion failed!"。

```lua
local function add(a,b)
   assert(type(a) == "number", "a 不是一个数字")
   assert(type(b) == "number", "b 不是一个数字")
   return a+b
end
add(10)
```

### error函数

语法格式：

```lua
error (message [, level])
```

功能：中止正在执行的函数，并返回message的内容作为错误信息（error函数永远都不会返回）。

通常情况下，error会附加一些错误位置的信息到message头部。

level参数指示获得错误的位置：

* level=1[默认]：为调用error位置（文件+行号）
* level=2：指出哪个调用error的函数的函数
* level=0：不添加错误位置信息

### pcall和xpcall、debug

Lua中处理错误，可以使用函数pcall（protected call）来包装需要执行的代码。

pcall接收一个函数和要传递个后者的参数，并执行，执行结果：有错误、无错误；返回值true或者或false, errorinfo。

语法格式如下

```lua
if pcall(function_name, ….) then
-- 没有错误
else
-- 一些错误
end
```

pcall以一种"保护模式"来调用第一个参数，因此pcall可以捕获函数执行中的任何错误。

通常在错误发生时，希望落得更多的调试信息，而不只是发生错误的位置。但pcall返回时，它已经销毁了调用桟的部分内容。

Lua提供了xpcall函数，xpcall接收第二个参数——一个错误处理函数，当错误发生时，Lua会在调用桟展开（unwind）前调用错误处理函数，于是就可以在这个函数中使用debug库来获取关于错误的额外信息了。

debug库提供了两个通用的错误处理函数:

- debug.debug：提供一个Lua提示符，让用户来检查错误的原因
- debug.traceback：根据调用桟来构建一个扩展的错误消息

## 调试

Lua 提供了 debug 库用于提供创建我们自定义调速器的功能。Lua 本身并未有内置的调速器，但很多开发者共享了他们的 Lua 调速器代码。

Lua 中 debug 库包含以下函数：

| 方法                                           | 用途                                                                                                                                                                             |
| -------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **debug()**                                  | 进入一个用户交互模式，运行用户输入的每个字符串。 使用简单的命令以及其它调试设置，用户可以检阅全局变量和局部变量， 改变变量的值，计算一些表达式，等等。 输入一行仅包含 cont 的字符串将结束这个函数， 这样调用者就可以继续向下运行。                                                         |
| **getfenv(object)**                          | 返回对象的环境变量。                                                                                                                                                                     |
| **gethook(optional thread)**                 | 返回三个表示线程钩子设置的值： 当前钩子函数，当前钩子掩码，当前钩子计数                                                                                                                                           |
| **getinfo ([thread,] f [, what])**           | 返回关于一个函数信息的表。 你可以直接提供该函数， 也可以用一个数字 f 表示该函数。 数字 f 表示运行在指定线程的调用栈对应层次上的函数： 0 层表示当前函数（getinfo 自身）； 1 层表示调用 getinfo 的函数 （除非是尾调用，这种情况不计入栈）；等等。 如果 f 是一个比活动函数数量还大的数字， getinfo 返回 nil。 |
| **debug.getlocal ([thread,] f, local)**      | 此函数返回在栈的 f 层处函数的索引为 local 的局部变量 的名字和值。 这个函数不仅用于访问显式定义的局部变量，也包括形参、临时变量等。                                                                                                        |
| **getmetatable(value)**                      | 把给定索引指向的值的元表压入堆栈。如果索引无效，或是这个值没有元表，函数将返回 0 并且不会向栈上压任何东西。                                                                                                                        |
| **getregistry()**                            | 返回注册表表，这是一个预定义出来的表， 可以用来保存任何 C 代码想保存的 Lua 值。                                                                                                                                   |
| **getupvalue (f, up)**                       | 此函数返回函数 f 的第 up 个上值的名字和值。 如果该函数没有那个上值，返回 nil 。 以 '(' （开括号）打头的变量名表示没有名字的变量 （去除了调试信息的代码块）。                                                                                       |
| **sethook ([thread,] hook, mask [, count])** | 将一个函数作为钩子函数设入。 字符串 mask 以及数字 count 决定了钩子将在何时调用。 掩码是由下列字符组合成的字符串，每个字符有其含义：**'c': **每当 Lua 调用一个函数时，调用钩子；**'r': **每当 Lua 从一个函数内返回时，调用钩子；**'l': **每当 Lua 进入新的一行时，调用钩子。             |
| **setlocal ([thread,] level, local, value)** | 这个函数将 value 赋给 栈上第 level 层函数的第 local 个局部变量。 如果没有那个变量，函数返回 nil 。 如果 level 越界，抛出一个错误。                                                                                            |
| **setmetatable (value, table)**              | 将 value 的元表设为 table （可以是 nil）。 返回 value。                                                                                                                                       |
| **setupvalue (f, up, value)**                | 这个函数将 value 设为函数 f 的第 up 个上值。 如果函数没有那个上值，返回 nil 否则，返回该上值的名字。                                                                                                                   |
| `traceback ( [thread,][message [, level]] )` | 如果 message 有，且不是字符串或 nil， 函数不做任何处理直接返回 message。 否则，它返回调用栈的栈回溯信息。 字符串可选项 message 被添加在栈回溯信息的开头。 数字可选项 level 指明从栈的哪一层开始回溯 （默认为 1 ，即调用 traceback 的那里）。                             |

### 调试类型

- 命令行调试
- 图形界面调试

命令行调试器有：RemDebug、clidebugger、ctrace、xdbLua、LuaInterface - Debugger、Rldb、ModDebug。

图形界调试器有：SciTE、Decoda、ZeroBrane Studio、akdebugger、luaedit。

## 垃圾回收

Lua 采用了自动内存管理。 这意味着你不用操心新创建的对象需要的内存如何分配出来， 也不用考虑在对象不再被使用后怎样释放它们所占用的内存。 Lua 运行了一个 *垃圾收集器* 来收集所有 *死对象* （即在 Lua 中不可能再访问到的对象）来完成自动内存管理的工作。 Lua 中所有用到的内存，如：字符串、表、用户数据、函数、线程、 内部结构等，都服从自动管理。

Lua 实现了一个增量标记-扫描收集器。 它使用这两个数字来控制垃圾收集循环： *垃圾收集器间歇率* 和 *垃圾收集器步进倍率*。 这两个数字都使用百分数为单位 （例如：值 100 在内部表示 1 ）。

垃圾收集器间歇率控制着收集器需要在开启新的循环前要等待多久。 增大这个值会减少收集器的积极性。 当这个值比 100 小的时候，收集器在开启新的循环前不会有等待。 设置这个值为 200 就会让收集器等到总内存使用量达到 之前的两倍时才开始新的循环。

垃圾收集器步进倍率控制着收集器运作速度相对于内存分配速度的倍率。 增大这个值不仅会让收集器更加积极，还会增加每个增量步骤的长度。 不要把这个值设得小于 100 ， 那样的话收集器就工作的太慢了以至于永远都干不完一个循环。 默认值是 200 ，这表示收集器以内存分配的“两倍”速工作。

如果你把步进倍率设为一个非常大的数字 （比你的程序可能用到的字节数还大 10% ）， 收集器的行为就像一个 stop-the-world 收集器。 接着你若把间歇率设为 200 ， 收集器的行为就和过去的 Lua 版本一样了： 每次 Lua 使用的内存翻倍时，就做一次完整的收集。

你可以通过在 C 中调用 [`lua_gc`](http://www.runoob.com/manual/lua53doc/manual.html#lua_gc) 或在 Lua 中调用 [`collectgarbage`](http://www.runoob.com/manual/lua53doc/manual.html#pdf-collectgarbage) 来改变这俩数字。 这两个函数也可以用来直接控制收集器（例如停止它或重启它）。

### 垃圾回收器函数

Lua 提供了以下函数`collectgarbage ([opt [, arg]])`用来控制自动内存管理:

- **collectgarbage("collect"): **做一次完整的垃圾收集循环。通过参数 opt 它提供了一组不同的功能：
- **collectgarbage("count"): **以 K 字节数为单位返回 Lua 使用的总内存数。 这个值有小数部分，所以只需要乘上 1024 就能得到 Lua 使用的准确字节数（除非溢出）。
- **collectgarbage("restart"): **重启垃圾收集器的自动运行。
- **collectgarbage("setpause"): **将 arg 设为收集器的 间歇率 （参见 §2.5）。 返回 间歇率 的前一个值。
- **collectgarbage("setstepmul"): **返回 步进倍率 的前一个值。
- **collectgarbage("step"): **单步运行垃圾收集器。 步长"大小"由 arg 控制。 传入 0 时，收集器步进（不可分割的）一步。 传入非 0 值， 收集器收集相当于 Lua 分配这些多（K 字节）内存的工作。 如果收集器结束一个循环将返回 true 。
- **collectgarbage("stop"): **停止垃圾收集器的运行。 在调用重启前，收集器只会因显式的调用运行。

### 垃圾收集元方法

你可以为表设定垃圾收集的元方法， 对于完全用户数据， 则需要使用 C API 。 该元方法被称为 *终结器*。 终结器允许你配合 Lua 的垃圾收集器做一些额外的资源管理工作 （例如关闭文件、网络或数据库连接，或是释放一些你自己的内存）。

如果要让一个对象（表或用户数据）在收集过程中进入终结流程， 你必须 *标记* 它需要触发终结器。 当你为一个对象设置元表时，若此刻这张元表中用一个以字符串 "`__gc`" 为索引的域，那么就标记了这个对象需要触发终结器。 注意：如果你给对象设置了一个没有 `__gc` 域的元表，之后才给元表加上这个域， 那么这个对象是没有被标记成需要触发终结器的。 然而，一旦对象被标记， 你还是可以自由的改变其元表中的 `__gc` 域的。

当一个被标记的对象成为了垃圾后， 垃圾收集器并不会立刻回收它。 取而代之的是，Lua 会将其置入一个链表。 在收集完成后，Lua 将遍历这个链表。 Lua 会检查每个链表中的对象的 `__gc` 元方法：如果是一个函数，那么就以对象为唯一参数调用它； 否则直接忽略它。

在每次垃圾收集循环的最后阶段， 本次循环中检测到的需要被回收之对象， 其终结器的触发次序按当初给对象作需要触发终结器的标记之次序的逆序进行； 这就是说，第一个被调用的终结器是程序中最后一个被标记的对象所携的那个。 每个终结器的运行可能发生在执行常规代码过程中的任意一刻。

由于被回收的对象还需要被终结器使用， 该对象（以及仅能通过它访问到的其它对象）一定会被 Lua *复活*。 通常，复活是短暂的，对象所属内存会在下一个垃圾收集循环释放。 然后，若终结器又将对象保存去一些全局的地方 （例如：放在一个全局变量里），这次复活就持续生效了。 此外，如果在终结器中对一个正进入终结流程的对象再次做一次标记让它触发终结器， 只要这个对象在下个循环中依旧不可达，它的终结函数还会再调用一次。 无论是哪种情况， 对象所属内存仅在垃圾收集循环中该对象不可达且 没有被标记成需要触发终结器才会被释放。

当你关闭一个状态机（参见 [`lua_close`](http://www.runoob.com/manual/lua53doc/manual.html#lua_close)）， Lua 将调用所有被标记了需要触发终结器对象的终结过程， 其次序为标记次序的逆序。 在这个过程中，任何终结器再次标记对象的行为都不会生效。

### 弱表

*弱表* 指内部元素为 *弱引用* 的表。 垃圾收集器会忽略掉弱引用。 换句话说，如果一个对象只被弱引用引用到， 垃圾收集器就会回收这个对象。

一张弱表可以有弱键或是弱值，也可以键和值都是弱引用。 仅含有弱键的表允许收集器回收它的键，但会阻止对值所指的对象被回收。 若一张表的键值均为弱引用， 那么收集器可以回收其中的任意键和值。 任何情况下，只要键或值的任意一项被回收， 相关联的键值对都会从表中移除。 一张表的元表中的 `__mode` 域控制着这张表的弱属性。 当 `__mode` 域是一个包含字符 '`k`' 的字符串时，这张表的所有键皆为弱引用。 当 `__mode` 域是一个包含字符 '`v`' 的字符串时，这张表的所有值皆为弱引用。

属性为弱键强值的表也被称为 *暂时表*。 对于一张暂时表， 它的值是否可达仅取决于其对应键是否可达。 特别注意，如果表内的一个键仅仅被其值所关联引用， 这个键值对将被表内移除。

对一张表的弱属性的修改仅在下次收集循环才生效。 尤其是当你把表由弱改强，Lua 还是有可能在修改生效前回收表内一些项目。

只有那些有显式构造过程的对象才会从弱表中移除。 值，例如数字和轻量 C 函数，不受垃圾收集器管辖， 因此不会从弱表中移除 （除非它们的关联项被回收）。 虽然字符串受垃圾回收器管辖， 但它们没有显式的构造过程，所以也不会从弱表中移除。

弱表针对复活的对象 （指那些正在走终结流程，仅能被终结器访问的对象） 有着特殊的行为。 弱值引用的对象，在运行它们的终结器前就被移除了， 而弱键引用的对象则要等到终结器运行完毕后，到下次收集当对象真的被释放时才被移除。 这个行为使得终结器运行时得以访问到由该对象在弱表中所关联的属性。

如果一张弱表在当次收集循环内的复活对象中， 那么在下个循环前这张表有可能未被正确地清理。

## 面向对象

我们知道，对象由属性和方法组成。LUA中最基本的结构是table，所以需要用table来描述对象的属性。

lua中的function可以用来表示方法。那么LUA中的类可以通过table + function模拟出来。

至于继承，可以通过metetable模拟出来（不推荐用，只模拟最基本的对象大部分时间够用了）。

Lua中的表不仅在某种意义上是一种对象。像对象一样，表也有状态（成员变量）；也有与对象的值独立的本性，特别是拥有两个不同值的对象（table）代表两个不同的对象；一个对象在不同的时候也可以有不同的值，但他始终是一个对象；与对象类似，表的生命周期与其由什么创建、在哪创建没有关系。对象有他们的成员函数，表也有：

```lua
Account = {balance = 0}
function Account.withdraw (v)
    Account.balance = Account.balance - v
end
```

这个定义创建了一个新的函数，并且保存在Account对象的withdraw域内，下面我们可以这样调用：

```lua
Account.withdraw(100.00)
```

### 一个简单实例

以下简单的类包含了三个属性： area, length 和 breadth，printArea方法用于打印计算结果：

```lua
-- Meta class
Rectangle = {area = 0, length = 0, breadth = 0}

-- 派生类的方法 new
function Rectangle:new (o,length,breadth)
  o = o or {}
  setmetatable(o, self)
  self.__index = self
  self.length = length or 0
  self.breadth = breadth or 0
  self.area = length*breadth;
  return o
end

-- 派生类的方法 printArea
function Rectangle:printArea ()
  print("矩形面积为 ",self.area)
end
```

### 创建对象

创建对象是位类的实例分配内存的过程。每个类都有属于自己的内存并共享公共数据。

```lua
r = Rectangle:new(nil,10,20)
```

### 访问属性

我们可以使用点号(.)来访问类的属性：

```lua
print(r.length)
```

### 访问成员函数

我们可以使用冒号(:)来访问类的成员函数：

```lua
r:printArea()
```

内存在对象初始化时分配。

### 完整实例

以下我们演示了 Lua 面向对象的完整实例：

```lua
-- Meta class
Shape = {area = 0}

-- 基础类方法 new
function Shape:new (o,side)
  o = o or {}
  setmetatable(o, self)
  self.__index = self
  side = side or 0
  self.area = side*side;
  return o
end

-- 基础类方法 printArea
function Shape:printArea ()
  print("面积为 ",self.area)
end

-- 创建对象
myshape = Shape:new(nil,10)

myshape:printArea()
```

执行以上程序，输出结果为：

```
面积为     100
```

### Lua 继承

继承是指一个对象直接使用另一对象的属性和方法。可用于扩展基础类的属性和方法。

以下演示了一个简单的继承实例：

```lua
 -- Meta class
Shape = {area = 0}
-- 基础类方法 new
function Shape:new (o,side)
  o = o or {}
  setmetatable(o, self)
  self.__index = self
  side = side or 0
  self.area = side*side;
  return o
end
-- 基础类方法 printArea
function Shape:printArea ()
  print("面积为 ",self.area)
end
```

接下来的实例，Square 对象继承了 Shape 类:

```lua
Square = Shape:new()
-- Derived class method new
function Square:new (o,side)
  o = o or Shape:new(o,side)
  setmetatable(o, self)
  self.__index = self
  return o
end
```

#### 完整实例

以下实例我们继承了一个简单的类，来扩展派生类的方法，派生类中保留了继承类的成员变量和方法：

```lua
 -- Meta class
Shape = {area = 0}
-- 基础类方法 new
function Shape:new (o,side)
  o = o or {}
  setmetatable(o, self)
  self.__index = self
  side = side or 0
  self.area = side*side;
  return o
end
-- 基础类方法 printArea
function Shape:printArea ()
  print("面积为 ",self.area)
end

-- 创建对象
myshape = Shape:new(nil,10)
myshape:printArea()

Square = Shape:new()
-- 派生类方法 new
function Square:new (o,side)
  o = o or Shape:new(o,side)
  setmetatable(o, self)
  self.__index = self
  return o
end

-- 派生类方法 printArea
function Square:printArea ()
  print("正方形面积为 ",self.area)
end

-- 创建对象
mysquare = Square:new(nil,10)
mysquare:printArea()

Rectangle = Shape:new()
-- 派生类方法 new
function Rectangle:new (o,length,breadth)
  o = o or Shape:new(o)
  setmetatable(o, self)
  self.__index = self
  self.area = length * breadth
  return o
end

-- 派生类方法 printArea
function Rectangle:printArea ()
  print("矩形面积为 ",self.area)
end

-- 创建对象
myrectangle = Rectangle:new(nil,10,20)
myrectangle:printArea()
```

执行以上代码，输出结果为：

```
面积为     100
正方形面积为     100
矩形面积为     200
```

### 函数重写

Lua 中我们可以重写基础类的函数，在派生类中定义自己的实现方式：

```lua
-- 派生类方法 printArea
function Square:printArea ()
  print("正方形面积 ",self.area)
end
```

## 数据库访问

本文主要为大家介绍 Lua 数据库的操作库：[LuaSQL](http://luaforge.net/projects/luasql/)。他是开源的，支持的数据库有：ODBC, ADO, Oracle, MySQL, SQLite 和 PostgreSQL。

本文为大家介绍MySQL的数据库连接。

LuaSQL 可以使用 [LuaRocks](https://luarocks.org/) 来安装可以根据需要安装你需要的数据库驱动。

LuaRocks 安装方法：

```shell
$ wget http://luarocks.org/releases/luarocks-2.2.1.tar.gz
$ tar zxpf luarocks-2.2.1.tar.gz
$ cd luarocks-2.2.1
$ ./configure; sudo make bootstrap
$ sudo luarocks install luasocket
$ lua
Lua 5.3.0 Copyright (C) 1994-2015 Lua.org, PUC-Rio
> require "socket"
```

Window 下安装 LuaRocks：[https://github.com/keplerproject/luarocks/wiki/Installation-instructions-for-Windows](https://github.com/keplerproject/luarocks/wiki/Installation-instructions-for-Windows)

安装不同数据库驱动：

```
luarocks install luasql-sqlite3
luarocks install luasql-postgres
luarocks install luasql-mysql
luarocks install luasql-sqlite
luarocks install luasql-odbc
```

你也可以使用源码安装方式，Lua Github 源码地址：[https://github.com/keplerproject/luasql](https://github.com/keplerproject/luasql)

Lua 连接MySql 数据库：

```lua
require "luasql.mysql"

--创建环境对象
env = luasql.mysql()

--连接数据库
conn = env:connect("数据库名","用户名","密码","IP地址",端口)

--设置数据库的编码格式
conn:execute"SET NAMES UTF8"

--执行数据库操作
cur = conn:execute("select * from role")

row = cur:fetch({},"a")

--文件对象的创建
file = io.open("role.txt","w+");

while row do
    var = string.format("%d %s\n", row.id, row.name)

    print(var)

    file:write(var)

    row = cur:fetch(row,"a")
end


file:close()  --关闭文件对象
conn:close()  --关闭数据库连接
env:close()   --关闭数据库环境
```
