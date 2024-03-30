---
layout: post
title: "KBEngine学习笔记"
description: "KBEngine学习笔记"
category: development
tags: [GameServer]
---


## 安装与卸载

* [项目主页](http://kbengine.org/)

* 编译

  + 打开/kbe/src/kbengine_vs120.sln
  + build solution

* [安装说明](http://kbengine.org/docs/installation.html)

  + 使用脚本需要以管理员权限运行命令行提示符

* [卸载说明](http://kbengine.org/docs/uninstallation.html)

* [更新说明](http://kbengine.org/docs/updating.html)

* [启动和关闭说明](http://kbengine.org/docs/startup_shutdown.html)

##  服务端架构

### 服务端组成

```
    |----------|
		      |  client  | x N
		      |----------|

------------------------|-----|-------------------------------

|----------|	     |----------|         |----------|
| loginsrv | x N     |  basesrv | x N     |basesrvmgr| x 1
|----------|         |----------|         |----------|

------------------------|-----|-------------------------------


	|----------|            |----------|
	|  cellsrv | x N	|cellsrvmgr| x 1
	|----------|            |----------|

------------------------|-----|-------------------------------


	|----------|            |----------|
	|  dbmgr   | x 1	|interfaces| x 1
	|----------|            |----------|

------------------------|-----|-------------------------------

		      |----------|
		      |  mysql   | x 1
		      |----------|
```

### 基本概念

#### Entity(实体)：

BaseApp上有两种实体

* Base
  * 通常的游戏Entity
  * 例如：存储在数据库里的NPC，拍卖行...
* Proxy
  * 与客户端连接
  * C++继承自KBEngine.base
  * 特殊的Base

#### Entity与Cell

* 每个Space至少有一个Entity
  * 通常第一个Entity是SpcaceEntity，用于让用户操控Space
* CellApp上的每个玩家Entity都有一个Witness对象
  * witness监视周围的Entity，将发生的事件消息同步到客户端
* Entity的兴趣范围（AOI）缺省是500M
  * 可以自定义，依赖于很多因素
* Entity穿越Cell边界是无缝的
  * 客户端不会感觉到（穿越边界的发生）
* 每个Cell维护着一个List，存放着在其边界外沿的Entity
  * Ghost Entities
  * 半径500M，可配置
  * 大于等于AOI

#### Entity：Real与Ghost

* Real Entity是权威的Entity
* 一个Ghost Entity是从邻近的Cell的对应的Entity的部分数据的拷贝

#### Ghost Entity

* 解决跨越Cell边界的Entity的交互问题
* 方法调用
  * 转发给其Real Entity
* 属性
  * 一个属性可以是Real Only的，例如：将永远不会存在于Ghost上
  * 如果一个属性对于客户端是可见的，那么该属性必须是可以Ghost的，例如：当前的武器、等级、名称
* Ghost属性是只读的
  * 要更改属性值只能通过方法调用来更新其对应的Real Entity

#### Entity的数据更新

* 客户端实现LOD以加速渲染
* CellApp实现LOD以减少：
  * 带宽的消耗
  * 每个Entity的CPU消耗
* LOD在CellApp上的作用类似于在客户端的作用
  * 细节程度是相对于玩家Entity与之的距离的
* 客户端Entity方法可以实现LOD
* Entity属性实现LOD可以避免不必要的通信到客户端
  * 当前的血量（对于很远的距离的Entity来说是不可见）

#### Entity备份

* 存档
  * 在BaseApp间轮流调度处理
  * **BaseApp向CellApp要Entity的Cell部分的数据再定时转发给DBMgr存储**

#### 游戏项目资产库

* KBEngine引擎默认资产库
  * 如果用户没有设置环境变量的指向，引擎默认会尝试读取引擎根目录assets作为默认的资产库
  * 资产库的概念类似于Unity3D中的Assets，不过其中一些文件夹名称结构被固定了
* 不同项目是不同的资产库
  * 要想引擎启动时读取到对应的项目资产库，必须在环境变量中指定

#### 资产库文件夹结构

![资产库文件夹结构图1](http://115.imagebam.com/download/L6TjdFIW8tcAXwQhrNO-qA/50118/501172228/1.jpg)

![资产库文件夹结构图2](http://116.imagebam.com/download/PKyhaaNqVHdKIbyEB6xLew/50118/501172233/2.jpg)

### 服务端组件概述

#### LoginApp: 

登录验证、注册、接入口。可在多台机器部署多个loginapp进程来负载。

+ 与客户端的第一个连接点

+ 固定的端口

+ 初始通信时加密

  - 公用密钥对（任意长度的密钥）
  - 用户名/密码

+ 使用多个LoginApps使得负载均衡

  + DNS轮流调度

  

#### DBMgr:

高性能多线程的数据存取。默认使用Mysql作为数据库。

* 管理Entity数据的数据库存储
* 负责数据库与其余的服务器间的Entity信息的通信
* 支持的数据库:
  * MySQL
  * MongoDB
  * Redis
  * ...
* 最好在独立的机器运行

#### BaseAppMgr:

协调所有baseapp的工作，包括baseapp负载均衡处理等。

* 负责管理BaseApp间的负载平衡
* 监视所有的BaseApp以实现各个BaseApp间的容错
* 主要用于玩家登录分配和创建Entity
* 一个服务器群组有**一个**BaseAppMgr实例

#### BaseApp:

与客户端通信的固定点

* 客户端与服务端的交互只能通过LoginApp分配的BaseApp来完成。
* **定时写Entity的数据到数据库**、**BaseApp数据相互备份、灾难恢复**。
* 可在多台机器部署多个BaseApp进程来均衡负载。
* 脚本层通常会选择在BaseApp上实现如：社交系统、广播聊天、排行、游戏大厅、等等逻辑系统。
* 用于处理没有空间位置属性的Entity:
  * 拍卖行
  * 公会管理
  * 管理器
* 通常一个CPU/核上处理一个BaseApp

#### CellAppMgr:

负责协调所有CellApp的工作，包括负载均衡处理等。

* 管理：
  * 所有的CellApp(及它们的负载)
  * 所有的Cell边界
  * 所有Space
* 管理CellApp的负载平衡
  * **告诉CellApps它们的Cell边界应该在哪里**
* 把新建的Entity加入到正确的Cell上
* 一个服务器群组**一个**CellAppMgr实例

#### CellApp:

处理游戏与空间和位置有关的逻辑，如：AOI、Navigate、AI、战斗等等。
可在多台机器部署多个cellapp进程来动态均衡负载。 

* 空间与位置数据的处理
  * 处理玩家交互的Space（空间、房间、场景...）
* 处理在Space内的Entity
* 处理Space内的一个区域（Cell）
  * 一个CellApp在一个Space上的Cell只会有一个（通常进程占用一个CPU/核，多个Cell并没有意义）
* 一个CellApp有可能处理多个Space
* 通常一个CPU/核上处理一个CellApp
* 主要负载：
  * 管理的Entity的总数量
  * Entity的通信的频率
    * 用户所调用的方法
    * 系统自动更新的属性
    * Entity的密集度
  * Entity脚本
  * Entity的数据大小
  * 

#### Client:

客户端我们将提供基础框架，这个框架不包括渲染部分和输入输出部分的具体实现, 
我们将提供一个lib文件和一套API接口，开发者可以选择使用自己比较适合的图形渲染引擎与输入输出控制部分。
Unity3D, HTML5, Cocos2d等技术我们提供了相关插件，能够快速的和服务端对接。

#### Machine(KBEngine的机器Daemon):

抽象出一个服务端硬件节点(一台硬件服务器只能存在一个这样的进程)。主要用途是接收远程指令处理本机上的组件启动与关闭, 
提供本机上运行组件的接入口以及收集当前机器上的一些信息， 
如：CPU、内存等。 这些信息会提供给一些对此比较感兴趣的组件。 

* Daemon用于监视服务器进程
* 每个服务器机器上还有一个Machine
* 启动/停止服务器进程
* 通知服务器群组各个进程的存活状态
* 监事机器的使用状态
  * CPU/内存/带宽

#### Interfaces: 

支持快速接入第三方计费、第三方账号、第三方数据， 快速与运营系统耦合。

#### GuiConsole: 

这是一个可视化的图形界面控制台工具，可以实时的观察服务端运行状态，实时观测不同Space中Entity的动态，
并支持动态调试服务端Python逻辑层以及查看各个组件的日志，启动服务端与关闭等。 

#### Logger: 

收集和备份各个组件的运行日志。

### 目录结构

```
|- kbengine							(KBE_ROOT 根目录)
	|- assets						(默认的游戏项目资产库，你可以添加新的资产库通过环境变量绑定)
		|- res						(所有资源文件)
			|- spaces				(通常存放游戏场景相关的资源，例如Navmesh)
			|- server				(通常放置服务端相关的配置文件)
		|- scripts				(所有的游戏逻辑，Python文件)
			|- base				(Base的Python逻辑)
			|- cell				(Cell的Python逻辑)
			|- client			(Client的Python逻辑)
			|- bots				(机器人的Python逻辑，压力测试)
			|- common			(逻辑公共文件夹)
			|- data				(游戏逻辑用到的数据资源)
			|- db				(dbmgr扩展脚本)
			|- entity_defs			(实体定义与声明)
				|- interfaces		(实体的接口声明)
			|- server_common		(服务端逻辑公共)
			|- user_type			(自定义用户类型目录)
	   |- kbe						(引擎目录)
		|- tools					(引擎工具)
			|- server				(引擎服务端工具)
				|- guiconsole			(可视化的控制台工具)
				|- install			(引擎安装工具)
				|- pycluster			(跨平台的集群控制Python脚本工具)
			|- xlsx2py				(游戏数据表导出工具)
		|- src						(KBEngine源代码)
			|- build				(makefile公共脚本)
			|- client				(客户端插件和例子目录)
				|- kbengine_dll			(Windows应用程序插件源代码)
			|- common				(公共目录)
			|- lib					(各种模块源代码)
				|- client_lib			(客户端底层公共框架)
				|- cstdkbe			(KBEngine标准库)
				|- db_mysql			(Mysql存取实现)
				|- dbmgr_lib			(数据存取公共接口)
				|- dependencies			(依赖库)
				|- entitydef			(实体定义解析模块)
				|- helper			(一些通用的协助性模块)
				|- math				(数学相关)
				|- navigation			(2D/3D导航模块)
				|- network			(网络模块)
				|- pyscript			(脚本插件)
				|- python			(python源代码)
				|- resmgr			(资源管理器)
				|- server			(服务端公共模块)
				|- thread			(多线程模块)
				|- xmlplus			(xml解析库)
			|- libs					(编译后的*.lib, *.a文件)
			|- server				(服务端app源代码)
				|- baseapp			(baseapp源代码)
				|- baseappmgr			(baseappmgr源代码)
				|- cellapp			(cellapp源代码)
				|- cellappmgr			(cellappmgr源代码)
				|- dbmgr			(dbmgr源代码)
				|- loginapp			(loginapp源代码)
				|- machine			(machine源代码)
				|- resourcemgr			(resourcemgr源代码)
				|- tools			(服务端助手工具)
					|- interfaces		(支持第三方计费、第三方账号等接口)
					|- bots			(压力测试， 虚拟客户端, 
```

### 常规部署

* 一个BaseApp，2个及以上CellApp
  * 不同游戏不同情况
  * 早Profile，经常Profile
* 情况允许，应放在独立的机器的进程
  * DBMgr
    * 一些工具类进程

## 登录过程

1. 客户端发起登录请求
   * 指定IP/端口
2. LoginApp收到登录请求
   * 解密请求消息（一些客户端也会选择不加密通讯，那么服务端不进行解密）
3. LoginApp转发登录消息到DBMgr
4. DBMgr验证用户名/密码
   * 查询数据库
5. 转发请求到BaseAppMgr
6. BaseAppMgr发送创建Player Entity的消息到负载最小的BaseApp
7. BaseApp创建一个新的Proxy
   * 可能会创建一个新的Cell Entity
8. Proxy的TCP端口被返回给客户端
   * 途径BaseAppMgr，DBMgr，LoginApp

## 实现一个Entity

### 实现要求

* 每个Entity必须：
  * 在entities.xml文件的列表里
  * 必须有一个<entity_name>.def文件
  * 必须有<Entity_name>.py文件
* 每个Entity可以：
  * 有最多3个部分的实现（Client/Cell/Base）
  * 使用common路径下的共享脚本
* Client/Server的定义文件必须匹配
  * 在以下插件环境，插件会根据协议MD5保证协议是最新的，当协议不匹配时会从服务端网络导入并存储到本地

### 简单的Entity示例

Account.def

```
<root>
	<Properties>
	</Properties>
	
	<ClientMethods>
	</ClientMethods>
	
	<BaseMethods>
	</BaseMethods>
	
	<CellMethods>
	</CellMethods>
</root>
```

### Entity的继承

* Entity定义文件支持继承
  * <assets>/scripts/entity_defs/interfaces
* 两种继承机制：
  * <Parent>
    * 继承所有的东西
    * 属性/方法
    * Volatile属性定义
    * LOD级别
    * 简单级别的继承
  * <Implements>
    * 继承属性和方法
    * 多级别的继承

### Entity的属性

* 类型（Type）

  * 向所有语言一样
  * 为网络传输/数据库存储标准化

* [固定协议ID（UType）](http://www.kbengine.org/cn/docs/programming/entitydef.html)

* 缺省值（Default）

  * 由类型决定
  * 可以在定义文件里覆盖

* 广播形式的标志（Flags）

* Detail Level

* Volatile信息

* 是否存储到数据库（Persistent）

* Cell上的属性

  * Entity数据被频繁访问
  * 当跨越Cell Boundary时数据会被复制（到新的Cell）
  * 数据备份到Base
  * 数据改变时通知客户端：
    * 属性的改变
    * 当一个Entity进入玩家的AOI时

* Base上的属性

  * 更复杂/访问较少
  * 数据改变时通知客户端

* Client的属性

  * 可访问部分的Server属性

  * 属性值从Cell上发布得来

  * Cell属性改变会触发set_<property>()

  * 例如：

    ```
    def set_HP(self, old):
    	if self.HP == 0 and old > 0:
    		self.doDeath()
    ```

### Entity定义数据类型

#### 简单类型

* INT8 / UINT8
* FLOAT32 / FLOAT64
* STRING
* VECTOR3
* ...

#### 序列类型

* ARRAY
* TUPLE

#### 复杂类型

* FIXED_DICT
  * Dictonary型的对象
  * 固定的key集
* PYTHON
  * 比FIXED_DICT低效
  * 可以支持任何Python数据类型
  * 安全性
    * 读取客户端传来的数据来序列化Python对象
  * 使用Python的pickle模块
  * Unity3D等插件环境不应该将该属性类型传输到客户端（C#无法解析）

#### 可重用的类型自定义

```
<assets>/scripts/entity_defs/alias.xml
```

### Entity属性的发布

* BASE
  * 属于Base
  * 只有Base可以访问
    * BaseApp2和BaseApp3无法访问到BaseApp1中红色实体的BASE属性
  * BASE属性的修改不会被广播
  * 把它们定义在.def文件里就意味着它们会被定期的备份到其他BaseApp上和数据库里
  * 例如：
    * 当前账号Entity记录玩家上次进入游戏所选择的角色DBID
    * 工会管理器记录的工会成员信息列表
* BASE_AND_CLIENT
  * 属于Base
  * Base和自己的客户端可以访问
    * BaseApp2和BaseApp3无法访问到BaseApp1中红色实体的BASE_AND_CLIENT属性
  * 该类属性的值的改变也会被发布到其对应的自己的客户端的Entity上。并且会有脚本的回调（set_<property_name>()）函数会被调用
  * 例如：
    * 当前账号Entity记录玩家上次进入游戏所选择的角色DBID，但客户端也需要对所选角色进行表现
    * 很少用到
* CELL_PRIVATE
  * 属于Real Entity，只有Real Entity能访问
    * CellApp2和CellApp3无法访问到CellApp1红色实体的CELL_PRIVATE属性
  * 在.def文件里定义它们就意味着在Cell的Entity从一个Cell换到另一个Cell上时这类的属性会被随着移植到新的Cell上。另外，这类的属性会被定期的备份到Base Entity上
  * 例如：
    * NPC AI
    * Player的关于游戏Play的属性，但是其他Player不应该看到
* CELL_PUBLIC
  * 属于Real Entity
    * 它所属于的Real Entity和其对应的Ghost Entity上都可以访问
  * 该类属性的值的改变会被发布到其对应的Ghost Entity上。在Ghost Entity上这类属性只是只读的属性
  * 例如：
    * 怪物的暴力级别
    * NPC的等级
* CELL_PUBLIC_AND_OWN
  * 属于Real Entity
    * 它所属于的Real Entity和其对应的Ghost Entity上都可以访问
  * 该类属性的值的改变会被发布到其对应的Ghost Entity上。在Ghost Entity上这类属性只是只读的属性
  * 该类属性的值的改变也会被发布到其对应的自己的客户端的Entity上。并且会有脚本的回调（set_<property_name>()）函数会被调用
  * 例如：
    * Avatar的敌人列表，服务端其他实体AI可以检查Avatar敌人列表并协助战斗，客户端可以显示敌人列表中的仇恨值做排名，而其他客户端则不需要看到当前Avatar的仇恨列表
* ALL_CLIENTS
  * 属于Real Entity
    * 它所属于的Real Entity和其对应的Ghost Entity上都可以访问
  * 该类属性的值的改变会被发布到其对应的Ghost Entity上。在Ghost Entity上这类属性只是只读的属性
  * 该类属性的值的改变也会被发布到其对应的自己的客户端的Entity上。并且会有脚本的回调（set_<property_name>()）函数会被调用
  * 如果其他的玩家的AOI范围内有这个属性隶属的Entity，那么这个属性的值的改变也会被发布这些玩家的客户端的该Entity上。并且会有脚本的回调（set_<property_name>()）函数会被调用
  * 例如：
    * 实体名称
    * 实体血量与等级
* OWN_CLIENT
  * 属于Real Entity
  * 它所属于的Real Entity和自己的客户端可以访问
  * 该类属性的值的改变也会被发布到其对应的自己的客户端的Entity上。并且会有脚本的回调（set_<property_name>()）函数会被调用
  * 例如：
    * 角色当前的敏捷、力量、智力属性，该属性用于计算角色最终的能力值，但其他实体不需要访问该属性，而自己的客户端需要在角色面板上显示这三个属性用于配点
    * 角色的经验值
* OTHER_CLIENTS
  * 属于Real Entity
    * 它所属于的Real Entity和其对应的Ghost Entity上以及其他的客户端都可以访问
  * 该类属性的值的改变会被发布到其对应的Ghost Entity上。在Ghost Entity上这类属性只是只读的属性
  * 如果其他的玩家的AOI范围内有这个属性隶属的Entity，那么这个属性的值的改变也会被发布这些玩家的客户端的该Entity上。并且会有脚本的回调（set_<property_name>()）函数会被调用
  * 例如：
    * 动态的世界物品的状态（如：门，按钮，战利品）
    * 客户端本地已知某状态，只是想将状态广播给其他客户端

### Volatile属性

* 优化的协议
* 仅仅对最近更新的数据值有兴趣
* Position(x,y,z)
* Yaw, Pitch, Roll

### Entity的数据保存(Persistent)

* 一些Entity和它们的数据可能需要保存到数据库，这样就是服务器重启了这些数据也还有效
* 在属性上定义
* Entity被存到数据库里
* 自动在数据库里创建一个self.databaseID

### Entity方法

* 分别定义在
  * Client/Cell/Base
* 必须定义参数
* Base/Cell方法可以被暴露给Client端使用
* Client方法可以指定一个最大的可调用范围
* 要远程的调用（跨域Client/Cell/Base）必须在定义文件（.def）里定义
* Entity根据需要存在于Cell/Base/Client分布平台的一个或多个上。（没有Base部分的entity是不参与容错的）
* 如果在一个分布平台上没有Entity存在的需要，那么在这个平台上也不需要该Entity的Python脚本

### Entity暴露方法（允许Client调用）

* 不是所有的Server方法都被暴露的
* 需要以<Exposed/>声明
* 暴露的Cell方法
  * 自动的接收调用方的EntityID
  * 通常要检查是否self.id == callerID
* 暴露的Base方法
  * 只有自己的Client可以调用

## 脚本开发注意事项

* 尽可能的把负载放到BaseApp
* 尽可能减少需要保存到数据库的Entity的属性
* 避免过多调用WriteToDB()
* 尽量减少复杂层级的数据
  * 如：多维数组
* 如果脚本的执行事件超过一个GameTick，会负面地影响服务器的效率

