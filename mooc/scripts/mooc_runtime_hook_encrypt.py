#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""运行时 hook 登录加密函数（不落敏感明文）
- hook: MP.encrypt / MP.encrypt2 / URSSM4.encrypt / RSA.encrypt
- 抓取调用次数、参数特征、返回值长度/前缀（脱敏）
- 联合网络请求，关联 encParams 提交
"""
from __future__ import annotations
import json, re, time
from pathlib import Path
from playwright.sync_api import sync_playwright

OUT = Path(__file__).resolve().parents[1] / "logs"
OUT.mkdir(parents=True, exist_ok=True)

PHONE = "18565002576"
PASSWORD = "linjie0714"


def main():
    ts = int(time.time())
    out = OUT / f"runtime_hook_{ts}.json"
    snap = OUT / f"runtime_hook_{ts}.png"

    report = {
        "time": ts,
        "hooked": False,
        "hook_logs": [],
        "net_logs": [],
        "notes": [],
        "screenshot": str(snap),
    }

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()

        def on_req(req):
            u = req.url
            if any(k in u for k in ["reg.icourse163.org/dl/", "reg.icourse163.org/zc/", "passport/cellphone", "ac.dun.163.com/v3/d"]):
                item = {"type": "req", "url": u, "method": req.method}
                if req.post_data:
                    pd = req.post_data
                    # 脱敏：只保留 encParams 前缀
                    m = re.search(r'"encParams"\s*:\s*"([0-9a-fA-F]+)"', pd)
                    if m:
                        v = m.group(1)
                        item["encParams_len"] = len(v)
                        item["encParams_prefix"] = v[:32]
                    else:
                        item["post_preview"] = pd[:120]
                report["net_logs"].append(item)

        def on_resp(resp):
            u = resp.url
            if any(k in u for k in ["reg.icourse163.org/dl/", "reg.icourse163.org/zc/", "passport/cellphone", "ac.dun.163.com/v3/d"]):
                it = {"type": "resp", "url": u, "status": resp.status}
                try:
                    body = resp.text()[:300]
                    it["body_preview"] = body
                except Exception:
                    pass
                report["net_logs"].append(it)

        page.on("request", on_req)
        page.on("response", on_resp)

        page.goto("https://www.icourse163.org/", wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(2000)

        for txt in ["登录", "登录/注册", "请先登录"]:
            loc = page.get_by_text(txt)
            if loc.count() > 0:
                loc.first.click(timeout=3000)
                break

        page.wait_for_timeout(3000)
        fr = [f for f in page.frames if "reg.icourse163.org" in (f.url or "")][0]

        # 注入 hook
        hook_js = r'''
        () => {
          window.__HOOK_LOGS__ = [];
          const mask = (x) => {
            try {
              if (typeof x !== 'string') return x;
              let s = x;
              s = s.replace(/1\d{10}/g, '<PHONE>');
              s = s.replace(/[A-Za-z0-9_@#\-]{6,}/g, (m)=> m.length>10? m.slice(0,4)+'***'+m.slice(-2) : '<STR>');
              return s;
            } catch(e){ return '<mask_err>'; }
          };

          const wrap = (obj, key, name) => {
            if (!obj || typeof obj[key] !== 'function') return false;
            const orig = obj[key];
            obj[key] = function(...args){
              let ret;
              try {
                ret = orig.apply(this, args);
              } catch (e) {
                window.__HOOK_LOGS__.push({fn:name, err:String(e)});
                throw e;
              }
              const item = {
                fn: name,
                args_len: args.length,
                args_preview: args.map(a => typeof a === 'string' ? mask(a).slice(0,120) : (typeof a)),
                ret_type: typeof ret,
              };
              if (typeof ret === 'string') {
                item.ret_len = ret.length;
                item.ret_prefix = ret.slice(0, 48);
              }
              window.__HOOK_LOGS__.push(item);
              return ret;
            };
            return true;
          };

          const hooked = {
            mp_encrypt: wrap(window.MP, 'encrypt', 'MP.encrypt'),
            mp_encrypt2: wrap(window.MP, 'encrypt2', 'MP.encrypt2'),
            sm4_encrypt: wrap(window.URSSM4, 'encrypt', 'URSSM4.encrypt'),
            rsa_encrypt: wrap(window.RSA, 'encrypt', 'RSA.encrypt'),
          };
          return hooked;
        }
        '''

        hooked = fr.evaluate(hook_js)
        report["hooked"] = any(bool(v) for v in hooked.values())
        report["notes"].append({"hook_result": hooked})

        # 切密码登录 tab
        for sel in ["a.tab0", "a:has-text('密码登录')", "a:has-text('账号登录')"]:
            l = fr.locator(sel)
            if l.count() > 0:
                try:
                    l.first.click(timeout=2000)
                    break
                except Exception:
                    pass
        page.wait_for_timeout(1200)

        def pick(selectors):
            for sel in selectors:
                loc = fr.locator(sel)
                for i in range(loc.count()):
                    c = loc.nth(i)
                    try:
                        if c.is_visible():
                            return c
                    except Exception:
                        pass
            return None

        phone = pick(["#phoneipt", "input[type='tel']", "input[placeholder*='手机号']"])
        pwd = pick(["input[name='email'][type='password']", "input[placeholder*='密码']", "input[type='password']"])
        if phone:
            phone.fill(PHONE)
        if pwd:
            pwd.fill(PASSWORD)

        for sel in ["button:has-text('登录')", "input[type='submit']", "a:has-text('登录')"]:
            l = fr.locator(sel)
            if l.count() > 0:
                try:
                    l.first.click(timeout=2500)
                    break
                except Exception:
                    pass

        page.wait_for_timeout(8000)
        try:
            hook_logs = fr.evaluate("() => window.__HOOK_LOGS__ || []")
        except Exception:
            hook_logs = []

        # 再次脱敏（保险）
        safe_logs = []
        for it in hook_logs:
            it = dict(it)
            if "args_preview" in it and isinstance(it["args_preview"], list):
                cleaned = []
                for a in it["args_preview"]:
                    if isinstance(a, str):
                        a = a.replace(PHONE, "<PHONE>").replace(PASSWORD, "<PASSWORD>")
                    cleaned.append(a)
                it["args_preview"] = cleaned
            safe_logs.append(it)

        report["hook_logs"] = safe_logs
        page.screenshot(path=str(snap), full_page=True)

        context.close()
        browser.close()

    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(out)


if __name__ == "__main__":
    main()
