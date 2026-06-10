#!/usr/bin/env python3
"""手动数据库迁移脚本 - 添加 case_category 字段并删除 type 字段"""
import sqlite3
import sys

def migrate_sqlite(db_path: str):
    """SQLite 数据库迁移"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # 检查字段是否已存在
        cursor.execute("PRAGMA table_info(functional_case)")
        columns = {row[1] for row in cursor.fetchall()}
        
        # 1. 添加 case_category 字段（如果不存在）
        if 'case_category' not in columns:
            print("添加 case_category 字段...")
            cursor.execute("ALTER TABLE functional_case ADD COLUMN case_category VARCHAR(20) NOT NULL DEFAULT 'functional'")
            print("case_category 字段添加成功")
        else:
            print("case_category 字段已存在，跳过")
        
        # 2. 如果 type 字段存在，需要重建表来删除它
        if 'type' in columns:
            print("检测到 type 字段，开始重建表以删除该字段...")
            
            # 获取所有索引和外键
            cursor.execute("SELECT sql FROM sqlite_master WHERE type='index' AND tbl_name='functional_case' AND name NOT LIKE 'sqlite_autoindex%'")
            indexes = cursor.fetchall()
            
            cursor.execute("PRAGMA foreign_key_list(functional_case)")
            foreign_keys = cursor.fetchall()
            
            # 创建新表（不包含 type 字段）
            cursor.execute("""
                CREATE TABLE functional_case_new (
                    id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
                    case_no VARCHAR(100),
                    case_name VARCHAR(255) NOT NULL,
                    priority SMALLINT NOT NULL DEFAULT 3,
                    dimension VARCHAR(100),
                    case_category VARCHAR(20) NOT NULL DEFAULT 'functional',
                    status VARCHAR(10) NOT NULL DEFAULT 'design',
                    content_format VARCHAR(4) NOT NULL DEFAULT 'text',
                    preconditions LONGTEXT,
                    test_steps LONGTEXT,
                    test_data LONGTEXT,
                    expected_result LONGTEXT,
                    actual_result LONGTEXT,
                    source VARCHAR(6) NOT NULL DEFAULT 'manual',
                    created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    created_by_id INTEGER NOT NULL,
                    generation_session_id INTEGER,
                    module_id INTEGER,
                    project_id INTEGER NOT NULL,
                    requirement_id INTEGER,
                    test_point_id INTEGER,
                    FOREIGN KEY (created_by_id) REFERENCES user (id) ON DELETE RESTRICT,
                    FOREIGN KEY (generation_session_id) REFERENCES ai_generation_session (id) ON DELETE SET NULL,
                    FOREIGN KEY (module_id) REFERENCES project_module (id) ON DELETE SET NULL,
                    FOREIGN KEY (project_id) REFERENCES project (id) ON DELETE CASCADE,
                    FOREIGN KEY (requirement_id) REFERENCES requirement_doc (id) ON DELETE SET NULL,
                    FOREIGN KEY (test_point_id) REFERENCES functional_test_point (id) ON DELETE SET NULL
                )
            """)
            
            # 复制数据（将 type 字段的值映射到 case_category）
            cursor.execute("""
                INSERT INTO functional_case_new 
                SELECT id, case_no, case_name, priority, dimension, 
                       COALESCE(NULLIF(type, ''), 'functional') as case_category,
                       status, content_format, preconditions, test_steps, 
                       test_data, expected_result, actual_result, source,
                       created_at, updated_at, created_by_id, generation_session_id,
                       module_id, project_id, requirement_id, test_point_id
                FROM functional_case
            """)
            
            # 删除旧表
            cursor.execute("DROP TABLE functional_case")
            
            # 重命名新表
            cursor.execute("ALTER TABLE functional_case_new RENAME TO functional_case")
            
            # 重建索引
            for idx in indexes:
                if idx[0]:
                    cursor.execute(idx[0])
            
            print("type 字段已成功删除")
        else:
            print("type 字段不存在，跳过删除")
        
        conn.commit()
        print("迁移完成！")
        
    except Exception as e:
        conn.rollback()
        print(f"迁移失败: {e}")
        import traceback
        traceback.print_exc()
        raise
    finally:
        conn.close()

if __name__ == "__main__":
    db_path = "db.sqlite3"
    migrate_sqlite(db_path)
