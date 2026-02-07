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
    return sqlite3.connect(db_path)


if __name__ == "__main__":
    # 测试初始化
    init_database()
