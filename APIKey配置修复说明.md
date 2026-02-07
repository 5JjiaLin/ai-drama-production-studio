# API Key配置问题修复

## 问题原因

之前的代码使用 `process.env.API_KEY` 从环境变量读取API Key，但这在浏览器环境中**不起作用**（process.env只在Node.js后端可用）。

导致的错误：
- `net::ERR_CONNECTION_CLOSED` - 没有API Key，连接被拒绝
- `Failed to fetch` - API调用失败

## 解决方案

已实施以下改进：

### 1. ✅ 创建API配置模块
**文件**：`services/apiConfig.ts`
- 全局管理API Key和Base URL
- 支持动态更新

### 2. ✅ 添加界面输入框
**位置**：页面顶部工具栏
- 新增"API Key"输入框（密码类型）
- 位于模型选择器左侧
- 支持自动加载和手动输入

### 3. ✅ 自动加载机制
**流程**：
1. 页面加载时尝试从 `/public/apikey.txt` 读取
2. 如果成功，自动填入输入框
3. 如果失败，提示手动输入

### 4. ✅ 动态配置更新
- 修改输入框内容会实时更新配置
- 所有API调用都使用最新配置

## 使用说明

### 方法一：自动加载（推荐）

1. 确保 `apikey.txt` 在 `public` 目录下
2. 刷新页面：http://localhost:3001/
3. API Key会自动加载到输入框
4. 直接使用

### 方法二：手动输入

1. 打开页面：http://localhost:3001/
2. 找到顶部的"API Key"输入框
3. 粘贴您的API Key
4. 开始使用

## 文件位置

```
public/
  └── apikey.txt  ← 将API Key文件放这里

services/
  ├── apiConfig.ts  ← 新增：API配置模块
  ├── gemini.ts     ← 修改：使用getApiKey()获取
  └── gemini-chunking.ts
```

## 测试步骤

1. 刷新页面（强制刷新：Ctrl+F5）
2. 检查顶部是否显示"API Key"输入框
3. 确认API Key已自动加载或手动输入
4. 尝试生成基础元素（测试API连接）
5. 如果成功，继续生成分镜

## 常见问题

### Q1: 输入框没有自动填充API Key
**A**: 检查 `public/apikey.txt` 是否存在，或手动输入

### Q2: 仍然报错"请先在页面顶部输入API Key"
**A**: 确认输入框中已有内容，刷新页面后重试

### Q3: API调用失败
**A**:
1. 检查API Key是否正确
2. 检查网络连接
3. 确认backgrace.com服务是否正常

## 安全提示

- API Key在输入框中显示为密码（●●●●）
- 不会存储到localStorage（每次刷新需重新输入或从文件加载）
- 仅在前端内存中保存

## 下一步

刷新页面后：
- 确认顶部有两个输入框："API Key" 和 "模型"
- 输入或确认API Key
- 选择模型（默认：Claude Sonnet 4.5）
- 开始测试功能
