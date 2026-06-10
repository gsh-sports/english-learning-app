# -*- coding: utf-8 -*-
"""从 ECDICT 词库筛出牛津3000日常核心词，按词频排序，导出为 words.json。
用法: python3 build_words.py
"""
import csv, json, re

csv.field_size_limit(10**7)

def clean_translation(t):
    """清理中文释义：去掉[网络]等噪声行，最多保留前2条核心释义。"""
    if not t:
        return ""
    t = t.replace("\\r", "").replace("\r", "")
    lines = [ln.strip(" ；;") for ln in t.split("\\n") if ln.strip()]
    core = [ln for ln in lines if not ln.startswith("[")]
    if not core:
        core = lines
    return "；".join(core[:2])

# 词性英文缩写 -> 中文标签
POS_MAP = {
    "n": "名", "v": "动", "vt": "动", "vi": "动", "adj": "形", "a": "形",
    "adv": "副", "ad": "副", "prep": "介", "conj": "连", "pron": "代",
    "art": "冠", "num": "数", "int": "叹", "aux": "助", "modal": "情",
}

def parse_pos(translation):
    """从释义里抽出词性，如 'n. 罩；v. 覆盖' -> ['名','动']（去重保序）。"""
    found = []
    for seg in re.split(r"[；;\n]", translation):
        m = re.match(r"\s*([a-zA-Z]+)\.", seg)
        if m:
            label = POS_MAP.get(m.group(1).lower())
            if label and label not in found:
                found.append(label)
    return found

# 词形变化字段 key -> 中文标签
EXCHANGE_MAP = {
    "p": "过去式", "d": "过去分词", "i": "现在分词",
    "3": "第三人称单数", "r": "比较级", "t": "最高级", "s": "复数",
}

def parse_forms(exchange):
    """解析 ECDICT exchange 字段，如 'p:looked/d:looked/3:looks' -> {'过去式':'looked',...}。"""
    forms = {}
    if not exchange:
        return forms
    for part in exchange.split("/"):
        if ":" not in part:
            continue
        k, v = part.split(":", 1)
        label = EXCHANGE_MAP.get(k)
        if label and v and v not in forms.values():
            forms[label] = v
    return forms

words = []
with open("ecdict.csv", encoding="utf-8") as f:
    for row in csv.DictReader(f):
        if row.get("oxford") != "1":
            continue
        word = row["word"].strip()
        # 跳过带空格/特殊符号的词组，先做最基础的单词
        if not re.fullmatch(r"[A-Za-z'-]+", word):
            continue
        trans = clean_translation(row.get("translation", ""))
        if not trans:
            continue
        # frq: COCA词频排名，越小越常用；0或空表示未知，排到最后
        try:
            frq = int(row.get("frq") or 0)
        except ValueError:
            frq = 0
        words.append({
            "word": word,
            "phonetic": (row.get("phonetic") or "").strip(),
            "translation": trans,
            "pos": parse_pos(trans),
            "forms": parse_forms(row.get("exchange", "")),
            "tag": (row.get("tag") or "").strip(),
            "frq": frq,
        })

# 按词频排序：有词频的在前(从最常用开始)，无词频(0)的排最后
words.sort(key=lambda w: (w["frq"] == 0, w["frq"]))

# 加上序号，去掉内部用的 frq 字段
out = []
for i, w in enumerate(words, 1):
    out.append({
        "id": i,
        "word": w["word"],
        "phonetic": w["phonetic"],
        "translation": w["translation"],
        "pos": w["pos"],
        "forms": w["forms"],
        "tag": w["tag"],
    })

with open("words.json", "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=1)

# 同时生成 words.js，供 index.html 用 <script> 直接加载（双击html即可运行，无需服务器）
with open("words.js", "w", encoding="utf-8") as f:
    f.write("window.WORDS = ")
    json.dump(out, f, ensure_ascii=False)
    f.write(";\n")

print(f"导出 {len(out)} 个日常核心词 -> words.json + words.js")
print("最常用的前10个:")
for w in out[:10]:
    print(f"  {w['id']:>4} {w['word']:<12} {w['phonetic']:<18} {w['translation'][:30]}")
