# AI服务网关设计

## 1. 架构概述

AI服务网关是系统的核心组件，负责统一管理多个AI提供商的调用、配额控制、重试机制和降级策略。

### 1.1 设计目标

- **统一接口**: 屏蔽不同AI提供商的API差异
- **配额管理**: 用户级和系统级配额控制
- **高可用**: 自动重试、降级、熔断
- **可观测**: 完整的调用链追踪和监控
- **成本优化**: 智能路由、缓存策略

### 1.2 架构图

```
┌─────────────────────────────────────────────────────────┐
│                   API Layer (Flask)                      │
└─────────────────────────────────────────────────────────┘
                            │
┌─────────────────────────────────────────────────────────┐
│                  AI Gateway Facade                       │
│  ┌──────────────────────────────────────────────────┐  │
│  │  - Request Validation                             │  │
│  │  - Quota Check                                    │  │
│  │  - Provider Selection                             │  │
│  │  - Response Normalization                         │  │
│  └──────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
                            │
        ┌───────────────────┼───────────────────┐
        │                   │                   │
┌───────▼──────┐   ┌───────▼──────┐   ┌───────▼──────┐
│   Circuit    │   │    Retry     │   │   Rate       │
│   Breaker    │   │   Handler    │   │   Limiter    │
└───────┬──────┘   └───────┬──────┘   └───────┬──────┘
        └───────────────────┼───────────────────┘
                            │
        ┌───────────────────┼───────────────────┐
        │                   │                   │
┌───────▼──────┐   ┌───────▼──────┐   ┌───────▼──────┐
│   Claude     │   │  DeepSeek    │   │   Gemini     │
│   Provider   │   │   Provider   │   │   Provider   │
└──────────────┘   └──────────────┘   └──────────────┘
```

---

## 2. 核心组件设计

### 2.1 AI Provider 抽象层

**基础接口定义:**

```python
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum

class AIProviderType(Enum):
    CLAUDE = "claude"
    DEEPSEEK = "deepseek"
    GEMINI = "gemini"
    GPT4 = "gpt4"

@dataclass
class AIRequest:
    """统一的AI请求格式"""
    prompt: str
    model: str
    max_tokens: int = 4096
    temperature: float = 0.7
    user_id: Optional[int] = None
    metadata: Dict[str, Any] = None

@dataclass
class AIResponse:
    """统一的AI响应格式"""
    content: str
    provider: AIProviderType
    model: str
    tokens_used: int
    latency_ms: int
    request_id: str
    metadata: Dict[str, Any] = None

class AIProviderError(Exception):
    """AI提供商错误基类"""
    pass

class QuotaExceededError(AIProviderError):
    """配额超限错误"""
    pass

class RateLimitError(AIProviderError):
    """速率限制错误"""
    pass

class ProviderUnavailableError(AIProviderError):
    """提供商不可用错误"""
    pass

class BaseAIProvider(ABC):
    """AI提供商基类"""

    def __init__(self, api_key: str, config: Dict[str, Any] = None):
        self.api_key = api_key
        self.config = config or {}
        self.provider_type = None

    @abstractmethod
    async def call(self, request: AIRequest) -> AIResponse:
        """调用AI服务"""
        pass

    @abstractmethod
    def validate_config(self) -> bool:
        """验证配置"""
        pass

    @abstractmethod
    def get_cost_per_token(self, model: str) -> float:
        """获取每token成本"""
        pass

    def estimate_cost(self, tokens: int, model: str) -> float:
        """估算成本"""
        return tokens * self.get_cost_per_token(model)
```

### 2.2 Claude Provider 实现

```python
import anthropic
import time
from typing import Dict, Any

class ClaudeProvider(BaseAIProvider):
    """Claude AI提供商"""

    MODELS = {
        "claude-sonnet-4-5": {
            "max_tokens": 8192,
            "cost_per_1k_input": 0.003,
            "cost_per_1k_output": 0.015
        },
        "claude-3-5-sonnet": {
            "max_tokens": 8192,
            "cost_per_1k_input": 0.003,
            "cost_per_1k_output": 0.015
        }
    }

    def __init__(self, api_key: str, config: Dict[str, Any] = None):
        super().__init__(api_key, config)
        self.provider_type = AIProviderType.CLAUDE
        self.client = anthropic.Anthropic(api_key=api_key)

    def validate_config(self) -> bool:
        """验证API密钥"""
        try:
            # 发送测试请求
            self.client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=10,
                messages=[{"role": "user", "content": "test"}]
            )
            return True
        except Exception:
            return False

    async def call(self, request: AIRequest) -> AIResponse:
        """调用Claude API"""
        start_time = time.time()

        try:
            response = self.client.messages.create(
                model=request.model or "claude-sonnet-4-5-20250929",
                max_tokens=request.max_tokens,
                temperature=request.temperature,
                messages=[
                    {"role": "user", "content": request.prompt}
                ]
            )

            latency_ms = int((time.time() - start_time) * 1000)

            return AIResponse(
                content=response.content[0].text,
                provider=self.provider_type,
                model=response.model,
                tokens_used=response.usage.input_tokens + response.usage.output_tokens,
                latency_ms=latency_ms,
                request_id=response.id,
                metadata={
                    "input_tokens": response.usage.input_tokens,
                    "output_tokens": response.usage.output_tokens,
                    "stop_reason": response.stop_reason
                }
            )

        except anthropic.RateLimitError as e:
            raise RateLimitError(f"Claude速率限制: {str(e)}")
        except anthropic.APIError as e:
            raise ProviderUnavailableError(f"Claude API错误: {str(e)}")
        except Exception as e:
            raise AIProviderError(f"Claude调用失败: {str(e)}")

    def get_cost_per_token(self, model: str) -> float:
        """获取每token成本(平均值)"""
        model_config = self.MODELS.get(model, self.MODELS["claude-3-5-sonnet"])
        avg_cost = (model_config["cost_per_1k_input"] + model_config["cost_per_1k_output"]) / 2
        return avg_cost / 1000
```

### 2.3 Provider Factory

```python
class AIProviderFactory:
    """AI提供商工厂"""

    _providers: Dict[AIProviderType, type] = {
        AIProviderType.CLAUDE: ClaudeProvider,
        AIProviderType.DEEPSEEK: DeepSeekProvider,
        AIProviderType.GEMINI: GeminiProvider,
        AIProviderType.GPT4: GPT4Provider,
    }

    @classmethod
    def create(cls, provider_type: AIProviderType, api_key: str, config: Dict = None) -> BaseAIProvider:
        """创建提供商实例"""
        provider_class = cls._providers.get(provider_type)
        if not provider_class:
            raise ValueError(f"不支持的提供商: {provider_type}")

        return provider_class(api_key, config)

    @classmethod
    def register(cls, provider_type: AIProviderType, provider_class: type):
        """注册新提供商"""
        cls._providers[provider_type] = provider_class
```

---

## 3. 配额管理系统

### 3.1 配额模型设计

```python
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Float
from datetime import datetime, timedelta

class UserQuota(Base):
    """用户配额表"""
    __tablename__ = 'user_quotas'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, unique=True)

    # 配额限制
    quota_total = Column(Integer, default=100)  # 总配额(次数)
    quota_used = Column(Integer, default=0)     # 已使用
    quota_remaining = Column(Integer, default=100)  # 剩余

    # 速率限制
    rate_limit_per_minute = Column(Integer, default=10)
    rate_limit_per_hour = Column(Integer, default=100)
    rate_limit_per_day = Column(Integer, default=500)

    # 重置策略
    reset_period = Column(String, default='MONTHLY')  # DAILY/WEEKLY/MONTHLY
    last_reset_at = Column(DateTime, default=datetime.utcnow)
    next_reset_at = Column(DateTime)

    # 成本追踪
    total_cost = Column(Float, default=0.0)
    cost_limit = Column(Float, default=100.0)

    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class QuotaUsageLog(Base):
    """配额使用日志"""
    __tablename__ = 'quota_usage_logs'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)

    # 请求信息
    provider = Column(String, nullable=False)
    model = Column(String, nullable=False)
    tokens_used = Column(Integer, nullable=False)
    cost = Column(Float, nullable=False)

    # 元数据
    request_id = Column(String)
    endpoint = Column(String)  # 调用的API端点
    latency_ms = Column(Integer)

    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index('idx_quota_logs_user_created', 'user_id', 'created_at'),
    )
```

### 3.2 配额检查器

```python
from datetime import datetime, timedelta
from typing import Optional
import redis

class QuotaChecker:
    """配额检查器"""

    def __init__(self, db_session, redis_client: redis.Redis):
        self.db = db_session
        self.redis = redis_client

    def check_quota(self, user_id: int, estimated_tokens: int = 1000) -> bool:
        """检查用户配额"""
        # 1. 检查总配额
        quota = self._get_user_quota(user_id)
        if quota.quota_remaining <= 0:
            raise QuotaExceededError("配额已用尽，请升级套餐")

        # 2. 检查成本限制
        estimated_cost = self._estimate_cost(estimated_tokens)
        if quota.total_cost + estimated_cost > quota.cost_limit:
            raise QuotaExceededError("成本限制已达上限")

        # 3. 检查速率限制
        self._check_rate_limit(user_id, quota)

        return True

    def _get_user_quota(self, user_id: int) -> UserQuota:
        """获取用户配额(带缓存)"""
        cache_key = f"quota:user:{user_id}"
        cached = self.redis.get(cache_key)

        if cached:
            return UserQuota.from_json(cached)

        quota = self.db.query(UserQuota).filter_by(user_id=user_id).first()
        if not quota:
            # 创建默认配额
            quota = UserQuota(user_id=user_id)
            self.db.add(quota)
            self.db.commit()

        # 缓存5分钟
        self.redis.setex(cache_key, 300, quota.to_json())
        return quota

    def _check_rate_limit(self, user_id: int, quota: UserQuota):
        """检查速率限制(使用Redis滑动窗口)"""
        now = datetime.utcnow()

        # 每分钟限制
        key_minute = f"rate:user:{user_id}:minute:{now.strftime('%Y%m%d%H%M')}"
        count_minute = self.redis.incr(key_minute)
        self.redis.expire(key_minute, 60)

        if count_minute > quota.rate_limit_per_minute:
            raise RateLimitError("每分钟请求次数超限，请稍后重试")

        # 每小时限制
        key_hour = f"rate:user:{user_id}:hour:{now.strftime('%Y%m%d%H')}"
        count_hour = self.redis.incr(key_hour)
        self.redis.expire(key_hour, 3600)

        if count_hour > quota.rate_limit_per_hour:
            raise RateLimitError("每小时请求次数超限")

        # 每天限制
        key_day = f"rate:user:{user_id}:day:{now.strftime('%Y%m%d')}"
        count_day = self.redis.incr(key_day)
        self.redis.expire(key_day, 86400)

        if count_day > quota.rate_limit_per_day:
            raise RateLimitError("每日请求次数超限")

    def consume_quota(self, user_id: int, tokens_used: int, cost: float, provider: str, model: str):
        """消费配额"""
        with self.db.begin():
            # 悲观锁
            quota = self.db.query(UserQuota).filter_by(user_id=user_id).with_for_update().first()

            quota.quota_used += 1
            quota.quota_remaining -= 1
            quota.total_cost += cost

            # 记录使用日志
            log = QuotaUsageLog(
                user_id=user_id,
                provider=provider,
                model=model,
                tokens_used=tokens_used,
                cost=cost
            )
            self.db.add(log)
            self.db.flush()

        # 清除缓存
        self.redis.delete(f"quota:user:{user_id}")

    def _estimate_cost(self, tokens: int) -> float:
        """估算成本(使用平均价格)"""
        avg_cost_per_1k = 0.01  # $0.01 per 1k tokens
        return (tokens / 1000) * avg_cost_per_1k
```

---

## 4. 重试机制设计

### 4.1 指数退避重试

```python
import asyncio
from typing import Callable, TypeVar, Optional
import random

T = TypeVar('T')

class RetryStrategy:
    """重试策略"""

    def __init__(
        self,
        max_attempts: int = 3,
        initial_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_base: float = 2.0,
        jitter: bool = True
    ):
        self.max_attempts = max_attempts
        self.initial_delay = initial_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.jitter = jitter

    def get_delay(self, attempt: int) -> float:
        """计算延迟时间"""
        delay = min(
            self.initial_delay * (self.exponential_base ** attempt),
            self.max_delay
        )

        if self.jitter:
            # 添加随机抖动(0.5-1.5倍)
            delay *= (0.5 + random.random())

        return delay

class RetryHandler:
    """重试处理器"""

    # 可重试的错误类型
    RETRYABLE_ERRORS = (
        RateLimitError,
        ProviderUnavailableError,
        TimeoutError,
        ConnectionError
    )

    def __init__(self, strategy: RetryStrategy = None):
        self.strategy = strategy or RetryStrategy()

    async def execute_with_retry(
        self,
        func: Callable[..., T],
        *args,
        **kwargs
    ) -> T:
        """执行函数并自动重试"""
        last_exception = None

        for attempt in range(self.strategy.max_attempts):
            try:
                return await func(*args, **kwargs)

            except self.RETRYABLE_ERRORS as e:
                last_exception = e

                if attempt < self.strategy.max_attempts - 1:
                    delay = self.strategy.get_delay(attempt)
                    logger.warning(
                        f"重试 {attempt + 1}/{self.strategy.max_attempts}: {str(e)}, "
                        f"等待 {delay:.2f}秒"
                    )
                    await asyncio.sleep(delay)
                else:
                    logger.error(f"重试失败，已达最大尝试次数: {str(e)}")

            except Exception as e:
                # 不可重试的错误，直接抛出
                logger.error(f"不可重试的错误: {str(e)}")
                raise

        raise last_exception
```

### 4.2 重试策略配置

```python
# 不同场景的重试策略
RETRY_STRATEGIES = {
    "default": RetryStrategy(
        max_attempts=3,
        initial_delay=1.0,
        max_delay=10.0
    ),
    "aggressive": RetryStrategy(
        max_attempts=5,
        initial_delay=0.5,
        max_delay=30.0
    ),
    "conservative": RetryStrategy(
        max_attempts=2,
        initial_delay=2.0,
        max_delay=5.0
    )
}
```

---

## 5. 熔断器模式

### 5.1 熔断器实现

```python
from enum import Enum
from datetime import datetime, timedelta
from typing import Callable, Optional
import threading

class CircuitState(Enum):
    CLOSED = "closed"      # 正常状态
    OPEN = "open"          # 熔断状态
    HALF_OPEN = "half_open"  # 半开状态(测试恢复)

class CircuitBreaker:
    """熔断器"""

    def __init__(
        self,
        failure_threshold: int = 5,      # 失败阈值
        success_threshold: int = 2,      # 恢复阈值
        timeout: int = 60,               # 熔断超时(秒)
        window_size: int = 60            # 统计窗口(秒)
    ):
        self.failure_threshold = failure_threshold
        self.success_threshold = success_threshold
        self.timeout = timeout
        self.window_size = window_size

        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time: Optional[datetime] = None
        self.opened_at: Optional[datetime] = None

        self._lock = threading.Lock()

    def call(self, func: Callable, *args, **kwargs):
        """通过熔断器调用函数"""
        with self._lock:
            if self.state == CircuitState.OPEN:
                if self._should_attempt_reset():
                    self.state = CircuitState.HALF_OPEN
                    logger.info("熔断器进入半开状态，尝试恢复")
                else:
                    raise ProviderUnavailableError("熔断器已打开，服务暂时不可用")

        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result

        except Exception as e:
            self._on_failure()
            raise e

    def _on_success(self):
        """成功回调"""
        with self._lock:
            if self.state == CircuitState.HALF_OPEN:
                self.success_count += 1
                if self.success_count >= self.success_threshold:
                    self._reset()
                    logger.info("熔断器已关闭，服务恢复正常")
            else:
                self.failure_count = 0

    def _on_failure(self):
        """失败回调"""
        with self._lock:
            self.failure_count += 1
            self.last_failure_time = datetime.utcnow()

            if self.state == CircuitState.HALF_OPEN:
                self._trip()
                logger.warning("半开状态测试失败，熔断器重新打开")

            elif self.failure_count >= self.failure_threshold:
                self._trip()
                logger.error(f"失败次数达到阈值({self.failure_threshold})，熔断器打开")

    def _trip(self):
        """打开熔断器"""
        self.state = CircuitState.OPEN
        self.opened_at = datetime.utcnow()
        self.success_count = 0

    def _reset(self):
        """重置熔断器"""
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.opened_at = None

    def _should_attempt_reset(self) -> bool:
        """是否应该尝试恢复"""
        if self.opened_at is None:
            return False

        elapsed = (datetime.utcnow() - self.opened_at).total_seconds()
        return elapsed >= self.timeout

    def get_state(self) -> dict:
        """获取熔断器状态"""
        return {
            "state": self.state.value,
            "failure_count": self.failure_count,
            "success_count": self.success_count,
            "opened_at": self.opened_at.isoformat() if self.opened_at else None
        }
```

### 5.2 为每个Provider配置熔断器

```python
class AIGateway:
    """AI网关(集成熔断器)"""

    def __init__(self):
        self.providers: Dict[AIProviderType, BaseAIProvider] = {}
        self.circuit_breakers: Dict[AIProviderType, CircuitBreaker] = {}

        # 为每个提供商创建熔断器
        for provider_type in AIProviderType:
            self.circuit_breakers[provider_type] = CircuitBreaker(
                failure_threshold=5,
                timeout=60
            )

    async def call_provider(
        self,
        provider_type: AIProviderType,
        request: AIRequest
    ) -> AIResponse:
        """通过熔断器调用提供商"""
        circuit_breaker = self.circuit_breakers[provider_type]
        provider = self.providers[provider_type]

        return circuit_breaker.call(provider.call, request)
```

---

## 下一部分预告

接下来将详细分析:
- 降级策略和备用方案
- 智能路由和负载均衡
- 响应缓存策略
- 完整的AI Gateway实现示例

是否继续输出下一部分?
