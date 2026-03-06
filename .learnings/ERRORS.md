# ERRORS

## [ERR-20260306-001] mooc_crawler_v2 fetch_courses_by_channel NoneType

**Logged**: 2026-03-06T12:40:00Z
**Priority**: medium
**Status**: resolved
**Area**: backend

### Summary
`searchCourseCardByChannelAndCategoryId` 的返回在部分频道上 `result=null`，导致 `NoneType.get` 异常。

### Error
```
AttributeError: 'NoneType' object has no attribute 'get'
```

### Context
- Command: `python mooc_crawler_v2.py`
- File: `mooc/mooc_crawler_v2.py`

### Suggested Fix
对 `data.get("result")` 做空值兜底：`result = data.get("result") or {}`。

### Resolution
- **Resolved**: 2026-03-06T12:41:00Z
- **Notes**: 已修改并继续执行。

---
