"""
添加 completed_stages 字段到 ai_generation_session 表
"""
import asyncio
from tortoise import Tortoise, fields

async def add_field():
    await Tortoise.init(
        db_url="mysql://root:123456@127.0.0.1:3306/aiTestPlatform",
        modules={"models": []}
    )
    
    conn = Tortoise.get_connection("default")
    
    # 检查字段是否已存在
    check_sql = """
    SELECT COLUMN_NAME 
    FROM INFORMATION_SCHEMA.COLUMNS 
    WHERE TABLE_SCHEMA = 'aiTestPlatform' 
    AND TABLE_NAME = 'ai_generation_session' 
    AND COLUMN_NAME = 'completed_stages'
    """
    result = await conn.execute_query(check_sql)
    
    if result[1]:  # 字段已存在
        print("字段 completed_stages 已存在，跳过添加")
    else:
        # 添加字段
        add_sql = """
        ALTER TABLE ai_generation_session 
        ADD COLUMN completed_stages JSON DEFAULT NULL COMMENT '记录Agent已完成的阶段，用于SSE断点续传'
        """
        await conn.execute_script(add_sql)
        print("字段 completed_stages 添加成功")
    
    await Tortoise.close_connections()

if __name__ == "__main__":
    asyncio.run(add_field())
