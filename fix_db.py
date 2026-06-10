#!/usr/bin/env python3
"""修复 functional_case 表，添加 case_category 字段"""
import sqlite3
import os

def fix_functional_case_table(db_path: str):
    """修复 functional_case 表"""
    if not os.path.exists(db_path):
        print(f"[ERROR] 数据库文件不存在: {db_path}")
        return False
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # 检查 functional_case 表是否存在
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='functional_case'")
        if not cursor.fetchone():
            print("[ERROR] functional_case 表不存在")
            return False
        
        # 检查 case_category 字段是否存在
        cursor.execute("PRAGMA table_info(functional_case)")
        columns = [row[1] for row in cursor.fetchall()]
        print(f"[INFO] functional_case 表字段: {columns}")
        
        if 'case_category' in columns:
            print("[OK] case_category 字段已存在，无需修复")
            return True
            
        # 添加 case_category 字段
        print("[INFO] 正在添加 case_category 字段...")
        try:
            # 尝试直接添加字段（SQLite 3.35.0+ 支持 NOT NULL DEFAULT）
            cursor.execute("ALTER TABLE functional_case ADD COLUMN case_category VARCHAR(20) NOT NULL DEFAULT 'functional'")
            conn.commit()
            print("[OK] case_category 字段添加成功（直接 ALTER）")
            return True
        except sqlite3.OperationalError as e:
            print(f"[WARN] 直接 ALTER 失败: {e}")
            print("[INFO] 开始重建表...")
            
            # 重建表
            # 1. 创建新表
            cursor.execute("""
                CREATE TABLE functional_case_new (
                    id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
                    project_id INTEGER NOT NULL,
                    catalog_id INTEGER,
                    module_id INTEGER,
                    test_point_id INTEGER,
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
                    exec_result VARCHAR(10),
                    jira_issue_key VARCHAR(50),
                    sort_order INTEGER NOT NULL DEFAULT 0,
                    created_by_id INTEGER NOT NULL,
                    generation_session_id INTEGER,
                    created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (project_id) REFERENCES project (id) ON DELETE CASCADE,
                    FOREIGN KEY (catalog_id) REFERENCES functional_case_catalog (id) ON DELETE SET NULL,
                    FOREIGN KEY (module_id) REFERENCES project_module (id) ON DELETE SET NULL,
                    FOREIGN KEY (test_point_id) REFERENCES functional_test_point (id) ON DELETE SET NULL,
                    FOREIGN KEY (created_by_id) REFERENCES user (id) ON DELETE RESTRICT,
                    FOREIGN KEY (generation_session_id) REFERENCES ai_generation_session (id) ON DELETE SET NULL
                )
            """)
            
            # 2. 复制数据（如果 type 字段存在，则映射它的值到 case_category）
            if 'type' in columns:
                print("[INFO] 检测到 type 字段，将映射其值到 case_category...")
                cursor.execute("""
                    INSERT INTO functional_case_new 
                    SELECT id, project_id, catalog_id, module_id, test_point_id,
                           case_no, case_name, priority, dimension,
                           COALESCE(type, 'functional') as case_category,
                           status, content_format, preconditions, test_steps,
                           test_data, expected_result, actual_result,
                           source, exec_result, jira_issue_key, sort_order,
                           created_by_id, generation_session_id, created_at, updated_at
                    FROM functional_case
                """)
            else:
                print("[INFO] 未检测到 type 字段，case_category 将使用默认值 'functional'...")
                cursor.execute("""
                    INSERT INTO functional_case_new 
                    SELECT id, project_id, catalog_id, module_id, test_point_id,
                           case_no, case_name, priority, dimension,
                           'functional' as case_category,
                           status, content_format, preconditions, test_steps,
                           test_data, expected_result, actual_result,
                           source, exec_result, jira_issue_key, sort_order,
                           created_by_id, generation_session_id, created_at, updated_at
                    FROM functional_case
                """)
            
            # 3. 删除旧表
            cursor.execute("DROP TABLE functional_case")
            
            # 4. 重命名新表
            cursor.execute("ALTER TABLE functional_case_new RENAME TO functional_case")
            
            # 5. 重建索引（如果有）
            # TODO: 如果需要，可以在这里重建索引
            
            conn.commit()
            print("[OK] functional_case 表重建完成，case_category 字段已添加")
            return True
            
    except Exception as e:
        conn.rollback()
        print(f"[ERROR] 修复失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        conn.close()

if __name__ == '__main__':
    db_path = "db.sqlite3"
    print("=" * 50)
    print("修复 functional_case 表")
    print("=" * 50)
    
    if fix_functional_case_table(db_path):
        print("\n[OK] 修复成功！")
    else:
        print("\n[FAIL] 修复失败！")
    
    print("=" * 50)
