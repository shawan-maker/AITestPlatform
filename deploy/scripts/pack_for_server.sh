#!/usr/bin/env bash
# ============================================================================
# AITestPlatform 一键打包脚本
#
# 将代码 + 数据备份 + 部署配置打包为 tar.gz，用于传输到目标服务器。
#
# 用法: bash deploy/scripts/pack_for_server.sh
# 输出: deploy/aitestplatform_deploy_<date>.tar.gz
# ============================================================================
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
DATE=$(date +%Y%m%d_%H%M%S)
PACKAGE_NAME="aitestplatform_deploy_${DATE}"
OUTPUT="${ROOT}/deploy/${PACKAGE_NAME}.tar.gz"

echo "=========================================="
echo "  AITestPlatform Deployment Package"
echo "=========================================="
echo ""
echo "[1/4] Finding latest backup..."

# Find the most recent backup JSON
BACKUP=$(ls -t "${ROOT}"/deploy/backup_*.json 2>/dev/null | head -1 || true)
if [ -z "$BACKUP" ]; then
    BACKUP=$(ls -t "${ROOT}"/backup_*.json 2>/dev/null | head -1 || true)
fi

if [ -n "$BACKUP" ]; then
    echo "  Found: $(basename "$BACKUP") ($(du -h "$BACKUP" | cut -f1))"
else
    echo "  [WARN] No backup JSON found. Run export first:"
    echo "    PYTHONPATH=. python deploy/scripts/export_data.py --output deploy/backup_${DATE}.json"
    echo ""
    read -p "  Continue without backup? (y/N) " -n 1 -r
    echo
    [[ $REPLY =~ ^[Yy]$ ]] || exit 1
fi

echo ""
echo "[2/4] Creating deployment package..."

# Build the tar.gz, excluding unnecessary files
cd "$ROOT"
tar czf "$OUTPUT" \
    --exclude='.git' \
    --exclude='node_modules' \
    --exclude='__pycache__' \
    --exclude='*.pyc' \
    --exclude='.venv' \
    --exclude='venv' \
    --exclude='frontend/dist' \
    --exclude='data/rag' \
    --exclude='logs' \
    --exclude='.env' \
    --exclude='*.log' \
    --exclude='deploy/mysql-data' \
    --exclude='deploy/redis-data' \
    . \
    2>/dev/null

# Include .env.example (not .env with secrets)
echo "  .env excluded (contains secrets) — .env.example included"

# If backup exists, append it to the archive
if [ -n "$BACKUP" ]; then
    tar rzf "$OUTPUT" -C "$(dirname "$BACKUP")" "$(basename "$BACKUP")" 2>/dev/null || {
        # tar append may not work with gz, copy and re-archive
        cp "$BACKUP" "${ROOT}/deploy/$(basename "$BACKUP")"
    }
fi

SIZE=$(du -h "$OUTPUT" | cut -f1)

echo ""
echo "[3/4] Creating server-side .env template..."

# Create a server-specific .env template
cat > "${ROOT}/deploy/.env.server" << 'ENVEOF'
# ============================================================================
# AITestPlatform Server .env
# Copy to project root: cp deploy/.env.server .env
# Edit the values marked with [CHANGE ME]
# ============================================================================

# RAG
HOST=0.0.0.0
PORT=9621
WEBUI_TITLE='AITestPlatform RAG'
WEBUI_DESCRIPTION="RAG"
PARSE_METHOD=ocr
TIKTOKEN_CACHE_DIR=./data/rag/temp/tiktoken
SUMMARY_LANGUAGE=Chainese
ENABLE_LLM_CACHE_FOR_EXTRACT=true
MAX_ASYNC=4
MAX_PARALLEL_INSERT=2

# LLM [CHANGE ME]
LLM_BINDING=openai
LLM_MODEL=deepseek-ai/DeepSeek-V3.2
LLM_BINDING_HOST=https://api.siliconflow.cn/v1
LLM_BINDING_API_KEY=your-llm-api-key-here

# Embedding [CHANGE ME]
EMBEDDING_BINDING=openai
EMBEDDING_MODEL=Qwen/Qwen3-Embedding-8B
EMBEDDING_DIM=4096
EMBEDDING_BINDING_HOST=https://api.siliconflow.cn/v1
EMBEDDING_BINDING_API_KEY=your-embedding-api-key-here

# Rerank [optional]
ENABLE_RERANK=True
MIN_RERANK_SCORE=0.6
RERANK_MODEL=Qwen/Qwen3-Reranker-8B
RERANK_BINDING_HOST=https://api.siliconflow.cn/v1/rerank
RERANK_BINDING_API_KEY=your-rerank-api-key-here

# Visual [optional]
VISUAL_BINDING=openai
VISUAL_MODEL=Qwen/Qwen3.5-9B
VISUAL_BINDING_HOST=https://api.siliconflow.cn/v1/chat/completions
VISUAL_BINDING_API_KEY=your-visual-api-key-here

# RAG Server
RAG_SERVER_URL=http://127.0.0.1:9621
RAG_API_KEY=your-rag-api-key-here

# Database (Docker deployment — uses internal mysql hostname)
DATABASE_URL=mysql://root:aitest2026@mysql:3306/aiTestPlatform

# JWT [CHANGE ME — generate with: python -c "import secrets; print(secrets.token_hex(32))"]
JWT_SECRET_KEY=please-generate-a-random-secret-key
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=120
REFRESH_TOKEN_EXPIRE_DAYS=7

# Redis (Docker deployment)
REDIS_URL=redis://redis:6379/0

# Server
BACKEND_HOST=0.0.0.0
BACKEND_PORT=8000
CORS_ORIGINS=
LOG_FILE=
ENVEOF

echo "  deploy/.env.server created"

echo ""
echo "[4/4] Package ready!"
echo ""
echo "=========================================="
echo "  Output: $OUTPUT"
echo "  Size:   $SIZE"
echo "=========================================="
echo ""
echo "Transfer to server:"
echo "  scp $OUTPUT user@server:/opt/"
echo ""
echo "On server:"
echo "  cd /opt && tar xzf $(basename "$OUTPUT")"
echo "  cp deploy/.env.server .env && vim .env"
echo "  PYTHONPATH=. python deploy/scripts/migrate_to_server.py"
echo ""
