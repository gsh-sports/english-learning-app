# -*- coding: utf-8 -*-
"""用 Tatoeba 数据为每个目标词配一条英中例句，输出 examples.js。
依赖：words.json, cmn_sentences.tsv, eng_sentences.tsv, links.csv
用法：python3 build_examples.py
"""
import json, re
from collections import defaultdict
try:
    import zhconv
    to_simp = lambda s: zhconv.convert(s, "zh-cn")
except ImportError:
    to_simp = lambda s: s  # 未装 zhconv 则原样保留

# 1) 目标词集合（小写）
words = json.load(open("words.json", encoding="utf-8"))
targets = {w["word"].lower() for w in words if w["word"].isalpha()}
print("目标词:", len(targets))

# 2) 中文句子 {id: text}
cmn = {}
with open("cmn_sentences.tsv", encoding="utf-8") as f:
    for line in f:
        p = line.rstrip("\n").split("\t")
        if len(p) >= 3:
            cmn[p[0]] = p[2]
print("中文句:", len(cmn))

# 3) 英文句子：筛短句 + 命中目标词，每词最多留 15 条最短候选
TOKEN = re.compile(r"[a-z']+")
BAD = re.compile(r"[0-9]|\.\.\.|…|[^\x00-\x7f]")  # 含数字/省略号/非ASCII的句子朗读不友好，跳过
cand_per_word = defaultdict(list)   # word -> [(len, eng_id, text), ...]
eng_text = {}                       # eng_id -> text（候选句）
candidate_ids = set()
with open("eng_sentences.tsv", encoding="utf-8") as f:
    for line in f:
        p = line.rstrip("\n").split("\t")
        if len(p) < 3:
            continue
        eid, text = p[0], p[2]
        n = len(text)
        if n < 12 or n > 65:
            continue
        if BAD.search(text):
            continue
        toks = set(TOKEN.findall(text.lower()))
        hit = toks & targets
        if not hit:
            continue
        for w in hit:
            lst = cand_per_word[w]
            if len(lst) < 15:
                lst.append((n, eid, text))
                eng_text[eid] = text
                candidate_ids.add(eid)
print("候选英文句:", len(candidate_ids))

# 4) 流式扫 links，给候选英文句找中文翻译 eng_id -> cmn_id
eng2cmn = {}
with open("links.csv", encoding="utf-8") as f:
    for line in f:
        a, _, b = line.partition("\t")
        b = b.rstrip("\n")
        if a in candidate_ids and b in cmn:
            eng2cmn.setdefault(a, b)
        elif b in candidate_ids and a in cmn:
            eng2cmn.setdefault(b, a)
print("有中文翻译的英文句:", len(eng2cmn))

# 5) 每个词挑最短且有中文翻译的句子
examples = {}
for w, lst in cand_per_word.items():
    for n, eid, text in sorted(lst):
        if eid in eng2cmn:
            examples[w] = {"en": text, "cn": to_simp(cmn[eng2cmn[eid]])}
            break

print("成功配例句的词:", len(examples), f"覆盖率 {len(examples)/len(targets)*100:.1f}%")

# 6) 输出 examples.js（按原词大小写映射）
out = {}
for w in words:
    lw = w["word"].lower()
    if lw in examples:
        out[w["word"]] = [examples[lw]]   # 列表格式，可再追加 AI 例句
with open("examples_tatoeba.json", "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=1)
print("已写出 examples_tatoeba.json，共", len(out), "条")
print("提示：再运行 build_merge.py 合并 AI 例句，生成最终 examples.js")
