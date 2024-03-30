---
layout: post
title: python mock使用初识
category: coder
---

## 关键点
patch 的关键在于 mock 掉正确的对象，所以 patch 里面的那个对象地址很重要。  
假设我们的工程有下面的结构：
```
a.py
    -> 定义了一个类 SomeClass

b.py
    -> from a import SomeClass
```
如果我们需要把 SomeClass mock 掉，这时候我们在单元测试里 import b，这时候我们应该使用 @patch('b.SomeClass')   
如果 b.py 里的定义是 import a，那这时候就应该是 @patch('a.SomeClass')   

更具体的用法可以参考官方文档: https://docs.python.org/3/library/unittest.mock.html

## 一些 mock 相关的属性
将外部依赖模块直接在单元测试代码中赋值为 `mock.Mock()` 即可. 另外, mock 提供以下属性(也可以作为默认参数设置):
```
my_method = mock.Mock()
my_method.return_value = 'ret'				# 设置返回值
my_method.side_effect = KeyError('key')		# 调用触发异常
```
side_effect 属性的另一个用法, 是传递一个函数, 在 mock 的对象被调用的时候会被用同样的参数调用, 用来动态地生成返回值
```
def func(str):
	return len(str)

my_method.side_effect = mock.Mock(side_effect=func, return_value=100)
my_method('abc')							# 返回3, 设置函数接收相同参数, 用于动态返回值
```

## patch 和 patch.object

在了解了 mock 对象之后，我们来看两个方便测试的函数：patch 和 patch.object。这两个函数都会返回一个 mock 内部的类实例，这个类是 class _patch。返回的这个类实例既可以作为函数的装饰器，也可以作为类的装饰器，也可以作为上下文管理器。使用 patch 或者 patch.object 的目的是为了控制 mock 的范围，意思就是在一个函数范围内，或者一个类的范围内，或者 with 语句的范围内 mock 掉一个对象。

下面我们使用 patch 装饰器来重写上面的示例：
```
class SMSTest(unittest.TestCase):
    @mock.patch('sms.send_sms')
    def test_sms(self, mock_sms):
        mock_sms.return_value = True
        result = sms.func()
        self.assertEqual(result, 'success')
```
mock 掉 sms.send_sms，我们传入的参数 mock_sms 就是那个 mock 对象

使用 patch.object 的效果是一样的，不过有一点区别：
```
class SMSTest(unittest.TestCase):
    @mock.patch.object(sms, 'send_sms')
    def test_sms(self, mock_sms):
        mock_sms.return_value = True
        result = sms.func()
        self.assertEqual(result, 'success')
```
patch 是替换一个完整路径的对象，而 patch.object 是替换掉一个对象指定名称的属性，用法和 setattr 类似。

注意：如果使用了多个 mock.patch 装饰器，注意装饰器和传入参数的对应：最里面的装饰器对应第一个参数，下面有一个示例：
```
@mock.patch('a.sys')
@mock.patch('a.os')
@mock.patch('a.os.path')
def test_something(self, mock_os_path, mock_os, mock_sys):
    pass
```
然后实际情况是这样调用的
patch_sys(patch_os(patch_os_path(test_something)))
也就是说是相反的
由于这个关于 sys 的在最外层，因此会在最后被执行，使得它成为实际测试方法的最后一个参数。请特别注意这一点，以保证在测试的时候保证正确的参数按照正确的顺序被注入。



### 使用经验总结:

(1)如果一个类上相同的mock过多的话, 可以选择

* 在setUp()函数中直接对要mock的成员进行赋值或变更
* 在类上使用@patch()