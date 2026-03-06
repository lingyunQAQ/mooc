# 更新流程（每次都可复用）

1. 在本地执行探测：
```bash
cd /root/.openclaw/workspace/mooc
source /root/.openclaw/workspace/.venv/bin/activate
MOOC_PHONE="<手机号>" MOOC_PASSWORD="<密码>" ./scripts/run_all.sh
```

2. 查看产物：
- `logs/requests_probe_*.json`
- `logs/playwright_probe_*.json`
- `logs/playwright_probe_*.png`

3. 更新日志：
- 把本次发现写入 `CHANGELOG.md`

4. 提交并推送：
```bash
cd /root/.openclaw/workspace
git add mooc/
git commit -m "chore(mooc): update probes and logs"
git push
```

5. 如 push 失败：
- 检查代理（7890）
- 检查 GitHub PAT 是否具备 repo 写权限
