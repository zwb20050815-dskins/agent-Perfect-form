# linux

> 来源：linux.pdf

## PDF物理第 1 页

基础指令

2025年11月8日    17:29

sudo：管理员权限      sudo-I
Sudo apt update/upgarde/install git 更新软件包索引/更新软件包/下载安装软件包
ls：查看当前目录      ls-a查看隐藏文件
cd：切换目录     cd../~ 返回上一级/返回根目录也就是root目录
Vi/nano编辑器：    退出编辑器     ctrl o输入：wq
rm：删除文件
Rm-r 删除目录里的所有文件
docker：docker ps/images 查看运行中的服务/查看拉取好的服务，包含运行中的和未运行的
Docker-compose up -d/down/restart用docker-compose启动服务/停止服务/重启服务
Docker restart/run/start/stop重启docker服务/运行一个新的docker容器/启动服务/停止服务
Docker --version，docker-compose--version 查看版本，也可用来查看是否安装成功
Docker rm bisheng_rt_v001 删除服务
Docker restart$(docker ps-q) 重启所有服务
Git 工具
Git clone 克隆项目
Git lfspull拉取大文件
Git lfsls-files检查文件完整性
Conda 虚拟环境工具
Conda create-name  sb python = 创建虚拟环境
Conda init初始化
Conda activate激活环境
Mkdir -p model_repository 创建目录
Cd model_repository 进入目录
Sudo aptupdate 更新索引
Sudo apt installgit-lfs安装git-lfs
Git lfs install 初始化lfs

## PDF物理第 2 页

git
2026年3月23日   10:08

现代最流行的分布式版本控制系统：
创建一个git仓库（在项目文件夹中执行）：git init
配置全局变量名和邮箱（首次使用必须设置）
git config --global user.name"你的名字”
git config --global user.email "你的邮箱”
核心三板斧
查看当前文件状态（红色表示未被跟踪或者已经修改）
Git status
将文件添加到提交暂存区（相当于放入提交候选区）git commit 文件名.文件类型
添加指定文件：git add 文件名.文件格式
添加当前目录所有变动：git add .
将暂存区的内容提交到仓库（形成版本记录）
Git commit -m "这里是本次修改的描述"
分支操作
查看所有分支     当前分支会有*号：git branch
创建新分支    基于当前所在位置：git branch feature-login
切换到指定的分支：       git checkout feature_login
合并为新版本指令（创建并切换）: git checkout -b feature-login
引入githug仓库后   核心指令就变成pull push clone merge
克隆与连接：将远程仓库下载到本地（首次参与项目是使用）：                     git clone https://githug.com/用户名/仓库名.git
查看已配置的远程仓库地址：git remote -v
日常同步流程：先拉取（pull) -      本地提交（commit）      -再推送（push）
第一步取远程的最新代码并与本地合并（相当于先同步）
Git pull origin main
第二步本地开发后提交到仓库：
Git add .
Git commit -m“完成了登录内容”
第三步将本地提交推送到远程仓库
Git push originmain
常用指令速查表：
查看简洁版提交历史：git log      --oneline
撤销工作区的修改（未add前）：git checkout        --文件名
撤销暂存区（已经add但是没有commit):git reset HEAD       文件名
强制覆盖远程仓库：git push      -f
临时保存当前未提交的修改，清空工作区：              gitstash
Git merge和gitrebase的区别:
Git merge可以直观的观察到每一条分支的记录            知晓是从哪里分支的       从哪里合并
Git checkout feature
Git merge main
Git rebase就是一条直观的修改路线，让提交记录看起来像是一条历史
Git checkoutfeature
Git rebase main
开发新功能这种个人的用git rebase
Git rebase--abort 取消合并
Git rebase--continue解决冲突后继续
Git rebase -I HEAD~3 交互式变基处理最近的三个提交
公共的用git merge
Git merge--abort取消合并
Git merge--no-ff 强制创建合并提交
merge和rebase的混合使用案例：
本地开发时用rebase
Git checkoutfeature/login
Git rebasemain
推送到远程来供我们查阅：

## PDF物理第 3 页

推送到远程来供我们查阅：
Git pushoriginfeature/login
合并到main时用merge：
Git checkout main
Git merge --no-ff feature/login
Git pushoriginmain
git的格式规范：
类型  说明
feat：新功能（feature）
Fix：修复bug
docs： 仅文档修改（例如README）
style：代码格式调整（不影响代码运行的变动）
refactor：重构（既不是新增功能，也不是修bug）
perf：性能优化
test：增加或者修改测试
chore：构建过程或辅助工具的变动（如依赖更新）
revert：回退某个提交
ci：持续集成相关的配置变更

## PDF物理第 4 页

docker

2026年3月23日  11:19

docker的五大核心概念：
镜像（Image):
只读模板：包含运行应用所需的一切（代码，运行时，库，环境变量，配置文件）
并可以基于基础镜像如ubuntu等构建自己的镜像
镜像由多层组成，每一层对应Dockerfile中的一条指令
容器（container）：
镜像的运行实例，可以被启动，停止，删除
容器是轻量级的，彼此都是隔离的
仓库（repository）：
存放镜像的地方，类似git仓库
公有仓库：Docker Hub（官方），阿里云镜像服务
私有仓库：可以自建Harbor或使用云服务商的私有仓库
Dockerfile：
文本文件，定义如何构建镜像
包含一系列的指令，如FROM（基础镜像），RUN（执行命令），COPY（复制文件），CMD（容器启动命令等）
Docker Compose：
用于定义和运行多容器Docker应用的工具
通过YAML文件配置的所有服务，一条命令即可启动整个应用栈
常用命令：
镜像管理：
列出本地镜像：docker images
从仓库拉取镜像：docker pull nginx：latest
删除镜像：   docker rmi nginx
根据Dockerfile构建镜像（当前目录）：docker build -t myapp：v1
给镜像打标签：docker tag myapp：v1 myapp：latest
容器生命周期：
运行容器（后台，端口映射）：docker run -d --name web -p 8080：80 nginx
列出运行中的容器：      docker ps
列出所有容器包括停止的：        docker ps -a
停止容器：   docker stop web
启动已停止的容器：      docker start web
重启容器：docker restart web
删除容器：   docker rm web
强制删除运行中的容器：docker rm -f web
容器交互与调试：
进入容器内部（交互式终端）:docker exec -it web bash
查看容器日志：docker logs web
实时跟踪日志：docker logs -f web
复制文件到容器：docker cp file.txt web：/app/

## PDF物理第 5 页

复制文件到容器：docker cp file.txt web：/app/
容器详细信息（如ip地址）：docker inspect web
清理资源：
清理停止的容器，未使用的网络，dangling镜像等：                 docker system prune -f
清理未使用的卷：docker volume prune
清理未使用的镜像：        docker image prune -a
