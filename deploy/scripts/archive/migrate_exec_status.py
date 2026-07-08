"""迁移 exec_status 旧枚举值到新枚举值。

旧值 → 新值映射：
  ready    → success  （预执行通过 → 成功）
  disabled → pending   （已禁用 → 待执行）

用法：
  python scripts/migrate_exec_status.py
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from service.core.database import init_db, close_db


async def main():
    await init_db()
    try:
        from tortoise import connections

        conn = connections.get("default")

        # 统计旧值数量
        _, ready_rows = await conn.execute_query(
            "SELECT COUNT(*) as cnt FROM api_test_case WHERE exec_status = 'ready'"
        )
        ready_count = ready_rows[0]["cnt"] if ready_rows else 0

        _, disabled_rows = await conn.execute_query(
            "SELECT COUNT(*) as cnt FROM api_test_case WHERE exec_status = 'disabled'"
        )
        disabled_count = disabled_rows[0]["cnt"] if disabled_rows else 0

        print(f"找到 {ready_count} 条 exec_status='ready' 的记录")
        print(f"找到 {disabled_count} 条 exec_status='disabled' 的记录")

        if ready_count > 0:
            await conn.execute_query(
                "UPDATE api_test_case SET exec_status = 'success' WHERE exec_status = 'ready'"
            )
            print(f"已将 {ready_count} 条 ready → success")

        if disabled_count > 0:
            await conn.execute_query(
                "UPDATE api_test_case SET exec_status = 'pending' WHERE exec_status = 'disabled'"
            )
            print(f"已将 {disabled_count} 条 disabled → pending")

        if ready_count == 0 and disabled_count == 0:
            print("无需迁移，所有记录已是新枚举值。")

    finally:
        await close_db()


if __name__ == "__main__":
    asyncio.run(main())
