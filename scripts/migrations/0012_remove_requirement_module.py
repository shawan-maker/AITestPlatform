"""Remove requirement module migration.

This migration removes the requirement management module:
1. Drops requirement_candidate table
2. Drops requirement_doc table
3. Removes requirement_id column from functional_test_point table
4. Removes requirement_id column from functional_case table

Run with: python migrations/0012_remove_requirement_module.py
"""

import sqlite3
import sys
import os

DB_PATH = "db.sqlite3"


def upgrade():
    """Apply migration: remove requirement module."""
    if not os.path.exists(DB_PATH):
        print(f"Database file not found: {DB_PATH}")
        print("Please run this script from the project root directory.")
        sys.exit(1)
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    print("Starting migration: remove requirement module...")
    
    try:
        # 1. Drop requirement_candidate table
        print("Dropping requirement_candidate table...")
        cursor.execute("DROP TABLE IF EXISTS requirement_candidate;")
        
        # 2. Drop requirement_doc table
        print("Dropping requirement_doc table...")
        cursor.execute("DROP TABLE IF EXISTS requirement_doc;")
        
        # 3. Remove requirement_id column from functional_test_point
        print("Removing requirement_id from functional_test_point...")
        # SQLite doesn't support DROP COLUMN directly, need to recreate table
        cursor.execute("PRAGMA table_info(functional_test_point);")
        columns = [row[1] for row in cursor.fetchall()]
        
        if "requirement_id" in columns:
            # Get column definitions
            cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='functional_test_point';")
            create_sql = cursor.fetchone()[0]
            
            # Create new table without requirement_id
            cursor.execute("""
                CREATE TABLE functional_test_point_new (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    type VARCHAR(50) NOT NULL,
                    dimension VARCHAR(100) NOT NULL,
                    test_point TEXT NOT NULL,
                    source VARCHAR(20) NOT NULL DEFAULT 'ai',
                    generation_session_id INTEGER,
                    created_at TIMESTAMP NOT NULL,
                    FOREIGN KEY (generation_session_id) REFERENCES ai_generation_session(id)
                );
            """)
            
            # Copy data
            cursor.execute("""
                INSERT INTO functional_test_point_new 
                SELECT id, type, dimension, test_point, source, generation_session_id, created_at 
                FROM functional_test_point;
            """)
            
            # Drop old table and rename new one
            cursor.execute("DROP TABLE functional_test_point;")
            cursor.execute("ALTER TABLE functional_test_point_new RENAME TO functional_test_point;")
            print("  - requirement_id column removed from functional_test_point")
        
        # 4. Remove requirement_id column from functional_case
        print("Removing requirement_id from functional_case...")
        cursor.execute("PRAGMA table_info(functional_case);")
        columns = [row[1] for row in cursor.fetchall()]
        
        if "requirement_id" in columns:
            # Create new table without requirement_id
            cursor.execute("""
                CREATE TABLE functional_case_new (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_id INTEGER NOT NULL,
                    module_id INTEGER,
                    catalog_id INTEGER,
                    test_point_id INTEGER,
                    title VARCHAR(255) NOT NULL,
                    preconditions TEXT,
                    steps TEXT NOT NULL,
                    expected_result TEXT NOT NULL,
                    case_type VARCHAR(20) NOT NULL DEFAULT 'positive',
                    priority VARCHAR(20) NOT NULL DEFAULT 'medium',
                    status VARCHAR(20) NOT NULL DEFAULT 'draft',
                    executor_result VARCHAR(20),
                    executor_result_note TEXT,
                    creator_result VARCHAR(20),
                    creator_result_note TEXT,
                    created_by_id INTEGER NOT NULL,
                    updated_by_id INTEGER,
                    created_at TIMESTAMP NOT NULL,
                    updated_at TIMESTAMP NOT NULL,
                    FOREIGN KEY (project_id) REFERENCES project(id),
                    FOREIGN KEY (module_id) REFERENCES project_module(id),
                    FOREIGN KEY (catalog_id) REFERENCES functional_case_catalog(id),
                    FOREIGN KEY (test_point_id) REFERENCES functional_test_point(id),
                    FOREIGN KEY (created_by_id) REFERENCES user(id),
                    FOREIGN KEY (updated_by_id) REFERENCES user(id)
                );
            """)
            
            # Copy data
            cursor.execute("""
                INSERT INTO functional_case_new 
                SELECT id, project_id, module_id, catalog_id, test_point_id,
                       title, preconditions, steps, expected_result, case_type,
                       priority, status, executor_result, executor_result_note,
                       creator_result, creator_result_note, created_by_id, 
                       updated_by_id, created_at, updated_at
                FROM functional_case;
            """)
            
            # Drop old table and rename new one
            cursor.execute("DROP TABLE functional_case;")
            cursor.execute("ALTER TABLE functional_case_new RENAME TO functional_case;")
            print("  - requirement_id column removed from functional_case")
        
        conn.commit()
        print("Migration completed successfully!")
        
    except Exception as e:
        conn.rollback()
        print(f"Migration failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        conn.close()


def downgrade():
    """Rollback migration: restore requirement module."""
    if not os.path.exists(DB_PATH):
        print(f"Database file not found: {DB_PATH}")
        sys.exit(1)
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    print("Rolling back migration: restore requirement module...")
    
    try:
        # Re-create requirement_doc table
        print("Creating requirement_doc table...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS requirement_doc (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER NOT NULL,
                module_id INTEGER,
                title VARCHAR(255) NOT NULL,
                description TEXT,
                source_type VARCHAR(50) NOT NULL,
                source_document_id INTEGER,
                status VARCHAR(50) NOT NULL DEFAULT 'draft',
                created_by_id INTEGER NOT NULL,
                updated_by_id INTEGER,
                created_at TIMESTAMP NOT NULL,
                updated_at TIMESTAMP NOT NULL
            );
        """)
        
        # Re-create requirement_candidate table
        print("Creating requirement_candidate table...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS requirement_candidate (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                document_id INTEGER NOT NULL,
                version_id INTEGER NOT NULL,
                project_id INTEGER NOT NULL,
                title VARCHAR(255) NOT NULL,
                content TEXT NOT NULL,
                created_at TIMESTAMP NOT NULL
            );
        """)
        
        # Add requirement_id column back to functional_test_point
        print("Adding requirement_id to functional_test_point...")
        cursor.execute("PRAGMA table_info(functional_test_point);")
        columns = [row[1] for row in cursor.fetchall()]
        
        if "requirement_id" not in columns:
            cursor.execute(
                "ALTER TABLE functional_test_point ADD COLUMN requirement_id INTEGER REFERENCES requirement_doc(id);"
            )
        
        # Add requirement_id column back to functional_case
        print("Adding requirement_id to functional_case...")
        cursor.execute("PRAGMA table_info(functional_case);")
        columns = [row[1] for row in cursor.fetchall()]
        
        if "requirement_id" not in columns:
            cursor.execute(
                "ALTER TABLE functional_case ADD COLUMN requirement_id INTEGER REFERENCES requirement_doc(id);"
            )
        
        conn.commit()
        print("Rollback completed successfully!")
        
    except Exception as e:
        conn.rollback()
        print(f"Rollback failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        conn.close()


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "downgrade":
        downgrade()
    else:
        upgrade()
