"""
管理员路由
"""
from flask import Blueprint, request, jsonify
from functools import wraps
import jwt
from datetime import datetime
from database.init_db import get_connection
from werkzeug.security import generate_password_hash

admin_bp = Blueprint('admin', __name__, url_prefix='/api/admin')

# 从环境变量或配置文件读取密钥（与auth.py保持一致）
SECRET_KEY = 'dev-secret-key-change-in-production'


def admin_required(f):
    """管理员权限验证装饰器"""
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None

        # 从请求头获取token
        if 'Authorization' in request.headers:
            auth_header = request.headers['Authorization']
            try:
                token = auth_header.split(' ')[1]
            except IndexError:
                return jsonify({'success': False, 'error': '无效的token格式'}), 401

        if not token:
            return jsonify({'success': False, 'error': '缺少认证token'}), 401

        try:
            # 解码token
            data = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
            current_user_id = data['user_id']

            # 验证用户是否为管理员
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute('SELECT id, username, is_admin FROM users WHERE id = ? AND is_active = 1', (current_user_id,))
            user = cursor.fetchone()
            conn.close()

            if not user:
                return jsonify({'success': False, 'error': '用户不存在或已被禁用'}), 401

            if not user[2]:  # is_admin
                return jsonify({'success': False, 'error': '需要管理员权限'}), 403

            return f(current_user_id, *args, **kwargs)

        except jwt.ExpiredSignatureError:
            return jsonify({'success': False, 'error': 'Token已过期'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'success': False, 'error': '无效的token'}), 401
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500

    return decorated


@admin_bp.route('/users', methods=['GET'])
@admin_required
def list_users(current_user_id):
    """获取用户列表"""
    conn = None
    try:
        # 获取查询参数
        page = request.args.get('page', 1, type=int)
        page_size = request.args.get('page_size', 20, type=int)
        search = request.args.get('search', '')

        conn = get_connection()
        cursor = conn.cursor()

        # 构建查询条件
        where_clause = "WHERE 1=1"
        params = []

        if search:
            where_clause += " AND (username LIKE ? OR email LIKE ? OR full_name LIKE ?)"
            search_pattern = f'%{search}%'
            params.extend([search_pattern, search_pattern, search_pattern])

        # 获取总数
        cursor.execute(f'SELECT COUNT(*) FROM users {where_clause}', params)
        total = cursor.fetchone()[0]

        # 获取用户列表
        offset = (page - 1) * page_size
        cursor.execute(f'''
            SELECT id, username, email, full_name, is_admin, is_active, created_at, updated_at
            FROM users
            {where_clause}
            ORDER BY created_at DESC
            LIMIT ? OFFSET ?
        ''', params + [page_size, offset])

        users = []
        for row in cursor.fetchall():
            users.append({
                'id': row[0],
                'username': row[1],
                'email': row[2],
                'full_name': row[3],
                'is_admin': bool(row[4]),
                'is_active': bool(row[5]),
                'created_at': row[6],
                'updated_at': row[7]
            })

        return jsonify({
            'success': True,
            'data': {
                'users': users,
                'pagination': {
                    'page': page,
                    'page_size': page_size,
                    'total': total,
                    'total_pages': (total + page_size - 1) // page_size
                }
            }
        }), 200

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        if conn:
            conn.close()


@admin_bp.route('/users/<int:user_id>', methods=['GET'])
@admin_required
def get_user(current_user_id, user_id):
    """获取用户详情"""
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()

        # 获取用户信息
        cursor.execute('''
            SELECT id, username, email, full_name, is_admin, is_active, created_at, updated_at
            FROM users
            WHERE id = ?
        ''', (user_id,))

        user_row = cursor.fetchone()
        if not user_row:
            return jsonify({'success': False, 'error': '用户不存在'}), 404

        user = {
            'id': user_row[0],
            'username': user_row[1],
            'email': user_row[2],
            'full_name': user_row[3],
            'is_admin': bool(user_row[4]),
            'is_active': bool(user_row[5]),
            'created_at': user_row[6],
            'updated_at': user_row[7]
        }

        # 获取用户的项目统计
        cursor.execute('SELECT COUNT(*) FROM projects WHERE user_id = ? AND is_deleted = 0', (user_id,))
        project_count = cursor.fetchone()[0]

        user['statistics'] = {
            'project_count': project_count
        }

        return jsonify({'success': True, 'data': {'user': user}}), 200

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        if conn:
            conn.close()


@admin_bp.route('/users/<int:user_id>', methods=['PUT'])
@admin_required
def update_user(current_user_id, user_id):
    """更新用户信息"""
    conn = None
    try:
        data = request.get_json()
        conn = get_connection()
        cursor = conn.cursor()

        # 检查用户是否存在
        cursor.execute('SELECT id FROM users WHERE id = ?', (user_id,))
        if not cursor.fetchone():
            return jsonify({'success': False, 'error': '用户不存在'}), 404

        # 构建更新语句
        update_fields = []
        params = []

        if 'username' in data:
            # 检查用户名是否已被使用
            cursor.execute('SELECT id FROM users WHERE username = ? AND id != ?', (data['username'], user_id))
            if cursor.fetchone():
                return jsonify({'success': False, 'error': '用户名已被使用'}), 400
            update_fields.append('username = ?')
            params.append(data['username'])

        if 'email' in data:
            # 检查邮箱是否已被使用
            cursor.execute('SELECT id FROM users WHERE email = ? AND id != ?', (data['email'], user_id))
            if cursor.fetchone():
                return jsonify({'success': False, 'error': '邮箱已被使用'}), 400
            update_fields.append('email = ?')
            params.append(data['email'])

        if 'full_name' in data:
            update_fields.append('full_name = ?')
            params.append(data['full_name'])

        if 'password' in data and data['password']:
            update_fields.append('password_hash = ?')
            params.append(generate_password_hash(data['password']))

        if 'is_admin' in data:
            update_fields.append('is_admin = ?')
            params.append(1 if data['is_admin'] else 0)

        if not update_fields:
            return jsonify({'success': False, 'error': '没有要更新的字段'}), 400

        update_fields.append('updated_at = ?')
        params.append(datetime.utcnow())
        params.append(user_id)

        cursor.execute(f'''
            UPDATE users
            SET {', '.join(update_fields)}
            WHERE id = ?
        ''', params)

        conn.commit()

        return jsonify({'success': True, 'message': '用户信息更新成功'}), 200

    except Exception as e:
        if conn:
            conn.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        if conn:
            conn.close()


@admin_bp.route('/users/<int:user_id>/status', methods=['PUT'])
@admin_required
def update_user_status(current_user_id, user_id):
    """启用/禁用用户"""
    conn = None
    try:
        data = request.get_json()
        is_active = data.get('is_active')

        if is_active is None:
            return jsonify({'success': False, 'error': '缺少is_active参数'}), 400

        # 不能禁用自己
        if user_id == current_user_id and not is_active:
            return jsonify({'success': False, 'error': '不能禁用自己的账户'}), 400

        conn = get_connection()
        cursor = conn.cursor()

        # 检查用户是否存在
        cursor.execute('SELECT id FROM users WHERE id = ?', (user_id,))
        if not cursor.fetchone():
            return jsonify({'success': False, 'error': '用户不存在'}), 404

        # 更新状态
        cursor.execute('''
            UPDATE users
            SET is_active = ?, updated_at = ?
            WHERE id = ?
        ''', (1 if is_active else 0, datetime.utcnow(), user_id))

        conn.commit()

        status_text = '启用' if is_active else '禁用'
        return jsonify({'success': True, 'message': f'用户已{status_text}'}), 200

    except Exception as e:
        if conn:
            conn.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        if conn:
            conn.close()


@admin_bp.route('/users/<int:user_id>', methods=['DELETE'])
@admin_required
def delete_user(current_user_id, user_id):
    """删除用户"""
    conn = None
    try:
        # 不能删除自己
        if user_id == current_user_id:
            return jsonify({'success': False, 'error': '不能删除自己的账户'}), 400

        conn = get_connection()
        cursor = conn.cursor()

        # 检查用户是否存在
        cursor.execute('SELECT id FROM users WHERE id = ?', (user_id,))
        if not cursor.fetchone():
            return jsonify({'success': False, 'error': '用户不存在'}), 404

        # 删除用户的所有项目（软删除）
        cursor.execute('''
            UPDATE projects
            SET is_deleted = 1, updated_at = ?
            WHERE user_id = ?
        ''', (datetime.utcnow(), user_id))

        # 删除用户
        cursor.execute('DELETE FROM users WHERE id = ?', (user_id,))

        conn.commit()

        return jsonify({'success': True, 'message': '用户删除成功'}), 200

    except Exception as e:
        if conn:
            conn.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        if conn:
            conn.close()


@admin_bp.route('/statistics', methods=['GET'])
@admin_required
def get_statistics(current_user_id):
    """获取系统统计信息"""
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()

        # 用户统计
        cursor.execute('SELECT COUNT(*) FROM users WHERE is_active = 1')
        active_users = cursor.fetchone()[0]

        cursor.execute('SELECT COUNT(*) FROM users')
        total_users = cursor.fetchone()[0]

        cursor.execute('SELECT COUNT(*) FROM users WHERE is_admin = 1')
        admin_users = cursor.fetchone()[0]

        # 项目统计
        cursor.execute('SELECT COUNT(*) FROM projects WHERE is_deleted = 0')
        total_projects = cursor.fetchone()[0]

        # 剧集统计
        cursor.execute('SELECT COUNT(*) FROM episodes')
        total_episodes = cursor.fetchone()[0]

        # 分镜统计
        cursor.execute('SELECT COUNT(*) FROM storyboards')
        total_storyboards = cursor.fetchone()[0]

        # 资产统计
        cursor.execute('SELECT COUNT(*) FROM assets WHERE is_deleted = 0')
        total_assets = cursor.fetchone()[0]

        statistics = {
            'users': {
                'total': total_users,
                'active': active_users,
                'admins': admin_users
            },
            'projects': {
                'total': total_projects
            },
            'episodes': {
                'total': total_episodes
            },
            'storyboards': {
                'total': total_storyboards
            },
            'assets': {
                'total': total_assets
            }
        }

        return jsonify({'success': True, 'data': statistics}), 200

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        if conn:
            conn.close()
