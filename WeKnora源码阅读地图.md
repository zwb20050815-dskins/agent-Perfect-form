# WeKnora 源码阅读地图

WeKnora 的后端主要用 Go，文档解析用 Python。我们借鉴它的流程，用 Python + LangGraph 做自己的知识库 Agent。

下面链接固定到 2026-09-30 的提交 `bccb4b151bae403508da77fbb174efc79dc47c1a`，方便按同一版本学习。

## 按这 8 步读

每次只看指定函数，弄清楚“输入什么、处理什么、输出什么”，再写自己的版本。

| 步骤 | 看哪个文件、函数 | 要学会什么 |
|---|---|---|
| 1. 解析文件 | [html_parser.py:15](https://github.com/Tencent/WeKnora/blob/bccb4b151bae403508da77fbb174efc79dc47c1a/docreader/parser/html_parser.py#L15) 的 `parse_into_text`；[pdf_parser.py:1554](https://github.com/Tencent/WeKnora/blob/bccb4b151bae403508da77fbb174efc79dc47c1a/docreader/parser/pdf_parser.py#L1554) 的同名函数 | 提取正文，保留文件名、HTML 标题或 PDF 页码。扫描页还需要 OCR，也就是识图提字。 |
| 2. 切块 | [chunker/strategy.go:34](https://github.com/Tencent/WeKnora/blob/bccb4b151bae403508da77fbb174efc79dc47c1a/internal/infrastructure/chunker/strategy.go#L34) 的 `Split` | 按标题、段落把长文切成小块。当前入口在这个 Go 文件中，先学普通切块，父子块以后再加。 |
| 3. 生成向量 | [embedding/protocol.go:129](https://github.com/Tencent/WeKnora/blob/bccb4b151bae403508da77fbb174efc79dc47c1a/internal/models/embedding/protocol.go#L129) 的 `BatchEmbed` | 调 Embedding API，把每块文字变成一组数字，并与原文一起保存。 |
| 4. 检索 | [knowledgebase_search.go:125](https://github.com/Tencent/WeKnora/blob/bccb4b151bae403508da77fbb174efc79dc47c1a/internal/application/service/knowledgebase_search.go#L125) 的 `HybridSearch` | 把问题也变成向量，找含义接近的片段；关键词检索则帮助找到术语、名称等。先跑通向量检索。 |
| 5. 合并结果 | [knowledgebase_search_fusion.go:170](https://github.com/Tencent/WeKnora/blob/bccb4b151bae403508da77fbb174efc79dc47c1a/internal/application/service/knowledgebase_search_fusion.go#L170) 的 `fuseWithRRF` | 用 RRF 按两路结果的排名合并、去重。不要直接相加向量分数和关键词分数。 |
| 6. 重排 | [internal/reranking/rerank.go:100](https://github.com/Tencent/WeKnora/blob/bccb4b151bae403508da77fbb174efc79dc47c1a/internal/reranking/rerank.go#L100) 的 `Rerank` | 让专门的重排模型再判断“哪些片段最能回答问题”，只留下少量好结果。 |
| 7. 组织回答 | [into_chat_message.go:34](https://github.com/Tencent/WeKnora/blob/bccb4b151bae403508da77fbb174efc79dc47c1a/internal/application/service/chat_pipeline/into_chat_message.go#L34) 的 `OnEvent` | 把问题、片段和来源编号交给聊天模型，生成能追溯到文件或页码的回答。 |
| 8. 串成流程 | [chat_pipeline.go:11](https://github.com/Tencent/WeKnora/blob/bccb4b151bae403508da77fbb174efc79dc47c1a/internal/application/service/chat_pipeline/chat_pipeline.go#L11) 的 `Plugin`、`Trigger` | 看各阶段怎样传递数据。WeKnora 用自己的事件链；你的项目用 LangGraph 的节点和连线来组织。 |

## 学习时记住 4 件事

- **先完成 1–4 和 7。** 能用自己的笔记回答问题后，再加融合、重排和 LangGraph。
- **聊天模型与 Embedding 模型分开。** Qwen3 聊天模型负责回答；Embedding 模型负责生成向量。文档和问题必须使用同一套 Embedding 模型配置。
- **pgvector 不自带 BM25。** WeKnora 的向量检索用 pgvector，关键词 BM25 来自 ParadeDB。第一版可以先用 Python BM25 搭配向量库。
- **先用小样本。** 从一份 HTML 开始，再加 PDF；核对正文、表格和来源后再批量处理。保留原文件，Obsidian 可以以后再接。

读完一段源码，只需能解释它的输入、输出，并在自己的项目里做出最小版本。高级评分、多租户和部署配置留到后面。
