"""
数据库初始化脚本
使用原生SQL创建表结构
"""
import sqlite3
import os
from pathlib import Path


def init_database(db_path: str = "storage/projects/default.db"):
    """
    初始化数据库
    读取schema.sql并执行
    """
    # 确保目录存在
    db_dir = Path(db_path).parent
    db_dir.mkdir(parents=True, exist_ok=True)

    # 读取schema.sql
    schema_path = Path(__file__).parent / "schema.sql"
    with open(schema_path, 'r', encoding='utf-8') as f:
        schema_sql = f.read()

    # 创建数据库连接
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # 执行schema
        cursor.executescript(schema_sql)
        conn.commit()
        print(f"✅ 数据库初始化成功: {db_path}")
        return True
    except Exception as e:
        print(f"❌ 数据库初始化失败: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()


def get_connection(db_path: str = "storage/projects/default.db"):
    """获取数据库连接"""
    if not os.path.exists(db_path):
        init_database(db_path)
    else:
        # 运行迁移以确保数据库结构是最新的
        run_migrations(db_path)

    conn = sqlite3.connect(db_path)
    # 启用外键约束（SQLite默认不启用）
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def run_migrations(db_path: str):
    """
    运行数据库迁移
    为现有数据库添加新字段
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # 迁移1: 为 storyboards 表添加 asset_mapping 字段
        cursor.execute("PRAGMA table_info(storyboards)")
        columns = [col[1] for col in cursor.fetchall()]

        if 'asset_mapping' not in columns:
            print("🔄 正在迁移: 添加 storyboards.asset_mapping 字段...")
            cursor.execute("""
                ALTER TABLE storyboards
                ADD COLUMN asset_mapping TEXT
            """)
            conn.commit()
            print("✅ 迁移完成: storyboards.asset_mapping 字段已添加")

        # 迁移2: 为 users 表添加 is_admin 字段
        cursor.execute("PRAGMA table_info(users)")
        columns = [col[1] for col in cursor.fetchall()]

        if 'is_admin' not in columns:
            print("🔄 正在迁移: 添加 users.is_admin 字段...")
            cursor.execute("""
                ALTER TABLE users
                ADD COLUMN is_admin BOOLEAN DEFAULT 0
            """)
            conn.commit()
            print("✅ 迁移完成: users.is_admin 字段已添加")

        # 迁移3: 创建资产拆解版本表
        cursor.execute("""
            SELECT name FROM sqlite_master
            WHERE type='table' AND name='asset_extraction_versions'
        """)
        if not cursor.fetchone():
            print("🔄 正在迁移: 创建 asset_extraction_versions 表...")
            cursor.execute("""
                CREATE TABLE asset_extraction_versions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_id INTEGER NOT NULL,
                    episode_id INTEGER,
                    version_number INTEGER NOT NULL,
                    model_used TEXT NOT NULL,
                    extraction_type TEXT NOT NULL,
                    feedback TEXT,
                    asset_count INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (project_id) REFERENCES projects(id)
                )
            """)
            conn.commit()
            print("✅ 迁移完成: asset_extraction_versions 表已创建")

        # 迁移4: 为 assets 表添加 version_id 字段
        cursor.execute("PRAGMA table_info(assets)")
        columns = [col[1] for col in cursor.fetchall()]

        if 'version_id' not in columns:
            print("🔄 正在迁移: 添加 assets.version_id 字段...")
            cursor.execute("""
                ALTER TABLE assets
                ADD COLUMN version_id INTEGER
            """)
            conn.commit()
            print("✅ 迁移完成: assets.version_id 字段已添加")

    except Exception as e:
        print(f"⚠️ 迁移警告: {e}")
        conn.rollback()
    finally:
        conn.close()


if __name__ == "__main__":
    # 测试初始化
    init_database()
