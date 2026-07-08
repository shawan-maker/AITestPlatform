"""
全新部署初始化脚本。

用法（在项目根目录执行）：
    python deploy/scripts/init_deploy.py              # 正式执行
    python deploy/scripts/init_deploy.py --dry-run     # 仅检查，不执行

流程：
    1. 检查 .env 配置
    2. 检查数据库连接
    3. 创建数据库（如不存在）
    4. 运行 Aerich init-db（首次建表）
    5. 运行 Aerich upgrade（应用所有迁移）
    6. 验证：查询各表记录数
"""
from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[2]


def parse_db_url(url: str) -> dict:
    """从 DATABASE_URL 解析 MySQL 连接参数"""
    parsed = urlparse(url)
    return {
        "host": parsed.hostname or "127.0.0.1",
        "port": parsed.port or 3306,
        "user": parsed.username or "root",
        "password": parsed.password or "",
        "database": parsed.path.lstrip("/"),
    }


def run_cmd(cmd: list[str], check: bool = True, **kwargs) -> subprocess.CompletedProcess:
    """执行命令并打印结果"""
    print(f"  >>> {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=ROOT, **kwargs)
    if result.stdout.strip():
        print(f"  {result.stdout.strip()}")
    if result.returncode != 0 and result.stderr.strip():
        print(f"  [stderr] {result.stderr.strip()}")
    if check and result.returncode != 0:
        print(f"  [FAIL] 命令失败 (exit code {result.returncode})")
        sys.exit(1)
    return result


def main():
    dry_run = "--dry-run" in sys.argv
    print("=" * 60)
    print("AITestPlatform 部署初始化")
    print("=" * 60)

    # --- Step 1: 检查 .env ---
    print("\n[1/6] 检查 .env 配置...")
    env_file = ROOT / ".env"
    if not env_file.exists():
        print("  [FAIL] .env 文件不存在，请从 .env.example 复制并填写配置")
        sys.exit(1)

    # 读取关键配置
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")

    db_url = os.getenv("DATABASE_URL", "")
    jwt_key = os.getenv("JWT_SECRET_KEY", "")

    if not db_url:
        print("  [FAIL] DATABASE_URL 未配置")
        sys.exit(1)
    if jwt_key in ("", "change-me-in-production", "please-generate-a-random-secret-key"):
        print("  [WARN]  JWT_SECRET_KEY 使用了默认值，请在 .env 中设置安全密钥")

    db = parse_db_url(db_url)
    print(f"  数据库: {db['host']}:{db['port']}/{db['database']}")
    print(f"  用户: {db['user']}")
    print("  [OK] .env 配置检查通过")

    if dry_run:
        print("\n[dry-run] 后续步骤：")
        print("  [2] 检查数据库连接")
        print("  [3] 创建数据库（如不存在）")
        print("  [4] Aerich init-db")
        print("  [5] Aerich upgrade")
        print("  [6] 验证表结构")
        return

    # --- Step 2: 检查数据库连接 ---
    print("\n[2/6] 检查数据库连接...")
    mysql_cmd = ["mysql", "-h", db["host"], "-P", str(db["port"]),
                 "-u", db["user"], f"-p{db['password']}", "-e", "SELECT 1"]
    result = run_cmd(mysql_cmd, check=False)
    if result.returncode != 0:
        print("  [FAIL] 无法连接 MySQL，请检查网络和认证信息")
        sys.exit(1)
    print("  [OK] MySQL 连接成功")

    # --- Step 3: 创建数据库（如不存在）---
    print("\n[3/6] 创建数据库（如不存在）...")
    create_sql = f"CREATE DATABASE IF NOT EXISTS `{db['database']}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
    run_cmd(["mysql", "-h", db["host"], "-P", str(db["port"]),
             "-u", db["user"], f"-p{db['password']}", "-e", create_sql])
    print(f"  [OK] 数据库 {db['database']} 就绪")

    # --- Step 4: Aerich init-db ---
    print("\n[4/6] Aerich init-db...")
    result = run_cmd(["aerich", "init-db"], check=False)
    if result.returncode != 0:
        print("  [WARN]  init-db 可能已执行过，继续下一步...")

    # --- Step 5: Aerich upgrade ---
    print("\n[5/6] Aerich upgrade...")
    run_cmd(["aerich", "upgrade"])
    print("  [OK] 数据库迁移已应用")

    # --- Step 6: 验证 ---
    print("\n[6/6] 验证表结构...")
    verify_sql = (
        "SELECT TABLE_NAME, TABLE_ROWS FROM information_schema.TABLES "
        f"WHERE TABLE_SCHEMA='{db['database']}' ORDER BY TABLE_NAME;"
    )
    run_cmd(["mysql", "-h", db["host"], "-P", str(db["port"]),
             "-u", db["user"], f"-p{db['password']}", "-e", verify_sql])

    print("\n" + "=" * 60)
    print("[OK] 部署初始化完成！")
    print()
    print("后续步骤：")
    print("  1. 启动后端: python main.py")
    print("  2. 后端会自动创建默认管理员 (admin / 123456)")
    print("  3. 如从旧实例迁移数据: python deploy/scripts/import_data.py --input backup.sql")
    print("  4. 构建前端: cd frontend && npm run build")
    print("=" * 60)


if __name__ == "__main__":
    main()
