const fs = require('fs');

const filePath = String.raw`E:\AI coding\AI剧本批量拆解版本1\services\gemini.ts`;
let content = fs.readFileSync(filePath, 'utf8');
const lines = content.split('\n');

// 找到第808行（分段代码开始）和第807行（generateVisualStyle结束）之间的内容
const startIdx = lines.findIndex((line, idx) => idx >= 807 && line.includes('分段生成分镜表'));

if (startIdx > 0) {
  // 保留前807行 + 从808行开始的干净代码（去掉重复的 cleanJsonOutput 等）
  const cleanLines = lines.slice(0, startIdx);

  // 从808行开始，跳过重复定义的部分
  let foundChunking = false;
  for (let i = startIdx; i < lines.length; i++) {
    const line = lines[i];

    // 跳过重复定义的辅助函数
    if (line.includes('从 gemini.ts 导入')) {
      // 跳过到下一个主函数
      while (i < lines.length && !lines[i].includes('generateStoryboardInChunks')) {
        i++;
      }
      i--; // 回退一行，让循环继续
      continue;
    }

    // 跳过 export
    if (line.includes('export const generateStoryboardInChunks')) {
      cleanLines.push(line.replace('export ', ''));
      continue;
    }

    cleanLines.push(line);
  }

  // 写回文件
  fs.writeFileSync(filePath, cleanLines.join('\n'), 'utf8');
  console.log('✅ 已清理重复代码');
} else {
  console.log('❌ 未找到分段代码起始位置');
}
