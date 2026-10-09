# django

> 来源：django.pdf

## PDF物理第 1 页

一些通用指令与简单介绍

2026年3月23日  9:24

  一个完整的项目：通常有前后端组成，在django中许多包和对应模块都被封装好了，在完整的项目中首先我们要了解项目的商业模式到底是什么
  B是指公司   2就是to C就是个人
  在这里我们的前端使用vue 后端使用REST framework
  前端部分：用户页面，商品页面，购物车页面，订单页面，运营后台页面
  后端部分：用户模块，商品模块，购物车模块，订单模块，搜索模块
  主从同步双机热备：mysql
  session缓存：redis
  异步服务：celery
  分布式服务：Fastdfs
  指令：都是    python 项目名.py 指令
  创建一个项目：startproject（django-admin)
  创建一个应用：startapp
  校验项目完整性：check
  本地简易运行django项目：runserver
  开启django项目的python shell环境：shell
  django用例测试：test
  创建模型变更的迁移文件：makemigrations
  执行上一个命令创建的迁移文件：migrate
  把数据库数据导出到文件：dumpdata
  把文件数据导入到数据库：loaddata
  项目目录介绍：
  项目配置文件：settings.py
  项目路由配置文件：urls.py
  项目管理文件：manage.py
  唯一ID标记：Int数字类型
  发布日期：日期类型
  数字类型：IntegerField
  文本类型：    TextField
  日期类型：DateTimeField
  自增ID：AutoField
  主键定义：primary_key属性

## PDF物理第 2 页

登陆注册

2026年3月25日    15:39

     • taoyu/: 主项目配置目录
         ○  settings.py: 项目设置，使用 MySQL 数据库、JWT 认证、CORS 中间件
         ○  urls.py: 路由配置，包含用户和验证码模块
     • users/: 用户管理应用
         ○  自定义用户模型（扩展 Django 的 AbstractUser，添加手机号字段）
         ○  API 端点：用户注册/登录、JWT token 刷新
     • verifications/: 验证码应用
         ○  短信验证码发送和验证功能
         ○  使用常量定义验证码过期时间（5分钟）和发送间隔（1分钟）
     • celery_tasks/: 异步任务处理
         ○  使用 Celery + Redis 处理短信发送等异步任务
   技术栈
     • 框架: Django 6.0.3 + Django REST Framework
     • 认证: JWT (djangorestframework-simplejwt)
     • 数据库: MySQL (taoyu_db)
     • 缓存/队列: Redis (用于 Celery 消息代理)
     • 异步任务: Celery
     • 其他: CORS 支持、自定义用户模型
   主要功能
    1. 用户注册和登录（手机号 + 密码）
    2. JWT token 认证
    3. 短信验证码发送（异步处理）
    4. 手机号验证
   这是一个典型的移动端 API 项目，使用现代 Django 技术栈，支持前后端分离架构。项目配置为开
   发环境，包含虚拟环境和 Git 版本控制。

   好的 我讲一下这个项目的制作流程然后你帮我纠正：先去gitlab新建一个仓库 然后保存到
   本地 再打开pycharm 再再pycharm中打开这个项目 打开终端新建虚拟环境后 打开终端输
   入：python -m venv '虚拟环境名字' 然后 虚拟环境名字\scripts\activate.ps1 进入到虚拟环境
   之后 我再输入     python manage.py startproject '项目名字‘ 再python manage.py startapp
   ’taoyu‘重复这一步 分别创建      users还有verifications这几个app 然后进入到taoyu的settings更
   改项目配置 数据库选用mysql 再在我本机的ubuntu上启动mysql服务 在配置redis缓存服务
   redis这里主要是存储验证码 然后等到用户要使用的时候再发出验证码 然后就是                         python
   manage.py makemigrations 进行数据制作 再使用python manage.py migrate进行数据迁移 但
   是迁移到哪里我不知道redis吗  至于celery_tasks      这个异步的配置我不知道 新建玩
   celery_tasks这个app后对于celery_tasks这个模块我就不知道怎么做了 接着就是             users和
   verifications这两个app的model的修改和  view的修改还有    urls的修改以及   taoyu文件里的   urls的
   修改我都不知道      请你指点我

   以下是您描述的项目制作流程的纠正和完整指导。我会按步骤说明，指出您的流程中的错误或遗漏，
   并提供具体操作。流程基于 Windows 环境（从您的路径看），使用 VS Code（当前环境）。如果您
   坚持用 PyCharm，可以类似操作。

## PDF物理第 3 页

坚持用 PyCharm，可以类似操作。

   1. 版本控制和项目初始化
      •  您的流程：去 GitLab 新建仓库，保存到本地，然后打开 PyCharm 打开项目。
      •  纠正：
           ○  GitLab 新建仓库后，使用         git clone <仓库URL>克隆到本地（例如        C:\Users\Zwb\Desktop
              \DDjango test\taoyu_projects）。
           ○  打开 VS Code（或 PyCharm），打开克隆的文件夹作为工作区。
           ○  虚拟环境应在克隆后创建，不要在项目目录外。
   2. 创建虚拟环境
      •  您的流程：打开终端输入           python -m venv '虚拟环境名字'，然后     虚拟环境名字\scripts
         \activate.ps1。
      •  纠正：
           ○  在项目根目录（taoyu_projects）打开终端。
           ○  创建虚拟环境：python -m venv venv（推荐用        venv 作为名字，避免特殊字符）。
           ○  激活：venv\Scripts\activate.ps1（注意大小写，Windows 用       .ps1）。
           ○  激活后，提示符会显示           (venv)。
   3. 安装依赖
      •  您的流程：未提到。
      •  纠正：激活虚拟环境后，安装必要包：
           ○  pip install django djangorestframework djangorestframework-simplejwt mysqlclient
              redis celery。
           ○  如果需要 CORS：pip install django-cors-headers。
   4. 创建 Django 项目
      •  您的流程：python manage.py startproject '项目名字'   ——   错误，manage.py   在项目创建后才有。
      •  纠正：
           ○  在项目根目录：django-admin startproject taoyu .（注意末尾的        .，表示在当前目录创建项
              目）。
           ○  这会生成     taoyu/目录（包含      settings.py等）。
   5. 创建 Django App
      •  您的流程：python manage.py startapp 'taoyu'——   错误，taoyu   是项目名，不是 app。重复创
         建  users和  verifications。
      •  纠正：
           ○  python manage.py startapp users
           ○  python manage.py startapp verifications
           ○  这会生成     users/和  verifications/目录。
   6. 配置   settings.py
      •  您的流程：进入       taoyu/settings.py更改配置，数据库选 MySQL。
      •  纠正：
           ○  编辑   taoyu/settings.py：
                 ▪ 添加   INSTALLED_APPS：
                 ▪ 设置   AUTH_USER_MODEL = 'users.User'
                 ▪ 数据库配置（MySQL）：
                 ▪ 中间件添加      'corsheaders.middleware.CorsMiddleware'（在最前）。
                 ▪ DRF 和 JWT 配置：
                 ▪ 语言和时区：LANGUAGE_CODE = 'zh-hans',   TIME_ZONE = 'Asia/Shanghai'。
   7. 启动 MySQL 和 Redis
      •  您的流程：在 Ubuntu 上启动 MySQL，配置 Redis 存储验证码。
      •  纠正：
           ○  MySQL：确保本地 MySQL 服务运行，创建数据库               taoyu_db。

## PDF物理第 4 页

○  MySQL：确保本地 MySQL 服务运行，创建数据库            taoyu_db。
          ○  Redis：安装 Redis（Windows 可下载 Redis-x64），启动服务（默认端口 6379）。用
             于 Celery 消息队列和验证码缓存。
   8. 数据迁移
     •  您的流程：python manage.py makemigrations（数据制作），python manage.py migrate（迁移到哪里
        不知道 Redis）。
     •  纠正：
          ○  makemigrations生成迁移文件（基于模型）。
          ○  migrate将迁移应用到数据库（MySQL），不是 Redis。Redis 用于缓存/队列。
   9. Celery 配置
     •  您的流程：新建      celery_tasksapp 后不知道怎么做。
     •  纠正：
          ○  celery_tasks不是 Django app，而是 Celery 配置目录。手动创建：
               ▪  创建  celery_tasks/目录。
               ▪  创建  celery_tasks/__init__.py（空文件）。
               ▪  创建  celery_tasks/config.py：
               ▪  创建  celery_tasks/main.py：
               ▪  在  taoyu/__init__.py添加：from .celery import celery_app as celery_app
               ▪  创建  celery_tasks/sms/__init__.py和celery_tasks/sms/tasks.py（异步任务代码）。
   10.模型、视图、URL 修改
     •  您的流程：不知道怎么修改。
     •  纠正：以下是关键代码示例（您需要编写）。
          ○  users/models.py：
          ○  verifications/models.py：可为空，或添加验证码模型（可选）。
          ○  verifications/constants.py：
          ○  users/views.py（示例登录视图）：
          ○  verifications/views.py（短信验证码）：
          ○  users/urls.py：
          ○  verifications/urls.py：
          ○  taoyu/urls.py：
   11.运行项目
     •  python manage.py runserver启动开发服务器。
     •  celery -A celery_tasks.main worker -l info启动 Celery 工人。
   如果需要具体代码实现或调试，请提供更多细节。我可以帮您编写或修改文件。### 11.                            运行项目

     •  python manage.py runserver启动开发服务器。
     •  celery -A celery_tasks.main worker -l info启动 Celery 工人。
   如果需要具体代码实现或调试，请提供更多细节。我可以帮您编写或修改文件。

   第六步配置的纠正这里           INSTALLED_APPS=[] 这个列表内是我user和verifications两个项目和一
   个我要用的drf框架 这里是用来再项目中先注册 可是corsheaders又是什么意思
   AUTH_USER_MODEL 为什么等于’users.USER‘ 是我的users项目里自定义的USER吗 中间件添
   加'corsheaders.middleware.CorsMiddleware'又是为什么   DRF和JWT的配置给我讲讲吧 这个语
   言和时区：LANGUAGE_CODE = 'zh-hans'的zh-hans是汉语的意思吗 什么情况我能够开始进
   行数据迁移呢在ubuntu启动mysql和redis之后吗             users的model文件这里主要是用户的登录注
   册功能吗 但是有drf的AbstractUser以及编写好了这部分功能所以就写一个类是怎么通过手
   机号码登录的来实现 因为model作为数据库和view中间的东西 起到的是确认view需要什么
   数据 然后找数据库要数据再吧数据给view verifications的constants中的代码是什么意思呢
   短信存在时间和短信刷新时间吗

## PDF物理第 5 页

短信存在时间和短信刷新时间吗

   ✅ 你已经理解得非常对（很好，问题问得很到位）
   你这次问的每个点都是正常流程中最关键的。下面我逐条解释，帮你把概念理清，方便按顺序落地。

   1.  INSTALLED_APPS = [...]  是干啥的？
      • Django 项目运行前要先“注册”应用（App）：
           ○  users：你写用户模型、用户 API 的 app
           ○  verifications：你写短信验证码逻辑的 app
           ○  rest_framework：DRF（Django REST Framework），提供 API 支撑功能
      • 还有 Django 自带几个默认 app（admin,        auth,sessions等）基本不动。
      • 你少写了     corsheaders是它造成跨域时能处理请求头的工具。

   2.  corsheaders 是什么
      • 跨域请求控制（CORS）
      • 前端（比如      http://localhost:3000）访问后端 http://127.0.0.1:8000，浏览器会检查   CORS。
      • django-cors-headers提供：允许 / 拒绝跨域、设置安全策略等。
      • 所需步骤：pip install django-cors-headers+INSTALLED_APPS加  corsheaders+ 中间件头部
        加  corsheaders.middleware.CorsMiddleware+CORS_ALLOWED_ORIGINS（或CORS_ALLOW_ALL_ORIGINS=True
        ）

   3.  AUTH_USER_MODEL = 'users.User'   解释
      • 这是 Django 机制：告诉系统“用这个用户模型替代默认                    auth.User”。
      • 格式：<app_label>.<model_class>，你确定   users/models.py里class User(AbstractUser)，所以是
        对的。
      • 你项目里自定义了 User，实质是扩展了              AbstractUser，加了   mobile字段。

   4.  corsheaders.middleware.CorsMiddleware放中间件最前面的原因
      • 它需要在其它中间件前先执行，把跨域头早给浏览器响应，避免后续判断失效。
      • 如果放后面，可能请求在           CSRF / 认证 阶段就被直接拒绝了。

   5. DRF + JWT 配置释义
   DRF（rest_framework）
      • API 框架：序列化、视图、权限、异常、分页、过滤、认证
      • REST_FRAMEWORK里设置默认认证、权限、分页等
   JWT（djangorestframework-simplejwt）
      • 无状态 Token 认证（access + refresh）
      • 拿到   access后每次请求     Authorization: Bearer <token>
      • 你写了：
           ○  TOKEN_OBTAIN_SERIALIZER：定制返回内容
           ○  ACCESS_TOKEN_LIFETIME/REFRESH_TOKEN_LIFETIME：过期时间（你写 1 天）
      • 还要在    urls.py加  TokenObtainPairView/TokenRefreshView或自定义登录视图。

   6.  LANGUAGE_CODE  与  TIME_ZONE
      • LANGUAGE_CODE = 'zh-hans'：
           ○  是简体中文（Simplified Chinese）
           ○  Django 国际化 i18n 默认语言
      • TIME_ZONE = 'Asia/Shanghai'：

## PDF物理第 6 页

• TIME_ZONE = 'Asia/Shanghai'：
           ○  时区，用于     USE_TZ=True时数据库时间、now()      这种函数对应的区域时间

   7. 何时迁移？
      • 前提：MySQL 服务已起、数据库已建、settings            里 DB 配置正确、APP 注册完。
      • 顺序：
          1.  python manage.py makemigrations（生成迁移文件）
          2.  python manage.py migrate（把迁移应用到 MySQL）
      • Redis 不参与 Django ORM 迁移（Redis 用于缓存/任务队列），所以                 migrate只与 MySQL 一
        起。

   8.  users/models.py 逻辑
      • 本质：定义“用户表结构”
      • mobile 字段加了    unique=True，说明手机号唯一
      • 你理解对了：Model 是对象-数据库映射，视图（View）从它取数据/写数据
      • 用户登录注册：通常写在           serializers+views里，
        用  authenticate+User.objects.create_user。
      • 你“手机号登录”
           ○  可扩展：重写认证后端（authenticate        先根据手机查用户，再验证密码）
           ○  或“手机号+验证码登录”：verifications         处理验证码，users     进行用户创建/获取

   9.  verifications/constants.py 的意思
      • SMS_CODE_REDIS_EXPIRES = 300：验证码在 Redis 里保存 300 秒（5 分钟），过期自动无效
      • SEND_CODE_REDIS_INTERVAL = 60：同一手机号 60 秒内不能重复发（防刷）
      • 你说“短信刷新时间”也对，实际上是发送间隔控制（防滥用）

   10. celery_tasks 的用途和关系
      • 不是“APP”，是“任务模块”
      • 通过 Celery 做“异步短信发送、短信日志、邮件、耗时任务”
      • 基本文件：
           ○  celery_tasks/config.py（broker 配 Redis）
           ○  celery_tasks/main.py（Celery app）
           ○  celery_tasks/sms/tasks.py（定义@shared_task函数）
      • 启动:
           ○  celery -A celery_tasks.main worker -l info
      • 业务里：
           ○  verifications.views调send_sms_code.delay(mobile)，结果立即返回，发送在后台执
              行。

   11.  verifications 与  users  连接建议
      • verifications只是验证码引擎，不一定要建 DB model（可以全 Redis + Celery）
      • 登录注册流程示例：
          1.  前端手机号 ->     verifications/sms_code/188.../获取验证码（后台 Redis + Celery）
          2.  前端提交手机号+验证码 ->          users/register/或users/login_verif/
          3.  View 里：
                ▪  Redis 查存的验证码对比
                ▪  验证成功则     User.objects.get_or_create(mobile=xxx)或create_user(...)
                ▪  返回 JWT（TokenObtainPairSerializer或手写  RefreshToken.for_user(user)）
      • 这个 process 你说“model 是数据库和 view 中间”的理解非常正确，往后写 serializer +
        view 你就继续按这个思路做。

## PDF物理第 7 页

view 你就继续按这个思路做。

   小结（你现在可干这些了）
     1. 启动 MySQL、Redis（没必要 Ubuntu 特定，只要能访问）
     2. python manage.py makemigrations+migrate
     3. python manage.py runserver
     4. celeryworker 启动
     5. 用 Postman/前端测试：
          ○  /sms_code/<mobile>/获取验证码
          ○  users注册
          ○  /login/取 JWT
          ○  其他受 JWT 保护接口测试

   DRF Serializers 讲解
   在 Django REST Framework (DRF) 中，serializers.py是核心文件，用于处理数据转换、验证和对
   象操作。它连接前端数据与后端模型/数据库。

   1. Serializers 基本作用
     •  序列化：将模型实例（数据库对象）转为 JSON/Python 字典，前端可读。
     •  反序列化：将前端 JSON 转为模型实例，存入数据库。
     •  验证：检查数据格式、必填、自定义规则（如密码一致性）。
     •  创建/更新：自动生成对象，或自定义逻辑。
   2. 常见类型
     •  Serializer：基础类，手动定义字段。
     •  ModelSerializer：自动基于模型生成字段，常用。
   3. 你的  users/serializers.py分析
   你已有两个序列化器，逻辑完整。以下逐个解释：

     •  CreateUserSerializer（注册用）
          ○  继承  ModelSerializer，基于 User模型。
          ○  字段：
               ▪  password：只写（write_only=True），长度 8-20，错误信息自定义。
               ▪  password2：确认密码，只写。
               ▪  mobile：手机号。
               ▪  email：邮箱。
               ▪  allow：协议同意，只写。
               ▪  id：自动生成。
          ○  验证方法：
               ▪  validate_mobile：正则校验手机号格式（1 开头 11 位）。
               ▪  validate_email：正则校验邮箱格式。
               ▪  validate_allow：必须为  'true'。
               ▪  validate：整体校验密码一致性。
          ○  create 方法：移除临时字段，创建用户（用             create_user设置密码）。
     •  MyTokenSerializer（JWT 登录用）
          ○  继承  TokenObtainPairSerializer，扩展 JWT token。
          ○  get_token：添加  user_id、username、mobile到 token。
          ○  validate：添加用户数据到响应（id、username、mobile）。
   4. 使用场景
     •  注册：前端 POST 数据 ->     CreateUserSerializer验证 -> 创建用户。

## PDF物理第 8 页

•  注册：前端 POST 数据 ->      CreateUserSerializer验证 -> 创建用户。
     •  登录：前端 POST 用户名/密码 ->        MyTokenSerializer-> 返回 JWT + 用户数据。
     •  扩展：可加用户信息更新序列化器。

## PDF物理第 9 页

启动mysql

2026年3月25日       18:00

Mysql -uroot -pmysql
输入密码
mysql> CREATE DATABASE demo CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;创建数据库
