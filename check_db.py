#!/usr/bin/env python3
"""检查数据库表结构"""
import sqlite3
import os

def check_db(db_path: str):
    """检查数据库"""
    if not os.path.exists(db_path):
        print(f"[ERROR] 数据库文件不存在: {db_path}")
        return
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # 获取所有表名
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        print(f"[INFO] 数据库中的表: {tables}")
        
        # 检查 functional_case 相关的表
        target_tables = [t for t in tables if 'functional_case' in t]
        print(f"[INFO] functional_case 相关的表: {target_tables}")
        
        for table_name in target_tables:
            print(f"\n[INFO] 检查表: {table_name}")
            cursor.execute(f"PRAGMA table_info({table_name})")
            columns = cursor.fetchall()
            print(f"[INFO] 字段列表: {[col[1] for col in columns]}")
            
            if 'case_category' not in [col[1] for col in columns]:
                print(f"[WARN] 表 {table_name} 缺少 case_category 字段，正在添加...")
                try:
                    cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN case_category VARCHAR(20) NOT NULL DEFAULT 'functional'")
                    conn.commit()
                    print(f"[OK] 表 {table_name} 添加 case_category 字段成功")
                except Exception as e:
                    print(f"[ERROR] 添加字段失败: {e}")
            else:
                print(f"[OK] 表 {table_name} 已有 case_category 字段")
        
    except Exception as e:
        print(f"[ERROR] 检查失败: {e}")
        import traceback
        traceback.print_exc()
    finally:
        conn.close()

if __name__ == '__main__':
    db_path = "db.sqlite3"
    print("=" * 50)
    print("检查数据库表结构")
    print("=" * 50)
    
    check_db(db_path)
    
    print("\n" + "=" * 50)
    print("检查完成")
    print("=" * 50)
