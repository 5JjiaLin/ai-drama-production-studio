# 限流策略与防滥用机制

## 1. 限流算法选择

### 1.1 常见限流算法对比

| 算法 | 优点 | 缺点 | 适用场景 |
|------|------|------|----------|
| 固定窗口 | 实现简单，内存占用小 | 边界突刺问题 | 粗粒度限流 |
| 滑动窗口 | 平滑限流，精确控制 | 内存占用较大 | 精确限流 |
| 令牌桶 | 允许突发流量 | 实现复杂 | API网关 |
| 漏桶 | 流量平滑 | 无法应对突发 | 消息队列 |

### 1.2 推荐方案：滑动窗口 + Redis

**优势:**
- 精确控制请求速率
- 分布式环境友好
- 支持多维度限流(用户、IP、API)

---

## 2. Redis实现滑动窗口限流

### 2.1 核心实现

```python
import redis
import time
from typing import Optional
from functools import wraps
from flask import request, g

class RateLimiter:
    """基于Redis的滑动窗口限流器"""

    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client

    def is_allowed(
        self,
        key: str,
        limit: int,
        window: int = 60
    ) -> tuple[bool, dict]:
        """
        检查是否允许请求

        Args:
            key: 限流键(如 user:123 或 ip:192.168.1.1)
            limit: 限制次数
            window: 时间窗口(秒)

        Returns:
            (是否允许, 限流信息)
        """
        now = time.time()
        window_start = now - window

        pipe = self.redis.pipeline()

        # 1. 移除窗口外的记录
        pipe.zremrangebyscore(key, 0, window_start)

        # 2. 统计窗口内的请求数
        pipe.zcard(key)

        # 3. 添加当前请求
        pipe.zadd(key, {str(now): now})

        # 4. 设置过期时间
        pipe.expire(key, window + 1)

        results = pipe.execute()
        current_count = results[1]

        # 判断是否超限
        allowed = current_count < limit

        info = {
            'limit': limit,
            'remaining': max(0, limit - current_count - 1),
            'reset': int(now + window),
            'retry_after': None if allowed else window
        }

        return allowed, info

    def check_rate_limit(
        self,
        identifier: str,
        limit: int,
        window: int = 60,
        key_prefix: str = 'rate_limit'
    ) -> dict:
        """
        检查并记录限流

        Raises:
            RateLimitExceeded: 超过限流
        """
        key = f"{key_prefix}:{identifier}"
        allowed, info = self.is_allowed(key, limit, window)

        if not allowed:
            raise RateLimitExceeded(
                message=f"请求过于频繁，请在{info['retry_after']}秒后重试",
                details=info
            )

        return info
```

### 2.2 Lua脚本优化(原子操作)

```python
# 使用Lua脚本确保原子性
RATE_LIMIT_SCRIPT = """
local key = KEYS[1]
local limit = tonumber(ARGV[1])
local window = tonumber(ARGV[2])
local now = tonumber(ARGV[3])
local window_start = now - window

-- 移除过期记录
redis.call('ZREMRANGEBYSCORE', key, 0, window_start)

-- 获取当前计数
local current = redis.call('ZCARD', key)

if current < limit then
    -- 添加当前请求
    redis.call('ZADD', key, now, now)
    redis.call('EXPIRE', key, window + 1)
    return {1, limit - current - 1}
else
    return {0, 0}
end
"""

class OptimizedRateLimiter:
    """优化的限流器(使用Lua脚本)"""

    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
        self.script = self.redis.register_script(RATE_LIMIT_SCRIPT)

    def is_allowed(self, key: str, limit: int, window: int = 60) -> tuple[bool, dict]:
        """检查是否允许请求"""
        now = time.time()

        result = self.script(
            keys=[key],
            args=[limit, window, now]
        )

        allowed = bool(result[0])
        remaining = result[1]

        info = {
            'limit': limit,
            'remaining': remaining,
            'reset': int(now + window),
            'retry_after': None if allowed else window
        }

        return allowed, info
```

---

## 3. 多维度限流策略

### 3.1 用户级限流

```python
from flask import g

def user_rate_limit(limit: int = 100, window: int = 60):
    """
    用户级限流装饰器

    使用方式:
    @app.route('/api/projects')
    @login_required
    @user_rate_limit(limit=100, window=60)
    def get_projects():
        pass
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not hasattr(g, 'current_user_id'):
                raise UnauthorizedError("未登录")

            limiter = get_rate_limiter()
            key = f"user:{g.current_user_id}"

            try:
                info = limiter.check_rate_limit(key, limit, window)

                # 添加限流信息到响应头
                response = f(*args, **kwargs)
                if isinstance(response, tuple):
                    response, status_code = response
                else:
                    status_code = 200

                response.headers['X-RateLimit-Limit'] = str(info['limit'])
                response.headers['X-RateLimit-Remaining'] = str(info['remaining'])
                response.headers['X-RateLimit-Reset'] = str(info['reset'])

                return response, status_code

            except RateLimitExceeded as e:
                response = error_response(e)
                response.headers['Retry-After'] = str(e.details['retry_after'])
                return response

        return decorated_function
    return decorator
```

### 3.2 IP级限流

```python
def ip_rate_limit(limit: int = 1000, window: int = 3600):
    """
    IP级限流(防止恶意攻击)

    更宽松的限制，主要防止DDoS
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # 获取真实IP(考虑代理)
            ip = request.headers.get('X-Forwarded-For', request.remote_addr)
            if ',' in ip:
                ip = ip.split(',')[0].strip()

            limiter = get_rate_limiter()
            key = f"ip:{ip}"

            info = limiter.check_rate_limit(key, limit, window)

            return f(*args, **kwargs)

        return decorated_function
    return decorator
```

### 3.3 API端点级限流

```python
def endpoint_rate_limit(limit: int = 10, window: int = 60):
    """
    API端点级限流(针对特定昂贵操作)

    例如: AI调用、文件上传等
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            user_id = g.get('current_user_id', 'anonymous')
            endpoint = request.endpoint

            limiter = get_rate_limiter()
            key = f"endpoint:{user_id}:{endpoint}"

            info = limiter.check_rate_limit(key, limit, window)

            return f(*args, **kwargs)

        return decorated_function
    return decorator
```

### 3.4 组合限流策略

```python
@app.route('/api/episodes/<int:episode_id>/extract-assets', methods=['POST'])
@login_required
@ip_rate_limit(limit=1000, window=3600)  # IP限流: 1000次/小时
@user_rate_limit(limit=100, window=3600)  # 用户限流: 100次/小时
@endpoint_rate_limit(limit=10, window=60)  # 端点限流: 10次/分钟
def extract_assets(episode_id: int):
    """提取资产(多层限流保护)"""
    pass
```

---

## 4. 基于订阅等级的动态限流

### 4.1 订阅等级配置

```python
from enum import Enum

class SubscriptionTier(Enum):
    FREE = "FREE"
    PRO = "PRO"
    ENTERPRISE = "ENTERPRISE"

# 限流配置
RATE_LIMIT_CONFIG = {
    SubscriptionTier.FREE: {
        'requests_per_minute': 10,
        'requests_per_hour': 100,
        'requests_per_day': 500,
        'ai_calls_per_day': 10,
        'concurrent_tasks': 1
    },
    SubscriptionTier.PRO: {
        'requests_per_minute': 60,
        'requests_per_hour': 1000,
        'requests_per_day': 10000,
        'ai_calls_per_day': 100,
        'concurrent_tasks': 5
    },
    SubscriptionTier.ENTERPRISE: {
        'requests_per_minute': 300,
        'requests_per_hour': 10000,
        'requests_per_day': 100000,
        'ai_calls_per_day': 1000,
        'concurrent_tasks': 20
    }
}
```

### 4.2 动态限流装饰器

```python
def dynamic_rate_limit(limit_type: str = 'requests_per_minute'):
    """
    基于用户订阅等级的动态限流

    Args:
        limit_type: 限流类型(requests_per_minute/requests_per_hour等)
    """
    def decorator(f):
        @wraps(f)
        @login_required
        def decorated_function(*args, **kwargs):
            user = g.current_user
            tier = SubscriptionTier(user.subscription_tier)

            # 获取该等级的限流配置
            config = RATE_LIMIT_CONFIG[tier]
            limit = config.get(limit_type, 10)

            # 确定时间窗口
            window_map = {
                'requests_per_minute': 60,
                'requests_per_hour': 3600,
                'requests_per_day': 86400,
                'ai_calls_per_day': 86400
            }
            window = window_map.get(limit_type, 60)

            # 执行限流检查
            limiter = get_rate_limiter()
            key = f"user:{user.id}:{limit_type}"

            info = limiter.check_rate_limit(key, limit, window)

            return f(*args, **kwargs)

        return decorated_function
    return decorator
```

---

## 5. 并发控制

### 5.1 限制并发任务数

```python
class ConcurrencyLimiter:
    """并发任务限制器"""

    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client

    def acquire(self, key: str, limit: int, timeout: int = 300) -> bool:
        """
        获取并发槽位

        Args:
            key: 限流键
            limit: 最大并发数
            timeout: 超时时间(秒)

        Returns:
            是否获取成功
        """
        now = time.time()

        # 清理过期的槽位
        self.redis.zremrangebyscore(key, 0, now - timeout)

        # 检查当前并发数
        current = self.redis.zcard(key)

        if current >= limit:
            return False

        # 占用槽位
        self.redis.zadd(key, {str(now): now})
        self.redis.expire(key, timeout + 60)

        return True

    def release(self, key: str, slot_id: str):
        """释放并发槽位"""
        self.redis.zrem(key, slot_id)

    def get_current_count(self, key: str) -> int:
        """获取当前并发数"""
        return self.redis.zcard(key)
```

### 5.2 并发控制装饰器

```python
def concurrent_limit(max_concurrent: int = 5):
    """
    并发任务限制装饰器

    使用方式:
    @app.route('/api/heavy-task')
    @login_required
    @concurrent_limit(max_concurrent=3)
    def heavy_task():
        pass
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            user_id = g.current_user_id
            limiter = ConcurrencyLimiter(redis_client)

            key = f"concurrent:{user_id}:{request.endpoint}"
            slot_id = str(time.time())

            # 尝试获取槽位
            if not limiter.acquire(key, max_concurrent):
                current = limiter.get_current_count(key)
                raise RateLimitExceeded(
                    message=f"并发任务数已达上限({max_concurrent})，当前: {current}",
                    details={
                        'max_concurrent': max_concurrent,
                        'current': current
                    }
                )

            try:
                # 执行任务
                result = f(*args, **kwargs)
                return result

            finally:
                # 释放槽位
                limiter.release(key, slot_id)

        return decorated_function
    return decorator
```

---

## 6. 防滥用策略

### 6.1 异常行为检测

```python
class AbuseDetector:
    """滥用检测器"""

    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client

    def track_failed_attempts(self, user_id: int, action: str):
        """
        追踪失败尝试

        Args:
            user_id: 用户ID
            action: 操作类型(login/api_call等)
        """
        key = f"failed:{action}:{user_id}"
        count = self.redis.incr(key)
        self.redis.expire(key, 3600)  # 1小时过期

        # 失败次数过多，触发告警
        if count > 10:
            self._trigger_abuse_alert(user_id, action, count)

        # 失败次数超过阈值，临时封禁
        if count > 20:
            self._temporary_ban(user_id, duration=3600)

    def _trigger_abuse_alert(self, user_id: int, action: str, count: int):
        """触发滥用告警"""
        logger.warning(f"检测到异常行为: user_id={user_id}, action={action}, count={count}")

        # 发送告警通知
        from tasks.notification_tasks import send_abuse_alert
        send_abuse_alert.delay(user_id, action, count)

    def _temporary_ban(self, user_id: int, duration: int):
        """临时封禁用户"""
        key = f"banned:user:{user_id}"
        self.redis.setex(key, duration, "1")

        logger.error(f"用户被临时封禁: user_id={user_id}, duration={duration}秒")

    def is_banned(self, user_id: int) -> bool:
        """检查用户是否被封禁"""
        key = f"banned:user:{user_id}"
        return self.redis.exists(key)
```

### 6.2 请求指纹识别

```python
import hashlib

def generate_request_fingerprint() -> str:
    """
    生成请求指纹(用于检测重复请求)

    基于: IP + User-Agent + 请求路径 + 请求体
    """
    components = [
        request.remote_addr,
        request.headers.get('User-Agent', ''),
        request.path,
        request.get_data(as_text=True)
    ]

    fingerprint_str = '|'.join(components)
    return hashlib.sha256(fingerprint_str.encode()).hexdigest()

def deduplicate_request(window: int = 5):
    """
    请求去重装饰器(防止重复提交)

    Args:
        window: 去重时间窗口(秒)
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            fingerprint = generate_request_fingerprint()
            key = f"dedup:{fingerprint}"

            # 检查是否重复
            if redis_client.exists(key):
                raise ValidationError("请勿重复提交")

            # 标记请求
            redis_client.setex(key, window, "1")

            return f(*args, **kwargs)

        return decorated_function
    return decorator
```

### 6.3 蜜罐端点

```python
@app.route('/api/admin/secret', methods=['GET'])
def honeypot_endpoint():
    """
    蜜罐端点(检测恶意扫描)

    正常用户不会访问此端点
    """
    ip = request.remote_addr

    # 记录恶意访问
    logger.warning(f"检测到恶意扫描: IP={ip}")

    # 加入黑名单
    redis_client.sadd('blacklist:ips', ip)

    # 返回假数据
    return jsonify({'error': 'Not Found'}), 404
```

---

## 7. 限流监控与告警

### 7.1 限流指标收集

```python
class RateLimitMetrics:
    """限流指标收集器"""

    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client

    def record_rate_limit_hit(self, user_id: int, endpoint: str):
        """记录限流触发"""
        key = f"metrics:rate_limit_hits:{endpoint}"
        self.redis.hincrby(key, str(user_id), 1)
        self.redis.expire(key, 86400)  # 保留24小时

    def get_top_limited_users(self, endpoint: str, limit: int = 10) -> list:
        """获取触发限流最多的用户"""
        key = f"metrics:rate_limit_hits:{endpoint}"
        results = self.redis.hgetall(key)

        # 排序
        sorted_results = sorted(
            results.items(),
            key=lambda x: int(x[1]),
            reverse=True
        )

        return sorted_results[:limit]
```

### 7.2 限流告警

```python
@celery_app.task(name='tasks.monitoring.check_rate_limit_abuse')
def check_rate_limit_abuse():
    """定期检查限流滥用情况"""
    metrics = RateLimitMetrics(redis_client)

    # 检查各端点的限流情况
    endpoints = [
        '/api/episodes/<int:episode_id>/extract-assets',
        '/api/projects',
        '/api/assets/merge'
    ]

    for endpoint in endpoints:
        top_users = metrics.get_top_limited_users(endpoint, limit=5)

        for user_id, count in top_users:
            if int(count) > 100:  # 触发超过100次
                logger.warning(
                    f"用户频繁触发限流: user_id={user_id}, "
                    f"endpoint={endpoint}, count={count}"
                )

                # 发送告警
                send_alert_notification(
                    title="限流滥用告警",
                    message=f"用户{user_id}在{endpoint}触发限流{count}次"
                )
```

---

下一部分将详细分析：日志监控架构、部署方案。是否继续?
