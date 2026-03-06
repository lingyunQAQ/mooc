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

### Updated (深挖登录链路)
- 新增 `scripts/mooc_auth_chain_deep.py`：
  - 主页点击登录
  - 定位 `reg.icourse163.org` 登录 iframe
  - 尝试填充手机号/密码并点击登录
  - 抓取鉴权链路关键请求（仅记录 POST 字段名，不记录字段值）

- 新增产物：
  - `logs/auth_chain_deep_1772811335.json`
  - `logs/auth_chain_deep_1772811335.png`

### Findings (本轮深挖结论)
- 登录页位于：`reg.icourse163.org/webzj/v1.0.1/pub/index_dl2_new.html`
- 已确认登录链路关键端点（均为 `encParams` 加密载荷）：
  - `POST /dl/zj/yd/ini`
  - `POST /dl/zj/mail/ini`
  - `POST /dl/dlzc/yd/ini`
  - `POST /zc/zj/yd/ini`
- 说明：登录核心参数经前端加密后提交（非明文字段），后续需要在前端 JS 中还原 `encParams` 生成逻辑。

### Updated (密码登录模式修正)
- 调整 `scripts/mooc_auth_chain_deep.py`：新增“密码登录/账号登录”模式切换尝试。
- 新增产物：
  - `logs/auth_chain_deep_1772813282.json`
  - `logs/auth_chain_deep_1772813282.png`

### Findings (密码登录)
- 已执行“密码登录模式切换”逻辑，但当前页面仍出现 `password input not visible/editable`。
- 说明密码输入框在可见性层面受动态组件或前端状态控制（可能需要先切 tab、触发验证码组件初始化、或等待特定脚本渲染完成）。
- 鉴权请求仍统一为 `encParams` 加密提交，端点不变。

### Updated (密码登录链路打通)
- 修复 `scripts/mooc_auth_chain_deep.py`：改为选择“可见输入框”填充，避免命中隐藏密码框。
- 新增产物：
  - `logs/auth_chain_deep_1772815550.json`
  - `logs/auth_chain_deep_1772815550.png`

### Findings (关键进展)
- 本轮已实现：`phone_filled=true`、`password_filled=true`、`login_clicked=true`。
- 说明“密码验证登录”页面交互链路已打通（可正确填充并点击提交）。
- 登录请求仍为加密载荷 `encParams`，关键端点稳定：
  - `/dl/zj/yd/ini`
  - `/dl/zj/mail/ini`
  - `/dl/dlzc/yd/ini`
  - `/zc/zj/yd/ini`

### Updated (encParams 深挖与提交抓包)
- 新增 `scripts/extract_encrypt_clues.py`：从抓取到的前端 JS 静态提取加密链路线索。
- 新增产物：
  - `logs/encrypt_clues_1772816366.json`
  - `logs/auth_submit_capture_1772816496.json`

### Findings (本轮)
- 已抓到登录提交阶段真实 XHR 请求（密码登录点击后）。
- 核心提交接口：
  - `POST /zc/zj/yd/ini`
  - `POST /dl/zj/mail/ini`
  - `POST /dl/zj/yd/ini`
  - `POST /dl/dlzc/yd/ini`
- POST 体均为 JSON：`{"encParams":"..."}`（hex 密文）
- 接口响应均为 `ret=201`（当前返回为进一步验证状态，非登录成功态）。
- 静态 JS 线索显示：
  - 存在 `_formatParams` + `_$aesEncrypt` + `str2b64` 流程
  - 载荷包含 `params/timestamp/nonce/version(v1)`
  - 提交前会调用 `getEncryptKey`，说明使用动态下发密钥。

### Updated (运行时 Hook 加密函数)
- 新增 `scripts/mooc_runtime_hook_encrypt.py`：
  - 在登录 iframe 内运行时 hook `MP.encrypt/MP.encrypt2/URSSM4.encrypt/RSA.encrypt`
  - 抓取加密函数调用特征（参数脱敏）
  - 关联 `encParams` 提交请求（仅长度/前缀）
- 新增产物：
  - `logs/runtime_hook_1772817186.json`
  - `logs/runtime_hook_1772817186.png`

### Findings (关键突破)
- 已确认 `encParams` 由 **URSSM4.encrypt** 生成（本轮捕获到调用记录）。
- 本轮捕获：
  - `URSSM4.encrypt` 返回字符串长度 `320`，前缀与提交 `encParams` 一致。
  - 第二参数为动态密钥（疑似来自 `getEncryptKey` 链路）。
- 结论：登录提交链路为 **SM4 加密载荷 + 动态密钥**，而非固定 RSA 明文提交。
- 当前接口返回仍为 `ret=201`，后续需处理验证码/风控环节才能拿到最终登录态。
