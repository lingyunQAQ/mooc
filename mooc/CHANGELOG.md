# CHANGELOG

## 2026-03-06

### Added
- 新增 `scripts/mooc_requests_probe.py`：无浏览器接口探测（频道/课程/评论）
- 新增 `scripts/mooc_playwright_probe.py`：浏览器探测（首页、登录入口识别、网络请求抓取）
- 新增 `scripts/run_all.sh`：一键执行两类探测

### Notes
- 登录脚本默认**仅填充不提交**，避免触发风控或验证码失败
- 账号口令不写入仓库，运行时通过环境变量注入

### Updated (抓包进展)
- 新增 `scripts/mooc_packet_capture.py`：主页点击“登录”后自动抓取登录相关网络请求
- 新增产物：
  - `logs/packet_capture_1772810964.json`
  - `logs/packet_capture_1772810964.har`
  - `logs/packet_capture_1772810964.png`

### Findings (本轮)
- 登录链路入口位于 `reg.icourse163.org/webzj/.../index_dl2_new.html`
- 页面会加载 `CampusLogin` 相关脚本：
  - `https://mc.stu.126.net/rc/main/assets/CampusLogin...js`
  - `https://mc.stu.126.net/rc/main/assets/campus-login-entry...js`
- 登录相关参数中出现 `product=imooc`、`pkid=cjJVGQM`、`ursDeviceId` 等关键字段
- 下一步将基于 HAR 继续定位真正的鉴权请求（账号密码提交/验证码/登录态 cookie）
