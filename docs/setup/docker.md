# AI剧本批量拆解工具 - Docker版使用指南

## 📋 系统要求

- **Windows**: Windows 10/11 (64位)
- **Mac**: macOS 10.15 或更高版本
- **Linux**: 任意主流发行版
- **Docker**: Docker Desktop 或 Docker Engine
- **内存**: 至少 4GB RAM
- **磁盘**: 至少 2GB 可用空间

## 🚀 快速开始（3步启动）

### Windows用户

1. **安装Docker Desktop**
   - 下载地址: https://www.docker.com/products/docker-desktop
   - 安装后重启电脑

2. **配置API Key**
   - 双击 `start.bat` 启动脚本
   - 首次运行会自动打开 `.env` 文件
   - 填写你的Claude API Key（必需）
   - 保存并关闭文件

3. **启动服务**
   - 继续运行启动脚本
   - 等待构建完成（首次约5-10分钟）
   - 浏览器自动打开 http://localhost:3000

### Mac/Linux用户

1. **安装Docker**
   ```bash
   # Mac用户安装Docker Desktop
   # Linux用户参考: https://docs.docker.com/engine/install/
   ```

2. **配置API Key**
   ```bash
   # 复制环境变量模板
   cp .env.example .env

   # 编辑.env文件，填写API Key
   nano .env  # 或使用其他编辑器
   ```

3. **启动服务**
   ```bash
   # 添加执行权限
   chmod +x start.sh

   # 运行启动脚本
   ./start.sh
   ```

## 🔑 API Key配置说明

编辑 `.env` 文件，填写以下内容：

```env
# Claude API Key（必需）
CLAUDE_API_KEY=sk-ant-xxxxx

# Gemini API Key（可选）
GEMINI_API_KEY=xxxxx

# DeepSeek API Key（可选）
DEEPSEEK_API_KEY=xxxxx
```

**获取API Key:**
- Claude: https://console.anthropic.com/
- Gemini: https://makersuite.google.com/app/apikey
- DeepSeek: https://platform.deepseek.com/

## 📖 使用流程

1. **注册/登录**
   - 首次使用需要注册账号
   - 用户名、邮箱、密码

2. **创建项目**
   - 点击"创建新项目"
   - 填写项目名称和描述

3. **提取资产**
   - 上传剧本内容
   - AI自动提取角色、场景、道具
   - 可手动编辑和优化

4. **生成分镜**
   - 上传单集剧本
   - 设置分镜数量范围
   - AI生成分镜表格
   - 支持导出CSV和复制

## 🛠️ 管理命令

### 查看服务状态
```bash
docker-compose ps
```

### 查看日志
```bash
# 查看所有日志
docker-compose logs -f

# 只查看后端日志
docker-compose logs -f backend

# 只查看前端日志
docker-compose logs -f frontend
```

### 停止服务
```bash
docker-compose down
```

### 重启服务
```bash
docker-compose restart
```

### 完全清理（删除数据）
```bash
docker-compose down -v
```

## ❓ 常见问题

### Q1: Docker构建失败
**A:** 检查网络连接，确保能访问Docker Hub。可以配置Docker镜像加速器。

### Q2: 端口被占用
**A:** 修改 `docker-compose.yml` 中的端口映射：
```yaml
ports:
  - "3001:80"  # 将3000改为3001
```

### Q3: API Key无效
**A:**
- 检查 `.env` 文件中的API Key是否正确
- 确保API Key有足够的额度
- 重启服务: `docker-compose restart`

### Q4: 数据丢失
**A:** 数据保存在 `backend/storage` 目录，不要删除此目录。

### Q5: 更新版本
**A:**
```bash
# 停止服务
docker-compose down

# 拉取最新代码
git pull

# 重新构建并启动
docker-compose up -d --build
```

## 📊 性能优化

### 首次启动慢
- 首次构建需要下载依赖，约5-10分钟
- 后续启动只需10-30秒

### 减少内存占用
编辑 `docker-compose.yml` 添加资源限制：
```yaml
services:
  backend:
    deploy:
      resources:
        limits:
          memory: 1G
```

## 🔒 安全建议

1. **不要提交 .env 文件到Git**
2. **定期更换API Key**
3. **使用强密码注册账号**
4. **不要在公网暴露服务**（仅本地使用）

## 📞 技术支持

- 遇到问题请查看日志: `docker-compose logs -f`
- GitHub Issues: [项目地址]
- 邮箱: [联系邮箱]

## 📝 版本信息

- 版本: v2.0
- 更新日期: 2026-02-12
- Docker支持: ✅
- 跨平台: ✅

---

**祝使用愉快！** 🎬
