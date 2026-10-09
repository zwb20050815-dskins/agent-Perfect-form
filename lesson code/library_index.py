"""为混合知识库增量生成向量；保留第三课的索引格式。"""

import hashlib
import json
import os
from pathlib import Path
import tempfile

from lesson03b import LessonError, embedding_text, index_identity, read_index, unit_vector


def _identity(config):
    return {"model": config["model"], "base_url": config["base_url"]}


def _digest(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _write_json(path, payload):
    """同目录临时文件完整写好后再替换，失败不覆盖原文件。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
        Path(temporary).replace(path)
    finally:
        Path(temporary).unlink(missing_ok=True)


def _read_old_index(path):
    """按旧索引自身的知识块校验，不能用新知识块去校验旧索引。"""
    payload = json.loads(path.read_text(encoding="utf-8"))
    config = _identity(payload["identity"])
    if not all(isinstance(value, str) and value for value in config.values()):
        raise LessonError("旧索引的模型配置无效。")
    chunks = [{key: value for key, value in row.items() if key != "embedding"}
              for row in payload["rows"]]
    if not chunks:
        raise LessonError("旧索引没有知识块。")
    index = read_index(path, chunks, config)
    pairs = [(embedding_text(row), row["embedding"]) for row in index["rows"]]
    return config, index["dimension"], pairs


def _read_cache(path, config):
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload["version"] != 1 or not isinstance(payload["config"], dict):
        raise LessonError("向量缓存格式不正确。")
    identity = _identity(payload["config"])
    if payload["config"] != identity or not all(isinstance(v, str) and v for v in identity.values()):
        raise LessonError("向量缓存的模型配置无效。")
    if identity != _identity(config):
        print("增量缓存的模型配置已变化，本次不复用旧缓存。", flush=True)
        return None, []
    dimension, entries = payload["dimension"], payload["entries"]
    if type(dimension) is not int or dimension <= 0 or not isinstance(entries, list):
        raise LessonError("向量缓存的维度或条目不正确。")
    seen, pairs = set(), []
    for row in entries:
        text, digest = row["text"], row["sha256"]
        if not isinstance(text, str) or not text or digest != _digest(text) or digest in seen:
            raise LessonError("向量缓存的文本校验失败。")
        unit_vector(row["embedding"], dimension)
        seen.add(digest)
        pairs.append((text, row["embedding"]))
    return dimension, pairs


def build_library_index(chunks, config, model, path, seed_paths=(), batch_size=10):
    """每批存缓存，全部成功后原子保存索引；不修改 chunks 或种子索引。"""
    if type(batch_size) is not int or batch_size <= 0 or not chunks:
        raise LessonError("知识块不能为空，批次数量必须是正整数。")
    if len({chunk["chunk_id"] for chunk in chunks}) != len(chunks):
        raise LessonError("知识块编号重复，未生成向量。")
    texts = [embedding_text(chunk) for chunk in chunks]
    path = Path(path)
    cache_path = path.with_suffix(".embedding-cache.json")
    vectors, dimension = {}, None
    invalid = (OSError, ValueError, KeyError, TypeError, AttributeError, OverflowError, LessonError)

    def merge(old_dimension, pairs):
        nonlocal dimension
        if old_dimension is None:
            return
        if dimension is not None and old_dimension != dimension:
            raise LessonError("同一模型的向量维度不一致，未混合写入索引。")
        dimension = old_dimension
        for text, vector in pairs:
            vectors.setdefault(text, vector)

    if path.exists():
        try:
            old_config, old_dimension, pairs = _read_old_index(path)
            if old_config == _identity(config):
                merge(old_dimension, pairs)
            else:
                print("已有索引的模型配置已变化，本次不复用其中的向量。", flush=True)
        except invalid:
            raise LessonError("已有知识库索引未通过校验；原文件已保留，请检查索引。") from None

    if cache_path.exists():
        try:
            merge(*_read_cache(cache_path, config))
        except invalid:
            raise LessonError("增量缓存未通过校验；原索引已保留，请检查缓存。") from None

    skipped = 0
    for seed in seed_paths:
        seed = Path(seed)
        if not seed.exists() or seed.resolve() == path.resolve():
            continue
        try:
            old_config, old_dimension, pairs = _read_old_index(seed)
            if old_config != _identity(config):
                skipped += 1
                continue
            merge(old_dimension, pairs)
        except invalid:
            skipped += 1
    if skipped:
        print(f"跳过 {skipped} 个未通过校验或模型配置不同的种子索引。", flush=True)

    reused = sum(text in vectors for text in texts)
    missing = list(dict.fromkeys(text for text in texts if text not in vectors))
    print(f"知识块 {len(chunks)} 个；已有向量复用 {reused} 块；需新生成 {len(missing)} 段文本的向量。", flush=True)

    def save_cache():
        _write_json(cache_path, {"version": 1, "config": _identity(config), "dimension": dimension,
                               "entries": [{"sha256": _digest(text), "text": text, "embedding": vector}
                                           for text, vector in vectors.items()]})

    for start in range(0, len(missing), batch_size):
        batch = missing[start:start + batch_size]
        returned = model.embed_documents(batch)
        if not isinstance(returned, list) or len(returned) != len(batch):
            raise LessonError("Embedding 返回数量与本批文本数量不一致；已完成批次保存在缓存中。")
        proposed_dimension = dimension
        for vector in returned:
            unit_vector(vector, proposed_dimension)
            proposed_dimension = len(vector)
        dimension = proposed_dimension
        vectors.update(zip(batch, returned))
        save_cache()
        print(f"已缓存新向量 {min(start + batch_size, len(missing))}/{len(missing)}。", flush=True)

    # 无新调用时，也缓存通过校验的种子，供以后的增量导入使用。
    if not missing:
        save_cache()
    index = {"identity": index_identity(chunks, config), "dimension": dimension,
             "rows": [{**chunk, "embedding": vectors[text]} for chunk, text in zip(chunks, texts)]}
    _write_json(path, index)
    print(f"已保存 {len(chunks)} 个向量，每个 {dimension} 维：{path.resolve()}", flush=True)
    return {"total": len(chunks), "reused": reused, "embedded": len(missing),
            "deduplicated": len(chunks) - reused - len(missing), "dimension": dimension}
