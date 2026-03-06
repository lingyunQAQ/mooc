#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MOOC 抓包脚本（仅主页 + 登录入口链路）
输出：
- logs/packet_capture_<ts>.json
- logs/packet_capture_<ts>.har
- logs/packet_capture_<ts>.png
"""
from __future__ import annotations
import json, re, time
from pathlib import Path
from playwright.sync_api import sync_playwright

OUT_DIR = Path(__file__).resolve().parents[1] / "logs"
OUT_DIR.mkdir(parents=True, exist_ok=True)
KEY_PAT = re.compile(r"login|auth|passport|sms|captcha|token|sign", re.I)


def main():
    ts = int(time.time())
    har = OUT_DIR / f"packet_capture_{ts}.har"
    png = OUT_DIR / f"packet_capture_{ts}.png"
    out = OUT_DIR / f"packet_capture_{ts}.json"

    report = {
        "time": ts,
        "url": "https://www.icourse163.org/",
        "actions": [],
        "candidates": [],
        "final_url": None,
        "title": None,
        "har": str(har),
        "screenshot": str(png),
    }

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(record_har_path=str(har), record_har_mode="minimal")
        page = context.new_page()

        seen = set()
        def on_req(req):
            u = req.url
            if KEY_PAT.search(u):
                key = (req.method, u)
                if key not in seen:
                    seen.add(key)
                    report["candidates"].append({
                        "type": "request",
                        "method": req.method,
                        "resourceType": req.resource_type,
                        "url": u,
                    })

        def on_resp(resp):
            u = resp.url
            if KEY_PAT.search(u):
                key = ("resp", resp.status, u)
                if key not in seen:
                    seen.add(key)
                    report["candidates"].append({
                        "type": "response",
                        "status": resp.status,
                        "url": u,
                    })

        page.on("request", on_req)
        page.on("response", on_resp)

        page.goto("https://www.icourse163.org/", wait_until="domcontentloaded", timeout=60000)
        report["actions"].append("open_home")
        page.wait_for_timeout(2500)

        # 方案1：文本点击
        clicked = False
        for txt in ["登录", "登录/注册", "请先登录", "Sign in", "注册/登录"]:
            loc = page.get_by_text(txt)
            if loc.count() > 0:
                loc.first.click(timeout=3000)
                clicked = True
                report["actions"].append(f"click_text:{txt}")
                break

        # 方案2：常见选择器
        if not clicked:
            for sel in ["a[href*='login']", "button:has-text('登录')", "div:has-text('登录')", "span:has-text('登录')"]:
                try:
                    l = page.locator(sel)
                    if l.count() > 0:
                        l.first.click(timeout=3000)
                        clicked = True
                        report["actions"].append(f"click_selector:{sel}")
                        break
                except Exception:
                    pass

        # 方案3：脚本扫描可点击节点（包含“登录”）
        if not clicked:
            js = """
            () => {
              const nodes = Array.from(document.querySelectorAll('a,button,span,div'));
              for (const n of nodes) {
                const t = (n.innerText || '').trim();
                if (t.includes('登录') && n.offsetParent !== null) {
                  n.click();
                  return t;
                }
              }
              return null;
            }
            """
            t = page.evaluate(js)
            if t:
                clicked = True
                report["actions"].append(f"click_eval:{t}")

        page.wait_for_timeout(5000)

        report["title"] = page.title()
        report["final_url"] = page.url
        page.screenshot(path=str(png), full_page=True)

        context.close()
        browser.close()

    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(out)


if __name__ == "__main__":
    main()
