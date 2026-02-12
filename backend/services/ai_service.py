"""
AI资产提取服务
支持多模型调用: Claude, DeepSeek, Gemini, GPT-4
"""
import os
import json
import time
import logging
from typing import Dict, List, Any, Optional
from enum import Enum
from functools import wraps

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def retry_on_failure(max_retries=3, delay=1):
    """重试装饰器 - 用于AI API调用失败时自动重试"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < max_retries - 1:
                        wait_time = delay * (2 ** attempt)  # 指数退避
                        logger.warning(f"{func.__name__} 调用失败 (尝试 {attempt + 1}/{max_retries}): {str(e)}, {wait_time}秒后重试...")
                        time.sleep(wait_time)
                    else:
                        logger.error(f"{func.__name__} 调用失败，已达最大重试次数: {str(e)}")
            raise last_exception
        return wrapper
    return decorator


# 模型配置字典
MODEL_CONFIGS = {
    'claude-sonnet-4-5': {
        'name': 'Claude Sonnet 4.5',
        'provider': 'Anthropic',
        'model_id': 'claude-sonnet-4-5-20250929',
        'api_type': 'claude',
        'description': '最新的Claude Sonnet模型，平衡性能和成本'
    },
    'claude-opus-4': {
        'name': 'Claude Opus 4',
        'provider': 'Anthropic',
        'model_id': 'claude-opus-4-20250514',
        'api_type': 'claude',
        'description': 'Claude最强大的模型，适合复杂任务'
    },
    'deepseek-chat': {
        'name': 'DeepSeek Chat',
        'provider': 'DeepSeek',
        'model_id': 'deepseek-chat',
        'api_type': 'deepseek',
        'description': 'DeepSeek对话模型，性价比高'
    },
    'deepseek-reasoner': {
        'name': 'DeepSeek Reasoner',
        'provider': 'DeepSeek',
        'model_id': 'deepseek-reasoner',
        'api_type': 'deepseek',
        'description': 'DeepSeek推理模型，适合复杂逻辑任务'
    },
    'gemini-2.0-flash': {
        'name': 'Gemini 2.0 Flash',
        'provider': 'Google',
        'model_id': 'gemini-2.0-flash-exp',
        'api_type': 'gemini',
        'description': 'Google最新的快速模型'
    },
    'gpt-4': {
        'name': 'GPT-4',
        'provider': 'OpenAI',
        'model_id': 'gpt-4',
        'api_type': 'openai',
        'description': 'OpenAI的GPT-4模型'
    },
    'gpt-4-turbo': {
        'name': 'GPT-4 Turbo',
        'provider': 'OpenAI',
        'model_id': 'gpt-4-turbo',
        'api_type': 'openai',
        'description': 'GPT-4的更快版本'
    }
}


class AIModel(Enum):
    """支持的AI模型（保留用于向后兼容）"""
    CLAUDE = "claude"
    DEEPSEEK = "deepseek"
    GEMINI = "gemini"
    GPT4 = "gpt4"


class AIService:
    """AI服务封装类"""

    def __init__(self, model: str = 'claude-sonnet-4-5'):
        """
        初始化AI服务

        Args:
            model: 模型标识符（如'claude-sonnet-4-5'）或旧的枚举值（如'claude'）
        """
        # 兼容旧的枚举值
        if isinstance(model, AIModel):
            model = model.value

        # 如果是旧的简单值，映射到默认模型
        model_mapping = {
            'claude': 'claude-sonnet-4-5',
            'deepseek': 'deepseek-chat',
            'gemini': 'gemini-2.0-flash',
            'gpt4': 'gpt-4'
        }

        if model in model_mapping:
            model = model_mapping[model]

        # 验证模型是否存在
        if model not in MODEL_CONFIGS:
            raise ValueError(f"不支持的模型: {model}。可用模型: {list(MODEL_CONFIGS.keys())}")

        self.model = model
        self.model_config = MODEL_CONFIGS[model]
        self._load_api_keys()

    def _load_api_keys(self):
        """加载API密钥"""
        self.claude_api_key = os.getenv('CLAUDE_API_KEY')
        self.deepseek_api_key = os.getenv('DEEPSEEK_API_KEY')
        self.gemini_api_key = os.getenv('GEMINI_API_KEY')
        self.openai_api_key = os.getenv('OPENAI_API_KEY')

    def extract_assets(self, script_content: str, episode_number: int = 1,
                       feedback: Optional[str] = None, current_data: Optional[Dict] = None) -> Dict[str, List[Dict]]:
        """
        从剧本中提取资产

        Args:
            script_content: 剧本内容
            episode_number: 集数（默认为1）
            feedback: 用户优化反馈（可选）
            current_data: 当前已有数据（可选，用于优化）

        Returns:
            {
                "characters": [...],
                "props": [...],
                "scenes": [...]
            }
        """
        if feedback:
            logger.info(f"开始优化第{episode_number}集资产，使用模型: {self.model}")
        else:
            logger.info(f"开始提取第{episode_number}集资产，使用模型: {self.model}")
        start_time = time.time()

        try:
            prompt = self._build_extraction_prompt(script_content, episode_number, feedback, current_data)

            # 根据模型配置调用相应API
            api_type = self.model_config['api_type']
            model_id = self.model_config['model_id']

            if api_type == 'claude':
                response = self._call_claude(prompt, model_id)
            elif api_type == 'deepseek':
                response = self._call_deepseek(prompt, model_id)
            elif api_type == 'gemini':
                response = self._call_gemini(prompt, model_id)
            elif api_type == 'openai':
                response = self._call_openai(prompt, model_id)
            else:
                raise ValueError(f"不支持的API类型: {api_type}")

            # 解析AI响应
            result = self._parse_extraction_result(response)

            elapsed_time = time.time() - start_time
            logger.info(f"资产提取完成，耗时: {elapsed_time:.2f}秒，提取到: "
                       f"{len(result.get('characters', []))}个角色, "
                       f"{len(result.get('props', []))}个道具, "
                       f"{len(result.get('scenes', []))}个场景")

            return result

        except Exception as e:
            elapsed_time = time.time() - start_time
            logger.error(f"资产提取失败，耗时: {elapsed_time:.2f}秒，错误: {str(e)}")
            raise

    def generate_storyboards(self, script_content: str, min_shots: int = 10, max_shots: int = 30,
                            feedback: Optional[str] = None, current_shots: Optional[List[Dict]] = None,
                            assets: Optional[Dict[str, List[Dict]]] = None) -> List[Dict]:
        """
        生成分镜表

        Args:
            script_content: 剧本内容
            min_shots: 最小镜头数
            max_shots: 最大镜头数
            feedback: 用户优化反馈（可选）
            current_shots: 当前已有分镜（可选，用于优化）
            assets: 项目资产库（可选），包含角色、道具、场景信息

        Returns:
            分镜列表
        """
        if feedback:
            logger.info(f"开始优化分镜，使用模型: {self.model}")
        else:
            logger.info(f"开始生成分镜，使用模型: {self.model}")
        start_time = time.time()

        try:
            prompt = self._build_storyboard_prompt(script_content, min_shots, max_shots, feedback, current_shots, assets)

            # 定义系统指令（用于Claude和DeepSeek）
            system_instruction = "你是一位精通电影视觉工程的顶级导演。你必须严格遵守'分镜骨架复刻模版'。严禁脑补剧情，必须忠实于剧本原意。请输出合法的 JSON。不要使用 Markdown 符号或【】符号。"

            # 根据模型配置调用相应API
            api_type = self.model_config['api_type']
            model_id = self.model_config['model_id']

            if api_type == 'claude':
                response = self._call_claude(prompt, model_id, system_instruction)
            elif api_type == 'deepseek':
                response = self._call_deepseek(prompt, model_id, system_instruction)
            elif api_type == 'gemini':
                response = self._call_gemini(prompt, model_id)
            elif api_type == 'openai':
                response = self._call_openai(prompt, model_id)
            else:
                raise ValueError(f"不支持的API类型: {api_type}")

            # 解析AI响应
            result = self._parse_storyboard_result(response)

            elapsed_time = time.time() - start_time
            logger.info(f"分镜生成完成，耗时: {elapsed_time:.2f}秒，生成了{len(result)}个镜头")

            return result

        except Exception as e:
            elapsed_time = time.time() - start_time
            logger.error(f"分镜生成失败，耗时: {elapsed_time:.2f}秒，错误: {str(e)}")
            raise

    def _build_extraction_prompt(self, script_content: str, episode_number: int,
                                  feedback: Optional[str] = None, current_data: Optional[Dict] = None) -> str:
        """
        构建资产提取Prompt

        使用gemini.ts中定义的标准角色定义和Triple-Read Protocol
        """
        # 构建优化部分
        optimization_section = ""
        if feedback and current_data:
            optimization_section = f"""
## OPTIMIZATION INSTRUCTIONS (CRITICAL - INCREMENTAL UPDATE)
用户正在对现有的分析结果进行**局部优化**。你的任务是仅根据用户的反馈修改现有数据，**绝对保持其他未提及内容不变**。

**当前已有数据 (Current Data)**:
```json
{json.dumps(current_data, ensure_ascii=False)}
```

**用户反馈 (User Feedback)**:
"{feedback}"

**严格修改规则**:
1. **锚定原数据**: 必须以【当前已有数据】为基准进行修改，而不是重新从剧本生成。
2. **最小化修改**: 只修改用户明确提到的字段或条目。如果用户没提某个人物/道具/场景，**严禁改动它**。
3. **格式合规**: 任何修改或新增的内容，必须严格遵守上文定义的【角色/道具/场景描述格式】。
"""
        elif feedback:
            optimization_section = f"""
## OPTIMIZATION REQUEST
用户查看了之前的分析结果，并提出了以下优化要求。请务必根据此要求重新生成或修改表格内容：
>>> 用户要求: "{feedback}"
**重要规则**：所有的优化调整必须严格基于用户输入的内容进行，**严禁私自改变用户未提及的内容**。
"""

        return f"""# Role: AI 漫剧全资产一致性专家 (Expert Level)

## 🚀 Execution Protocol: The "Deep-Dive & Verify" Method
To ensure >99% accuracy and ZERO missed assets, you MUST simulate the following process internally before generating the JSON:

### Step 1: The Triple-Read Protocol
1.  **Pass 1 (Identification)**: Scan for all named Characters and named Locations.
2.  **Pass 2 (Interaction)**: Read again to find every object (Prop) that is held, used, or significant to the plot.
3.  **Pass 3 (Emotion & Detail)**: Read a third time to find "Silent Actors" - objects or environmental details that drive emotion or foreshadow events.

### Step 2: Self-Correction & Verification
- **Check**: Did I capture the villain's specific weapon?
- **Check**: Did I capture the object that triggers the flashback?
- **Check**: Did I capture the location of the final climax?
- **Verify**: Are the visual descriptions rich and consistent with the script's tone?
- **Action**: If ANY key asset is missing, add it to the list now.

## Task
Output the standardized JSON tables based on the rigorous process above.

### 1. 人物拆解表（参考视觉标准）
- **角色描述要求**: 必须严格使用以下固定句式生成（**注意：严禁使用 Markdown 加粗或特殊符号，输出纯文本**）：
  "角色设计图，正面视角，全身，白色背景，一位[气质] [身份]，[年龄]岁，[身高]厘米，身材[特征]，[发型及发色描述]，[脸型/轮廓/五官细节]，眼神[状态]，气质[关键词]，穿着[颜色][材质][款式]，[腰部及配饰细节]，[鞋履描述]，站立姿势。"
- **音色**: 听觉标签 (如: 男/女青年/少年)。

### 2. 核心代表性道具表（一致性控制项）
- **逻辑**: 仅提取与主要角色深度关联、能代表其身份或性格的【重要道具】。这些道具将作为角色的"视觉符号"贯穿全剧。
- **要求**: 描述必须纯物理样貌，**严禁出现人名**。
- **描述格式**: 必须严格使用以下固定句式生成（**注意：严禁使用 Markdown 加粗或特殊符号，输出纯文本**）：
  "产品图，白色背景，一个[材质] [名称]，整体呈现[形状结构]，表面具有[纹理/图案/刻痕]，[核心组件细节说明]，展现出[新旧程度/特定光泽/质感]。"

### 3. 核心场景表（空间资产项）
- **要求**: 描述必须纯物理样貌，**严禁出现人名**。
- **描述格式**: 必须严格使用以下固定句式生成（**注意：严禁使用 Markdown 加粗或特殊符号，输出纯文本**）：
  "场景概念图，广角视角，[空间结构/布局方式]，装修建筑风格为[风格]，整体主色调为[色彩]，[光影调性描述]，环境包含[地面/墙面/装饰物细节]，空气中带有[微粒/氛围元素]。"

## Rules
1. **完整性检查 (Verification)**: Ensure ALL assets that drive the plot or heighten emotions are included. Do not leave out "small but significant" items.
2. **强制格式一致性**: 所有描述必须严格遵循上述"流式结构"。
3. **去身份化描述**: 在道具和场景表中，禁止使用"某某的桌子"。
4. **资产锁定**: 道具和场景表的最后三列固定为"中性"、"青年"、"无"。
5. **纯净文本输出**: 严禁在输出内容中使用 Markdown 加粗符 (** 或 *)、方括号 ([]) 或【】等符号。
6. **语言**: 请使用中文输出所有内容。

{optimization_section}

## Output Format (Strict JSON)
必须严格按照以下JSON格式输出：

{{
  "characters": [
    {{
      "name": "角色名称",
      "description": "角色设计图，正面视角，全身，白色背景，一位[气质] [身份]，[年龄]岁，[身高]厘米，身材[特征]，[发型及发色描述]，[脸型/轮廓/五官细节]，眼神[状态]，气质[关键词]，穿着[颜色][材质][款式]，[腰部及配饰细节]，[鞋履描述]，站立姿势。",
      "gender": "男/女",
      "age": "年龄",
      "voice": "音色标签",
      "role": "主角/配角/群演"
    }}
  ],
  "props": [
    {{
      "name": "道具名称",
      "description": "产品图，白色背景，一个[材质] [名称]，整体呈现[形状结构]，表面具有[纹理/图案/刻痕]，[核心组件细节说明]，展现出[新旧程度/特定光泽/质感]。",
      "gender": "中性",
      "age": "青年",
      "voice": "无"
    }}
  ],
  "scenes": [
    {{
      "name": "场景名称",
      "description": "场景概念图，广角视角，[空间结构/布局方式]，装修建筑风格为[风格]，整体主色调为[色彩]，[光影调性描述]，环境包含[地面/墙面/装饰物细节]，空气中带有[微粒/氛围元素]。",
      "gender": "中性",
      "age": "青年",
      "voice": "无"
    }}
  ]
}}

# 剧本内容（第{episode_number}集）
{script_content}

请严格按照上述要求提取资产，输出合法的JSON格式。"""

    def _build_storyboard_prompt(self, script_content: str, min_shots: int, max_shots: int,
                                  feedback: Optional[str] = None, current_shots: Optional[List[Dict]] = None,
                                  assets: Optional[Dict[str, List[Dict]]] = None,
                                  analysis_context: Optional[Dict] = None) -> str:
        """
        构建分镜生成Prompt

        使用gemini.ts中定义的"顶级导演分镜视觉系统"角色定义
        """
        # 构建深度剧本理解上下文
        deep_analysis_context = ""
        if analysis_context:
            plot_summary = analysis_context.get('plotSummary', '')
            emotional_anchors = analysis_context.get('emotionalAnchors', '')

            deep_analysis_context = f"""
## 📚 DEEP SCRIPT UNDERSTANDING (STRICT ADHERENCE REQUIRED)
You have previously analyzed this script deeply. Use the following context to ensure the storyboard is 100% faithful to the plot and emotions.

**Plot Logic**: {plot_summary}
**Emotional Anchors**: {emotional_anchors}

**STRICT RULE**: Do NOT hallucinate scenes or actions that are not implied by the plot logic above. The storyboard must follow the script's actual flow accurately. Use the "Emotional Anchors" to set the correct [Emotion] and [Intensity] for each shot.
"""

        # 构建资产约束
        asset_constraints = ""
        if assets:
            characters = assets.get('characters', [])
            props = assets.get('props', [])
            scenes = assets.get('scenes', [])

            chars_list = ', '.join([c['name'] for c in characters]) if characters else ''
            props_list = ', '.join([p['name'] for p in props]) if props else ''
            scenes_list = ', '.join([s['name'] for s in scenes]) if scenes else ''

            asset_constraints = f"""
⚠️ **CRITICAL: ASSET MAPPING CONSISTENCY**
In the [assets] column (e.g., @角色 @场景), you MUST strictly use the names from the following extracted lists.
Do not invent new names for characters, props, or scenes that were already defined.
- **Available Characters**: {chars_list}
- **Available Props**: {props_list}
- **Available Scenes**: {scenes_list}
"""

        # 构建镜头数量约束
        shot_count_constraint = f"""
🔢 **CRITICAL: SHOT COUNT CONSTRAINT**
You MUST generate a storyboard with a total number of shots between **{min_shots}** and **{max_shots}**.
"""

        # 构建优化部分
        optimization_section = ""
        if feedback and current_shots:
            optimization_section = f"""
## OPTIMIZATION INSTRUCTIONS (CRITICAL - INCREMENTAL UPDATE)
用户正在对现有的分镜表进行**局部优化**。你的任务是仅根据用户的反馈修改现有镜头，**绝对保持其他未提及内容不变**。
**当前已有分镜 (Current Storyboard)**:
```json
{json.dumps({"shots": current_shots}, ensure_ascii=False)}
```
**用户反馈 (User Feedback)**:
"{feedback}"
"""
        elif feedback:
            optimization_section = f"""
## OPTIMIZATION REQUEST
用户查看了之前的分镜结果，并提出了以下优化要求。请务必根据此要求重新生成分镜表：
>>> 用户要求: "{feedback}"
"""

        return f"""# Role: 顶级导演分镜视觉系统 (System Prompt) - v13.1 工业资产匿名化版

🎭 **角色定位**
你是一位精通电影视觉工程与 AI 工业流提示词的顶级导演。你通过"图号占位符"与"视觉特征锚点"构建一套不依赖人名的、具备极高一致性的视觉系统。

🚨 **最高优先级：剧情忠实原则 (CRITICAL: Plot Fidelity)**
- **严禁添加情节**：严禁添加剧本中不存在的情节、事件或场景转换
- **严禁改变顺序**：严格按照剧本的情节顺序进行拆解，不得调整或重组
- **严禁推测前后**：不得推测或添加剧本未描述的"之前"或"之后"发生的事情

❌ 错误示例（脑补情节）：
- 剧本："小明在奶茶店买咖啡" → 不要拆成"小明从鲜花店出来，走向奶茶店，进入奶茶店买咖啡"
- 剧本："他们在会议室讨论" → 不要拆成"他们走进会议室，坐下，开始讨论"

✓ 正确做法（丰富视觉但不添加情节）：
- 剧本："小明在奶茶店买咖啡" → 可以丰富描述：特写镜头，图一站在收银台前，手指向菜单上的咖啡选项，嘴唇张合说话，店员微笑点头，背景是奶茶店吧台，货架上陈列着各种饮品原料，暖色调灯光
- 剧本："他们在会议室讨论" → 可以丰富描述：中景镜头，图一坐在会议桌前，身体前倾，手势指向桌面文件，嘴唇张合说话，图二坐在对面，专注倾听，会议室环境，白色墙面，背景有白板和投影屏幕

**核心区别**：
- 情节 = 发生了什么事（WHERE、WHEN、WHO、WHAT）→ 必须严格遵循剧本
- 视觉 = 怎么呈现这件事（HOW）→ 可以丰富镜头语言、构图、光影、细节

{deep_analysis_context}

{asset_constraints}

{shot_count_constraint}

📐 **核心全局协议 (The Iron Rules)**

1. **资产映射与匿名化 (Asset Anonymization)**
   - **标签定义**：【场景角色道具】栏使用 `@资产名` 格式，标签间以空格区分。
   - **绝对索引**：**图一** 锁定标签栏第 1 个 @ 资产，依此类推。
   - **【核心禁令】**：图片提示词（Fusion）与视频提示词（Motion）中**严禁出现任何角色名称**。必须统一使用 **图一**、**图二** 来指代。

2. **🔊 对白与嘴部逻辑 (Lip-Sync Logic)**
   - **对白内容**：若文案为角色说出的话 → 必须描述为"**图X嘴唇张合说话**"。
   - **内心独白**：若文案为心理活动/系统提示 → 必须描述为"**图X嘴唇紧闭**"。

3. **情绪强度限定 (Hard Parameters)**
   - **情绪**：快乐、愤怒、悲伤、害怕、厌恶、忧郁、惊讶、平静。
   - **强度**：微弱、弱、中等、较强、强烈。
   - **逻辑引用**: 参考[Deep Script Understanding]中的情绪锚点来决定每一镜的情绪。

4. **纯净文本输出 (Pure Text)**
   - 严禁在输出内容中使用 Markdown 加粗符 (** 或 *)、方括号 ([]) 或【】等符号。
   - 所有的描述必须是平铺直叙的文本。

🧱 **分镜骨架复刻模版 (The Skeleton)**
(请严格按照以下格式生成 Fusion Prompt 和 Motion Prompt)

【图片提示词 (Fusion Prompt)】—— 静态定义
格式要求：严格按照以下五个模块顺序排列，使用句号分隔。
1. [镜头语言与构图]
2. **图一是[主体描述]**：[视觉身份锚点+服装材质细节] + [具体肢体动作姿态] + [五官细节+神情状态+视线落点]
3. **图二是[交互描述]**：（若有）[视觉身份锚点+服装材质] + [与图一的方位关系/交互动作] + [神情细节+视线落点]
4. [环境背景]：[地理位置] + [具体的建筑/装饰/元素细节] + [远景/氛围细节]
5. [画面属性]：[景深参数] + [核心光影类型] + [画质标签/艺术风格]

【视频提示词 (Motion Prompt)】—— 动态演变
格式要求：[镜头轨迹指令]，动作，[图X的主体动作演变 + **嘴部状态（张合/紧闭）**] + [图Y的表情/反应反馈] + [环境/物理反馈动态]。

🚫 **严苛禁令 (Hard Constraints)**
- **剧情忠实**: 严禁脑补剧本中不存在的剧情。
- **禁止人名**: Fusion/Motion Prompt 中严禁出现具体名字。
- **顺序锁死**: 图X 必须与 @ 标签顺序完美契合。
- **声画逻辑**: 严禁在内心独白时出现张嘴动作。
- **资产上限**: 单镜头最多3个资产。
- **镜号唯一**: shotNumber 必须从1开始连续递增，每个镜号必须唯一，严禁出现重复镜号。

{optimization_section}

## Output Format (Strict JSON)
必须严格按照以下JSON格式输出：

{{
  "shots": [
    {{
      "shotNumber": 1,
      "voiceCharacter": "配音角色名称",
      "emotion": "情绪",
      "intensity": "强度",
      "assets": "@角色名 @场景名",
      "dialogue": "对白内容",
      "fusionPrompt": "图片提示词",
      "motionPrompt": "视频提示词"
    }},
    {{
      "shotNumber": 2,
      ...
    }}
  ]
}}

**重要提示**：
1. shotNumber 必须从1开始，按顺序递增（1, 2, 3, ...），不能跳号或重复
2. assets 字段必须使用 @资产名 格式，多个资产用空格分隔
3. 所有字段都必须填写，不能为空

# 剧本内容
{script_content}

请严格按照上述要求生成分镜表，输出合法的JSON格式。"""

    def _clean_content(self, data):
        """
        递归清理内容中的格式符号
        移除 Markdown 加粗符 (** 或 *)、方括号 ([]) 和【】等符号
        """
        import re

        if isinstance(data, str):
            # 移除 **, *, 【, 】, [, ]
            cleaned = re.sub(r'(\*\*|\*|【|】|\[|\])', '', data)
            return cleaned.strip()
        elif isinstance(data, list):
            return [self._clean_content(item) for item in data]
        elif isinstance(data, dict):
            return {key: self._clean_content(value) for key, value in data.items()}
        else:
            return data

    def _parse_storyboard_result(self, ai_response: str) -> List[Dict]:
        """
        解析分镜生成结果
        """
        try:
            import re
            json_match = re.search(r'```json\s*(\{.*?\})\s*```', ai_response, re.DOTALL)

            if json_match:
                json_str = json_match.group(1)
            else:
                json_str = ai_response.strip()

            result = json.loads(json_str)

            if not isinstance(result, dict) or 'shots' not in result:
                raise ValueError("返回结果格式错误")

            shots = result.get('shots', [])

            # 转换字段名以匹配数据库schema
            formatted_shots = []
            for shot in shots:
                formatted_shots.append({
                    'shot_number': shot.get('shotNumber'),
                    'voice_character': shot.get('voiceCharacter', ''),
                    'emotion': shot.get('emotion', ''),
                    'intensity': shot.get('intensity', ''),
                    'asset_mapping': shot.get('assets', ''),  # 映射 assets 到 asset_mapping
                    'dialogue': shot.get('dialogue', ''),
                    'fusion_prompt': shot.get('fusionPrompt', ''),
                    'motion_prompt': shot.get('motionPrompt', '')
                })

            # 清理所有内容中的格式符号
            formatted_shots = self._clean_content(formatted_shots)

            return formatted_shots

        except json.JSONDecodeError as e:
            raise RuntimeError(f"AI响应JSON解析失败: {str(e)}\n响应内容: {ai_response[:500]}")
        except Exception as e:
            raise RuntimeError(f"解析AI响应失败: {str(e)}")

    @retry_on_failure(max_retries=3, delay=1)
    def _call_claude(self, prompt: str, model_id: str = "claude-sonnet-4-5-20250929", system_instruction: Optional[str] = None) -> str:
        """调用Claude API"""
        logger.info(f"调用Claude API，模型: {model_id}")
        try:
            import anthropic

            if not self.claude_api_key:
                raise ValueError("CLAUDE_API_KEY未设置")

            client = anthropic.Anthropic(api_key=self.claude_api_key)

            # 构建API调用参数
            api_params = {
                "model": model_id,
                "max_tokens": 16384,
                "messages": [
                    {"role": "user", "content": prompt}
                ]
            }

            # 如果有系统指令，添加到参数中
            if system_instruction:
                api_params["system"] = system_instruction

            message = client.messages.create(**api_params)

            logger.info("Claude API调用成功")
            return message.content[0].text

        except Exception as e:
            logger.error(f"Claude API调用失败: {str(e)}")
            raise RuntimeError(f"Claude API调用失败: {str(e)}")

    @retry_on_failure(max_retries=3, delay=1)
    def _call_deepseek(self, prompt: str, model_id: str = "deepseek-chat", system_instruction: Optional[str] = None) -> str:
        """调用DeepSeek API"""
        logger.info(f"调用DeepSeek API，模型: {model_id}")
        try:
            import openai
            import httpx

            if not self.deepseek_api_key:
                raise ValueError("DEEPSEEK_API_KEY未设置")

            # 创建不使用代理的httpx客户端（trust_env=False禁用所有代理检测）
            http_client = httpx.Client(trust_env=False)

            client = openai.OpenAI(
                api_key=self.deepseek_api_key,
                base_url="https://api.deepseek.com",
                http_client=http_client
            )

            # 构建消息列表
            messages = []
            if system_instruction:
                messages.append({"role": "system", "content": system_instruction})
            messages.append({"role": "user", "content": prompt})

            response = client.chat.completions.create(
                model=model_id,
                messages=messages
            )

            logger.info("DeepSeek API调用成功")
            return response.choices[0].message.content

        except Exception as e:
            logger.error(f"DeepSeek API调用失败: {str(e)}")
            raise RuntimeError(f"DeepSeek API调用失败: {str(e)}")

    @retry_on_failure(max_retries=3, delay=1)
    def _call_gemini(self, prompt: str, model_id: str = "gemini-2.0-flash-exp") -> str:
        """调用Gemini API"""
        logger.info(f"调用Gemini API，模型: {model_id}")
        try:
            import google.generativeai as genai

            if not self.gemini_api_key:
                raise ValueError("GEMINI_API_KEY未设置")

            genai.configure(api_key=self.gemini_api_key)
            model = genai.GenerativeModel(model_id)

            response = model.generate_content(prompt)
            logger.info("Gemini API调用成功")
            return response.text

        except Exception as e:
            logger.error(f"Gemini API调用失败: {str(e)}")
            raise RuntimeError(f"Gemini API调用失败: {str(e)}")

    @retry_on_failure(max_retries=3, delay=1)
    def _call_openai(self, prompt: str, model_id: str = "gpt-4") -> str:
        """调用OpenAI API（GPT-4等）"""
        logger.info(f"调用OpenAI API，模型: {model_id}")
        try:
            import openai

            if not self.openai_api_key:
                raise ValueError("OPENAI_API_KEY未设置")

            client = openai.OpenAI(api_key=self.openai_api_key)

            response = client.chat.completions.create(
                model=model_id,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )

            logger.info("OpenAI API调用成功")
            return response.choices[0].message.content

        except Exception as e:
            logger.error(f"OpenAI API调用失败: {str(e)}")
            raise RuntimeError(f"OpenAI API调用失败: {str(e)}")

            logger.info("GPT-4 API调用成功")
            return response.choices[0].message.content

        except Exception as e:
            logger.error(f"GPT-4 API调用失败: {str(e)}")
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


def get_ai_service(model: str = 'claude-sonnet-4-5') -> AIService:
    """
    获取AI服务实例

    Args:
        model: 模型标识符（如'claude-sonnet-4-5'）或旧的枚举值（如'claude'）

    Returns:
        AIService实例
    """
    # 兼容旧的枚举值
    if isinstance(model, AIModel):
        model = model.value

    return AIService(model)


def get_available_models() -> List[Dict[str, str]]:
    """
    获取所有可用的模型配置

    Returns:
        模型配置列表，每个模型包含：id, name, provider, description
    """
    models = []
    for model_id, config in MODEL_CONFIGS.items():
        models.append({
            'id': model_id,
            'name': config['name'],
            'provider': config['provider'],
            'description': config['description']
        })
    return models


# 全局服务实例（已废弃，保留用于向后兼容）
_ai_service_instance = None


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
