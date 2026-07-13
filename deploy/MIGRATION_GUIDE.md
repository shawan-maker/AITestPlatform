# AITestPlatform 服务器迁移指南

## 概览

本指南将现有开发环境的全量数据迁移到目标服务器。

**迁移内容：**
- MySQL 数据库（38 张表，~3000 条记录）
- 项目代码 + 配置
- 可选：RAG 知识库文件（`data/` 目录）

**预计耗时：** 15-30 分钟

---

## 方式一：Docker 部署（推荐）

### 前提条件

目标服务器需要：
- Docker 20.10+
- Docker Compose v2+
- 至少 4GB 内存、20GB 磁盘

### 步骤

#### 1. 本地打包

```bash
# 在本地开发机执行
cd D:/PyProject/AITestPlatform

# 如果还没有备份
PYTHONPATH=. python deploy/scripts/export_data.py --output deploy/backup_20260712.json

# 打包（代码 + 备份 + 配置）
bash deploy/scripts/pack_for_server.sh
```

输出：`deploy/aitestplatform_deploy_<日期>.tar.gz`

#### 2. 传输到服务器

```bash
scp deploy/aitestplatform_deploy_*.tar.gz user@your-server:/opt/
```

#### 3. 服务器端部署

```bash
ssh user@your-server

# 解压
cd /opt
tar xzf aitestplatform_deploy_*.tar.gz -C aitestplatform
cd aitestplatform

# 配置 .env
cp deploy/.env.server .env
vim .env
# 必须修改：
#   LLM_BINDING_API_KEY     — 大模型 API Key
#   EMBEDDING_BINDING_API_KEY — 向量模型 API Key
#   JWT_SECRET_KEY          — 运行: python -c "import secrets; print(secrets.token_hex(32))"
#   MYSQL_ROOT_PASSWORD     — Docker Compose 使用，默认 aitest2026

# 启动 Docker（MySQL + Redis + Backend + Frontend）
docker compose -f deploy/multi-container/docker-compose.yml up -d --build

# 等待 MySQL 就绪（约 30 秒）
docker compose -f deploy/multi-container/docker-compose.yml ps

# 将备份文件复制到 backend 容器
docker cp deploy/backup_*.json aitestplatform-backend:/app/deploy/

# 执行数据导入
docker exec -it aitestplatform-backend python deploy/scripts/migrate_to_server.py

# 验证
docker exec -it aitestplatform-backend python -c "
import asyncio
from tortoise import Tortoise
from service.core.settings import TORTOISE_ORM

async def check():
    await Tortoise.init(config=TORTOISE_ORM)
    conn = Tortoise.get_connection('default')
    _, rows = await conn.execute_query('SELECT COUNT(*) as cnt FROM user')
    print(f'Users: {rows[0][\"cnt\"]}')
    _, rows = await conn.execute_query('SELECT COUNT(*) as cnt FROM project')
    print(f'Projects: {rows[0][\"cnt\"]}')
    _, rows = await conn.execute_query('SELECT COUNT(*) as cnt FROM api_test_case')
    print(f'API Test Cases: {rows[0][\"cnt\"]}')
    await Tortoise.close_connections()

asyncio.run(check())
"
```

#### 4. 访问

```
http://your-server-ip        # 前端
http://your-server-ip:8000   # 后端 API (如暴露)
```

默认管理员：`admin / 123456`（如备份中已有 admin 用户，使用备份中的密码）

---

## 方式二：原生部署

### 前提条件

目标服务器需要：
- Python 3.10+
- Node.js 18+
- MySQL 8.0
- Redis 7（可选）

### 步骤

#### 1. 本地打包 + 传输（同方式一 步骤 1-2）

#### 2. 服务器端部署

```bash
cd /opt/aitestplatform

# Python 依赖
pip install -r requirements.txt

# .env 配置
cp .env.example .env
vim .env
# DATABASE_URL=mysql://root:your-password@127.0.0.1:3306/aiTestPlatform
# ... 其他同方式一

# 一键迁移（建库 + 建表 + 导数据 + 验证）
PYTHONPATH=. python deploy/scripts/migrate_to_server.py --backup deploy/backup_*.json

# 构建前端
cd frontend
npm install
npm run build
cd ..

# 启动后端
python main.py

# 或使用 systemd / supervisor 守护进程
```

---

## 方式三：仅迁移数据（已有代码环境）

如果目标服务器已经有代码，只需要导入数据：

```bash
# 复制备份文件到服务器
scp deploy/backup_20260712.json user@server:/opt/aitestplatform/deploy/

# 在服务器上
cd /opt/aitestplatform

# 方式 A：通过脚本
PYTHONPATH=. python deploy/scripts/import_data.py --input deploy/backup_20260712.json --on-conflict=skip

# 方式 B：通过迁移脚本（含验证）
PYTHONPATH=. python deploy/scripts/migrate_to_server.py --backup deploy/backup_20260712.json
```

---

## 迁移文件清单

| 文件 | 说明 |
|------|------|
| `deploy/backup_20260712.json` | 数据库全量备份（42 表，3031 行，20.5 MB） |
| `deploy/scripts/migrate_to_server.py` | 服务器端一键迁移脚本 |
| `deploy/scripts/pack_for_server.sh` | 本地打包脚本 |
| `deploy/scripts/export_data.py` | 数据导出脚本（可重新生成备份） |
| `deploy/scripts/import_data.py` | 数据导入脚本 |
| `deploy/scripts/init_deploy.py` | 数据库初始化脚本 |
| `deploy/scripts/db_manage.py` | Aerich 迁移管理工具 |
| `deploy/.env.server` | Docker 部署用 .env 模板 |
| `deploy/multi-container/docker-compose.yml` | Docker Compose 编排文件 |
| `.env.example` | 通用 .env 模板 |

## 数据库备份详情

**格式：** JSON（跨数据库兼容）

| 类别 | 表 | 行数 |
|------|---|------|
| 用户 | user | 18 |
| 项目 | project, project_member, project_module | 258 |
| 测试环境 | test_environment, configs, snapshots, db connections 等 | 315 |
| 知识库 | knowledge_workspace, document, versions | 105 |
| API 测试 | api_interface, base_case, test_case, dependencies 等 | 596 |
| 功能测试 | functional_case, test_point, catalog | 317 |
| 测试管理 | test_suite, test_task, relations | 78 |
| 测试执行 | suite_run, task_run, run_records 等 | 752 |
| AI 生成 | ai_generation_session, messages | 456 |
| **合计** | **42 表** | **3031 行** |

## 故障排查

### MySQL 连接失败
```
[FAIL] Cannot connect to MySQL
```
- 检查 MySQL 服务是否运行：`docker compose ps` 或 `systemctl status mysql`
- 检查 `.env` 中的 `DATABASE_URL` 是否正确
- Docker 部署中，`DATABASE_URL` 的 host 应为 `mysql`（容器名）

### 导入冲突
```
[WARN] api_test_case: Duplicate entry
```
- 使用 `--on-conflict=skip` 策略（默认）可安全跳过重复记录
- 如需覆盖，使用 `--on-conflict=update`

### Aerich 迁移报错
```bash
# 重新初始化
docker exec -it aitestplatform-backend aerich init-db
docker exec -it aitestplatform-backend aerich upgrade
```

### 前端白屏
```bash
# 重新构建
cd frontend && npm run build
# Docker:
docker compose -f deploy/multi-container/docker-compose.yml up -d --build frontend
```

---

## 重新生成备份

如需在迁移后重新生成最新备份：

```bash
# 本地开发环境
PYTHONPATH=. python deploy/scripts/export_data.py --output deploy/backup_latest.json

# Docker 环境
docker exec -it aitestplatform-backend python deploy/scripts/export_data.py --output /app/deploy/backup_latest.json
docker cp aitestplatform-backend:/app/deploy/backup_latest.json ./deploy/
```
