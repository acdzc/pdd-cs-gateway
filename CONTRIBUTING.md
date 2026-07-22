# 贡献指南

欢迎改进 PDD CS Gateway。涉及拼多多开放平台、飞书或 OpenClaw 的变更，请先说明真实场景和接口边界，避免把生产凭据或业务数据带入仓库。

## 开发环境

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pytest
```

Windows PowerShell 激活命令为 `.\.venv\Scripts\Activate.ps1`。

## 提交要求

- 一个 PR 只处理一个主题，并说明用户影响。
- 新增接口或意图分类时补充测试。
- 外部 API 调用应包含超时、错误处理和脱敏日志。
- 配置项同步更新 `.env.example` 或 `config.yaml.example`。
- 不得提交真实商家 ID、订单、Cookie、Token、App Secret 或聊天记录。

提交前至少运行 `pytest`，并在 PR 中记录验证结果和未覆盖风险。
