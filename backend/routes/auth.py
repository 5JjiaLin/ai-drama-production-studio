"""
用户认证路由
实现注册、登录、登出、token刷新等功能
"""
from datetime import datetime, timedelta
from flask import Blueprint, request, jsonify, current_app
from werkzeug.security import generate_password_hash, check_password_hash
import jwt
import re
from functools import wraps
import sys
import os

# 添加backend目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 创建蓝图
auth_bp = Blueprint('auth', __name__, url_prefix='/api/auth')

# JWT配置（后续从app.config获取）
JWT_SECRET_KEY = 'dev-secret-key-change-in-production'
JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=1)
JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=7)


def validate_email(email):
    """验证邮箱格式"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None


def validate_password(password):
    """验证密码强度（至少8位，包含字母和数字）"""
    if len(password) < 8:
        return False, "密码至少需要8个字符"
    if not re.search(r'[A-Za-z]', password):
        return False, "密码必须包含字母"
    if not re.search(r'\d', password):
        return False, "密码必须包含数字"
    return True, ""


def generate_token(user_id, token_type='access'):
    """生成JWT token"""
    expires = JWT_ACCESS_TOKEN_EXPIRES if token_type == 'access' else JWT_REFRESH_TOKEN_EXPIRES
    payload = {
        'user_id': user_id,
        'type': token_type,
        'exp': datetime.utcnow() + expires,
        'iat': datetime.utcnow()
    }
    return jwt.encode(payload, JWT_SECRET_KEY, algorithm='HS256')


def decode_token(token):
    """解码JWT token"""
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=['HS256'])
        return payload, None
    except jwt.ExpiredSignatureError:
        return None, "Token已过期"
    except jwt.InvalidTokenError:
        return None, "无效的Token"


def token_required(f):
    """认证装饰器 - 保护需要登录的API"""
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None

        # 从请求头获取token
        if 'Authorization' in request.headers:
            auth_header = request.headers['Authorization']
            try:
                token = auth_header.split(' ')[1]  # Bearer <token>
            except IndexError:
                return jsonify({'success': False, 'error': '无效的Authorization头'}), 401

        if not token:
            return jsonify({'success': False, 'error': '缺少认证token'}), 401

        # 解码token
        payload, error = decode_token(token)
        if error:
            return jsonify({'success': False, 'error': error}), 401

        # 将user_id传递给路由函数
        return f(payload['user_id'], *args, **kwargs)

    return decorated


@auth_bp.route('/register', methods=['POST'])
def register():
    """用户注册"""
    from app import get_db

    data = request.get_json()

    # 验证必填字段
    if not data or not data.get('username') or not data.get('email') or not data.get('password'):
        return jsonify({
            'success': False,
            'error': '用户名、邮箱和密码为必填项'
        }), 400

    username = data['username'].strip()
    email = data['email'].strip().lower()
    password = data['password']
    full_name = data.get('full_name', '').strip()

    # 验证邮箱格式
    if not validate_email(email):
        return jsonify({'success': False, 'error': '邮箱格式不正确'}), 400

    # 验证密码强度
    is_valid, msg = validate_password(password)
    if not is_valid:
        return jsonify({'success': False, 'error': msg}), 400

    # 验证用户名长度
    if len(username) < 3 or len(username) > 50:
        return jsonify({'success': False, 'error': '用户名长度必须在3-50个字符之间'}), 400

    try:
        conn = get_db()
        cursor = conn.cursor()

        # 检查用户名是否已存在
        cursor.execute("SELECT id FROM users WHERE username = ?", (username,))
        if cursor.fetchone():
            return jsonify({'success': False, 'error': '用户名已被使用'}), 400

        # 检查邮箱是否已存在
        cursor.execute("SELECT id FROM users WHERE email = ?", (email,))
        if cursor.fetchone():
            return jsonify({'success': False, 'error': '邮箱已被注册'}), 400

        # 创建用户
        password_hash = generate_password_hash(password)
        cursor.execute("""
            INSERT INTO users (username, email, password_hash, full_name, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (username, email, password_hash, full_name, datetime.utcnow(), datetime.utcnow()))

        user_id = cursor.lastrowid
        conn.commit()

        # 生成token
        access_token = generate_token(user_id, 'access')
        refresh_token = generate_token(user_id, 'refresh')

        return jsonify({
            'success': True,
            'message': '注册成功',
            'data': {
                'user': {
                    'id': user_id,
                    'username': username,
                    'email': email,
                    'full_name': full_name
                },
                'access_token': access_token,
                'refresh_token': refresh_token
            }
        }), 201

    except Exception as e:
        conn.rollback()
        return jsonify({'success': False, 'error': f'注册失败: {str(e)}'}), 500


@auth_bp.route('/login', methods=['POST'])
def login():
    """用户登录"""
    from app import get_db

    data = request.get_json()

    # 验证必填字段
    if not data or not data.get('username') or not data.get('password'):
        return jsonify({
            'success': False,
            'error': '用户名和密码为必填项'
        }), 400

    username = data['username'].strip()
    password = data['password']

    try:
        conn = get_db()
        cursor = conn.cursor()

        # 查询用户（支持用户名或邮箱登录）
        cursor.execute("""
            SELECT id, username, email, password_hash, full_name, is_active
            FROM users
            WHERE username = ? OR email = ?
        """, (username, username))

        user = cursor.fetchone()

        if not user:
            return jsonify({'success': False, 'error': '用户名或密码错误'}), 401

        user_id, username, email, password_hash, full_name, is_active = user

        # 检查账户是否激活
        if not is_active:
            return jsonify({'success': False, 'error': '账户已被禁用'}), 403

        # 验证密码
        if not check_password_hash(password_hash, password):
            return jsonify({'success': False, 'error': '用户名或密码错误'}), 401

        # 更新最后登录时间
        cursor.execute("UPDATE users SET last_login_at = ? WHERE id = ?",
                      (datetime.utcnow(), user_id))
        conn.commit()

        # 生成token
        access_token = generate_token(user_id, 'access')
        refresh_token = generate_token(user_id, 'refresh')

        return jsonify({
            'success': True,
            'message': '登录成功',
            'data': {
                'user': {
                    'id': user_id,
                    'username': username,
                    'email': email,
                    'full_name': full_name
                },
                'access_token': access_token,
                'refresh_token': refresh_token
            }
        }), 200

    except Exception as e:
        return jsonify({'success': False, 'error': f'登录失败: {str(e)}'}), 500


@auth_bp.route('/me', methods=['GET'])
@token_required
def get_current_user(current_user_id):
    """获取当前登录用户信息"""
    from app import get_db

    try:
        conn = get_db()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT id, username, email, full_name, is_active, created_at, last_login_at
            FROM users
            WHERE id = ?
        """, (current_user_id,))

        user = cursor.fetchone()

        if not user:
            return jsonify({'success': False, 'error': '用户不存在'}), 404

        user_id, username, email, full_name, is_active, created_at, last_login_at = user

        return jsonify({
            'success': True,
            'data': {
                'id': user_id,
                'username': username,
                'email': email,
                'full_name': full_name,
                'is_active': is_active,
                'created_at': created_at,
                'last_login_at': last_login_at
            }
        }), 200

    except Exception as e:
        return jsonify({'success': False, 'error': f'获取用户信息失败: {str(e)}'}), 500


@auth_bp.route('/logout', methods=['POST'])
@token_required
def logout(current_user_id):
    """用户登出（JWT无状态，前端删除token即可）"""
    return jsonify({
        'success': True,
        'message': '登出成功'
    }), 200


@auth_bp.route('/refresh', methods=['POST'])
def refresh_token():
    """刷新access token"""
    data = request.get_json()

    if not data or not data.get('refresh_token'):
        return jsonify({'success': False, 'error': '缺少refresh_token'}), 400

    refresh_token = data['refresh_token']

    # 解码refresh token
    payload, error = decode_token(refresh_token)
    if error:
        return jsonify({'success': False, 'error': error}), 401

    # 验证token类型
    if payload.get('type') != 'refresh':
        return jsonify({'success': False, 'error': '无效的refresh token'}), 401

    # 生成新的access token
    user_id = payload['user_id']
    new_access_token = generate_token(user_id, 'access')

    return jsonify({
        'success': True,
        'data': {
            'access_token': new_access_token
        }
    }), 200

