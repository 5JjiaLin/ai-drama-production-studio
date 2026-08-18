# API Key 配置指南

本文档说明如何配置AI剧本批量拆解系统的API Key。

## 支持的AI模型

系统支持以下AI模型：

1. **Google Gemini**
   - 模型：gemini-2.0-flash-exp
   - 官网：https://ai.google.dev/

2. **DeepSeek**
   - 模型：deepseek-chat
   - 官网：https://platform.deepseek.com/

3. **OpenAI**
   - 模型：gpt-4, gpt-3.5-turbo
   - 官网：https://platform.openai.com/

## 配置方法

### 方法一：环境变量配置（推荐）

在项目根目录创建 `.env` 文件：

```bash
# Google Gemini API Key
GEMINI_API_KEY=your_gemini_api_key_here

# DeepSeek API Key
DEEPSEEK_API_KEY=your_deepseek_api_key_here

# OpenAI API Key
OPENAI_API_KEY=your_openai_api_key_here
```

### 方法二：系统环境变量

**Windows:**
```cmd
setx GEMINI_API_KEY "your_api_key_here"
setx DEEPSEEK_API_KEY "your_api_key_here"
setx OPENAI_API_KEY "your_api_key_here"
```

**Linux/Mac:**
```bash
export GEMINI_API_KEY="your_api_key_here"
export DEEPSEEK_API_KEY="your_api_key_here"
export OPENAI_API_KEY="your_api_key_here"
```

## 获取API Key

### Google Gemini

1. 访问 https://ai.google.dev/
2. 点击 "Get API Key"
3. 登录Google账号
4. 创建新的API Key
5. 复制API Key并保存

### DeepSeek

1. 访问 https://platform.deepseek.com/
2. 注册并登录账号
3. 进入"API Keys"页面
4. 创建新的API Key
5. 复制API Key并保存

### OpenAI

1. 访问 https://platform.openai.com/
2. 注册并登录账号
3. 进入"API Keys"页面
4. 创建新的API Key
5. 复制API Key并保存

## 配置验证

启动后端服务器后，系统会自动检测可用的API Key：

```bash
cd backend
python app.py
```

查看日志输出，确认API Key配置成功：
```
✅ Gemini API Key 已配置
✅ DeepSeek API Key 已配置
✅ OpenAI API Key 已配置
```

## 注意事项

1. **安全性**：不要将API Key提交到Git仓库
2. **费用**：注意API调用费用，建议设置使用限额
3. **配额**：免费API Key通常有调用次数限制
4. **备份**：建议配置多个API Key作为备用

## 故障排查

### API Key无效

- 检查API Key是否正确复制
- 确认API Key未过期
- 验证账号是否有足够余额

### 网络连接问题

- 检查网络连接
- 确认防火墙设置
- 尝试使用代理

### 配额超限

- 检查API使用情况
- 升级API套餐
- 切换到备用API Key

## 相关文档

- [README.md](./README.md) - 项目说明
- [GITHUB设置指南.md](./GITHUB设置指南.md) - GitHub配置
- [版本2开发进度.md](./版本2开发进度.md) - 开发进度
