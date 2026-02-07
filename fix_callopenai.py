import re

with open(r'services\gemini.ts', 'r', encoding='utf-8') as f:
    content = f.read()

# 在callOpenAI函数中，在getApiKey()后添加cleanApiKey声明
content = re.sub(
    r"(const callOpenAI = async.*?\n.*?const apiKey = getApiKey\(\);.*?\n.*?const baseUrl = getBaseUrl\(\);.*?\n.*?if \(!apiKey\) \{.*?\n.*?throw new Error.*?\n.*?\})",
    r"\1\n\n   const cleanApiKey = apiKey.replace(/[^\\x00-\\x7F]/g, '').trim();",
    content,
    flags=re.DOTALL
)

with open(r'services\gemini.ts', 'w', encoding='utf-8') as f:
    f.write(content)

print('已在callOpenAI中添加cleanApiKey')
