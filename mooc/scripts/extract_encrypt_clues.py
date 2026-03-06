#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""从已抓取 JS 中提取 encParams 生成线索（静态）"""
from __future__ import annotations
import json, re, time
from pathlib import Path

BASE = Path(__file__).resolve().parents[1] / "logs" / "jsdump2"
OUT = Path(__file__).resolve().parents[1] / "logs" / f"encrypt_clues_{int(time.time())}.json"

KEYS = ["_formatParams", "_$aesEncrypt", "str2b64", "getEncryptKey", "needVerifyCode", "sendValidationCode", "nonce", "version:\"v1\""]


def extract_snippet(text: str, needle: str, radius: int = 280):
    i = text.find(needle)
    if i < 0:
        return None
    s = max(0, i - radius)
    e = min(len(text), i + radius)
    return text[s:e]


def main():
    report = {
        "source_dir": str(BASE),
        "files": [],
        "findings": {},
        "conclusion": []
    }

    if not BASE.exists():
        raise SystemExit(f"missing: {BASE}")

    files = sorted(BASE.glob("*.js"))
    for f in files:
        txt = f.read_text(encoding="utf-8", errors="ignore")
        report["files"].append(f.name)
        for k in KEYS:
            if k in txt:
                report["findings"].setdefault(k, []).append({
                    "file": f.name,
                    "snippet": extract_snippet(txt, k)
                })

    # 结构化结论
    if report["findings"].get("_formatParams") and report["findings"].get("_$aesEncrypt"):
        report["conclusion"].append("encParams 相关链路采用前端 AES 加密 + base64 处理")
    if report["findings"].get("nonce") and report["findings"].get("version:\"v1\""):
        report["conclusion"].append("加密载荷包含 timestamp / nonce / version(v1)")
    if report["findings"].get("getEncryptKey"):
        report["conclusion"].append("登录前存在 getEncryptKey 动作，疑似动态密钥下发")

    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(OUT)


if __name__ == "__main__":
    main()
