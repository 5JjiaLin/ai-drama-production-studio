# 认证授权系统设计

## 1. JWT双Token机制

### 1.1 为什么使用双Token?

**单Token的问题:**
- Access Token过期时间长 → 安全风险高
- Access Token过期时间短 → 用户体验差(频繁登录)

**双Token方案:**
- **Access Token**: 短期有效(15分钟)，用于API访问
- **Refresh Token**: 长期有效(7天)，用于刷新Access Token

### 1.2 Token流程图

```
┌─────────┐                                    ┌─────────┐
│ Client  │                                    │ Server  │
└────┬────┘                                    └────┬────┘
     │                                              │
     │  1. POST /api/auth/login                    │
     │  { email, password }                        │
     ├─────────────────────────────────────────────>│
     │                                              │
     │  2. 验证用户凭证                              │
     │                                              │
     │  3. 生成Access Token + Refresh Token         │
     │  { access_token, refresh_token }            │
     │<─────────────────────────────────────────────┤
     │                                              │
     │  4. 存储tokens到localStorage/cookie          │
     │                                              │
     │  5. 使用Access Token访问API                  │
     │  Authorization: Bearer <access_token>       │
     ├─────────────────────────────────────────────>│
     │                                              │
     │  6. 验证Access Token                         │
     │  返回数据                                     │
     │<─────────────────────────────────────────────┤
     │                                              │
     │  7. Access Token过期                         │
     │  Authorization: Bearer <expired_token>      │
     ├─────────────────────────────────────────────>│
     │                                              │
     │  8. 返回401 Unauthorized                     │
     │<─────────────────────────────────────────────┤
     │                                              │
     │  9. POST /api/auth/refresh                  │
     │  { refresh_token }                          │
     ├─────────────────────────────────────────────>│
     │                                              │
     │  10. 验证Refresh Token                       │
     │  生成新的Access Token                        │
     │  { access_token }                           │
     │<─────────────────────────────────────────────┤
     │                                              │
```

---

## 2. 数据模型设计

### 2.1 用户表

```python
from sqlalchemy import Column, Integer, String, Boolean, DateTime
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    username = Column(String(100), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)

    # 个人信息
    full_name = Column(String(200))
    avatar_url = Column(String(500))

    # 账户状态
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    is_admin = Column(Boolean, default=False)

    # 订阅信息
    subscription_tier = Column(String(50), default='FREE')
    subscription_expires_at = Column(DateTime)

    # 配额
    quota_total = Column(Integer, default=100)
    quota_used = Column(Integer, default=0)
    quota_remaining = Column(Integer, default=100)

    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login_at = Column(DateTime)

    # 关系
    projects = relationship("Project", back_populates="user")
    refresh_tokens = relationship("RefreshToken", back_populates="user")

    def set_password(self, password: str):
        """设置密码"""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        """验证密码"""
        return check_password_hash(self.password_hash, password)

    def to_dict(self):
        """转换为字典"""
        return {
            'id': self.id,
            'email': self.email,
            'username': self.username,
            'full_name': self.full_name,
            'avatar_url': self.avatar_url,
            'subscription_tier': self.subscription_tier,
            'created_at': self.created_at.isoformat()
        }
```

### 2.2 Refresh Token表

```python
import secrets
from datetime import datetime, timedelta

class RefreshToken(Base):
    __tablename__ = 'refresh_tokens'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    token = Column(String(255), unique=True, nullable=False, index=True)

    # Token元数据
    device_info = Column(String(500))  # 设备信息
    ip_address = Column(String(50))
    user_agent = Column(String(500))

    # 状态
    is_revoked = Column(Boolean, default=False)
    revoked_at = Column(DateTime)

    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)
    last_used_at = Column(DateTime)

    # 关系
    user = relationship("User", back_populates="refresh_tokens")

    @staticmethod
    def generate_token() -> str:
        """生成安全的随机token"""
        return secrets.token_urlsafe(32)

    def is_expired(self) -> bool:
        """检查是否过期"""
        return datetime.utcnow() > self.expires_at

    def is_valid(self) -> bool:
        """检查是否有效"""
        return not self.is_revoked and not self.is_expired()
```

---

## 3. JWT实现

### 3.1 JWT工具类

```python
import jwt
from datetime import datetime, timedelta
from typing import Dict, Optional
from flask import current_app

class JWTManager:
    """JWT管理器"""

    @staticmethod
    def generate_access_token(user_id: int, additional_claims: Dict = None) -> str:
        """
        生成Access Token

        Args:
            user_id: 用户ID
            additional_claims: 额外的声明

        Returns:
            JWT token字符串
        """
        payload = {
            'user_id': user_id,
            'type': 'access',
            'iat': datetime.utcnow(),
            'exp': datetime.utcnow() + timedelta(minutes=15),  # 15分钟过期
            'jti': secrets.token_urlsafe(16)  # JWT ID(用于撤销)
        }

        if additional_claims:
            payload.update(additional_claims)

        return jwt.encode(
            payload,
            current_app.config['JWT_SECRET_KEY'],
            algorithm='HS256'
        )

    @staticmethod
    def generate_refresh_token_jwt(user_id: int, token_id: int) -> str:
        """
        生成Refresh Token的JWT表示(可选)

        注意: Refresh Token也可以使用随机字符串存储在数据库
        """
        payload = {
            'user_id': user_id,
            'token_id': token_id,
            'type': 'refresh',
            'iat': datetime.utcnow(),
            'exp': datetime.utcnow() + timedelta(days=7),  # 7天过期
        }

        return jwt.encode(
            payload,
            current_app.config['JWT_REFRESH_SECRET_KEY'],
            algorithm='HS256'
        )

    @staticmethod
    def decode_token(token: str, token_type: str = 'access') -> Dict:
        """
        解码并验证Token

        Args:
            token: JWT token
            token_type: token类型('access' or 'refresh')

        Returns:
            解码后的payload

        Raises:
            jwt.ExpiredSignatureError: Token过期
            jwt.InvalidTokenError: Token无效
        """
        secret_key = (
            current_app.config['JWT_SECRET_KEY']
            if token_type == 'access'
            else current_app.config['JWT_REFRESH_SECRET_KEY']
        )

        payload = jwt.decode(
            token,
            secret_key,
            algorithms=['HS256']
        )

        # 验证token类型
        if payload.get('type') != token_type:
            raise jwt.InvalidTokenError(f"Invalid token type: expected {token_type}")

        return payload

    @staticmethod
    def verify_access_token(token: str) -> Optional[int]:
        """
        验证Access Token并返回user_id

        Returns:
            user_id or None
        """
        try:
            payload = JWTManager.decode_token(token, 'access')

            # 检查是否在黑名单中
            if JWTManager.is_token_blacklisted(payload['jti']):
                return None

            return payload['user_id']

        except jwt.ExpiredSignatureError:
            raise TokenExpiredError("Access token已过期")
        except jwt.InvalidTokenError as e:
            raise InvalidTokenError(f"无效的token: {str(e)}")

    @staticmethod
    def is_token_blacklisted(jti: str) -> bool:
        """检查token是否在黑名单中(使用Redis)"""
        from extensions import redis_client
        return redis_client.exists(f"blacklist:token:{jti}")

    @staticmethod
    def blacklist_token(jti: str, expires_in: int = 900):
        """将token加入黑名单"""
        from extensions import redis_client
        redis_client.setex(f"blacklist:token:{jti}", expires_in, "1")
```

---

## 4. 认证装饰器

### 4.1 登录验证装饰器

```python
from functools import wraps
from flask import request, jsonify, g
import jwt

def login_required(f):
    """
    登录验证装饰器

    使用方式:
    @app.route('/api/protected')
    @login_required
    def protected_route():
        user_id = g.current_user_id
        return {'message': 'success'}
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # 1. 从请求头获取token
        auth_header = request.headers.get('Authorization')

        if not auth_header:
            return jsonify({'error': '缺少Authorization头'}), 401

        try:
            # 2. 解析Bearer token
            scheme, token = auth_header.split()
            if scheme.lower() != 'bearer':
                return jsonify({'error': '无效的认证方案'}), 401

        except ValueError:
            return jsonify({'error': '无效的Authorization头格式'}), 401

        # 3. 验证token
        try:
            user_id = JWTManager.verify_access_token(token)

            if not user_id:
                return jsonify({'error': 'Token无效'}), 401

            # 4. 加载用户信息
            user = User.query.get(user_id)
            if not user or not user.is_active:
                return jsonify({'error': '用户不存在或已禁用'}), 401

            # 5. 将用户信息存储到g对象
            g.current_user_id = user_id
            g.current_user = user

        except TokenExpiredError:
            return jsonify({'error': 'Token已过期', 'code': 'TOKEN_EXPIRED'}), 401
        except InvalidTokenError as e:
            return jsonify({'error': str(e)}), 401

        return f(*args, **kwargs)

    return decorated_function
```

### 4.2 权限验证装饰器

```python
def admin_required(f):
    """管理员权限验证"""
    @wraps(f)
    @login_required
    def decorated_function(*args, **kwargs):
        if not g.current_user.is_admin:
            return jsonify({'error': '需要管理员权限'}), 403

        return f(*args, **kwargs)

    return decorated_function

def subscription_required(tier: str):
    """订阅等级验证"""
    def decorator(f):
        @wraps(f)
        @login_required
        def decorated_function(*args, **kwargs):
            tier_levels = {'FREE': 0, 'PRO': 1, 'ENTERPRISE': 2}

            user_level = tier_levels.get(g.current_user.subscription_tier, 0)
            required_level = tier_levels.get(tier, 0)

            if user_level < required_level:
                return jsonify({
                    'error': f'需要{tier}订阅',
                    'current_tier': g.current_user.subscription_tier
                }), 403

            return f(*args, **kwargs)

        return decorated_function
    return decorator
```

---

## 5. 认证API实现

### 5.1 用户注册

```python
from flask import Blueprint, request, jsonify
from sqlalchemy.exc import IntegrityError

auth_bp = Blueprint('auth', __name__, url_prefix='/api/auth')

@auth_bp.route('/register', methods=['POST'])
def register():
    """
    用户注册

    请求体:
    {
        "email": "user@example.com",
        "username": "username",
        "password": "password123",
        "full_name": "Full Name"
    }
    """
    data = request.get_json()

    # 验证必填字段
    required_fields = ['email', 'username', 'password']
    for field in required_fields:
        if not data.get(field):
            return jsonify({'error': f'{field}不能为空'}), 400

    # 验证邮箱格式
    import re
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(email_pattern, data['email']):
        return jsonify({'error': '邮箱格式无效'}), 400

    # 验证密码强度
    if len(data['password']) < 8:
        return jsonify({'error': '密码长度至少8位'}), 400

    try:
        # 创建用户
        user = User(
            email=data['email'].lower(),
            username=data['username'],
            full_name=data.get('full_name', '')
        )
        user.set_password(data['password'])

        db.session.add(user)
        db.session.commit()

        # 发送验证邮件(异步)
        from tasks.email_tasks import send_verification_email
        send_verification_email.delay(user.id)

        return jsonify({
            'message': '注册成功，请查收验证邮件',
            'user': user.to_dict()
        }), 201

    except IntegrityError:
        db.session.rollback()
        return jsonify({'error': '邮箱或用户名已存在'}), 400
```

### 5.2 用户登录

```python
@auth_bp.route('/login', methods=['POST'])
def login():
    """
    用户登录

    请求体:
    {
        "email": "user@example.com",
        "password": "password123"
    }

    响应:
    {
        "access_token": "eyJ...",
        "refresh_token": "abc...",
        "user": {...}
    }
    """
    data = request.get_json()

    email = data.get('email')
    password = data.get('password')

    if not email or not password:
        return jsonify({'error': '邮箱和密码不能为空'}), 400

    # 查找用户
    user = User.query.filter_by(email=email.lower()).first()

    if not user or not user.check_password(password):
        return jsonify({'error': '邮箱或密码错误'}), 401

    # 检查账户状态
    if not user.is_active:
        return jsonify({'error': '账户已被禁用'}), 403

    # 生成tokens
    access_token = JWTManager.generate_access_token(user.id)

    # 创建refresh token记录
    refresh_token_record = RefreshToken(
        user_id=user.id,
        token=RefreshToken.generate_token(),
        device_info=request.headers.get('User-Agent', ''),
        ip_address=request.remote_addr,
        expires_at=datetime.utcnow() + timedelta(days=7)
    )
    db.session.add(refresh_token_record)

    # 更新最后登录时间
    user.last_login_at = datetime.utcnow()
    db.session.commit()

    return jsonify({
        'access_token': access_token,
        'refresh_token': refresh_token_record.token,
        'token_type': 'Bearer',
        'expires_in': 900,  # 15分钟
        'user': user.to_dict()
    })
```

### 5.3 刷新Token

```python
@auth_bp.route('/refresh', methods=['POST'])
def refresh():
    """
    刷新Access Token

    请求体:
    {
        "refresh_token": "abc..."
    }

    响应:
    {
        "access_token": "eyJ..."
    }
    """
    data = request.get_json()
    refresh_token = data.get('refresh_token')

    if not refresh_token:
        return jsonify({'error': '缺少refresh_token'}), 400

    # 查找refresh token
    token_record = RefreshToken.query.filter_by(token=refresh_token).first()

    if not token_record:
        return jsonify({'error': '无效的refresh token'}), 401

    # 验证token有效性
    if not token_record.is_valid():
        return jsonify({'error': 'Refresh token已过期或已撤销'}), 401

    # 生成新的access token
    access_token = JWTManager.generate_access_token(token_record.user_id)

    # 更新最后使用时间
    token_record.last_used_at = datetime.utcnow()
    db.session.commit()

    return jsonify({
        'access_token': access_token,
        'token_type': 'Bearer',
        'expires_in': 900
    })
```

### 5.4 登出

```python
@auth_bp.route('/logout', methods=['POST'])
@login_required
def logout():
    """
    用户登出

    请求体:
    {
        "refresh_token": "abc..."  # 可选
    }
    """
    data = request.get_json() or {}

    # 1. 将当前access token加入黑名单
    auth_header = request.headers.get('Authorization')
    if auth_header:
        token = auth_header.split()[1]
        try:
            payload = JWTManager.decode_token(token, 'access')
            JWTManager.blacklist_token(payload['jti'], expires_in=900)
        except:
            pass

    # 2. 撤销refresh token
    refresh_token = data.get('refresh_token')
    if refresh_token:
        token_record = RefreshToken.query.filter_by(
            token=refresh_token,
            user_id=g.current_user_id
        ).first()

        if token_record:
            token_record.is_revoked = True
            token_record.revoked_at = datetime.utcnow()
            db.session.commit()

    return jsonify({'message': '登出成功'})
```

---

## 6. 会话管理

### 6.1 查看活跃会话

```python
@auth_bp.route('/sessions', methods=['GET'])
@login_required
def get_sessions():
    """获取用户的所有活跃会话"""
    sessions = RefreshToken.query.filter_by(
        user_id=g.current_user_id,
        is_revoked=False
    ).filter(
        RefreshToken.expires_at > datetime.utcnow()
    ).order_by(
        RefreshToken.last_used_at.desc()
    ).all()

    return jsonify({
        'sessions': [
            {
                'id': s.id,
                'device_info': s.device_info,
                'ip_address': s.ip_address,
                'created_at': s.created_at.isoformat(),
                'last_used_at': s.last_used_at.isoformat() if s.last_used_at else None,
                'is_current': s.token == request.headers.get('X-Refresh-Token')
            }
            for s in sessions
        ]
    })
```

### 6.2 撤销会话

```python
@auth_bp.route('/sessions/<int:session_id>', methods=['DELETE'])
@login_required
def revoke_session(session_id: int):
    """撤销指定会话"""
    session = RefreshToken.query.filter_by(
        id=session_id,
        user_id=g.current_user_id
    ).first()

    if not session:
        return jsonify({'error': '会话不存在'}), 404

    session.is_revoked = True
    session.revoked_at = datetime.utcnow()
    db.session.commit()

    return jsonify({'message': '会话已撤销'})
```

---

下一部分将详细分析：API设计规范、限流策略、错误处理等内容。是否继续?
