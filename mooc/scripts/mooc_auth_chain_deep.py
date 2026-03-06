#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""深挖 MOOC 登录鉴权链路（抓包精简版）
- 打开主页 -> 点击登录
- 尝试在登录 iframe 中填手机号/密码并点击登录
- 抓取 reg.icourse163.org / dl.reg.163.com 相关请求
- 仅记录 POST 字段名，不记录字段值
"""
from __future__ import annotations
import json
import os
import re
import time
from pathlib import Path
from urllib.parse import parse_qsl, urlparse
from playwright.sync_api import sync_playwright

PHONE = os.getenv("MOOC_PHONE", "")
PASSWORD = os.getenv("MOOC_PASSWORD", "")
OUT_DIR = Path(__file__).resolve().parents[1] / "logs"
OUT_DIR.mkdir(parents=True, exist_ok=True)

HOST_PAT = re.compile(r"(reg\.icourse163\.org|dl\.reg\.163\.com|ac\.dun\.163\.com)", re.I)


def safe_post_keys(req):
    try:
        if req.method != "POST":
            return []
        data = req.post_data or ""
        if not data:
            return []
        ctype = req.headers.get("content-type", "")
        if "application/x-www-form-urlencoded" in ctype or "=" in data:
            keys = sorted({k for k, _ in parse_qsl(data, keep_blank_values=True)})
            return keys
        # json 或其他，尽量提 key
        if data.strip().startswith("{"):
            obj = json.loads(data)
            if isinstance(obj, dict):
                return sorted(obj.keys())
        return ["<opaque>"]
    except Exception:
        return ["<parse_error>"]


def main():
    ts = int(time.time())
    out = OUT_DIR / f"auth_chain_deep_{ts}.json"
    png = OUT_DIR / f"auth_chain_deep_{ts}.png"
    report = {
        "time": ts,
        "start": "https://www.icourse163.org/",
        "phone_filled": False,
        "password_filled": False,
        "login_clicked": False,
        "iframe_url": None,
        "events": [],
        "final_url": None,
        "title": None,
        "screenshot": str(png),
    }

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()

        seen = set()

        def on_req(req):
            u = req.url
            host = urlparse(u).netloc
            if HOST_PAT.search(host):
                item = {
                    "type": "request",
                    "method": req.method,
                    "host": host,
                    "path": urlparse(u).path,
                    "query": urlparse(u).query[:200],
                }
                if req.method == "POST":
                    item["post_keys"] = safe_post_keys(req)
                key = json.dumps(item, ensure_ascii=False, sort_keys=True)
                if key not in seen:
                    seen.add(key)
                    report["events"].append(item)

        def on_resp(resp):
            u = resp.url
            host = urlparse(u).netloc
            if HOST_PAT.search(host):
                item = {
                    "type": "response",
                    "status": resp.status,
                    "host": host,
                    "path": urlparse(u).path,
                }
                key = json.dumps(item, ensure_ascii=False, sort_keys=True)
                if key not in seen:
                    seen.add(key)
                    report["events"].append(item)

        page.on("request", on_req)
        page.on("response", on_resp)

        page.goto("https://www.icourse163.org/", wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(2000)

        # 点击登录
        clicked = False
        for txt in ["登录", "登录/注册", "请先登录"]:
            loc = page.get_by_text(txt)
            if loc.count() > 0:
                loc.first.click(timeout=4000)
                clicked = True
                break
        if not clicked:
            for sel in ["a[href*='login']", "button:has-text('登录')", "span:has-text('登录')"]:
                try:
                    l = page.locator(sel)
                    if l.count() > 0:
                        l.first.click(timeout=3000)
                        clicked = True
                        break
                except Exception:
                    pass

        page.wait_for_timeout(2500)

        # 定位登录 iframe
        target_frame = None
        for fr in page.frames:
            if "reg.icourse163.org" in (fr.url or ""):
                report["iframe_url"] = fr.url
                target_frame = fr
                break

        if target_frame:
            phone_sel = ["input[type='tel']", "input[placeholder*='手机号']", "input[name*='phone']", "#phone"]
            pass_sel = ["input[type='password']", "input[placeholder*='密码']", "input[name*='password']", "#password"]

            pbox = None
            for s in phone_sel:
                try:
                    loc = target_frame.locator(s)
                    if loc.count() > 0:
                        pbox = loc.first
                        break
                except Exception:
                    pass

            pwbox = None
            for s in pass_sel:
                try:
                    loc = target_frame.locator(s)
                    if loc.count() > 0:
                        pwbox = loc.first
                        break
                except Exception:
                    pass

            if pbox and PHONE:
                
                try:
                    pbox.fill(PHONE, timeout=3000)
                    report["phone_filled"] = True
                except Exception:
                    report["events"].append({"type":"note","msg":"phone input not visible/editable"})

            if pwbox and PASSWORD:
                
                try:
                    pwbox.fill(PASSWORD, timeout=3000)
                    report["password_filled"] = True
                except Exception:
                    report["events"].append({"type":"note","msg":"password input not visible/editable"})


            # 尝试点击登录按钮（可能触发验证码）
            for sel in ["button:has-text('登录')", "input[type='submit']", "a:has-text('登录')"]:
                try:
                    b = target_frame.locator(sel)
                    if b.count() > 0:
                        b.first.click(timeout=4000)
                        report["login_clicked"] = True
                        break
                except Exception:
                    pass

            page.wait_for_timeout(5000)

        report["final_url"] = page.url
        report["title"] = page.title()
        page.screenshot(path=str(png), full_page=True)

        context.close()
        browser.close()

    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(out)


if __name__ == "__main__":
    main()
