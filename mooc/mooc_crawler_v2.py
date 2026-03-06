#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
中国大学 MOOC 数据采集（改进版）
- 自动获取会话 Cookie / csrfKey（不再硬编码）
- 采集频道、课程、评论
- 额外探测“课程资源/测试题”相关接口可达性（研究用途）
"""

from __future__ import annotations

import csv
import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

import requests

BASE = "https://www.icourse163.org"
OUT_DIR = Path(__file__).resolve().parent / "output_v2"
OUT_DIR.mkdir(parents=True, exist_ok=True)


@dataclass
class MoocSession:
    session: requests.Session
    csrf_key: str

    @classmethod
    def build(cls) -> "MoocSession":
        s = requests.Session()
        s.headers.update(
            {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0.0.0 Safari/537.36"
                ),
                "Accept": "*/*",
                "Accept-Language": "zh-CN,zh;q=0.9",
            }
        )
        r = s.get(BASE, timeout=20)
        r.raise_for_status()
        csrf = s.cookies.get("NTESSTUDYSI") or s.cookies.get("EDUWEBDEVICE")
        if not csrf:
            raise RuntimeError("未获取到 csrfKey（NTESSTUDYSI/EDUWEBDEVICE）")
        return cls(session=s, csrf_key=csrf)

    def rpc_post(self, endpoint: str, data: Dict[str, str] | str, referer: str = BASE) -> Dict:
        url = f"{BASE}{endpoint}?csrfKey={self.csrf_key}"
        headers = {
            "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8",
            "Origin": BASE,
            "Referer": referer,
            "Edu-Script-Token": self.csrf_key,
        }
        resp = self.session.post(url, data=data, headers=headers, timeout=25)
        resp.raise_for_status()
        return resp.json()


def save_csv(path: Path, headers: List[str], rows: Iterable[Dict]):
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=headers)
        w.writeheader()
        for row in rows:
            w.writerow({k: row.get(k, "") for k in headers})


def fetch_channels(ms: MoocSession) -> List[Dict]:
    payload = "includeALLChannels=true&includeDefaultChannels=false&includeMyChannels=false"
    data = ms.rpc_post(
        "/web/j/channelBean.listChannelCategoryDetail.rpc",
        payload,
        referer=f"{BASE}/channel/2001.htm?cate=-1&subCate=-1",
    )
    if data.get("code") != 0:
        raise RuntimeError(f"获取频道失败: {data}")

    channels: List[Dict] = []
    for cate in data.get("result", {}).get("channelCategoryDetails", []):
        cate_name = cate.get("categoryName", "")
        for ch in cate.get("channels", []):
            channels.append(
                {
                    "categoryName": cate_name,
                    "id": ch.get("id"),
                    "name": ch.get("name"),
                    "shortDesc": ch.get("shortDesc"),
                    "weight": ch.get("weight"),
                    "defaultChannel": ch.get("defaultChannel"),
                    "charge": ch.get("charge"),
                }
            )
    return channels


def fetch_courses_by_channel(ms: MoocSession, channel_id: int, max_pages: int = 3) -> List[Dict]:
    all_rows: List[Dict] = []
    for page in range(1, max_pages + 1):
        query = (
            "{"
            f"categoryId:-1,categoryChannelId:{channel_id},"
            f"orderBy:0,stats:30,pageIndex:{page},pageSize:20,shouldConcatData:true"
            "}"
        )
        data = ms.rpc_post(
            "/web/j/mocSearchBean.searchCourseCardByChannelAndCategoryId.rpc",
            {"mocCourseQueryVo": query},
            referer=f"{BASE}/channel/{channel_id}.htm?cate=-1&subCate=-1",
        )
        if data.get("code") != 0:
            break
        result = data.get("result") or {}
        items = result.get("list", [])
        if not items:
            break

        for item in items:
            base = item.get("mocCourseBaseCardVo") or {}
            all_rows.append(
                {
                    "id": base.get("id"),
                    "name": base.get("name"),
                    "teacherName": base.get("teacherName"),
                    "schoolName": base.get("schoolName"),
                    "enrollCount": base.get("enrollCount"),
                    "startTime": base.get("startTime"),
                    "endTime": base.get("endTime"),
                    "currentTermId": base.get("currentTermId"),
                    "type": item.get("type"),
                    "channelId": channel_id,
                }
            )

        total_pages = result.get("query", {}).get("totlePageCount", page)
        if page >= total_pages:
            break
        time.sleep(0.2)

    return all_rows


def fetch_comments(ms: MoocSession, course_id: str, page_limit: int = 2) -> List[Dict]:
    rows: List[Dict] = []
    for page in range(1, page_limit + 1):
        data = ms.rpc_post(
            "/web/j/mocCourseV2RpcBean.getCourseEvaluatePaginationByCourseIdOrTermId.rpc",
            {
                "courseId": str(course_id),
                "pageIndex": str(page),
                "pageSize": "20",
                "orderBy": "3",
            },
            referer=BASE,
        )
        if data.get("code") != 0:
            break
        lst = data.get("result", {}).get("list", [])
        if not lst:
            break

        for item in lst:
            rows.append(
                {
                    "id": item.get("id"),
                    "gmtModified": item.get("gmtModified"),
                    "commentorId": item.get("commentorId"),
                    "userNickName": item.get("userNickName"),
                    "content": (item.get("content") or "").replace("\n", " ").replace("\r", " "),
                    "mark": item.get("mark"),
                    "schoolName": item.get("schoolName"),
                    "termId": item.get("termId"),
                    "status": item.get("status"),
                    "courseId": course_id,
                }
            )

        total_pages = data.get("result", {}).get("query", {}).get("totlePageCount", page)
        if page >= total_pages:
            break
        time.sleep(0.2)

    return rows


def probe_resource_quiz_endpoints(ms: MoocSession, course_id: str, term_id: Optional[str]) -> List[Dict]:
    """探测课程资源/测试题相关接口可达性。"""
    candidates: List[Tuple[str, Dict[str, str], str]] = [
        # endpoint, payload, tag
        ("/web/j/courseBean.getMocTermDto.rpc", {"courseId": str(course_id), "privileged": "false", "version": "0"}, "course_meta"),
        ("/web/j/courseBean.getMocTermDto.rpc", {"termId": str(term_id or "")}, "course_meta_by_term"),
        ("/web/j/mocCourseV2RpcBean.getCourseEvaluatePaginationByCourseIdOrTermId.rpc", {"courseId": str(course_id), "pageIndex": "1", "pageSize": "5", "orderBy": "3"}, "comments"),
        ("/web/j/mocCourseV2RpcBean.getCourseEvaluatePaginationByCourseIdOrTermId.rpc", {"termId": str(term_id or ""), "pageIndex": "1", "pageSize": "5", "orderBy": "3"}, "comments_by_term"),
        # 以下为资源/测验方向的候选（不同课程/权限下可能关闭）
        ("/web/j/courseBean.getLastLearnedMocTermDto.rpc", {"courseId": str(course_id)}, "last_learned_term"),
        ("/web/j/mocLessonUnitLearnBean.getLessonUnitLearnVo.rpc", {"termId": str(term_id or "")}, "lesson_units"),
        ("/web/j/mocQuizRpcBean.getQuizPaperDtoByTestId.rpc", {"termId": str(term_id or "")}, "quiz"),
        ("/web/j/mocExamRpcBean.getExamPaperDtoByExamId.rpc", {"termId": str(term_id or "")}, "exam"),
    ]

    results = []
    for endpoint, payload, tag in candidates:
        try:
            r = ms.rpc_post(endpoint, payload, referer=BASE)
            results.append(
                {
                    "tag": tag,
                    "endpoint": endpoint,
                    "payload": payload,
                    "code": r.get("code"),
                    "message": r.get("message", ""),
                    "hasResult": bool(r.get("result")),
                }
            )
        except Exception as e:
            results.append(
                {
                    "tag": tag,
                    "endpoint": endpoint,
                    "payload": payload,
                    "error": str(e),
                }
            )
        time.sleep(0.15)

    return results


def main():
    print("[1/5] 初始化会话...")
    ms = MoocSession.build()

    print("[2/5] 拉取频道...")
    channels = fetch_channels(ms)
    save_csv(
        OUT_DIR / "channel_data_v2.csv",
        ["categoryName", "id", "name", "shortDesc", "weight", "defaultChannel", "charge"],
        channels,
    )
    print(f"  - 频道数: {len(channels)}")

    print("[3/5] 拉取课程（每个频道最多前3页）...")
    all_courses: Dict[str, Dict] = {}
    for ch in channels:
        cid = ch["id"]
        if not cid:
            continue
        courses = fetch_courses_by_channel(ms, int(cid), max_pages=3)
        for c in courses:
            all_courses[str(c["id"])] = c

    courses_list = list(all_courses.values())
    save_csv(
        OUT_DIR / "course_data_v2.csv",
        [
            "id",
            "name",
            "teacherName",
            "schoolName",
            "enrollCount",
            "startTime",
            "endTime",
            "currentTermId",
            "type",
            "channelId",
        ],
        courses_list,
    )
    print(f"  - 去重后课程数: {len(courses_list)}")

    print("[4/5] 拉取评论（示例：前30门课，每课最多2页）...")
    comment_rows: List[Dict] = []
    for c in courses_list[:30]:
        comment_rows.extend(fetch_comments(ms, str(c["id"]), page_limit=2))
    save_csv(
        OUT_DIR / "course_comment_data_v2_sample.csv",
        ["id", "gmtModified", "commentorId", "userNickName", "content", "mark", "schoolName", "termId", "status", "courseId"],
        comment_rows,
    )
    print(f"  - 评论样本条数: {len(comment_rows)}")

    print("[5/5] 探测课程资源/测试题接口可达性（抽样10门）...")
    probes = []
    for c in courses_list[:10]:
        probes.append(
            {
                "courseId": c.get("id"),
                "termId": c.get("currentTermId"),
                "results": probe_resource_quiz_endpoints(ms, str(c.get("id")), str(c.get("currentTermId") or "")),
            }
        )
    with (OUT_DIR / "resource_quiz_probe_report.json").open("w", encoding="utf-8") as f:
        json.dump(probes, f, ensure_ascii=False, indent=2)

    print("完成。输出目录:", OUT_DIR)


if __name__ == "__main__":
    main()
