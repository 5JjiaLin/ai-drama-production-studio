# 部署架构方案

## 1. 部署架构选型

### 1.1 方案对比

| 方案 | 优点 | 缺点 | 适用场景 |
|------|------|------|----------|
| 传统部署 | 简单、成本低 | 扩展性差、运维复杂 | MVP阶段 |
| Docker | 环境一致、易迁移 | 需要容器知识 | 小规模生产 |
| Docker Compose | 快速部署、本地开发 | 单机限制 | 开发/测试环境 |
| Kubernetes | 高可用、自动扩展 | 复杂度高、成本高 | 大规模生产 |

### 1.2 推荐方案：Docker + Docker Compose

**理由:**
- 适合早期SaaS产品
- 成本可控
- 易于迁移到K8s
- 开发生产环境一致

---

## 2. Docker化

### 2.1 Dockerfile

```dockerfile
# backend/Dockerfile
FROM python:3.11-slim

# 设置工作目录
WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY requirements.txt .

# 安装Python依赖
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用代码
COPY . .

# 创建非root用户
RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app
USER appuser

# 暴露端口
EXPOSE 5000

# 健康检查
HEALTHCHECK --interval=30s --timeout=3s --start-period=40s \
    CMD python -c "import requests; requests.get('http://localhost:5000/api/health')"

# 启动命令
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "4", "--timeout", "120", "app:app"]
```

### 2.2 多阶段构建优化

```dockerfile
# 多阶段构建 - 减小镜像体积
FROM python:3.11-slim as builder

WORKDIR /app

# 安装构建依赖
RUN apt-get update && apt-get install -y gcc

# 安装Python依赖到临时目录
COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

# 最终镜像
FROM python:3.11-slim

WORKDIR /app

# 只复制必要的运行时依赖
RUN apt-get update && apt-get install -y \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# 从builder复制已安装的包
COPY --from=builder /root/.local /root/.local

# 复制应用代码
COPY . .

# 更新PATH
ENV PATH=/root/.local/bin:$PATH

# 创建非root用户
RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app
USER appuser

EXPOSE 5000

CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "4", "app:app"]
```

---

## 3. Docker Compose配置

### 3.1 完整配置

```yaml
# docker-compose.yml
version: '3.8'

services:
  # PostgreSQL数据库
  postgres:
    image: postgres:15-alpine
    container_name: ai_script_postgres
    environment:
      POSTGRES_DB: ai_script_db
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./init.sql:/docker-entrypoint-initdb.d/init.sql
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 10s
      timeout: 5s
      retries: 5
    networks:
      - app_network

  # Redis缓存和消息队列
  redis:
    image: redis:7-alpine
    container_name: ai_script_redis
    command: redis-server --appendonly yes --requirepass ${REDIS_PASSWORD}
    volumes:
      - redis_data:/data
    ports:
      - "6379:6379"
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 3s
      retries: 5
    networks:
      - app_network

  # Flask应用
  app:
    build:
      context: ./backend
      dockerfile: Dockerfile
    container_name: ai_script_app
    environment:
      - FLASK_ENV=production
      - DATABASE_URL=postgresql://postgres:${POSTGRES_PASSWORD}@postgres:5432/ai_script_db
      - REDIS_URL=redis://:${REDIS_PASSWORD}@redis:6379/0
      - JWT_SECRET_KEY=${JWT_SECRET_KEY}
      - CLAUDE_API_KEY=${CLAUDE_API_KEY}
      - DEEPSEEK_API_KEY=${DEEPSEEK_API_KEY}
      - GEMINI_API_KEY=${GEMINI_API_KEY}
      - OPENAI_API_KEY=${OPENAI_API_KEY}
    volumes:
      - ./backend:/app
      - app_storage:/app/storage
    ports:
      - "5000:5000"
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:5000/api/health"]
      interval: 30s
      timeout: 10s
      retries: 3
    networks:
      - app_network
    restart: unless-stopped

  # Celery Worker
  celery_worker:
    build:
      context: ./backend
      dockerfile: Dockerfile
    container_name: ai_script_celery_worker
    command: celery -A celery_config worker --loglevel=info --concurrency=4
    environment:
      - DATABASE_URL=postgresql://postgres:${POSTGRES_PASSWORD}@postgres:5432/ai_script_db
      - REDIS_URL=redis://:${REDIS_PASSWORD}@redis:6379/0
      - CLAUDE_API_KEY=${CLAUDE_API_KEY}
      - DEEPSEEK_API_KEY=${DEEPSEEK_API_KEY}
      - GEMINI_API_KEY=${GEMINI_API_KEY}
      - OPENAI_API_KEY=${OPENAI_API_KEY}
    volumes:
      - ./backend:/app
      - app_storage:/app/storage
    depends_on:
      - postgres
      - redis
    networks:
      - app_network
    restart: unless-stopped

  # Celery Beat (定时任务)
  celery_beat:
    build:
      context: ./backend
      dockerfile: Dockerfile
    container_name: ai_script_celery_beat
    command: celery -A celery_config beat --loglevel=info
    environment:
      - DATABASE_URL=postgresql://postgres:${POSTGRES_PASSWORD}@postgres:5432/ai_script_db
      - REDIS_URL=redis://:${REDIS_PASSWORD}@redis:6379/0
    volumes:
      - ./backend:/app
    depends_on:
      - postgres
      - redis
    networks:
      - app_network
    restart: unless-stopped

  # Nginx反向代理
  nginx:
    image: nginx:alpine
    container_name: ai_script_nginx
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf:ro
      - ./nginx/ssl:/etc/nginx/ssl:ro
    ports:
      - "80:80"
      - "443:443"
    depends_on:
      - app
    networks:
      - app_network
    restart: unless-stopped

volumes:
  postgres_data:
  redis_data:
  app_storage:

networks:
  app_network:
    driver: bridge
```

### 3.2 环境变量配置

```bash
# .env
POSTGRES_PASSWORD=your_secure_password
REDIS_PASSWORD=your_redis_password
JWT_SECRET_KEY=your_jwt_secret_key
JWT_REFRESH_SECRET_KEY=your_refresh_secret_key

# AI API Keys
CLAUDE_API_KEY=sk-ant-xxx
DEEPSEEK_API_KEY=sk-xxx
GEMINI_API_KEY=xxx
OPENAI_API_KEY=sk-xxx

# 应用配置
FLASK_ENV=production
SECRET_KEY=your_flask_secret_key
```

---

## 4. Nginx配置

### 4.1 反向代理配置

```nginx
# nginx/nginx.conf
user nginx;
worker_processes auto;
error_log /var/log/nginx/error.log warn;
pid /var/run/nginx.pid;

events {
    worker_connections 1024;
}

http {
    include /etc/nginx/mime.types;
    default_type application/octet-stream;

    # 日志格式
    log_format main '$remote_addr - $remote_user [$time_local] "$request" '
                    '$status $body_bytes_sent "$http_referer" '
                    '"$http_user_agent" "$http_x_forwarded_for" '
                    'rt=$request_time';

    access_log /var/log/nginx/access.log main;

    sendfile on;
    tcp_nopush on;
    tcp_nodelay on;
    keepalive_timeout 65;
    types_hash_max_size 2048;

    # Gzip压缩
    gzip on;
    gzip_vary on;
    gzip_proxied any;
    gzip_comp_level 6;
    gzip_types text/plain text/css text/xml text/javascript
               application/json application/javascript application/xml+rss;

    # 上游服务器
    upstream flask_app {
        server app:5000;
    }

    # HTTP服务器(重定向到HTTPS)
    server {
        listen 80;
        server_name api.example.com;

        location /.well-known/acme-challenge/ {
            root /var/www/certbot;
        }

        location / {
            return 301 https://$server_name$request_uri;
        }
    }

    # HTTPS服务器
    server {
        listen 443 ssl http2;
        server_name api.example.com;

        # SSL证书
        ssl_certificate /etc/nginx/ssl/fullchain.pem;
        ssl_certificate_key /etc/nginx/ssl/privkey.pem;

        # SSL配置
        ssl_protocols TLSv1.2 TLSv1.3;
        ssl_ciphers HIGH:!aNULL:!MD5;
        ssl_prefer_server_ciphers on;

        # 安全头
        add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
        add_header X-Frame-Options "SAMEORIGIN" always;
        add_header X-Content-Type-Options "nosniff" always;
        add_header X-XSS-Protection "1; mode=block" always;

        # 客户端最大请求体大小
        client_max_body_size 50M;

        # API路由
        location /api/ {
            proxy_pass http://flask_app;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;

            # 超时设置
            proxy_connect_timeout 60s;
            proxy_send_timeout 60s;
            proxy_read_timeout 120s;

            # WebSocket支持
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection "upgrade";
        }

        # 健康检查
        location /health {
            proxy_pass http://flask_app/api/health;
            access_log off;
        }

        # 静态文件(如果有)
        location /static/ {
            alias /var/www/static/;
            expires 30d;
            add_header Cache-Control "public, immutable";
        }
    }
}
```

---

## 5. 部署脚本

### 5.1 部署脚本

```bash
#!/bin/bash
# deploy.sh

set -e

echo "🚀 开始部署..."

# 1. 拉取最新代码
echo "📥 拉取最新代码..."
git pull origin main

# 2. 构建镜像
echo "🔨 构建Docker镜像..."
docker-compose build --no-cache

# 3. 停止旧容器
echo "🛑 停止旧容器..."
docker-compose down

# 4. 启动新容器
echo "▶️  启动新容器..."
docker-compose up -d

# 5. 等待服务启动
echo "⏳ 等待服务启动..."
sleep 10

# 6. 运行数据库迁移
echo "🗄️  运行数据库迁移..."
docker-compose exec -T app python -c "from database.models import init_db; init_db()"

# 7. 健康检查
echo "🏥 健康检查..."
for i in {1..30}; do
    if curl -f http://localhost:5000/api/health > /dev/null 2>&1; then
        echo "✅ 服务启动成功!"
        exit 0
    fi
    echo "等待服务启动... ($i/30)"
    sleep 2
done

echo "❌ 服务启动失败!"
docker-compose logs app
exit 1
```

### 5.2 回滚脚本

```bash
#!/bin/bash
# rollback.sh

set -e

echo "🔄 开始回滚..."

# 1. 获取上一个版本
PREVIOUS_VERSION=$(git rev-parse HEAD~1)

echo "📥 回滚到版本: $PREVIOUS_VERSION"

# 2. 切换到上一个版本
git checkout $PREVIOUS_VERSION

# 3. 重新部署
./deploy.sh

echo "✅ 回滚完成!"
```

---

## 6. 生产环境优化

### 6.1 Gunicorn配置

```python
# gunicorn.conf.py
import multiprocessing

# 绑定地址
bind = "0.0.0.0:5000"

# Worker配置
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = "sync"  # 或 "gevent" 用于异步
worker_connections = 1000
max_requests = 1000  # 防止内存泄漏
max_requests_jitter = 50

# 超时
timeout = 120
graceful_timeout = 30
keepalive = 5

# 日志
accesslog = "-"
errorlog = "-"
loglevel = "info"
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# 进程命名
proc_name = "ai_script_app"

# 预加载应用
preload_app = True

# 钩子函数
def on_starting(server):
    """服务器启动时"""
    print("🚀 Gunicorn服务器启动中...")

def when_ready(server):
    """服务器就绪时"""
    print("✅ Gunicorn服务器就绪!")

def on_exit(server):
    """服务器退出时"""
    print("👋 Gunicorn服务器关闭")
```

### 6.2 数据库连接池优化

```python
# config.py
import os

class ProductionConfig:
    """生产环境配置"""

    # 数据库
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL')
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_size': 20,
        'max_overflow': 10,
        'pool_timeout': 30,
        'pool_recycle': 3600,
        'pool_pre_ping': True,
    }

    # Redis
    REDIS_URL = os.getenv('REDIS_URL')

    # Celery
    CELERY_BROKER_URL = os.getenv('REDIS_URL')
    CELERY_RESULT_BACKEND = os.getenv('REDIS_URL')

    # 安全
    SECRET_KEY = os.getenv('SECRET_KEY')
    JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY')

    # 性能
    SEND_FILE_MAX_AGE_DEFAULT = 31536000  # 1年
```

---

下一部分将输出：监控和备份策略。是否继续?
