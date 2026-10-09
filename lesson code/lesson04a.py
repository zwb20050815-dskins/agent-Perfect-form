"""第四课 4.1：用中文分词和 BM25，按关键词检索笔记。"""

import argparse
import logging
from pathlib import Path

import jieba
from rank_bm25 import BM25Okapi

from lesson03b import DEFAULT_SOURCE, LessonError, load_chunks
from lesson03b import embedding_text as chunk_text

jieba.setLogLevel(logging.WARNING)
TOKENIZER = jieba.Tokenizer()


def tokenize(text: str) -> list[str]:
    """把标题、正文或问题拆成词；统一英文大小写，去掉空白和标点。"""
    words = TOKENIZER.lcut_for_search(text.casefold())
    return [word.strip() for word in words if any(char.isalnum() for char in word)]


def keyword_search(chunks: list[dict], question: str, top_k: int = 3) -> list:
    """返回 (BM25 分数, 原知识块)，与上一课的检索结果结构一致。"""
    if top_k <= 0:
        raise LessonError("top_k 必须大于 0。")
    query_words = tokenize(question)
    if not query_words or not chunks:
        return []

    # 标题和正文都参与检索；这一步只在本地统计词语，不调用模型。
    corpus = [tokenize(chunk_text(chunk)) for chunk in chunks]
    if not any(corpus):
        raise LessonError("知识块中没有可检索的文字。")
    bm25 = BM25Okapi(corpus)
    scores = bm25.get_scores(query_words)

    # 只保留确实有词语命中的块，不把没有命中的资料凑进前三名。
    # 不能简单用分数 > 0 判断命中：BM25 分数也可能为 0 或负数。
    results = []
    for chunk, words, score in zip(chunks, corpus, scores):
        if set(query_words).intersection(words):
            results.append((float(score), chunk))
    return sorted(results, key=lambda item: item[0], reverse=True)[:top_k]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("question", nargs="?", default="补充登记法适用于什么情况？")
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE, help="第三课 3.1 的切块文件")
    parser.add_argument("--top-k", type=int, default=3, help="最多显示几个片段，默认 3")
    parser.add_argument("--check", action="store_true", help="检查依赖与知识块，不联网")
    args = parser.parse_args()
    if not args.question.strip():
        parser.error("问题不能为空。")
    if args.top_k <= 0:
        parser.error("--top-k 必须大于 0。")

    try:
        chunks = load_chunks(args.source)
        if args.check:
            print(f"分词与 BM25 依赖可用，{len(chunks)} 个知识块检查通过；本课不需要 API 配置。")
            return 0
        words = tokenize(args.question)
        print("问题分词：" + (" / ".join(words) or "（没有可检索的词）"))
        results = keyword_search(chunks, args.question, args.top_k)
        if not results:
            print("没有关键词匹配的片段；这不等于知识库一定没有相关内容。")
            return 0
        print("以下是本地 BM25 检索结果；分数用于排序，不是答案正确率。")
        for rank, (score, chunk) in enumerate(results, 1):
            print(f"\n{rank}. BM25 分数 {score:.4f} | {chunk['chunk_id']}")
            print("标题：" + " > ".join(chunk["heading_path"]))
            print("来源：" + chunk["source_file"])
            print(chunk["text"])
        return 0
    except FileNotFoundError:
        print("找不到知识块，请先运行 lesson03a.py，或用 --source 指定切块文件。")
    except LessonError as exc:
        print(f"未完成：{exc}")
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        print("知识块文件无法读取或格式不正确，请检查第三课的切块结果。")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
