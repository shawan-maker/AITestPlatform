"""
修复 knowledge_document 表中无效的 doc_type 值
需求模块已删除，但数据库中仍有 doc_type='requirement' 的记录
"""
import asyncio
from tortoise import Tortoise

async def fix():
    await Tortoise.init(
        db_url="mysql://root:123456@192.168.40.145:3306/aiTestPlatform",
        modules={"models": []}
    )
    
    conn = Tortoise.get_connection("default")
    
    # 1. 查询无效的 doc_type 值
    print("查询无效的 doc_type 值...")
    result = await conn.execute_query(
        "SELECT DISTINCT doc_type FROM knowledge_document"
    )
    print(f"现有的 doc_type 值: {[row[0] for row in result[1]]}")
    
    # 2. 删除或更新无效的记录
    print("\n删除 doc_type='requirement' 的记录...")
    await conn.execute_script(
        "DELETE FROM knowledge_document WHERE doc_type = 'requirement'"
    )
    print("删除完成")
    
    # 3. 验证
    result = await conn.execute_query(
        "SELECT DISTINCT doc_type FROM knowledge_document"
    )
    print(f"\n修复后的 doc_type 值: {[row[0] for row in result[1]]}")
    
    await Tortoise.close_connections()

if __name__ == "__main__":
    asyncio.run(fix())
    print("\n完成！请重启后端服务。")
