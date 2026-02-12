"""
创建管理员账户脚本
使用方法: python create_admin.py
"""
import sys
import os
from pathlib import Path
from getpass import getpass
from werkzeug.security import generate_password_hash

# 添加backend目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database.init_db import get_connection


def create_admin_user():
    """创建管理员账户"""
    print("=" * 50)
    print("创建管理员账户")
    print("=" * 50)

    # 获取用户输入
    username = input("请输入管理员用户名 (默认: admin): ").strip() or "admin"
    email = input("请输入管理员邮箱 (默认: admin@example.com): ").strip() or "admin@example.com"
    full_name = input("请输入管理员全名 (默认: 系统管理员): ").strip() or "系统管理员"

    # 获取密码
    while True:
        password = getpass("请输入管理员密码 (至少8位，包含字母和数字): ")
        if len(password) < 8:
            print("❌ 密码至少需要8个字符")
            continue

        password_confirm = getpass("请再次输入密码: ")
        if password != password_confirm:
            print("❌ 两次输入的密码不一致")
            continue

        break

    try:
        conn = get_connection()
        cursor = conn.cursor()

        # 检查用户名是否已存在
        cursor.execute("SELECT id, is_admin FROM users WHERE username = ?", (username,))
        existing_user = cursor.fetchone()

        if existing_user:
            user_id, is_admin = existing_user
            if is_admin:
                print(f"⚠️  用户 '{username}' 已经是管理员")
                conn.close()
                return
            else:
                # 将现有用户升级为管理员
                cursor.execute("UPDATE users SET is_admin = 1 WHERE id = ?", (user_id,))
                conn.commit()
                print(f"✅ 用户 '{username}' 已升级为管理员")
                conn.close()
                return

        # 检查邮箱是否已存在
        cursor.execute("SELECT id FROM users WHERE email = ?", (email,))
        if cursor.fetchone():
            print(f"❌ 邮箱 '{email}' 已被使用")
            conn.close()
            return

        # 创建管理员账户
        password_hash = generate_password_hash(password)
        from datetime import datetime

        cursor.execute("""
            INSERT INTO users (username, email, password_hash, full_name, is_admin, is_active, created_at, updated_at)
            VALUES (?, ?, ?, ?, 1, 1, ?, ?)
        """, (username, email, password_hash, full_name, datetime.utcnow(), datetime.utcnow()))

        conn.commit()
        user_id = cursor.lastrowid

        print("\n" + "=" * 50)
        print("✅ 管理员账户创建成功！")
        print("=" * 50)
        print(f"用户ID: {user_id}")
        print(f"用户名: {username}")
        print(f"邮箱: {email}")
        print(f"全名: {full_name}")
        print(f"管理员权限: 是")
        print("\n请使用此账户登录管理后台: http://localhost:5000/admin")
        print("=" * 50)

        conn.close()

    except Exception as e:
        print(f"❌ 创建管理员失败: {str(e)}")
        if conn:
            conn.rollback()
            conn.close()


def list_admins():
    """列出所有管理员"""
    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT id, username, email, full_name, is_active, created_at
            FROM users
            WHERE is_admin = 1
            ORDER BY created_at
        """)

        admins = cursor.fetchall()

        if not admins:
            print("当前没有管理员账户")
            conn.close()
            return

        print("\n" + "=" * 80)
        print("管理员列表")
        print("=" * 80)
        print(f"{'ID':<5} {'用户名':<15} {'邮箱':<25} {'全名':<15} {'状态':<8} {'创建时间'}")
        print("-" * 80)

        for admin in admins:
            user_id, username, email, full_name, is_active, created_at = admin
            status = "活跃" if is_active else "禁用"
            print(f"{user_id:<5} {username:<15} {email:<25} {full_name:<15} {status:<8} {created_at}")

        print("=" * 80)
        conn.close()

    except Exception as e:
        print(f"❌ 获取管理员列表失败: {str(e)}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='管理员账户管理工具')
    parser.add_argument('--list', action='store_true', help='列出所有管理员')

    args = parser.parse_args()

    if args.list:
        list_admins()
    else:
        create_admin_user()
