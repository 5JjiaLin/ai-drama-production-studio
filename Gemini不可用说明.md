# Gemini模型不可用问题说明

## 问题描述

所有Gemini模型在当前API服务器（backgrace.com）上都无法使用，返回500错误：

### 错误详情

1. **gemini-2.5-flash**
   - 错误：`not implemented`
   - 状态：未实现/未配置

2. **gemini-3-flash**
   - 错误：`倍率或价格未配置 (Model gemini-3-flash ratio or price not set)`
   - 状态：后端未配置价格

3. **gemini-3-pro-high**
   - 错误：`倍率或价格未配置 (Model gemini-3-pro-high ratio or price not set)`
   - 状态：后端未配置价格

## 临时解决方案

已将所有Gemini选项从界面中移除，改用**Claude模型**作为默认。

### 当前可用模型

1. **Claude Sonnet 4.5 (推荐)** - `claude-sonnet-4-5-20250929` ✅ 默认
2. **Claude Opus 4.5 (最强)** - `claude-opus-4-5-20251101`
3. **Claude Haiku 4.5 (经济)** - `claude-haiku-4-5-20251001`

## 测试地址

请访问新地址测试：

- **本地：** http://localhost:3001/
- **网络：** http://192.168.31.94:3001/

## Claude模型优势

实际上Claude模型更适合这个项目：

### 1. 分段生成支持
- ✅ **Claude支持分段生成**（maxShots > 25时自动启用）
- ❌ Gemini不支持分段生成

### 2. 模板遵守能力
- ✅ Claude对复杂prompt的理解和遵守能力更强
- ✅ 更好地遵守"分镜骨架复刻模版"
- ✅ 更准确的资产匿名化（图一、图二指代）

### 3. 输出质量
- ✅ Claude在创意写作和结构化输出方面表现更好
- ✅ 更好的JSON格式控制
- ✅ 更少的格式错误

## 如果未来需要恢复Gemini

联系API服务提供商（backgrace.com）解决以下问题：
1. 启用Gemini模型转发功能
2. 配置正确的价格倍率
3. 确保后端实现完整

恢复步骤：
1. 在 `App.tsx` 第570行附近取消注释Gemini选项
2. 根据需要调整默认模型

## 建议

**推荐使用 Claude Sonnet 4.5**：
- 性价比高
- 质量优秀
- 支持分段生成
- 对模板的遵守度最好

如果需要最高质量，可以选择 **Claude Opus 4.5**。
