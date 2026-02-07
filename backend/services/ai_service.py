"""
AI资产提取服务
支持多模型调用: Claude, DeepSeek, Gemini, GPT-4
"""
import os
import json
from typing import Dict, List, Any, Optional
from enum import Enum


class AIModel(Enum):
    """支持的AI模型"""
    CLAUDE = "claude"
    DEEPSEEK = "deepseek"
    GEMINI = "gemini"
    GPT4 = "gpt4"


class AIService:
    """AI服务封装类"""

    def __init__(self, model: AIModel = AIModel.CLAUDE):
        """
        初始化AI服务

        Args:
            model: 使用的AI模型
        """
        self.model = model
        self._load_api_keys()

    def _load_api_keys(self):
        """加载API密钥"""
        self.claude_api_key = os.getenv('CLAUDE_API_KEY')
        self.deepseek_api_key = os.getenv('DEEPSEEK_API_KEY')
        self.gemini_api_key = os.getenv('GEMINI_API_KEY')
        self.openai_api_key = os.getenv('OPENAI_API_KEY')

    def extract_assets(self, script_content: str, episode_number: int) -> Dict[str, List[Dict]]:
        """
        从剧本中提取资产

        Args:
            script_content: 剧本内容
            episode_number: 集数

        Returns:
            {
                "characters": [...],
                "props": [...],
                "scenes": [...]
            }
        """
        prompt = self._build_extraction_prompt(script_content, episode_number)

        # 根据模型调用相应API
        if self.model == AIModel.CLAUDE:
            response = self._call_claude(prompt)
        elif self.model == AIModel.DEEPSEEK:
            response = self._call_deepseek(prompt)
        elif self.model == AIModel.GEMINI:
            response = self._call_gemini(prompt)
        elif self.model == AIModel.GPT4:
            response = self._call_gpt4(prompt)
        else:
            raise ValueError(f"不支持的模型: {self.model}")

        # 解析AI响应
        return self._parse_extraction_result(response)

    def _build_extraction_prompt(self, script_content: str, episode_number: int) -> str:
        """
        构建资产提取Prompt

        使用JSON Schema约束输出格式
        """
        return f"""你是一个专业的影视剧本分析助手。请从以下第{episode_number}集剧本中提取重要资产信息。

# 剧本内容
{script_content}

# 提取要求

## 1. 角色（CHARACTER）
提取所有**有台词或对剧情有重要影响**的角色，包括：
- name: 角色名称
- description: 外貌、性格、背景描述
- gender: 性别（男/女/未知）
- age: 年龄段（儿童/青年/中年/老年/未知）
- voice: 声线特点（如：温柔、沙哑、清脆等）
- role: 角色类型（主角/配角/群演）
- importance: 重要性评分（1-10，基于剧情重要性）

## 2. 道具（PROP）
提取所有**对剧情有推动作用**的道具，包括：
- name: 道具名称
- description: 详细描述（外观、用途等）
- importance: 重要性评分（1-10）

## 3. 场景（SCENE）
提取所有出现的场景，包括：
- name: 场景名称
- description: 场景详细描述（环境、氛围、时间等）
- importance: 重要性评分（1-10）

# 输出格式
必须严格按照以下JSON格式输出：

```json
{{
  "characters": [
    {{
      "name": "张三",
      "description": "30岁左右的男性，穿着西装，表情严肃",
      "gender": "男",
      "age": "中年",
      "voice": "低沉有力",
      "role": "主角",
      "importance": 9
    }}
  ],
  "props": [
    {{
      "name": "神秘信件",
      "description": "一封泛黄的信纸，边角有烧焦痕迹",
      "importance": 8
    }}
  ],
  "scenes": [
    {{
      "name": "咖啡馆",
      "description": "市中心一家安静的咖啡馆，下午3点，阳光透过玻璃窗洒进来",
      "importance": 7
    }}
  ]
}}
```

# 注意事项
1. 只提取importance >= 5的资产（过滤不重要的群演、路人甲等）
2. description必须详细，便于后续分镜生成时识别
3. 角色名称必须统一（如"张三"和"老张"指同一人时，使用剧本中最常用的称呼）
4. 输出必须是有效的JSON格式

请开始提取："""

    def _call_claude(self, prompt: str) -> str:
        """调用Claude API"""
        try:
            import anthropic

            if not self.claude_api_key:
                raise ValueError("CLAUDE_API_KEY未设置")

            client = anthropic.Anthropic(api_key=self.claude_api_key)

            message = client.messages.create(
                model="claude-sonnet-4-5-20250929",
                max_tokens=4096,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )

            return message.content[0].text

        except Exception as e:
            raise RuntimeError(f"Claude API调用失败: {str(e)}")

    def _call_deepseek(self, prompt: str) -> str:
        """调用DeepSeek API"""
        try:
            import openai

            if not self.deepseek_api_key:
                raise ValueError("DEEPSEEK_API_KEY未设置")

            client = openai.OpenAI(
                api_key=self.deepseek_api_key,
                base_url="https://api.deepseek.com"
            )

            response = client.chat.completions.create(
                model="deepseek-chat",
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )

            return response.choices[0].message.content

        except Exception as e:
            raise RuntimeError(f"DeepSeek API调用失败: {str(e)}")

    def _call_gemini(self, prompt: str) -> str:
        """调用Gemini API"""
        try:
            import google.generativeai as genai

            if not self.gemini_api_key:
                raise ValueError("GEMINI_API_KEY未设置")

            genai.configure(api_key=self.gemini_api_key)
            model = genai.GenerativeModel('gemini-2.0-flash-exp')

            response = model.generate_content(prompt)
            return response.text

        except Exception as e:
            raise RuntimeError(f"Gemini API调用失败: {str(e)}")

    def _call_gpt4(self, prompt: str) -> str:
        """调用GPT-4 API"""
        try:
            import openai

            if not self.openai_api_key:
                raise ValueError("OPENAI_API_KEY未设置")

            client = openai.OpenAI(api_key=self.openai_api_key)

            response = client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )

            return response.choices[0].message.content

        except Exception as e:
            raise RuntimeError(f"GPT-4 API调用失败: {str(e)}")

    def _parse_extraction_result(self, ai_response: str) -> Dict[str, List[Dict]]:
        """
        解析AI响应结果

        提取JSON代码块并解析
        """
        try:
            # 尝试提取JSON代码块
            import re
            json_match = re.search(r'```json\s*(\{.*?\})\s*```', ai_response, re.DOTALL)

            if json_match:
                json_str = json_match.group(1)
            else:
                # 尝试直接解析整个响应
                json_str = ai_response.strip()

            # 解析JSON
            result = json.loads(json_str)

            # 验证结构
            if not isinstance(result, dict):
                raise ValueError("返回结果不是字典格式")

            if 'characters' not in result:
                result['characters'] = []
            if 'props' not in result:
                result['props'] = []
            if 'scenes' not in result:
                result['scenes'] = []

            return result

        except json.JSONDecodeError as e:
            raise RuntimeError(f"AI响应JSON解析失败: {str(e)}\n响应内容: {ai_response[:500]}")
        except Exception as e:
            raise RuntimeError(f"解析AI响应失败: {str(e)}")


# 单例实例
_ai_service_instance: Optional[AIService] = None


def get_ai_service(model: AIModel = AIModel.CLAUDE) -> AIService:
    """获取AI服务单例"""
    global _ai_service_instance
    if _ai_service_instance is None or _ai_service_instance.model != model:
        _ai_service_instance = AIService(model)
    return _ai_service_instance


if __name__ == "__main__":
    # 测试代码
    test_script = """
    【第1场】
    场景：咖啡馆 - 下午

    张三坐在窗边，手里拿着一封泛黄的信件。

    张三：（低声自语）终于找到了...

    李四推门而入，径直走向张三。

    李四：找到什么了？
    张三：（递过信件）你自己看。
    """

    service = AIService(AIModel.CLAUDE)
    try:
        result = service.extract_assets(test_script, 1)
        print("提取结果：")
        print(json.dumps(result, ensure_ascii=False, indent=2))
    except Exception as e:
        print(f"错误: {e}")
