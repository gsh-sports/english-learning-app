# -*- coding: utf-8 -*-
"""清洗例句：规范化标点 + 丢弃朗读/初学者不友好的句子。
处理 examples_ai.json 与 examples_tatoeba.json，原地写回。
丢弃规则（任一即丢）：含数字 / 含省略号 / 规范化后仍含非ASCII字符。
用法：python3 clean_examples.py
"""
import json, re

# 弯引号、破折号等 -> 直引号/连字符
NORM = {
    "‘": "'", "’": "'", "“": '"', "”": '"',
    "–": "-", "—": "-", " ": " ",
}
def normalize(s):
    for k, v in NORM.items():
        s = s.replace(k, v)
    return s.strip()

BAD = re.compile(r"[0-9]|\.\.\.|…|[^\x00-\x7f]")  # 数字/省略号/非ASCII
def is_bad(en):
    return bool(BAD.search(en))

def clean_file(path):
    try:
        d = json.load(open(path, encoding="utf-8"))
    except FileNotFoundError:
        return
    out, dropped = {}, 0
    for w, exs in d.items():
        keep = []
        for e in exs:
            en = normalize(e.get("en", ""))
            cn = normalize(e.get("cn", ""))
            if not en or not cn:
                dropped += 1; continue
            if is_bad(en):
                dropped += 1; continue
            keep.append({"en": en, "cn": cn})
        if keep:
            out[w] = keep
    json.dump(out, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"{path}: 保留 {sum(len(v) for v in out.values())} 条，丢弃 {dropped} 条")

clean_file("examples_ai.json")
clean_file("examples_tatoeba.json")
clean_file("examples_curated.json")
