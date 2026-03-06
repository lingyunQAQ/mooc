#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MOOC 浏览器探测（Playwright）
- 访问首页
- 尝试打开登录入口并填充手机号/密码（仅填充，不自动提交）
- 记录网络请求 URL 关键字（auth/login）
输出: mooc/logs/playwright_probe_*.json + png
"""
from __future__ import annotations
import json, os, re, time
from pathlib import Path
from playwright.sync_api import sync_playwright

OUT_DIR = Path(__file__).resolve().parents[1] / "logs"
OUT_DIR.mkdir(parents=True, exist_ok=True)

PHONE = os.getenv("MOOC_PHONE", "")
PASSWORD = os.getenv("MOOC_PASSWORD", "")


def main():
    ts = int(time.time())
    report = {
        "time": ts,
        "start_url": "https://www.icourse163.org/",
        "opened": False,
        "login_ui_found": False,
        "filled": False,
        "submitted": False,
        "notes": [],
        "network_candidates": [],
        "title": None,
        "final_url": None,
    }

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context()
        page = ctx.new_page()

        seen = set()
        def on_req(req):
            u = req.url
            if re.search(r"login|auth|passport|sms|phone", u, re.I):
                if u not in seen:
                    seen.add(u)
                    report["network_candidates"].append(u)
        page.on("request", on_req)

        page.goto("https://www.icourse163.org/", wait_until="domcontentloaded", timeout=60000)
        report["opened"] = True
        report["title"] = page.title()

        # 尝试点击登录
        clicked = False
        for text in ["登录", "登录/注册", "请先登录", "Sign in"]:
            loc = page.get_by_text(text)
            if loc.count() > 0:
                loc.first.click(timeout=3000)
                clicked = True
                break
        if not clicked:
            # 备选：常见按钮
            for sel in ["a[href*='login']", "button:has-text('登录')", "div:has-text('登录')"]:
                try:
                    page.locator(sel).first.click(timeout=3000)
                    clicked = True
                    break
                except Exception:
                    pass

        page.wait_for_timeout(2000)

        # 常见输入框
        phone_sel = ["input[type='tel']", "input[placeholder*='手机号']", "input[name*='phone']", "input[id*='phone']"]
        pass_sel = ["input[type='password']", "input[placeholder*='密码']", "input[name*='password']", "input[id*='password']"]

        pbox = None
        for s in phone_sel:
            if page.locator(s).count() > 0:
                pbox = page.locator(s).first
                break
        pwbox = None
        for s in pass_sel:
            if page.locator(s).count() > 0:
                pwbox = page.locator(s).first
                break

        if pbox and pwbox:
            report["login_ui_found"] = True
            if PHONE:
                pbox.fill(PHONE)
            if PASSWORD:
                pwbox.fill(PASSWORD)
            report["filled"] = bool(PHONE and PASSWORD)
            report["notes"].append("已填充账号密码，未自动提交（避免触发风控/验证码）")
        else:
            report["notes"].append("未识别到标准账号密码输入框，可能是 iframe/滑块/动态组件")

        png = OUT_DIR / f"playwright_probe_{ts}.png"
        page.screenshot(path=str(png), full_page=True)
        report["screenshot"] = str(png)
        report["final_url"] = page.url

        browser.close()

    out = OUT_DIR / f"playwright_probe_{ts}.json"
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(out)


if __name__ == "__main__":
    main()
