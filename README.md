# 拼多多客服网关 (PDD CS Gateway)

拼多多客服消息处理网关，支持自动回复、飞书通知、OpenClaw AI 集成。

## 功能特性

- ✅ 拼多多官方 API 对接（稳定合规）
- ✅ Webhook 消息推送接收
- ✅ 意图分类（订单查询、物流查询、商品咨询、售后、投诉）
- ✅ 自动回复（规则 + AI）
- ✅ 人工接管（关键词触发 + 飞书通知）
- ✅ OpenClaw Fleet 集成（多实例 AI 处理）
- ✅ 飞书消息通知

## 快速开始

### 1. 安装依赖

```bash
cd pdd-cs-gateway
pip install -r requirements.txt
```

### 2. 配置

复制配置模板：

```bash
cp .env.example .env
```

编辑 `.env` 填入实际配置：

```bash
# 拼多多开放平台
PDD_CLIENT_ID=your_client_id
PDD_CLIENT_SECRET=your_client_secret

# 飞书
FEISHU_APP_ID=your_feishu_app_id
FEISHU_APP_SECRET=your_feishu_app_secret
FEISHU_RECEIVE_ID=oc_xxx  # 接收通知的群ID

# OpenClaw Fleet（可选）
FLEET_URL=http://localhost:18789
```

### 3. 运行

```bash
# 开发模式
uvicorn app.main:app --reload

# 生产模式
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### 4. Docker 部署

```bash
docker-compose up -d
```

## API 接口

### Webhook 接收消息

```
POST /api/webhook/pdd/message
```

拼多多开放平台会推送客服消息到此接口。

### 健康检查

```
GET /health
```

### API 文档

启动后访问：http://localhost:8000/docs

## 配置说明

### 拼多多开放平台

1. 访问 https://open.pinduoduo.com
2. 注册账号并认证为"商家服务商"或"电商软件服务商"
3. 创建应用，获取 Client ID 和 Client Secret
4. 申请以下 API 权限：
   - `pdd.customer.service.message.send`
   - `pdd.customer.service.session.get`
   - `pdd.customer.service.history.get`
   - `pdd.order.info.get`
   - `pdd.logistics.tracking.get`
5. 配置 Webhook 回调地址

### 飞书机器人

1. 创建飞书自定义机器人或企业自建应用
2. 获取 App ID 和 App Secret
3. 配置消息接收权限

### OpenClaw Fleet

如需使用 AI 生成回复，需部署 OpenClaw Fleet 协调中心。

## 架构

```
拼多多商家后台
    │
    ▼
拼多多开放平台 API (Webhook)
    │
    ▼
┌─────────────────────────┐
│   pdd-cs-gateway        │
│                         │
│  ┌─────────────────┐    │
│  │ Webhook Handler │    │
│  └────────┬────────┘    │
│           │             │
│  ┌────────▼────────┐    │
│  │ Message Handler │    │
│  │ - 意图分类       │    │
│  │ - 自动回复       │    │
│  │ - 人工接管判断   │    │
│  └────────┬────────┘    │
│           │             │
│     ┌─────┴─────┐       │
│     │           │       │
│     ▼           ▼       │
│ OpenClaw    Feishu     │
│ (AI回复)   (通知)       │
└─────────────────────────┘
```

## 项目结构

```
pdd-cs-gateway/
├── app/
│   ├── main.py              # FastAPI 入口
│   ├── config.py            # 配置管理
│   ├── pdd/
│   │   ├── client.py        # 拼多多 API 客户端
│   │   ├── webhook.py       # Webhook 处理
│   │   └── message_handler.py  # 消息处理
│   ├── feishu/
│   │   └── bot.py           # 飞书通知
│   ├── openclaw/
│   │   └── client.py        # OpenClaw 客户端
│   └── models/
│       └── __init__.py      # 数据模型
├── tests/
├── config.yaml.example
├── .env.example
├── requirements.txt
├── Dockerfile
└── docker-compose.yml
```

## 开发

### 运行测试

```bash
pytest
```

### 代码风格

```bash
# 格式化
black app/

# 类型检查
mypy app/
```

## License

MIT