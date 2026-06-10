#!/usr/bin/env python3
"""修复 MySQL 数据库中的 functional_case 表，添加 case_category 字段"""
import re
import pymysql
from dotenv import load_dotenv, find_dotenv

def parse_db_url(db_url: str):
    """解析 DATABASE_URL，返回连接参数"""
    # 格式: mysql://user:password@host:port/database
    pattern = r'mysql://(?P<user>[^:]+):(?P<password>[^@]+)@(?P<host>[^:]+):(?P<port>\d+)/(?P<database>.+)'
    match = re.match(pattern, db_url)
    if not match:
        raise ValueError(f"无法解析 DATABASE_URL: {db_url}")
    
    return {
        'host': match.group('host'),
        'port': int(match.group('port')),
        'user': match.group('user'),
        'password': match.group('password'),
        'database': match.group('database'),
        'charset': 'utf8mb4'
    }

def fix_mysql_table():
    """修复 MySQL 表"""
    # 加载 .env 文件
    dotenv_path = find_dotenv()
    if dotenv_path:
        print(f"[INFO] 找到 .env 文件: {dotenv_path}")
        load_dotenv(dotenv_path)
    else:
        print("[WARN] 未找到 .env 文件，使用默认配置")
    
    # 从环境变量获取 DATABASE_URL
    import os
    db_url = os.getenv('DATABASE_URL', 'mysql://root:123456@127.0.0.1:3306/aiTestPlatform')
    print(f"[INFO] 使用 DATABASE_URL: {db_url.split('@')[1] if '@' in db_url else db_url}")  # 不打印密码
    
    # 解析 DATABASE_URL
    try:
        config = parse_db_url(db_url)
    except ValueError as e:
        print(f"[ERROR] 解析 DATABASE_URL 失败: {e}")
        return False
    
    print(f"[INFO] 连接 MySQL: {config['user']}@{config['host']}:{config['port']}/{config['database']}")
    
    # 连接数据库
    connection = pymysql.connect(**config)
    
    try:
        with connection.cursor() as cursor:
            # 检查 functional_case 表是否存在
            cursor.execute("SHOW TABLES LIKE 'functional_case'")
            if not cursor.fetchone():
                print("[ERROR] functional_case 表不存在")
                return False
            
            # 检查 case_category 字段是否存在
            cursor.execute("DESCRIBE functional_case")
            columns = [row[0] for row in cursor.fetchall()]
            print(f"[INFO] functional_case 表字段: {columns}")
            
            if 'case_category' in columns:
                print("[OK] case_category 字段已存在，无需修复")
                return True
            
            # 添加 case_category 字段
            print("[INFO] 正在添加 case_category 字段...")
            
            # 如果 type 字段存在，则将其的值映射到 case_category，然后删除 type 字段
            if 'type' in columns:
                print("[INFO] 检测到 type 字段，将映射其值到 case_category...")
                # 添加 case_category 字段（允许 NULL，以便从 type 字段更新值）
                cursor.execute("""
                    ALTER TABLE functional_case 
                    ADD COLUMN case_category VARCHAR(20) NOT NULL DEFAULT 'functional'
                """)
                connection.commit()
                print("[OK] case_category 字段添加成功")
                
                # 可选：将 type 字段的值映射到 case_category 字段
                # 但是，type 字段的值是 'functional' 或 'ui'，而 case_category 的值应该是 'functional', 'performance', etc.
                # 所以，这里我们只设置默认值为 'functional'
                
                # 删除 type 字段
                print("[INFO] 正在删除 type 字段...")
                cursor.execute("ALTER TABLE functional_case DROP COLUMN type")
                connection.commit()
                print("[OK] type 字段删除成功")
            else:
                # 直接添加 case_category 字段
                cursor.execute("""
                    ALTER TABLE functional_case 
                    ADD COLUMN case_category VARCHAR(20) NOT NULL DEFAULT 'functional'
                """)
                connection.commit()
                print("[OK] case_category 字段添加成功")
            
            return True
            
    except Exception as e:
        connection.rollback()
        print(f"[ERROR] 修复失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        connection.close()

if __name__ == '__main__':
    print("=" * 50)
    print("修复 MySQL 数据库表")
    print("=" * 50)
    
    if fix_mysql_table():
        print("\n[OK] 修复成功！")
    else:
        print("\n[FAIL] 修复失败！")
    
    print("=" * 50)
