---
layout: post
title: clickhouse
category: app
typora-root-url: ../../..
---

## 数据库部署

### 简介

主要参考: 

* https://www.hnbian.cn/tags/clickhouse/
* 副本&分片部署说明：https://www.cnblogs.com/zhoujinyi/p/14890319.html
* 官网: https://clickhouse.com/docs/en/

### 安装

直接下载deb安装包进行安装即可, 安装包有如下:

* clickhouse-client
* clickhouse-server
* clickhouse-common-static

官网源: https://repo.clickhouse.com/deb/stable/main/

国内源: https://mirrors.tuna.tsinghua.edu.cn/clickhouse/deb/stable/main/

### 单机部署

```shell
# 查看下当前集群ontime_cluster状态, 关注shard_num, shard_weight, replica_num
select * from system.clusters

# 创建数据库test, 使用`ON CLUSTER`对整个集群都执行, 关注每个节点都成功了
CREATE DATABASE IF NOT EXISTS xxmysdn
# 创建xxmysdn.test表, `PARTITION BY`指定自动分区规则
CREATE TABLE xxmysdn.test
(
    `ts` DateTime('Asia/Shanghai'),
    `uid` String,
    `biz` String
)
ENGINE = MergeTree
PARTITION BY toYYYYMM(ts)
ORDER BY ts
SETTINGS index_granularity = 8192
# 插入多行数据
INSERT INTO xxmysdn.test FORMAT JSONEachRow [{"ts": "2020-12-20 00:01:01", "uid": "a", "biz": "-"}, {"ts": "2020-12-20 00:01:01", "uid": "b", "biz": "-"}, {"ts": "2020-12-20 00:01:01", "uid": "c", "biz": "-"}]
```

### MergeTree + Distributed 实现双主不分片(不依赖zookeeper)

这里有三点配置时需要特别注意的:

(一) 配置文件config.xml中对于`internal_replication`的配置设为`false`

> Each shard can have the `internal_replication` parameter defined in the config file. If this parameter is set to `true`, the write operation selects the first healthy replica and writes data to it. Use this if the tables underlying the `Distributed` table are replicated tables (e.g. any of the `Replicated*MergeTree` table engines). One of the table replicas will receive the write and it will be replicated to the other replicas automatically.
> 
> If `internal_replication` is set to `false` (the default), data is written to all replicas. In this case, the `Distributed` table replicates data itself. This is worse than using replicated tables because the consistency of replicas is not checked and, over time, they will contain slightly different data.

(二) 建表不能是`Replicated*`系列的表, 否则就会依赖zookeeper执行数据同步备份功能

(三) 不能使用`ON CLUSTER`语法, 所以**建表需要事先在每个数据库中依次创建**: 

```shell
# 创建数据库test, 使用`ON CLUSTER`对整个集群都执行, 关注每个节点都成功了
CREATE DATABASE IF NOT EXISTS xxmysdn
# 创建xxmysdn.test表, `PARTITION BY`指定自动分区规则
CREATE TABLE xxmysdn.test
(
    `ts` DateTime('Asia/Shanghai'),
    `uid` String,
    `biz` String
)
ENGINE = MergeTree
PARTITION BY toYYYYMM(ts)
ORDER BY ts
SETTINGS index_granularity = 8192
# 创建分布式表用于对整个集群操作, AS这里意为拷贝test.t1表各字段到新建的表
CREATE TABLE xxmysdn.tall AS xxmysdn.test ENGINE = Distributed('ontime_cluster', 'xxmysdn', 'test', rand())
```

(四) 如果clickhouse设置了密码, 密码需要写入`remote_servers`配置项的每一个`replica`中, 用于数据同步时帐密验证

clickhouse集群中并没有主从的概念, 每一个节点都可以完整的提供增删查改的功能. 数据库创建完成后, 在任意一个节点插入数据, 另一个节点会自动同步:

```shell
# 插入多行数据
INSERT INTO xxmysdn.tall FORMAT JSONEachRow [{"ts": "2020-12-20 00:01:01", "uid": "a", "biz": "-"}, {"ts": "2020-12-20 00:01:01", "uid": "b", "biz": "-"}, {"ts": "2020-12-20 00:01:01", "uid": "c", "biz": "-"}]
```

### 集群部署

我们采用docker部署来简化clickhouse集群的部署工作, 需要部属的组件包括:

* clickhouse-server
* zookeeper

我们部署的集群是2分片1副本结构, 11是分片1, 12是分片1的副本; 21是分片2, 22是分片2的副本. 分片和副本的最小单位都是数据表, 分片, 副本, 分区这三个概念区别如下:

* 分片shard: 每个分片存储同一个数据表的不同数据, 有利于充分利用不同机器性能进行高并发读写. 读的话是通过分配器zookeeper分别到每个分片服上读取再合并结果返回; 写的话则是通过分配器zookeeper按照配置的不同策略(比如rand()为随机分配)写入不同的分片节点
* 副本replica: 一个分片中如果有多个副本, 多个副本会保存该分片数据的备份. 如果数据表建表时使用的引擎是ReplicatedMergeTree, 则副本间的数据赋值就有引擎自己负责, 这样能减轻分配器zookeeper的压力.
* 分区partition: 在建表时利用`PARTITION BY`子句可以指定按照任意合法表达式进行数据分区操作, 比如通过toYYYYMM()将数据按月进行分区、toMonday()将数据按照周几进行分区

通常我们使用最少3台机器, 互为分片和副本, zookeeper以集群方式部署在任意3台服上, 可以达到最小化高可用. 

编排配置文件:

```shell
version: "3.2"
services:
  ch-server-11:
    container_name: ch-server-11
    hostname: ch-server-11
    image: yandex/clickhouse-server
    volumes:
      # local.xml是对于clickhouse集群的配置
      - ./config.xml:/etc/clickhouse-server/config.d/local.xml
      # macros.xml是集群中每个节点的特有配置
      - ./macros11.xml:/etc/clickhouse-server/config.d/macros.xml
      # 将数据库持久化到本地
      - ./db11:/var/lib/clickhouse
    ports:
      - 9011:9000
    ulimits:
      nproc: 65535
      nofile:
       soft: 262144
       hard: 262144
  ch-server-12:
    container_name: ch-server-12
    hostname: ch-server-12
    image: yandex/clickhouse-server
    volumes:
      - ./config.xml:/etc/clickhouse-server/config.d/local.xml
      - ./macros12.xml:/etc/clickhouse-server/config.d/macros.xml
      - ./db12:/var/lib/clickhouse
    ports:
      - 9012:9000
    ulimits:
      nproc: 65535
      nofile:
       soft: 262144
       hard: 262144
  ch-server-21:
    container_name: ch-server-21
    hostname: ch-server-21
    image: yandex/clickhouse-server
    volumes:
      - ./config.xml:/etc/clickhouse-server/config.d/local.xml
      - ./macros21.xml:/etc/clickhouse-server/config.d/macros.xml
      - ./db21:/var/lib/clickhouse
    ports:
      - 9021:9000
    ulimits:
      nproc: 65535
      nofile:
       soft: 262144
       hard: 262144
  ch-server-22:
    container_name: ch-server-22
    hostname: ch-server-22
    image: yandex/clickhouse-server
    volumes:
      - ./config.xml:/etc/clickhouse-server/config.d/local.xml
      - ./macros22.xml:/etc/clickhouse-server/config.d/macros.xml
      - ./db22:/var/lib/clickhouse
    ports:
      - 9022:9000
    ulimits:
      nproc: 65535
      nofile:
       soft: 262144
       hard: 262144
  zookeeper:
    container_name: zookeeper
    hostname: zookeeper
    image: zookeeper
```

clickhouse集群配置文件: config.xml

```shell
<yandex>
    <remote_servers>
        <ontime_cluster>
            <shard>
                <weight>1</weight>
                <internal_replication>true</internal_replication>
                <replica>
                    <host>ch-server-11</host>
                    <port>9000</port>
                </replica>
                <replica>
                    <host>ch-server-12</host>
                    <port>9000</port>
                </replica>
            </shard>
            <shard>
                <weight>1</weight>
                <internal_replication>true</internal_replication>
                <replica>
                    <host>ch-server-21</host>
                    <port>9000</port>
                </replica>
                <replica>
                    <host>ch-server-22</host>
                    <port>9000</port>
                </replica>
            </shard>
        </ontime_cluster>
    </remote_servers>
    <zookeeper>
        <node>
            <host>zookeeper</host>
            <port>2181</port>
        </node>
    </zookeeper>
</yandex>
```

clickhouse各节点特有配置:

macros11.xml

```shell
<yandex>
    <macros replace="replace">
        <layer>01</layer>
        <shard>01</shard>
        <rep>11</rep>
        <replica>ch-server-11</replica>
        <cluster>ontime_cluster</cluster>
    </macros>
</yandex>
```

macros12.xml

```shell
<yandex>
    <macros replace="replace">
        <layer>01</layer>
        <shard>01</shard>
        <rep>12</rep>
        <replica>ch-server-12</replica>
        <cluster>ontime_cluster</cluster>
    </macros>
</yandex>
```

macros21.xml

```shell
<yandex>
    <macros replace="replace">
        <layer>01</layer>
        <shard>02</shard>
        <rep>21</rep>
        <replica>ch-server-21</replica>
        <cluster>ontime_cluster</cluster>
    </macros>
</yandex>
```

macros22.xml

```shell
<yandex>
    <macros replace="replace">
        <layer>01</layer>
        <shard>02</shard>
        <rep>22</rep>
        <replica>ch-server-22</replica>
        <cluster>ontime_cluster</cluster>
    </macros>
</yandex>
```

配置完毕, 拉起docker容器集群即可:

```shell
# 安装插件
curl -L "https://github.com/docker/compose/releases/download/v2.2.2/docker-compose-$(uname -s)-$(uname -m)" -o ~/.docker/cli-plugins/
# 启动
docker compose up -d
# 终止
docker compose down
```

### 集群使用

集群部署完毕, 我们对其做建库建表操作, 并测试下读写:

首先我们连上任意一台clickhouse-server, 如:

```shell
# 如果没有下载yandex/clickhouse-client镜像, 先下载
docker pull yandex/clickhouse-client

# 连接ch-server-11
docker run -ti --rm --network clickhouse-cluster_default yandex/clickhouse-client --host ch-server-11 --port 9000
```

然后进行数据库表的创建, 主要创建test.t1表用于存测试数据, 以及创建对应分布式表test.tall用于对整个集群读写操作. 注意, 基于集群可以使用 **on cluster** **cluster_name** 语法, 这样只需要在一个节点上执行SQL即可同步到所有节点

```shell
# 查看下当前集群ontime_cluster状态, 关注shard_num, shard_weight, replica_num
select * from system.clusters

# 创建数据库test, 使用`ON CLUSTER`对整个集群都执行, 关注每个节点都成功了
CREATE DATABASE IF NOT EXISTS test ON CLUSTER ontime_cluster
# 创建t1表, `PARTITION BY`指定自动分区规则
CREATE TABLE test.t1 ON CLUSTER ontime_cluster
(
    `ts` DateTime('Asia/Shanghai'),
    `uid` String,
    `biz` String
)
ENGINE = ReplicatedMergeTree('/ClickHouse/test/tables/{shard}/t1', '{replica}')
PARTITION BY toYYYYMM(ts)
ORDER BY ts
SETTINGS index_granularity = 8192
# 创建分布式表用于对整个集群操作, AS这里意为拷贝test.t1表各字段到新建的表
CREATE TABLE test.tall ON CLUSTER ontime_cluster AS test.t1 ENGINE = Distributed('ontime_cluster', 'test', 't1', rand())
```

注意这里设置时区为`DateTime('Asia/Shanghai')`, 否则python脚本clickhouse_driver会检查当前时区, 如果不匹配会抛异常

我们发起读写测试:

```sql
# 首先查看ch-server-11的test.t1表, 没有数据
SELECT * FROM test.t1

# 插入测试数据
INSERT INTO test.tall VALUES ('2020-12-20 00:01:01', 'a', '-')
INSERT INTO test.tall VALUES ('2020-12-20 00:01:01', 'b', '-')
INSERT INTO test.tall VALUES ('2020-12-20 00:01:01', 'c', '-')
INSERT INTO test.tall VALUES ('2020-12-20 00:01:01', 'd', '-')
INSERT INTO test.tall VALUES ('2020-12-20 00:01:01', 'e', '-')
```

我们也可以同时插入多行(批量插入):

```shell
# 使用json结构同时插入多行
INSERT INTO test.tall FORMAT JSONEachRow [{"ts": "2020-12-20 00:01:01", "uid": "a", "biz": "-"}, {"ts": "2020-12-20 00:02:01", "uid": "b", "biz": "-"}, {"ts": "2020-12-20 00:03:01", "uid": "c", "biz": "-"}]
```

查询已插入的数据:

```sql
# 连接ch-server-11
docker run -ti --rm --network clickhouse-cluster_default yandex/clickhouse-client --host ch-server-11 --port 9000

# 查询集群所有数据
select * from test.tall
# 查询当前节点数据
select * from test.t1

# 时间比较. 注意这里的字符串不能用双引号!
# SQL中只支持单引号, 表示字符串常量
SELECT * FROM test.tall WHERE (ts > '2020-12-20 00:02:00')
```

### 数据库初始化, 导入导出

```shell
# 使用init.sql文件初始化; 文件中sql语句按`;`分隔; 文件中不能有`#`开头的注释, 可以有`/*...*/`类型的注释
clickhouse-client --user 用户名 --password 密码 --queries-file ./init.sql
# 另一种做法是:
clickhouse-client --user 用户名 --password 密码 --multiquery < ./init.sql

# 导出为csv文件
clickhouse-client --query="select * from test.tall" > test.csv

# 导入
cat test.csv | clickhouse-client --query "insert into test.tall FORMAT CSV"
```

### python链接测试

```shell
from clickhouse_driver import Client

cli = Client(host="127.0.0.1", port="9011", alt_hosts="127.0.0.1:9012")
cli.execute("create database if not exists test")
print("show tables: ")
for tbl in cli.execute("show tables from test"):
        print(tbl)

print("\nshow tall data: ")
for line in cli.execute("select * from tall"):
        print(line)
```

注意python实现的clickhouse_driver库, 对每个clickhouse socket连接同一时间只能给一个执行体(协程, 线程, 进程)访问, 这是库内部请求执行跟踪机制的限制. 如果需要在多协程或多线程环境下执行, 官方推荐**自行实现连接池或者使用短链接**

> Every ClickHouse query is assigned an identifier to enable request execution tracking.
> 
> ...
> 
> However, if you are using DB API for communication with the server each cursor create its own Client instance. This makes communication thread-safe.

### 集群扩缩容/容灾

### 数据迁移

### 经验总结

- 副本集是针对的表，不是库也不上整个ck，所以可以一些表用ReplicatedMergeTree也可以直接不复制，所以数据库都需要创建
- 和ES分片和副本机器分布有区别，CK的每台机器只能一个分片的副本，所以如果要搭建2分片2副本需要2*2的机器，不然报错
- 测试读写数据的时候发现，新建的表会同步，但是数据没有同步，通过查CK log以及zk里面对应host发现 zk存储的是主机名，不是ip，所以就无法找到主机写入，需要改hosts文件
- 测试python ClickHouse_driver连接集群，发现需要高版本的ClickHouse_driver，不然没有alt_hosts参数
- 增删数据库每台需要手动执行，增删表需要加上ON CLUSTER bigdata，增删数据是实时异步
