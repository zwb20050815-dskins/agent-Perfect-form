# python进阶

> 来源：python进阶.pdf

## PDF物理第 1 页

对象

2025年9月16日  22:51

对象：
1.面向对象：将编程当成一个对象，对外界来说这个对象是直接使用的，不需要去管内部的情况，保证它能够做什么
2.类和对象：对一系列具有相同属性和行为的列统称为类（大驼峰命名）查看方法：print（类名.属性）
Class 类名：
代码块：属性
              方法（定义函数形参为self）
（实例化方法）变量     = 类（）
（顶格）变量.属性（）
新增类属性：类名.属性     = 值 即可
主体函数__init__(self):表示初始化函数
Self.属性= 值
变量 = 类（参数个数对应）
3.构造对象：就是拼接函数     字母拼起来就好     效果与主体函数差不多
4.析构对象：__del__()表示删除对象时，__del__()函数会被优先相应并且在正常运行时此函数不会被运行
例子：Def __del__（self）:
(自动换行)print（‘立马销毁’）
p.类
Del p 内存会被立刻回收，然后调用__del__,表示该程序库完全运行并结束
封装：将复杂的信息包起来，然后内部处理，以便后续简便化处理
一个_:是私有属性
隐藏处理：与上面那一个都不可以被         import 库from *显示
Def __di():
print（‘帝’）
O = 类
print（o._类__di）

## PDF物理第 2 页

继承

2025年9月17日22:02

  Class 类名（父亲名）：
  （自动换行）代码块
  继承分为单继承和多继承
  单继承：只有一个后代    子类可以继承父类的属性和方法
  class（父类）（）：
  （自动换行）def 函数（方法）：
  print（）
  Class 子类名字（父类名）：
  （自动换行）pass（占位符）
  变量名 = 子类名字（）
  变量名.方法函数名（）    这两行表示调用
  多层继承：孙子继承儿子儿子继承爹
  比上面多一层class （子类变量）#方法后面的括号通常都是（self）
  在子类添加父类的方法的方法：父类名.父类的方法（self）
  新式类写法：
  Class A（object）：
  （自动换行）pass
  子类若是拥有父类的属性或者方法那么称为派生类
  多继承：子类可以拥有多个父类      并拥有他们的属性与方法，若是有父类同名，括号距离哪一个近那么便优先调用哪一个父类                class 类名（父类1，父类2）
  pass
  搜索内置属性print（Son.__mro__）
  多态：一个对象有多个状态，在不同环境以不同形态展示功能，则这个对象具有多态特征
  比如 = 这个符号既可以为算术运算符     字符串拼接  def在不同子类可以是同一个名字     但输出不同
  多态性：定义一个统一的接口，一个接口多种实现
  静态方法  ：class 类名：无参数限制
  @staticmethon：
  Def 方法名（形参）：
  方法体
  调用格式：
  类名.方法名（实参）
  对象名.方法名（实参）
  取消不必要的参数传递，有利于减少不必要的内存占用和性能消耗
  类方法：@classmethon与上面的静态方法大差不差就是多了参数
  一般配合类对象或者类属性一起调用
  小结：类对象：object 实例对象：self
  1.实例方法:方法内部访问内属性，可以通过类名.类属性访问类属性
  2.静态方法：方法内部不需要访问实例属性与类属性，不能访问类属性，可以通过类名.类属性访问类属性
  3.类方法：方法内部只需要访问类属性，不能访问实例属性，可以通过cls.类属性名访问类属性
  个人小结：类属性是公用的，所有都可以访问，静态方法不需要访问实例属性因为不需要传参，实例属性是私有的，要在实例内部方法内访问

## PDF物理第 3 页

单例与魔法方法

2025年9月18日  21:37

静态方法：__new__:object基类提供的内置的静态方法
作用：1.在内存中为对象分配空间
2.返回对象引用
利用重写__new__方法实现单例模式：音乐的播放器         数据库连接   垃圾桶等等（只存在一个对象）每一次实例化创造的都是同一个对象，内存地址都一样
例子：
Class add:
(自动换行) ob = None
（自动换行）def __new__(cls,*args,**kwargs):
(自动换行)print（）
（自动换行）if 变量   = None
（自动换行）cls.变量名   = super（）.__new__(cls)
（自动换行）return cls.变量名 == super（）.cls() 若无这一步return 那么便不会被分配空间，则不会往下调用方法
__new__与__init__的区别：
1.前者只是创建对象，后者是初始化对象
2.前者需要返回对象引用，后者可以定义实例属性
3.前者是类级别的方法，后者是实例级别的方法
类方法一般是配合类属性      cls代表类对象，类本质上就是一个对象
通过导入模块实现单例模式：
一般导入模块后这个模块会形成一个.pyc文件后续就会直接调用这个文件
导入模块就是一个单例模式
__函数__：拥有特殊函数的就叫做魔法方法（具备特殊功能）调用（变量.函数）
1.__doc__:表示类的基本信息  在class下一行用三个引号表示作用
2.__str__: 对象的描述信息def下一行一定要有return +字符串
Callable：表示函数能否被调用
3.__call__:表示调用一个可调用的实例对象

## PDF物理第 4 页

读写文件行列

2025年9月21日  22:24

readlines：按照行的方式把文件内容一次性全部读取，返回的是一个列表，每一行的数据就是每一个列表的元素
open：创建一个文件对象，默认是以只读模式打开
read（n）：n代表从文件中读取的数据长度，若没有传n值或者是负值，便一次性读取文件中所有数据

write：将指定数据写入文件
close：关闭文件
readline：一次读取一行数据
F = open（‘text.txt’）|引号中可以是文件的路径
Text = f.readlines
Print('text') 打印出来
For I in text:
Print(i) 把text中的内容输出出来
r：只读模式
w：只写模式  若文件存在就先删除文件内容而后输入内容              不存在就创建文件     在open后加
F = open('text.txt','w')
+
r+:表示文件以读写的方式打开，若文件不存在便报错
w+:表示文件先写在读，直接覆盖原有内容          不存在就创建再报错
f.write（‘’）书写格式
每一个最后都需要f.close（）
查询：
seek（offset，whence）
offset：表示指针偏移的数量
whence：起始位置   表示移动字节的参考位置
seek（0，0）会把文件指针移动到开头位置
f.tell():字节长度

## PDF物理第 5 页

编码格式与迭代

2025年9月22日    21:57

不需要close函数：
With open('路径'，encoding = 'utf-8') as f:
Print('')即可
自行置入模块：import os
重命名：os.rename
删除文件：os.remove
删除文件夹：os.rmdir
创建文件夹：os.mkdir
获取当前目录：os.getcwd
获取目录列表：上一级目录：os.listdir('../')
可迭代对象：Iteable：迭代（遍历）代表把对象中每一个元素一个一个取出来
条件：实现了__iter__()并返回了迭代器对象
for循环工作原理：通过__iter__()方法获取可迭代对象的迭代器                再调用__next__()获取下一个值赋值给临时变量I
isinstance（）：判断一个函数是否是可迭代对象或者内置函数                  但要先from collections.abc import Iterable
print（isinstance（要检验的对象，函数））函数可以是两个，满足其中一个返回True
迭代器   Iterator：记住遍历对象，在这期间可以做其他事（中间体）
创建迭代器对象：li = 【1，2】
Li2 = __iter__(li)
Print(next（li2）) 取值出现几次取几次
next取完值后若是超出值报stopiteration错误
print（dir（变量））    演示函数    看是否包含next和iter函数
有next功能才是迭代器       可以for循环遍历的是可迭代对象
自定义迭代器：
先定义一个类class add(object):
def__init___(self):
设置初始值：     self.num = 1
def __iter__(self):
Return self 返回迭代器的实例对象
def __next__(self):
if self.num == 10 设置终点值
   raise stopiteration() 终止迭代
   self.num +=1 设置步长
Return self.num 返回值
M = Myiterator()
Print(M) 调用函数

## PDF物理第 6 页

生成器与线程

2025年9月24日                     22:08

使用了yield函数与next的调用函数则为生成器
例子代码：
Def 函数（）：
Yield ‘添加对象‘
print（·‘函数（）’）
变量       = 函数（）
print（next（函数（变量）））                                       函数后面不能加（）                            不然变成调用函数
可迭代对象：只有__iter__函数
迭代器：在可迭代对象的基础上多一个next函数
生成器：拥有以上的特点但是是yield主导
线程：
多线程：线程之间的执行是无序的                                              之间会共享资源也会竞争资源
例子：
先定义一个可迭代对象：li = 【】
写入数据：
Def 函数（）：
 For i in range（数字）:
(自动换行) li.append(i)
(自动换行)time.sleep(几秒钟)
 （与for同列）print（li）
读取数据：def 函数（）：
print（）
创建子线程：
First = Thread（target = 函数名）
Second = Thread（target = 函数名）
开启子线程：
First.start()
阻塞子线程：
First.join（）
Time.sleep(时间) 阻塞时间
Second.start()
资源竞争：                from threading import Thread 以及import time
A = 0  全局变量
B = 1000000 数值不能太少                                不然数值叠加均等
Def add（）：
 for I in range（b）：
 global a（定义全局变量）
 a += 1 给a循环加值
print（第一次的a）
add（）           调用第一次函数
Def add1（）：
 for I in range（b）：
 global a 每次都要定义全局变量
print（第二次的a）
Add1（）调用第二次函数
If __name__ == '__main__'：
First = Thread(target = 第一个函数)
Second = Thread（target = 第二个函数名）

## PDF物理第 7 页

（未提取到文字，需要人工检查或OCR）

## PDF物理第 8 页

b

## PDF物理第 9 页

线程与进程

2025年9月28日 19:55

线程同步：join和互斥锁
Join.指定的定义函数（）   负责阻碍线程
互斥锁：对共享数据进行锁定，确保共享数据在多线程访问中不会出现数据错误，同一时刻的线程只有一个
acquire（）：上锁
release（）：释放锁
两个函数必须同步出现，不然出现死锁。
在线程函数中for循环前：加上lock.acquire()表示该线程上锁     同时在此定义函数结尾加上lock.release（）表示线程解锁        自动换行即可
进程：是操作系统进行资源分配和调度的基本单位，也是操作系统结构的基础
比如一个软件运行就是一个进程
进程里可以有多个线程，多个进程也可以完成多个任务
进程的状态
就绪状态：启动的条件已经满足，等待cpu响应
执行状态：cpu运行程序
阻塞（等待）状态：等待某些条件满足，等程序处于休眠（sleep）状态，导致程序运行阻塞
先import time和from multiprocessing import Process
Sex = input（‘输入性别：’）  等待状态
print（Sex）执行状态
Time.sleep(1) 等待状态
进程语法结构：
multiprocessing模块提供了process类进程对象
进程参数：
Target：执行的木匾任务名，即子进程要执行的任务
args：以元组形式输出
kwargs：以字典形式输出
常用方法：
Start()：子进程开始
Is_alive()：检查子进程是否存活
Join():主程序等待子进程结束
进程属性：
name：当前进程的别名，默认是Process-N
pid：当前进程的进程编号
访问name属性：print（函数名.name）   不能加（）    不然就是调用函数了
修改子进程的方式：
1.函数.name = ‘新名字’
2.
访问进程编号就是    把访问名字中的name'属性改为pid 前提条件：import os
在定义函数中：os.getpid() 表示获取当前进程编号
Os.getppid则为父进程编号
pycharm默认是11608
使用命令行窗口cmd 输入指令tasklist 再通过ctrl+f查找编号
pycharm的默认编号就是主进程的父进程编号
写在子进程中判断进程是否存活时要利用join先阻塞进程

## PDF物理第 10 页

匹配

2025年10月3日    10:29

正则表达式：导入re模块
而后使用变量名      = re.match() 进行匹配  若没有则返回None
最后使用group导出数据
特点：语法复杂      通用性强
Re.match(匹配的元素（正则表达式pattern），要匹配的对象（要匹配的字符串（string））)
注意：是从开头开始匹配
字符匹配：
1.. 表示匹配任意一个字符       除了\n：re.match（'.任意字符‘，’匹配的字符串‘）
2.【】：表示其中列举的字符：re.match('[he]','hello') 表示提取he 但结果只提取h
Re.match('[he][he]','hello') 表示提取两个字符
re.match('[12345]','543') 提取5
re.match('[1-46-9]','542')提取5 表示跳过5提取字符    报错re.match('[1-68-9]','5423') 即可
3.\d:表示匹配数字0-9
Re.match('\d','132')提取1 若开头非数字   则匹配失败     若要多匹配则再加\d即可匹配3
4.\D:匹配非数字
Re.match('\D','sdd') 匹配s
5.\s:表示匹配空格与tap键
6.\S：表示匹配非空格与tap键
7.\w:表示匹配单词字符：英文大小写           数字0-9 汉字
Re.match('\w','术后‘)匹配术
8.\W:匹配非单词字符
Re.match('\W','|ee') 匹配|
匹配多个字符：
1.*表示匹配大于0次的字符
Re,match('\d*','1223') 输出1223、
2.+表示匹配至少一次出现的字符：
re.match('/d+','1223') 输出1223
3.？表示匹配0或者1次的字符：
re.match('/d？','1223') 输出1
4.{m}：表示匹配出现m次的字符：
re.match('/d{2}','1223') 输出12 此为表示两个连续的数字
Re.match(r'2{2}','2213')输出2 表示出现两次的数字2 必须开头
5.{m，n}:表示匹配出现m到n次的字符          n必须大于m 否则报错  n取不到
理解也如上
匹配开头和结尾：
1^表示匹配开头：
Re.match('^py','python')  将‘^py'改为'【^p】' 表示不以p开头匹配
2.$表示匹配结尾
Re.match('.{前面有几位}p$','aapp') 输出aapp全部   表示这个字符是以p结尾的
3.（）将其中字符作为一个分组
Re.match('\w*@(152|213).\w*','www@152.com) （）后尽量用.不用其他
4.\num:匹配分组num匹配到的字符串
Re,match(r'<(\w*)><(\w*)>.*</\2></\1>','<html><agg>aahd<agg><html>') 从左往右为编号1开始
r表示转义标志
5.?P<name> 表示取别名
Re.match(r'<(?P<z1\w*>)><(?P<z2\w*>)>.*</(?P = z2)></(?P = z1)>','<html><agg>atn<agg><html>')
6.?P = name 表示应用别名
匹配网址：利用列表储存网址           再使用for循环遍历

## PDF物理第 11 页

匹配网址：利用列表储存网址         再使用for循环遍历
Li = 【'www.baidu.com','www.python.arg'】
For i in li:
（自动换行）变量名      = re.match('www\.\w*.(arg|com)',i)
（自动换行）If 变量名    ！= None：  #表示这个变量名储存的网址不为None则继续
（自动换行）print（变量名.group()）
（自动换行）Else:
(自动换行)print（f'{i}网址有错误'）
匹配的替代品：
1.search：re.search(要匹配的元素，匹配字符串)只会匹配第一个成功匹配的字符串，后续若再有重复也不匹配与打印，匹配失败返回None
2.findall：先遍历字符串然后打印出所有满足条件的字符串最后返回列表（不需要                  group函数抓取）
3.sub：将字符串代替    re.sub(新内容，旧内容，字符串，替换次数) 也不需要group函数抓取
4.split：切割满足匹配条件的字符串，并返回列表re.split(’|‘，‘string’，最大分割次数) 没有设置次数默认将字符串所有字母都隔开
贪婪与非贪婪匹配:
贪婪匹配：在匹配允许的情况下，有限匹配长字符串
Re.match('fa*','fake')
非贪婪匹配：在匹配允许的情况下，优先匹配短字符串（多一个？）
Re.match('fa*?','fake') 问号表示出现一次或者零次
\与r的关系表示r = 2\

## PDF物理第 12 页

模块

2025年10月4日   23:09

os模块：与操作系统进行交互        常用于获取平台信息       对目录的操作     判断操作
Os.name:返回系统名字    windows返回nt ；linux返回posix
Os.getenv:返回此系统环境变量
Os.path.split:将文件变量名与目录分开以元组形式打印         第一个元素为目录路径        第二个为文件名      可以用下标输出目录路径或者文件名但需要用变量名先储存
Os.path.dirname:表示文件路径  同下
Os.path.basename:表示文件名  print（os.path.basename(r'文件位置名')） 以/结尾返回空值     以\结尾报错
Os.path.exists:判断路径（文件或者目录）是否存在
Os.path.isfile：表示文件是否存在
Os.path.isdir：判读目录是否存在    以上三个皆返回True或者Flase
Os.path.abspath：获取当前路径下的绝对路径
sys模块：负责跟python解释器与软件交互
Sys.getdeflautencoding:表示获取系统默认编码格式
Sys.platform:获取操作系统平台名称
Sys.path：获取环境变量路径，与解释器有关          以列表形式返回，第一个为当前所在的工作目录
Sys.version:获取当前python解释器版本信息
time模块：
时间戳（timestamp）：距离1970年1月1日的时间精确到秒与分
time.time函数返回时间戳    time.sleep():函数表示停止几秒钟
localtime：将当前时间戳转化为当前时区的struct_time 可以用下标也可以使用变量名储存后使用                    变量名.tm_year等来输出    没有括号
[年月  日 小时  分钟  秒 当前这一周第几天从0开始计算          当前所在年的第几天       isdsttime]
Time.asctime函数：获取系统当前时间
格式化的时间字符（format time）：
Time.strftime():表示将struct_time转化为时间字符串 print（time.strftime(‘%y-%m-%d%H：%M：%S’，time.localtime()）
Time.strptime:表示将时间字字符串转化为struct_time 同上f变成p即可
时间元组（struct_time）
random模块：
Random.random():产生大于0小于1的小数（随机生成）
Random.uniform(a,b):产生指定范围的小数（随机生成）
Random.randint(a,b):产生指定范围的整数，包含开头结尾（随机生成）
Random.randrange(start,stop,step):产生范围中按步调的整数，包含开头不包含结尾
logging模块：用于记录日志信息       程序调试与软件故障分析与运行情况
级别顺序：CRITICAL>ERROR>WARNING>INFO>DEBUG>NOTSET
会创建一个文件     里面默认等级是WARNING所以只会显示等级比WARNING高的结果
Logging.basicConfig():配置rootlogger参数
filename：指定文件名   所有指令结果都会传输到这个文件里面
Logging.basicConfig(filename=要传输到的文件名)
Level:级别Logging.basicConfig(filename=’要传输到的文件名‘，filename    = ‘只读还是只写什么的’，level = logging.NOTSET) 级别可以更改

## PDF物理第 13 页

（未提取到文字，需要人工检查或OCR）
