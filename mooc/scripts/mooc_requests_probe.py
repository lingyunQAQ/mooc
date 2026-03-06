#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MOOC 接口探测（无浏览器）
输出: mooc/logs/requests_probe_*.json
"""
from __future__ import annotations
import json, time
from pathlib import Path
import requests

BASE = "https://www.icourse163.org"
OUT_DIR = Path(__file__).resolve().parents[1] / "logs"
OUT_DIR.mkdir(parents=True, exist_ok=True)


def rpc(session: requests.Session, csrf: str, endpoint: str, data, referer: str = BASE):
    url = f"{BASE}{endpoint}?csrfKey={csrf}"
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8",
        "Origin": BASE,
        "Referer": referer,
        "Edu-Script-Token": csrf,
    }
    r = session.post(url, data=data, headers=headers, timeout=20)
    return r.status_code, r.text


def main():
    s = requests.Session()
    s.headers["User-Agent"] = "Mozilla/5.0"
    home = s.get(BASE, timeout=20)
    csrf = s.cookies.get("NTESSTUDYSI") or s.cookies.get("EDUWEBDEVICE") or ""

    report = {
        "time": int(time.time()),
        "home_status": home.status_code,
        "csrf_present": bool(csrf),
        "probes": []
    }

    probes = [
        (
            "/web/j/channelBean.listChannelCategoryDetail.rpc",
            "includeALLChannels=true&includeDefaultChannels=false&includeMyChannels=false",
            f"{BASE}/channel/2001.htm?cate=-1&subCate=-1",
            "channel_list",
        ),
        (
            "/web/j/mocSearchBean.searchCourseCardByChannelAndCategoryId.rpc",
            {"mocCourseQueryVo": "{categoryId:-1,categoryChannelId:2001,orderBy:0,stats:30,pageIndex:1,pageSize:20,shouldConcatData:true}"},
            f"{BASE}/channel/2001.htm?cate=-1&subCate=-1",
            "course_list",
        ),
        (
            "/web/j/mocCourseV2RpcBean.getCourseEvaluatePaginationByCourseIdOrTermId.rpc",
            {"courseId": "1003316002", "pageIndex": "1", "pageSize": "5", "orderBy": "3"},
            BASE,
            "course_comments",
        ),
    ]

    for ep, data, ref, tag in probes:
        try:
            code, text = rpc(s, csrf, ep, data, ref)
            j = json.loads(text)
            report["probes"].append({
                "tag": tag,
                "endpoint": ep,
                "http": code,
                "code": j.get("code"),
                "message": j.get("message", ""),
                "has_result": bool(j.get("result")),
            })
        except Exception as e:
            report["probes"].append({"tag": tag, "endpoint": ep, "error": str(e)})

    out = OUT_DIR / f"requests_probe_{int(time.time())}.json"
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(out)


if __name__ == "__main__":
    main()
