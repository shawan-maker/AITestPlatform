# 巧乐AI智能体测试平台 — 前端（ChocoTest AI Test Platform）

Vue 3 + Vite + Element Plus 单页应用（F1a：鉴权 + 全高侧栏 Shell）。

## 环境要求

- Node.js 18+
- 后端 FastAPI 运行于 `http://127.0.0.1:8000`

## 快速开始

```bash
# 后端（仓库根目录）
python deploy/scripts/db_manage.py upgrade
python main.py

# 前端
cd frontend
npm install
npm run dev
```

浏览器访问 http://localhost:5173

## 默认开发账号

后端首次启动会自动创建超级管理员（见 `service/user/bootstrap.py`）：

- 用户名：`admin`
- 密码：`123456`

## 环境变量

| 变量 | 说明 |
|------|------|
| `VITE_API_BASE_URL` | API 前缀，默认 `/api/v1` |

开发环境通过 Vite 代理将 `/api` 转发到后端，无需 CORS。

## 目录说明

见 [service/design/04-前端页面的技术架构设计.md](../service/design/04-前端页面的技术架构设计.md)

知识库「保存需求 / 保存接口」按钮与 API 解析列表展示规则见 [service/knowledge/README.md](../service/knowledge/README.md)。
