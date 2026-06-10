# -*- coding: utf-8 -*-
"""合并三个来源的例句 -> examples.js / examples.json。
优先级：精选(curated) > AI批量(ai) > Tatoeba真实句。每词最多 3 条，去重。
来源：
  examples_curated.json  手工精选的简单例句（最高频词）
  examples_ai.json       工作流 AI 批量生成（全量覆盖）
  examples_tatoeba.json  Tatoeba 真实例句（简体）
用法：python3 build_merge.py
"""
import json

def load(path):
    try:
        return json.load(open(path, encoding="utf-8"))
    except FileNotFoundError:
        return {}

curated = load("examples_curated.json")
ai = load("examples_ai.json")
tatoeba = load("examples_tatoeba.json")

MAX_PER_WORD = 3
merged = {}
all_words = set(curated) | set(ai) | set(tatoeba)
for w in all_words:
    seen, items = set(), []
    for e in (curated.get(w, []) + ai.get(w, []) + tatoeba.get(w, [])):
        en = (e.get("en") or "").strip()
        cn = (e.get("cn") or "").strip()
        if not en or not cn:
            continue
        key = en.lower()
        if key in seen:
            continue
        seen.add(key)
        items.append({"en": en, "cn": cn})
        if len(items) >= MAX_PER_WORD:
            break
    if items:
        merged[w] = items

with open("examples.js", "w", encoding="utf-8") as f:
    f.write("window.EXAMPLES = ")
    json.dump(merged, f, ensure_ascii=False)
    f.write(";\n")
with open("examples.json", "w", encoding="utf-8") as f:
    json.dump(merged, f, ensure_ascii=False, indent=1)

multi = sum(1 for v in merged.values() if len(v) >= 2)
print(f"合并完成：{len(merged)} 个词有例句，其中 {multi} 个有 2 条以上")
print(f"来源覆盖 -> 精选:{len(curated)}  AI:{len(ai)}  Tatoeba:{len(tatoeba)}")
