# mysql

> 来源：mysql.pdf

## PDF物理第 1 页

基础概念

2026年6月16日 21:50

关系型数据库   （robms）
概念：建立在关系模型的基础上，由多张相互连接的二维表组成的数据库
用表来存储数据   格式统一   便于维护
使用sql语句 标准统一  使用方便
其余的叫非关系型数据库
sql的四种语言：
Ddl dml dql dcl

## PDF物理第 2 页

ddl
2026年6月16日   22:29

展示所有库：     show databases；
转化库使用：     use 库名；
显示当前库：     selectdatabase（）；
删除库：   drop database 库名；
创建库：   createdatabase 库名  defaultcharset 字符集（utf8bm4）；
展示当前库的所有表：show tables；
查询表结构：desc 表名；
查询指定表的建表语句：         show createtable表名；
建表：
Create table 表名（
Id char comment；
Number verchar
）；comment   备注

添加字段：alter table 表名   add 字段名字   类型；
修改数据类型：alter    table 表名 midif 字段名  类型
修改字段名和数据类型：alter        table 表名 change 原字段名   改后字段名     类型
删除字段：alter   table 表名 drop 字段名
删除表：   drop table表名
删除指定表并重新创建该表：truncate table        表名

## PDF物理第 3 页

dml
2026年6月17日    19:45

数据操作语言     用于增删改
添加数据：
Select into 表名set (“id”） value（)
删除数据
Delect from 表名 where条件
改数据名字：
Update 表名  set 字段 改前改后    where

## PDF物理第 4 页

dql
2026年6月20日   12:44

dql又称数据查询语言      用来查询数据库中表的记录
dql基本语法

查询多个字段
Select （字段1，字段2…..) from 表名
设置别名
Select 字段as 别名  from 表名
去除重复记录
Select distinct 字段名from 表名

条件查询语句：
Select 字段名 from 表名  where 条件

聚合函数：给select后的指定字段用的          having也可以用

## PDF物理第 5 页

分组函数
Select 字段from 表名 where 条件  group by 分组字段名   having 分组后过滤条件
执行时间不同    where 分组前  having分组后   where不可以对聚类函数判断        having可以
例子

排序方式
Select 字段from 表名 order by 字段 asc（默认），字段     desc；
多字段排序时，第一个字段值相同，才开始第二个字段的排序
分页查询：

Select 字段from 表名 limit 起始索引，插叙数据数
例子：

## PDF物理第 6 页

小总结：

执行顺序：

## PDF物理第 7 页

dcl
2026年6月21日   10:00

查询用户
Use mysql
Select * from user
创建用户
Create user “用户名”@“主机名”       identified by “密码”
修改用户密码
Alter user “用户名”@“主机名”      identified with mysql_native_password by "新密码"
删除用户
Drop user “用户名”@“主机名”
%代表所有主机
例子：

权限控制：

查询权限：    show grants for “用户名”@“主机名”
授予权限：grant 权限列表      on 数据库.表名    to “用户名”@“主机名”
撤销权限：revoke 权限列表      on 数据库名.表名     from “用户名”@“主机名”
总结：

## PDF物理第 8 页

（未提取到文字，需要人工检查或OCR）

## PDF物理第 9 页

函数

2026年6月21日  21:46

字符串函数：直接跟在select后面
concat（字符串1，字符串2）结果为两个字符串拼在一起
Lower 大写变小写   upper相反
lpad（“01”，“5”，“-”) 结果为---01 把01用-号变成5位数字          -在01左边
rlap为右边与lpad相反

例子：

## PDF物理第 10 页

数值函数：
ceil（）向上取整：变大  floor（）向下取整：变小
mod（x，y）：x除以y取余
rand（）：随机小数范围为0-1 round（x，y）：求参数x四舍五入保留y位

例子：

随机rand函数只有0-1小数所以乘以一百万变成六位再利用           round函数保留0位小数最后因为
只有五位不算0所以还要用lpad或者rlpa函数补足数字

## PDF物理第 11 页

只有五位不算0所以还要用lpad或者rlpa函数补足数字
日期函数：

查询所有员工的入职天数，根据入职天数倒叙排序

## PDF物理第 12 页

查询所有员工的入职天数，根据入职天数倒叙排序
Select name，datediff（curdate（），entrydate） as entrydates from emp order by
entrydates desc；
流程控制函数：
Ifnull 若第一个参数不为空则直接返回若为空则返回第二个参数
if第一个参数和第二个参数不一样则返回第三个参数若一样则返回第二个参数

范围为case when 字段   then 条件 else 条件 end
特指为case 字段   when 数据元素    then 条件 else 条件 end

## PDF物理第 13 页

约束

2026年6月30日   20:38

默认约束：default 主键约束：primary key 外键约束：foreign key 非空约束：          not null
唯一约束：unique 检查约束：check

外键约束：
Alter table 表名add constraint 外键名字foreign key 外键enferences 另一张表的表名
（括号内是它的关联的字段名）

cascade是外键内容删除了      主表的也删除了
Set null是外键内容删除了    主表的内容变为null
外键多对多：
在创建表的语法里面加上对应的副表外键内容：
Constraint 外键名 foreign key 副表名+字段  references 副表名（字段）

一对一：
要关联的副表的字段       类型  unique
Constraint 外键名 foreign key 副表名+字段  references 副表名（字段）

## PDF物理第 14 页

Constraint 外键名foreign key 副表名+字段   references 副表名（字段）
与多对多的区别就是在创建字段中有唯一约束               外键创建不变

## PDF物理第 15 页

多表查询

2026年7月1日  21:06

笛卡尔积：两个表的数据元素组合的所有情况：
Select * from 表1，表2 where 表1.字段= 表二.字段（这个句子会展示两个表的笛卡尔积
的情况）
三个连接方式：空格后面跟着新名字
内连接  只查询两个表的交际部分
隐式：select 表1.字段，表2.字段   from 表1，表2 where 表1.字段，表2.字段的数学关系
显式：select 表1.字段，表2.字段   from 表1，表2 inner join 第二张表名on 表1.字段，表2.
字段的数学关系

外连接：
左外连接：左表的所有数据包括交集数据
select 表1，表2 from 设置的左边表（两个表的主表）left join 右表    on 表1.字段，表2.字段
的数学关系
右外连接：右表的所有数据包括交集数据
select 表1，表2 from 设置的右边表（两个表的主表）right join 左表     on 表1.字段，表2.字
段的数学关系

## PDF物理第 16 页

自连接：把一张表变成两张一样的表       然后按照外连接的方式就行      只不过字段变一下

子查询：括号内的语句    通常用于两个需求的联合情况

联合语句
Union all 就是结果拼接在一起

## PDF物理第 17 页

union则需要去重后再拼接在一起

例子：

## PDF物理第 18 页

子查询

2026年7月1日 21:33

一般有四种：标量子查询     列子查询  行子查询  表子查询

where语句就行了 例子如下

行子查询：第一个的输出是多行的输出就是行子查询

列子查询：输出是多列就是列子查询

总结：

## PDF物理第 19 页

（未提取到文字，需要人工检查或OCR）

## PDF物理第 20 页

事务

2026年7月13日 23:55

事务是一组操作的集合，是一个不可分割的工作单位，事务会把所有操作作为一个整体一起向
系统提交或撤销操作请求，这些操作要么同时成功要么同时失败
需要保证数据的完整性和一致性      set@@autocommit = 0；为手动提交 rollback为回滚事务
事务默认为自动提交的，当执行一条dml语句时，mysql会立刻隐式的提交事务
程序异常例子：

开启事务：  begin 或者start transaction
提交事务：  commit
回滚事务：rollback
完整例子：

事务的四大特性
原子性（a）：事务是不可分割的最小操作单元，要么全部执行，要么全部中断
一致性（c）：事务完成后，所有的数据都要保持一致性
隔离性（l）：每一个事务都处于特定的环境中，互不干扰，不受外部干扰

## PDF物理第 21 页

隔离性（l）：每一个事务都处于特定的环境中，互不干扰，不受外部干扰
持久性（d）：事务一旦提交或回滚，他对数据库中数据的改变就是永久性的
脏读：在事务没有提交前，另一个事务读到了因为这个事务的操作改变的数据
不可重复读：一个事务两次读取同一个数据，但返回不同的结果
幻读：事务在更新操作时，显示数据已经存在，但其实不存在（另一个事务中生成这个数据）

隔离级别：read uncommitted（脏读   不可重复读   幻读）  read communitted（不可重复读
幻读）  repeatable read（幻读）serializable
查看事务等级：select @@transaction_isolation
设置事务隔离级别：
Set 【session|global】transaction_isolation level [隔离级别]
小结：

## PDF物理第 22 页

（未提取到文字，需要人工检查或OCR）

## PDF物理第 23 页

索引引擎

2026年7月19日 0:08

索引引擎就是存储数据，建立索引，更新/查询数据等技术的实现方法。存储引擎是基于表
的，不是基于库的，所以存储引擎也可被称作表类型
innodb：操作多 事务完整性要求高    在并发条件下要求数据的一致性
兼顾高性能和搞可靠性的存储引擎，为默认的表类型（存储引擎）
dml操作（增删改）遵从acid四大原理，支持事务       行级锁，提高并发访问性能
支持外键约束，保证数据的完整性和正确性
Xxx.ibd代表的是表名，innodb引擎的每张表都会对应一个表空间文件，存储该表的表结构
（frm、sdl）、数据和索引  参数：  innodb_file_table
innodb：逻辑存储结构：表空间-段-区-页-行

mylsam：不支持事务、外键、行锁     支持表锁  访问速度快   若是以读操作和插入操作为主      只有
很少的删除和更新操作，对事务的完整性和并发性不是很高            文件 xxx.sdi:存储表结构信息
Xxx.myd:存储数据xxx.myi:存储索引
memory（现阶段被redis替代）：此引擎的表存储在内存中，受到硬件、断电问题，只将此
表作为临时表或者缓存使用     无法保证数据安全性
内容存放  hash索引xxx.sdi：存储表的结构信息
三个引擎的不同：

体系结构：连接层    服务层 引擎层  存储层
Show engines；
Create table 表名（字段字段类型约束）engine = 索引引擎；
区分mylsam和innodb的事务、外键、行级锁

## PDF物理第 24 页

索引

2026年7月22日22:10

索引：
优点：提高数据检测的效率     降低数据库的io成本   索引对数据进行排序，降低排序成本，降低
cpu消耗
缺点：索引要占用空间    索引虽然提高了查询效率，但降低了更新表的速度，如对表进行insert
update delete时效率降低
二叉树算法：如最多5个指针     那么一行有5个元素时    中间的可以向上爬

介绍：index可帮助mysql高效获取数据的数据结构，在数据之外，数据库系统还维护着满足
特定查找算法的数据结构，这些数据结构以某种方式引用（指向）数据，这样就可以在这些数
据结构上实现高效查找算法，这种数据结构就是索引
mysql默认为b-tree适用于innodb myisam memory三种数据引擎
b-tree索引：（适用三种索引引擎）如最多5个指针      那么一行有5个元素时    中间的可以向上
爬层级更少  检索效率更高   一页中无论是叶子还是非叶子节点       都会存储数据   那么键值就会减
少指针就会减少   但是同时还要存储大量数据      所以层级变多  性能降低  而且相较于memery的
hash索引innodb可以范围查找和排序

hash索引：采用一定的哈希算法    将键值换算成新的hash值   映射到对应的槽位上    然后存储在
hash表中但是当两个或者多个键值映射到了同一个槽位上         那么产生了hash冲突使用链表解
决（底层数据结构是用哈希表实现      在精确匹配索引列的查询才有效，不支持范围查询（只支
持memory））hash只支持（= in）对等比较类   不支持范围查询（between ><）  无法使用
索引完成排序操作   查询效率高   一次检索即可   检索效率高于b + tree

## PDF物理第 25 页

索引完成排序操作   查询效率高  一次检索即可   检索效率高于b + tree
但是 innodb表中具有自适应hash功能  hash索引是存储引擎根据b+tree索引根据需求自动构
建

r-tree索引：（空间索引是myisam引擎（只支持这个引擎）的一个特殊索引类型，主要用于
地理数据类型）
Full-text索引：（是一种通过建立倒排索引，快速匹配文档的方式（支持myisam和5.6版本
后的innodb引擎））
二叉树都属于树：数据越多     层级越多  检索速度慢

二叉树：22小于36小于48
红黑树：红黑树能有效避免链表化，保持较低高度，适合大规模数据
聚集索引：将数据存储和索引放到一起，索引结构的叶子节点保存了行数据             只能有一个  必须
有
二级索引：数据与索引分开存储，索引结构对应的叶子节点对应的是主键            可以存在多个
如果存在主键  那么主键就是聚集索引
如果不存在主键   那么第一个唯一索引就是聚集索引
如果没有主键也没有合适的唯一索引      那么innodb就会自动生成一个rowid作为隐藏的聚集索
引

## PDF物理第 26 页

创建索引：create index index_name on table_name(字段)
查看索引：     show index from table_name
删除索引：drop index index_name on table_name

sql的执行频率：mysql客户端连接成功后              通过show 【session|global】    status 查看服务器
的状态信息     查看当前数据库的select等语句的访问频次
Show global status like “Com______”
查看慢日志文件尾部实时输出的内容：tail -f localhost-slow.log

## PDF物理第 27 页

profile模块

2026年7月28日  22:45

查看每一条sql的耗时基本情况：        show profiles；
查看指定query_id的sql语句各个阶段的耗时情况：show profile for query query_id;
查看指定query_id的sql语句的cpu使用情况：show profile cpu for query query_id
获取mysql如何执行select语句的信息      包括这个select语句执行过程中表是如何连接的和连接
顺序是什么：explain select 字段列表   from 表名 where 条件；

各个字段含义：
id：select查询的序列号   表示查询中select子句或者操作表的顺序（id相同           执行顺序从上到下
id不同 值越大越先执行）
Select_type:表示select的类型常见的取值有simple（简单表：不使用表连接或者子查询）
primary(主查询：外层的查询)union（union中的第二个或者后面的查询语句）
subquery（select/where后面包含了子查询）
type：表示连接类型    性能由好到差的连接类型为null system const ed_ref range index all
Possible_key：显示可能出现在这张表上的索引        一个或者多个
key：实际使用索引    如果为null 就是没有使用索引
Key_len：索引中使用的字节数      值为索引字段的最大可能长度         并非实际使用长度      在不损失精
确性的前提下    长度越短越好
rows：mysql认为必须要执行查询的行数        在innodb引擎的表中是一个估计值         并不总是准确
filtered：返回结果的行数占需读取行数的百分比          越大越好

## PDF物理第 28 页

（未提取到文字，需要人工检查或OCR）
