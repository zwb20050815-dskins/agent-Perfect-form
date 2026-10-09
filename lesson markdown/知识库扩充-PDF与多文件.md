# 补充实践：把 PDF 和多份 HTML 放进知识库

这是现有项目的知识库扩充，还没进入第九课。我们继续使用学过的混合检索、重排、工具和技能流程。

`lesson08b.py` 默认仍读原来的 24 个银行会计知识块。新的 `knowledge_agent.py` 默认读统一的“个人笔记”库，包含这次导入的多份 HTML 和 PDF。

本次本地提取了 **11 份 PDF（179 页）和 3 份 HTML，共 414 个知识块**。这是文字提取结果，是否能正确回答还要检查向量、检索结果和原文。

PDF 中有 126 页含图片，26 页清理后不足 50 字。**目前只导入能提取的文字，没有进行 OCR（图片文字识别）**；截图、图片和部分图表里的知识还不完整。含图片也不代表整页都没被读到。

## 1. 入库仍然是三步

1. **提取文字**：HTML 转为 Markdown；PDF 按页提取，记录文件名和页码。
2. **切成知识块**：保留来源，较长文字分段；PDF 的块不会跨页。
3. **生成向量**：Embedding 模型处理知识块，保存下来供以后检索。

向量仍保存在本地 JSON 文件中；Redis 继续保存会话状态和历史。把 PDF 加入知识库，不等于把 PDF 放入 Redis。

PDF 引用会标明文档和“PDF 物理第几页”，从文件的第一页开始数，可能与正文印刷页码不同。

## 2. 开始使用扩充后的库

本次已在工作区完成建库与金融/PDF问答验证。E盘写入被系统拒绝，请在你自己的PowerShell执行下面这组命令安装。安装前会整批检查文件，并备份更新前的课程代码和依赖配置：

```powershell
Set-Location -LiteralPath 'E:\agent Perfect form\knowledge-agent'
uv run python 'C:\Users\Zwb\Documents\Codex\2026-10-06\n-h-2\outputs\knowledge-agent\install_library.py'
uv sync
uv run python knowledge_agent.py --check
```

`--check` 做本地配置与索引检查，不代表网络、模型权限和回答质量都已验证。问答时仍需 Redis 运行。

先问银行金融笔记，再换一个来自 PDF 的问题：

```powershell
uv run python knowledge_agent.py --session finance "根据笔记，风险管理的三道防线分别是什么？"
uv run python knowledge_agent.py --session pdf "根据接口笔记，Starlette 和 Pydantic 分别负责什么？"
```

本次实测：风险管理三道防线命中金融笔记0085；再贴现/公开市场主动权命中0076；Starlette/Pydantic命中接口PDF第1页。后两题在收紧技能领域选择后都选择none，仍成功查笔记。详细覆盖范围见 [导入清单](<E:/agent Perfect form/knowledge-agent/data/library/导入清单.md>)。

观察工具日志、回答和引用，回到原文核对。`finance` 与 `pdf` 是两个会话；新入口也使用独立的 Redis 会话前缀，不会接上旧课程同名会话的历史。

银行金融问题能否答好，取决于**资料是否包含答案、检索是否找对、回答是否得到原文支持**。加入资料扩大了可查范围，不保证每道题都答对。

目前 `bank-study` 的说明偏会计；其他问题可能选 `none`。这仍然可以调用 `search_notes` 查金融笔记或 PDF，技能名称不会把检索范围锁定为会计。

## 3. 以后新增或修改笔记

把文件放进桌面的“笔记”文件夹，再执行下面的命令。本次已建好414个向量，**不用为了第一次提问重复运行**：

```powershell
uv run python library_ingest.py build
```

`prepare` 只在本地提取与切块；`index` 读取已有知识块并生成向量；`build` 依次完成两步。也可以分别运行，例如断连后重试 `uv run python library_ingest.py index`。

建库会复用配置一致、文本相同的已有向量，只为需要处理的知识块请求 Embedding。模型、接口或其他相关配置变了，旧向量不能随意混用。

代码先看：[library_ingest.py](<E:/agent Perfect form/knowledge-agent/library_ingest.py>) 的 `prepare_library()` 和 `pdf_chunks()`；再看 [library_index.py](<E:/agent Perfect form/knowledge-agent/library_index.py>) 的 `build_library_index()`；最后看 [knowledge_agent.py](<E:/agent Perfect form/knowledge-agent/knowledge_agent.py>) 如何指定新的知识库和会话前缀。

运行后回答两个问题：

1. PDF 已经提取出文字，为什么还要生成向量？图片里的文字这次都入库了吗？
2. 金融问题选择了 `none`，为什么仍然能查笔记？怎样判断回答确实有资料支持？
