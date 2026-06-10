#!/usr/bin/env python3
"""
直接用 pymysql 修复 functional_case_run_record 表的 task_run_id 字段
"""
import asyncio
import pymysql

async def fix():
    # 连接数据库
    conn = await pymysql.connect(
        host='127.0.0.1',
        port=3306,
        user='root',
        password='123456',
        db='aiTestPlatform',
        autocommit=True,
    )
    
    async with conn.cursor() as cur:
        # 检查当前字段是否可为空
        await cur.execute(
            "SELECT IS_NULLABLE FROM INFORMATION_SCHEMA.COLUMNS "
            "WHERE TABLE_SCHEMA = 'aiTestPlatform' "
            "AND TABLE_NAME = 'functional_case_run_record' "
            "AND COLUMN_NAME = 'task_run_id'"
        )
        row = await cur.fetchone()
        print(f"当前 task_run_id 字段 IS_NULLABLE: {row[0]}")
        
        if row[0] == 'NO':
            print("修改 task_run_id 字段为可空...")
            # 先删除外键约束（如果存在）
            await cur.execute(
                "SELECT CONSTRAINT_NAME FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE "
                "WHERE TABLE_SCHEMA = 'aiTestPlatform' "
                "AND TABLE_NAME = 'functional_case_run_record' "
                "AND COLUMN_NAME = 'task_run_id' "
                "AND REFERENCED_TABLE_NAME IS NOT NULL"
            )
            fk_row = await cur.fetchone()
            if fk_row:
                fk_name = fk_row[0]
                print(f"删除外键约束: {fk_name}")
                await cur.execute(f"ALTER TABLE functional_case_run_record DROP FOREIGN KEY `{fk_name}`")
            
            # 修改字段为可空
            await cur.execute(
                "ALTER TABLE functional_case_run_record MODIFY COLUMN task_run_id INT NULL"
            )
            print("[PASS] 已成功修改 task_run_id 字段为可空")
        else:
            print("[PASS] task_run_id 字段已经可空，无需修改")
    
    conn.close()

if __name__ == '__main__':
    asyncio.run(fix())
