"""
数据库迁移管理脚本（封装 Aerich CLI）。

用法（在项目根目录执行）：
    python scripts/db_manage.py init-db          # 首次：生成并应用初始迁移
    python scripts/db_manage.py migrate -m "描述" # 模型变更后：生成新迁移文件
    python scripts/db_manage.py upgrade          # 应用未执行的迁移
    python scripts/db_manage.py downgrade        # 回滚上一版本
    python scripts/db_manage.py history          # 查看迁移历史
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 1

    command = sys.argv[1]
    extra = sys.argv[2:]

    aerich_args = ["aerich", command, *extra]
    print(f">>> {' '.join(aerich_args)}")
    result = subprocess.run(aerich_args, cwd=ROOT)
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
