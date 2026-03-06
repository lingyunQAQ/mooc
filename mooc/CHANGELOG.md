# CHANGELOG

## 2026-03-06

### Added
- 新增 `scripts/mooc_requests_probe.py`：无浏览器接口探测（频道/课程/评论）
- 新增 `scripts/mooc_playwright_probe.py`：浏览器探测（首页、登录入口识别、网络请求抓取）
- 新增 `scripts/run_all.sh`：一键执行两类探测

### Notes
- 登录脚本默认**仅填充不提交**，避免触发风控或验证码失败
- 账号口令不写入仓库，运行时通过环境变量注入
