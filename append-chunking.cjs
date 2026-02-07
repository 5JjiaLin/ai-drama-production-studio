const fs = require('fs');

// 读取源文件和要追加的代码
const geminiPath = String.raw`E:\AI coding\AI剧本批量拆解版本1\services\gemini.ts`;
const chunkingPath = String.raw`E:\AI coding\AI剧本批量拆解版本1\services\gemini-chunking-final.ts`;

const geminiContent = fs.readFileSync(geminiPath, 'utf8');
const chunkingContent = fs.readFileSync(chunkingPath, 'utf8');

// 提取要追加的代码（跳过注释部分）
const codeToAppend = chunkingContent.split('\n').slice(3).join('\n');

// 追加到 gemini.ts
const newContent = geminiContent + '\n' + codeToAppend;

// 写回文件
fs.writeFileSync(geminiPath, newContent, 'utf8');

console.log('✅ 分段生成代码已成功追加到 gemini.ts');
