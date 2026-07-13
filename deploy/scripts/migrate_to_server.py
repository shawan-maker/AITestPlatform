"""
服务器迁移一键脚本 — 在目标服务器上执行完整部署流程。

用法（在目标服务器项目根目录执行）：
    python deploy/scripts/migrate_to_server.py --backup backup_20260712.json
    python deploy/scripts/migrate_to_server.py --backup backup_20260712.json --dry-run

流程：
    1. 检查环境（Python/Node/Docker/MySQL）
    2. 检查 .env 配置（DATABASE_URL, JWT_SECRET_KEY, LLM 等）
    3. 连接目标 MySQL 并创建数据库
    4. Aerich 初始化 + 应用所有迁移（建表）
    5. 导入备份数据（JSON 格式，skip 冲突策略）
    6. 验证数据完整性（对比源库表/行数）
    7. 构建前端（可选）
    8. 启动服务（可选）

前置条件：
    - 已将项目代码上传到服务器（git clone 或 rsync）
    - 已将 backup_*.json 文件放到项目根目录或 deploy/ 目录下
    - MySQL 8.0 已在目标服务器运行（或可通过 docker-compose 启动）
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[2]


def parse_db_url(url: str) -> dict:
    """Parse DATABASE_URL into MySQL connection parameters."""
    parsed = urlparse(url)
    return {
        "host": parsed.hostname or "127.0.0.1",
        "port": parsed.port or 3306,
        "user": parsed.username or "root",
        "password": parsed.password or "",
        "database": parsed.path.lstrip("/"),
    }


def run_cmd(cmd: list[str], check: bool = True, **kwargs) -> subprocess.CompletedProcess:
    """Execute a command, print output, and optionally abort on failure."""
    print(f"  >>> {' '.join(cmd[:6])}{'...' if len(cmd) > 6 else ''}")
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=ROOT, **kwargs)
    if result.stdout.strip():
        for line in result.stdout.strip().split("\n")[:20]:
            print(f"    {line}")
    if result.returncode != 0 and result.stderr.strip():
        for line in result.stderr.strip().split("\n")[:10]:
            print(f"    [stderr] {line}")
    if check and result.returncode != 0:
        print(f"  [FAIL] Command exited with code {result.returncode}")
        sys.exit(1)
    return result


def check_tool(name: str, version_flag: str = "--version") -> bool:
    """Check if a CLI tool is available."""
    try:
        result = subprocess.run(
            [name, version_flag], capture_output=True, text=True, timeout=10
        )
        ver = (result.stdout or result.stderr).strip().split("\n")[0]
        print(f"  {name}: {ver}")
        return True
    except (FileNotFoundError, subprocess.TimeoutExpired):
        print(f"  {name}: NOT FOUND")
        return False


def main():
    dry_run = "--dry-run" in sys.argv

    # Find backup file
    backup_file = None
    for i, arg in enumerate(sys.argv):
        if arg == "--backup" and i + 1 < len(sys.argv):
            backup_file = sys.argv[i + 1]
            break

    if not backup_file:
        # Auto-detect backup file in deploy/ or root
        candidates = sorted(ROOT.glob("deploy/backup_*.json"), reverse=True)
        if not candidates:
            candidates = sorted(ROOT.glob("backup_*.json"), reverse=True)
        if candidates:
            backup_file = str(candidates[0].relative_to(ROOT))
            print(f"[INFO] Auto-detected backup: {backup_file}")
        else:
            print(__doc__)
            print("[FAIL] No backup file found. Use --backup <path> to specify.")
            sys.exit(1)

    backup_path = Path(backup_file) if os.path.isabs(backup_file) else ROOT / backup_file
    if not backup_path.exists():
        print(f"[FAIL] Backup file not found: {backup_path}")
        sys.exit(1)

    # Validate backup
    print(f"[INFO] Backup file: {backup_path}")
    with open(backup_path, "r", encoding="utf-8") as f:
        backup_data = json.load(f)
    total_tables = len(backup_data)
    total_rows = sum(len(v) for v in backup_data.values())
    print(f"  Tables: {total_tables}, Total rows: {total_rows}")

    print()
    print("=" * 64)
    print("  AITestPlatform Server Migration")
    print("=" * 64)

    # ================================================================
    # Step 1: Check environment
    # ================================================================
    print("\n[1/7] Checking environment...")
    tools_ok = True
    for tool in ["python", "node", "mysql", "docker"]:
        if not check_tool(tool):
            tools_ok = False

    if not tools_ok:
        print("  [WARN] Some tools are missing. You can still proceed if:")
        print("    - 'mysql' CLI not needed if using Docker MySQL")
        print("    - 'node' not needed if using Docker frontend")
        print("    - 'docker' not needed if deploying natively")

    # Check Python packages
    try:
        import tortoise  # noqa: F401
        import aerich  # noqa: F401
        from dotenv import load_dotenv  # noqa: F401
        print("  Python deps: tortoise, aerich, python-dotenv OK")
    except ImportError as e:
        print(f"  [FAIL] Missing Python package: {e}")
        print("  Run: pip install -r requirements.txt")
        sys.exit(1)

    # ================================================================
    # Step 2: Check .env
    # ================================================================
    print("\n[2/7] Checking .env configuration...")
    env_file = ROOT / ".env"
    if not env_file.exists():
        print("  [FAIL] .env file not found.")
        print("  Run: cp .env.example .env && edit .env")
        sys.exit(1)

    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")

    db_url = os.getenv("DATABASE_URL", "")
    jwt_key = os.getenv("JWT_SECRET_KEY", "")
    llm_key = os.getenv("LLM_BINDING_API_KEY", "")

    if not db_url:
        print("  [FAIL] DATABASE_URL not set in .env")
        sys.exit(1)

    db = parse_db_url(db_url)
    print(f"  Database: {db['host']}:{db['port']}/{db['database']}")
    print(f"  User: {db['user']}")

    if jwt_key in ("", "change-me-in-production", "please-generate-a-random-secret-key"):
        print("  [WARN] JWT_SECRET_KEY uses default value — generate one:")
        print('    python -c "import secrets; print(secrets.token_hex(32))"')

    if llm_key in ("", "your-llm-api-key-here"):
        print("  [WARN] LLM_BINDING_API_KEY not configured — AI features will not work")

    if dry_run:
        print("\n[dry-run] Remaining steps:")
        print("  [3] Connect to MySQL and create database")
        print("  [4] Aerich init-db + upgrade (create tables)")
        print("  [5] Import backup data")
        print("  [6] Verify data integrity")
        print("  [7] Build frontend + start services")
        return

    # ================================================================
    # Step 3: Connect MySQL + create database
    # ================================================================
    print("\n[3/7] Connecting to MySQL and creating database...")
    mysql_base = [
        "mysql", "-h", db["host"], "-P", str(db["port"]),
        "-u", db["user"], f"-p{db['password']}",
    ]

    result = run_cmd(mysql_base + ["-e", "SELECT 1"], check=False)
    if result.returncode != 0:
        print("  [FAIL] Cannot connect to MySQL.")
        print("  Check: host, port, username, password in DATABASE_URL")
        sys.exit(1)
    print("  [OK] MySQL connection successful")

    create_sql = (
        f"CREATE DATABASE IF NOT EXISTS `{db['database']}` "
        "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
    )
    run_cmd(mysql_base + ["-e", create_sql])
    print(f"  [OK] Database '{db['database']}' ready")

    # ================================================================
    # Step 4: Aerich init + upgrade (create all tables)
    # ================================================================
    print("\n[4/7] Initializing database schema (Aerich)...")

    result = run_cmd(["aerich", "init-db"], check=False)
    if result.returncode != 0:
        print("  [WARN] init-db may have been run already, continuing...")

    run_cmd(["aerich", "upgrade"])
    print("  [OK] All migrations applied")

    # Verify tables exist
    verify_sql = (
        "SELECT TABLE_NAME, TABLE_ROWS "
        "FROM information_schema.TABLES "
        f"WHERE TABLE_SCHEMA='{db['database']}' "
        "ORDER BY TABLE_NAME;"
    )
    result = run_cmd(mysql_base + ["-e", verify_sql], check=False)
    if result.returncode == 0:
        lines = result.stdout.strip().split("\n")
        table_count = len(lines) - 1 if len(lines) > 1 else 0  # minus header
        print(f"  [OK] {table_count} tables created in target database")

    # ================================================================
    # Step 5: Import backup data
    # ================================================================
    print(f"\n[5/7] Importing backup data ({total_rows} rows from {total_tables} tables)...")

    # Use import_data.py for proper FK-ordered import
    import_script = ROOT / "deploy" / "scripts" / "import_data.py"
    if not import_script.exists():
        print("  [FAIL] deploy/scripts/import_data.py not found")
        sys.exit(1)

    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT)

    result = run_cmd(
        [
            sys.executable,
            str(import_script),
            "--input", str(backup_path),
            "--on-conflict=skip",
        ],
        check=False,
        env=env,
    )
    if result.returncode != 0:
        print("  [FAIL] Data import failed. Check errors above.")
        print("  You can retry manually:")
        print(f"    PYTHONPATH=. python deploy/scripts/import_data.py --input {backup_file} --on-conflict=skip")
        sys.exit(1)

    print("  [OK] Data import completed")

    # ================================================================
    # Step 6: Verify data integrity
    # ================================================================
    print("\n[6/7] Verifying data integrity...")

    # Compare source backup row counts with target database
    verify_sql_parts = []
    for table_name, rows in backup_data.items():
        if rows:
            verify_sql_parts.append(
                f"SELECT '{table_name}' AS tbl, COUNT(*) AS cnt FROM `{table_name}`"
            )

    if verify_sql_parts:
        verify_query = " UNION ALL ".join(verify_sql_parts) + " ORDER BY tbl;"
        result = run_cmd(mysql_base + ["-e", verify_query], check=False)

        if result.returncode == 0 and result.stdout.strip():
            print("\n  Source vs Target comparison:")
            print(f"  {'Table':<35} {'Source':>8} {'Target':>8} {'Status':>8}")
            print(f"  {'-'*35} {'-'*8} {'-'*8} {'-'*8}")

            # Parse target counts from MySQL output
            target_counts = {}
            for line in result.stdout.strip().split("\n")[1:]:
                parts = line.split()
                if len(parts) >= 2:
                    target_counts[parts[0]] = int(parts[1])

            matched = 0
            mismatched = 0
            for table_name, rows in sorted(backup_data.items()):
                source_count = len(rows)
                target_count = target_counts.get(table_name, 0)
                status = "OK" if target_count >= source_count else "MISS"
                if source_count > 0:
                    if target_count >= source_count:
                        matched += 1
                    else:
                        mismatched += 1
                    print(f"  {table_name:<35} {source_count:>8} {target_count:>8} {status:>8}")

            print(f"\n  Summary: {matched} tables matched, {mismatched} tables with fewer rows")
            if mismatched == 0:
                print("  [OK] All data imported successfully")
            else:
                print(f"  [WARN] {mismatched} tables have fewer rows (may be due to skip on duplicate)")

    # ================================================================
    # Step 7: Build frontend + start services
    # ================================================================
    print("\n[7/7] Post-migration steps...")
    print()
    print("  Migration complete! Next steps:")
    print()
    print("  Option A: Docker deployment (recommended)")
    print("    docker compose -f deploy/multi-container/docker-compose.yml up -d --build")
    print()
    print("  Option B: Native deployment")
    print("    cd frontend && npm install && npm run build   # Build frontend")
    print("    python main.py                                  # Start backend")
    print()
    print("  Default admin account: admin / 123456")
    print("  (If admin already exists in backup, use that account)")
    print()
    print("=" * 64)
    print("  Migration finished!")
    print("=" * 64)


if __name__ == "__main__":
    main()
