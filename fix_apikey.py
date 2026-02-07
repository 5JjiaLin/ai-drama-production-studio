import re

with open(r'services\gemini.ts', 'r', encoding='utf-8') as f:
    content = f.read()

# 在所有使用apiKey的地方，先清理它
# 查找并替换模式：'x-api-key': apiKey  或  'Authorization': `Bearer ${apiKey}`

# 替换1: x-api-key头
content = re.sub(
    r"'x-api-key': apiKey,",
    r"'x-api-key': cleanApiKey,",
    content
)

# 替换2: Authorization头中的apiKey
content = re.sub(
    r"'Authorization': `Bearer \$\{apiKey\}`",
    r"'Authorization': `Bearer ${cleanApiKey}`",
    content
)

with open(r'services\gemini.ts', 'w', encoding='utf-8') as f:
    f.write(content)

print('已替换所有apiKey为cleanApiKey')
