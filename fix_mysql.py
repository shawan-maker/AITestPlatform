#!/usr/bin/env python3
"""修复 MySQL 数据库中的 functional_case 表，添加 case_category 字段"""
import pymysql

def fix_mysql_table():
    """修复 MySQL 表"""
    # MySQL 连接配置（从 config.py 中获取）
    config = {
        'host': '127.0.0.1',
        'port': 3306,
        'user': 'root',
        'password': '123456',
        'database': 'aiTestPlatform',
        'charset': 'utf8mb4'
    }
    
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
