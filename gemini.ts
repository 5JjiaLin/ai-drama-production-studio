import { GoogleGenAI, Type, Schema } from "@google/genai";
import { BasicElementsData, StoryboardShot, VisualStyleElement, ScriptAnalysis } from "../types";

// Initialize Gemini Client
const apiKey = process.env.API_KEY || '';
const ai = new GoogleGenAI({ apiKey });

// Helper: Clean output (Remove Markdown and Think tags for R1)
const cleanJsonOutput = (text: string): string => {
  let cleaned = text.trim();
  // Remove markdown code blocks
  if (cleaned.startsWith('```')) {
    cleaned = cleaned.replace(/^```(?:json)?\n/, '').replace(/\n```$/, '');
  }
  // Remove <think> tags (common in DeepSeek R1)
  cleaned = cleaned.replace(/<think>[\s\S]*?<\/think>/g, '').trim();
  return cleaned;
};

// Helper: Recursively clean content strings (Remove symbols like *, [], 【】)
const cleanContent = (data: any): any => {
  if (typeof data === 'string') {
    // Remove Markdown bold (** or *), brackets (【】[]), and trim extra spaces
    // We remove these strictly as per request
    return data.replace(/(\*\*|\*|【|】|\[|\])/g, '').trim();
  }
  if (Array.isArray(data)) {
    return data.map(cleanContent);
  }
  if (typeof data === 'object' && data !== null) {
    const newData: any = {};
    for (const key in data) {
      newData[key] = cleanContent(data[key]);
    }
    return newData;
  }
  return data;
};

// Helper: Call DeepSeek API
const callDeepSeek = async (model: string, prompt: string, systemInstruction: string): Promise<string> => {
   const deepseekApiKey = process.env.DEEPSEEK_API_KEY;
   if (!deepseekApiKey) {
     throw new Error("请在环境变量中配置 DEEPSEEK_API_KEY 以使用 DeepSeek 模型。");
   }
   
   // DeepSeek R1 does not support json_object mode with reasoning enabled safely in all contexts,
   // but V3 (deepseek-chat) does.
   const responseFormat = model === 'deepseek-reasoner' ? undefined : { type: "json_object" };

   const response = await fetch('https://api.deepseek.com/chat/completions', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${deepseekApiKey}`
    },
    body: JSON.stringify({
      model: model,
      messages: [
        { role: "system", content: systemInstruction },
        { role: "user", content: prompt }
      ],
      response_format: responseFormat,
      stream: false
    })
  });

  if (!response.ok) {
     const errText = await response.text();
     throw new Error(`DeepSeek API 请求失败: ${response.status} - ${errText}`);
  }

  const json = await response.json();
  return json.choices[0].message.content;
};

// Helper: Call Claude API
const callClaude = async (model: string, prompt: string, systemInstruction: string): Promise<string> => {
   const anthropicApiKey = process.env.ANTHROPIC_API_KEY;
   if (!anthropicApiKey) {
     throw new Error("请在环境变量中配置 ANTHROPIC_API_KEY 以使用 Claude 模型。");
   }

   const response = await fetch('https://api.anthropic.com/v1/messages', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'x-api-key': anthropicApiKey,
      'anthropic-version': '2023-06-01',
      // 'anthropic-dangerous-direct-browser-access': 'true' // Only needed for SDK in browser, fetching directly is standard CORS
    },
    body: JSON.stringify({
      model: model,
      max_tokens: 8192,
      system: systemInstruction,
      messages: [
        { role: "user", content: prompt }
      ]
    })
  });

  if (!response.ok) {
     const errText = await response.text();
     throw new Error(`Claude API 请求失败: ${response.status} - ${errText}`);
  }

  const json = await response.json();
  return json.content[0].text;
};

/**
 * 深度研读剧本 (Deep Reading Phase)
 * 模拟通读三遍，提取核心理解、细节和情绪锚点。
 */
export const analyzeScriptDeeply = async (
  scriptText: string,
  modelName: string = "gemini-3-flash-preview"
): Promise<ScriptAnalysis> => {
  
  const isDeepSeek = modelName.startsWith('deepseek');
  const isClaude = modelName.startsWith('claude');
  const maxCharLimit = (isDeepSeek || isClaude) ? 200000 : 500000;

  const prompt = `
  # Role: 资深文学顾问 / 剧本分析师

  # 🚀 Execution Strategy: The "Three-Pass" Reading Method
  To ensure 100% understanding, you must verify the script through three distinct reading passes before outputting:
  1.  **Pass 1 (The Skeleton)**: Identify the core plot, major twists, and character arcs.
  2.  **Pass 2 (The Flesh)**: Hunt for specific visual details, hidden clues, and physical objects mentioned.
  3.  **Pass 3 (The Soul)**: Map the emotional beats. Why do characters act? what is the mood?

  # Task
  Based on the "Three-Pass" analysis, output the following:

  # Analysis Requirements
  1. **剧情深度理解 (Plot Logic)**: 概括核心故事线，理清因果关系，确保后续拆解不遗漏关键情节，也不脑补不存在的剧情。
  2. **细节挖掘 (Hidden Details)**: 挖掘剧本字里行间容易被忽略但对画面至关重要的细节（如：环境的破损程度、角色手里一直把玩的小物件、特定的光影暗示）。
  3. **情绪锚点 (Emotional Anchors)**: 梳理整个剧本的情绪流动曲线。找出剧情的高潮点、转折点和角色的心理变化节点。

  # Output Format (JSON)
  请严格按照以下Schema输出JSON：
  {
    "plotSummary": "...",
    "hiddenDetails": ["细节1", "细节2"...],
    "emotionalAnchors": "..."
  }

  Screenplay:
  ${scriptText.substring(0, maxCharLimit)}...
  `;

  if (isDeepSeek) {
    const systemInstruction = "You are a script analysis expert. Please output valid JSON only.";
    const resultText = await callDeepSeek(modelName, prompt, systemInstruction);
    return cleanContent(JSON.parse(cleanJsonOutput(resultText))) as ScriptAnalysis;
  }

  if (isClaude) {
    const systemInstruction = "You are a script analysis expert. Please output valid JSON only.";
    const resultText = await callClaude(modelName, prompt, systemInstruction);
    return cleanContent(JSON.parse(cleanJsonOutput(resultText))) as ScriptAnalysis;
  }

  // Gemini Path
  const schema: Schema = {
    type: Type.OBJECT,
    properties: {
      plotSummary: { type: Type.STRING },
      hiddenDetails: { type: Type.ARRAY, items: { type: Type.STRING } },
      emotionalAnchors: { type: Type.STRING }
    },
    required: ["plotSummary", "hiddenDetails", "emotionalAnchors"]
  };

  const response = await ai.models.generateContent({
    model: modelName,
    contents: prompt,
    config: {
      responseMimeType: "application/json",
      responseSchema: schema,
    }
  });

  return cleanContent(JSON.parse(response.text || '{}')) as ScriptAnalysis;
};

export const generateBasicElements = async (
  scriptText: string, 
  feedback?: string, 
  currentData?: BasicElementsData | null,
  modelName: string = "gemini-3-flash-preview",
  analysisContext?: ScriptAnalysis | null
): Promise<BasicElementsData> => {
  
  const isDeepSeek = modelName.startsWith('deepseek');
  const isClaude = modelName.startsWith('claude');
  const maxCharLimit = (isDeepSeek || isClaude) ? 200000 : 500000;

  // Construct Analysis Context String
  let deepAnalysisContext = "";
  if (analysisContext) {
    deepAnalysisContext = `
    ## 📚 PRE-COMPUTED DEEP SCRIPT ANALYSIS
    (Use this understanding to ensure no important assets are missed and details are accurate)
    
    **Plot Summary**: ${analysisContext.plotSummary}
    **Crucial Hidden Details**: ${analysisContext.hiddenDetails.join(', ')}
    **Emotional Flow**: ${analysisContext.emotionalAnchors}
    `;
  }

  const optimizationSection = feedback && currentData ? `
  ## OPTIMIZATION INSTRUCTIONS (CRITICAL - INCREMENTAL UPDATE)
  用户正在对现有的分析结果进行**局部优化**。你的任务是仅根据用户的反馈修改现有数据，**绝对保持其他未提及内容不变**。

  **当前已有数据 (Current Data)**:
  \`\`\`json
  ${JSON.stringify(currentData)}
  \`\`\`

  **用户反馈 (User Feedback)**:
  "${feedback}"

  **严格修改规则**:
  1. **锚定原数据**: 必须以【当前已有数据】为基准进行修改，而不是重新从剧本生成。
  2. **最小化修改**: 只修改用户明确提到的字段或条目。如果用户没提某个人物/道具/场景，**严禁改动它**。
  3. **格式合规**: 任何修改或新增的内容，必须严格遵守上文定义的【角色/道具/场景描述格式】。
  ` : feedback ? `
  ## OPTIMIZATION REQUEST
  用户查看了之前的分析结果，并提出了以下优化要求。请务必根据此要求重新生成或修改表格内容：
  >>> 用户要求: "${feedback}"
  **重要规则**：所有的优化调整必须严格基于用户输入的内容进行，**严禁私自改变用户未提及的内容**。
  ` : '';

  const jsonFormatTemplate = `
  {
    "characters": [
      { "name": "...", "role": "...", "description": "...", "gender": "...", "age": "...", "voice": "..." }
    ],
    "props": [
      { "name": "...", "description": "..." }
    ],
    "scenes": [
      { "name": "...", "description": "..." }
    ]
  }
  `;

  const prompt = `
  # Role: AI 漫剧全资产一致性专家 (Expert Level)

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

  ${deepAnalysisContext}

  ## Task
  Output the standardized JSON tables based on the rigorous process above.
  
  ## Output Format (Strict JSON)
  You must output a single JSON object. Do not wrap in markdown unless requested.
  Structure:
  ${jsonFormatTemplate}

  ### 1. 人物拆解表（参考视觉标准）
  - **角色描述要求**: 必须严格使用以下固定句式生成（**注意：严禁使用 Markdown 加粗或特殊符号，输出纯文本**）：
    "角色设计图，正面视角，全身，白色背景，一位[气质] [身份]，[年龄]岁，[身高]厘米，身材[特征]，[发型及发色描述]，[脸型/轮廓/五官细节]，眼神[状态]，气质[关键词]，穿着[颜色][材质][款式]，[腰部及配饰细节]，[鞋履描述]，站立姿势。"
  - **音色**: 听觉标签 (如: 男/女青年/少年)。

  ### 2. 核心代表性道具表（一致性控制项）
  - **逻辑**: 仅提取与主要角色深度关联、能代表其身份或性格的【重要道具】。这些道具将作为角色的“视觉符号”贯穿全剧。参考[深度研读]中的细节挖掘，确保不遗漏关键小物件。
  - **要求**: 描述必须纯物理样貌，**严禁出现人名**。
  - **描述格式**: 必须严格使用以下固定句式生成（**注意：严禁使用 Markdown 加粗或特殊符号，输出纯文本**）：
    "产品图，白色背景，一个[材质] [名称]，整体呈现[形状结构]，表面具有[纹理/图案/刻痕]，[核心组件细节说明]，展现出[新旧程度/特定光泽/质感]。"

  ### 3. 核心场景表（空间资产项）
  - **要求**: 描述必须纯物理样貌，**严禁出现人名**。
  - **描述格式**: 必须严格使用以下固定句式生成（**注意：严禁使用 Markdown 加粗或特殊符号，输出纯文本**）：
    "场景概念图，广角视角，[空间结构/布局方式]，装修建筑风格为[风格]，整体主色调为[色彩]，[光影调性描述]，环境包含[地面/墙面/装饰物细节]，空气中带有[微粒/氛围元素]。"

  ## Rules
  1. **完整性检查 (Verification)**: Ensure ALL assets that drive the plot or heighten emotions are included. Do not leave out "small but significant" items.
  2. **强制格式一致性**: 所有描述必须严格遵循上述“流式结构”。
  3. **去身份化描述**: 在道具和场景表中，禁止使用“某某的桌子”。
  4. **资产锁定**: 道具和场景表的最后三列固定为“中性”、“青年”、“无”。
  5. **纯净文本输出**: 严禁在输出内容中使用 Markdown 加粗符 (** 或 *)、方括号 ([]) 或【】等符号。
  6. **语言**: 请使用中文输出所有内容。

  ${optimizationSection}
  
  Screenplay Text:
  ${scriptText.substring(0, maxCharLimit)}... (truncated if too long)`;

  if (isDeepSeek) {
    const systemInstruction = "你是一位AI漫剧全资产一致性专家。请严格输出合法的 JSON 格式。不要使用 Markdown 符号。";
    const resultText = await callDeepSeek(modelName, prompt, systemInstruction);
    return cleanContent(JSON.parse(cleanJsonOutput(resultText))) as BasicElementsData;
  }

  if (isClaude) {
    const systemInstruction = "你是一位AI漫剧全资产一致性专家。请严格输出合法的 JSON 格式。不要使用 Markdown 符号。";
    const resultText = await callClaude(modelName, prompt, systemInstruction);
    return cleanContent(JSON.parse(cleanJsonOutput(resultText))) as BasicElementsData;
  }

  // Gemini Path
  const schema: Schema = {
    type: Type.OBJECT,
    properties: {
      characters: {
        type: Type.ARRAY,
        items: {
          type: Type.OBJECT,
          properties: {
            name: { type: Type.STRING },
            role: { type: Type.STRING },
            description: { type: Type.STRING },
            gender: { type: Type.STRING },
            age: { type: Type.STRING },
            voice: { type: Type.STRING }
          },
          required: ["name", "role", "description", "gender", "age", "voice"]
        }
      },
      props: {
        type: Type.ARRAY,
        items: {
          type: Type.OBJECT,
          properties: {
            name: { type: Type.STRING },
            description: { type: Type.STRING }
          },
          required: ["name", "description"]
        }
      },
      scenes: {
        type: Type.ARRAY,
        items: {
          type: Type.OBJECT,
          properties: {
            name: { type: Type.STRING },
            description: { type: Type.STRING }
          },
          required: ["name", "description"]
        }
      }
    },
    required: ["characters", "props", "scenes"]
  };

  const response = await ai.models.generateContent({
    model: modelName,
    contents: prompt,
    config: {
      responseMimeType: "application/json",
      responseSchema: schema,
      systemInstruction: "你是一位AI漫剧全资产一致性专家。在输出前，请务必进行自我审查，确保准确率达到99%以上，绝无遗漏。确保输出纯文本，不要包含 * 或【】等特殊符号。"
    }
  });

  return cleanContent(JSON.parse(response.text || '{}')) as BasicElementsData;
};

export const generateStoryboard = async (
  scriptText: string, 
  basicElements?: BasicElementsData | null,
  feedback?: string,
  minShots?: number,
  maxShots?: number,
  currentShots?: StoryboardShot[] | null,
  modelName: string = "gemini-3-flash-preview",
  analysisContext?: ScriptAnalysis | null
): Promise<{ shots: StoryboardShot[] }> => {
  
  const isDeepSeek = modelName.startsWith('deepseek');
  const isClaude = modelName.startsWith('claude');
  const maxCharLimit = (isDeepSeek || isClaude) ? 200000 : 500000;

  // Construct asset constraints string
  let assetConstraints = "";
  if (basicElements) {
    const chars = basicElements.characters.map(c => c.name).join(', ');
    const props = basicElements.props.map(p => p.name).join(', ');
    const scenes = basicElements.scenes.map(s => s.name).join(', ');
    
    assetConstraints = `
    ⚠️ **CRITICAL: ASSET MAPPING CONSISTENCY**
    In the [assets] column (e.g., @角色 @场景), you MUST strictly use the names from the following extracted lists.
    Do not invent new names for characters, props, or scenes that were already defined.
    - **Available Characters**: ${chars}
    - **Available Props**: ${props}
    - **Available Scenes**: ${scenes}
    `;
  }

  // Construct Deep Analysis Context
  let deepAnalysisContext = "";
  if (analysisContext) {
    deepAnalysisContext = `
    ## 📚 DEEP SCRIPT UNDERSTANDING (STRICT ADHERENCE REQUIRED)
    You have previously analyzed this script deeply. Use the following context to ensure the storyboard is 100% faithful to the plot and emotions.

    **Plot Logic**: ${analysisContext.plotSummary}
    **Emotional Anchors**: ${analysisContext.emotionalAnchors}

    **STRICT RULE**: Do NOT hallucinate scenes or actions that are not implied by the plot logic above. The storyboard must follow the script's actual flow accurately. Use the "Emotional Anchors" to set the correct [Emotion] and [Intensity] for each shot.
    `;
  }

  // Construct shot count constraints
  let shotCountConstraint = "";
  if (minShots !== undefined && maxShots !== undefined && minShots > 0 && maxShots >= minShots) {
    shotCountConstraint = `
    🔢 **CRITICAL: SHOT COUNT CONSTRAINT**
    You MUST generate a storyboard with a total number of shots between **${minShots}** and **${maxShots}**.
    `;
  }

  const optimizationSection = feedback && currentShots ? `
  ## OPTIMIZATION INSTRUCTIONS (CRITICAL - INCREMENTAL UPDATE)
  用户正在对现有的分镜表进行**局部优化**。你的任务是仅根据用户的反馈修改现有镜头，**绝对保持其他未提及内容不变**。
  **当前已有分镜 (Current Storyboard)**:
  \`\`\`json
  ${JSON.stringify({ shots: currentShots })}
  \`\`\`
  **用户反馈 (User Feedback)**:
  "${feedback}"
  ` : feedback ? `
  ## OPTIMIZATION REQUEST
  用户查看了之前的分镜结果，并提出了以下优化要求。请务必根据此要求重新生成分镜表：
  >>> 用户要求: "${feedback}"
  ` : '';

  const jsonFormatTemplate = `
  {
    "shots": [
      {
        "shotNumber": 1,
        "voiceCharacter": "...",
        "emotion": "...",
        "intensity": "...",
        "assets": "@...",
        "dialogue": "...",
        "fusionPrompt": "...",
        "motionPrompt": "..."
      }
    ]
  }
  `;

  // UPDATED PROMPT: v13.0 Industrial Asset Anonymization Version
  const prompt = `
  # Role: 顶级导演分镜视觉系统 (System Prompt) - v13.0 工业资产匿名化版

  🎭 **角色定位**
  你是一位精通电影视觉工程与 AI 工业流提示词的顶级导演。你通过“图号占位符”与“视觉特征锚点”构建一套不依赖人名的、具备极高一致性的视觉系统。

  ${deepAnalysisContext}

  ${assetConstraints}

  ${shotCountConstraint}

  📐 **核心全局协议 (The Iron Rules)**

  1. **资产映射与匿名化 (Asset Anonymization)**
     - **标签定义**：【场景角色道具】栏使用 \`@资产名\` 格式，标签间以空格区分。
     - **绝对索引**：**图一** 锁定标签栏第 1 个 @ 资产，依此类推。
     - **【核心禁令】**：图片提示词（Fusion）与视频提示词（Motion）中**严禁出现任何角色名称**。必须统一使用 **图一**、**图二** 来指代。

  2. **🔊 对白与嘴部逻辑 (Lip-Sync Logic)**
     - **对白内容**：若文案为角色说出的话 → 必须描述为“**图X嘴唇张合说话**”。
     - **内心独白**：若文案为心理活动/系统提示 → 必须描述为“**图X嘴唇紧闭**”。

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

  ## Output Format (Strict JSON)
  You must output a single JSON object.
  Structure:
  ${jsonFormatTemplate}

  ${optimizationSection}

  Screenplay Text:
  ${scriptText.substring(0, maxCharLimit)}...`;

  if (isDeepSeek) {
    const systemInstruction = "你是一位精通电影视觉工程的顶级导演。你必须严格遵守'分镜骨架复刻模版'。严禁脑补剧情，必须忠实于剧本原意。请输出合法的 JSON。不要使用 Markdown 符号或【】符号。";
    const resultText = await callDeepSeek(modelName, prompt, systemInstruction);
    return cleanContent(JSON.parse(cleanJsonOutput(resultText)));
  }

  if (isClaude) {
    const systemInstruction = "你是一位精通电影视觉工程的顶级导演。你必须严格遵守'分镜骨架复刻模版'。严禁脑补剧情，必须忠实于剧本原意。请输出合法的 JSON。不要使用 Markdown 符号或【】符号。";
    const resultText = await callClaude(modelName, prompt, systemInstruction);
    return cleanContent(JSON.parse(cleanJsonOutput(resultText)));
  }

  // Gemini Path
  const schema: Schema = {
    type: Type.OBJECT,
    properties: {
      shots: {
        type: Type.ARRAY,
        items: {
          type: Type.OBJECT,
          properties: {
            shotNumber: { type: Type.INTEGER },
            voiceCharacter: { type: Type.STRING },
            emotion: { type: Type.STRING },
            intensity: { type: Type.STRING },
            assets: { type: Type.STRING, description: "@标签 格式，空格分隔" },
            dialogue: { type: Type.STRING },
            fusionPrompt: { type: Type.STRING, description: "关键帧图片提示词" },
            motionPrompt: { type: Type.STRING, description: "视频动态提示词" }
          },
          required: ["shotNumber", "voiceCharacter", "emotion", "intensity", "assets", "dialogue", "fusionPrompt", "motionPrompt"]
        }
      }
    },
    required: ["shots"]
  };

  const response = await ai.models.generateContent({
    model: modelName,
    contents: prompt,
    config: {
      responseMimeType: "application/json",
      responseSchema: schema,
      systemInstruction: "你是一位精通电影视觉工程的顶级导演。你必须严格遵守'分镜骨架复刻模版'。严禁脑补剧情，必须忠实于剧本原意。请确保输出纯文本，不要包含 * 或【】等特殊符号。"
    }
  });

  return cleanContent(JSON.parse(response.text || '{"shots": []}'));
};

export const generateVisualStyle = async (
  scriptText: string, 
  feedback?: string,
  currentElements?: VisualStyleElement[] | null,
  modelName: string = "gemini-3-flash-preview"
): Promise<{ elements: VisualStyleElement[] }> => {
  
  const isDeepSeek = modelName.startsWith('deepseek');
  const isClaude = modelName.startsWith('claude');
  const maxCharLimit = (isDeepSeek || isClaude) ? 200000 : 500000;

  // Visual style usually doesn't need deep plot analysis, just style extraction, 
  // keeping it as is to save tokens unless requested.
  const optimizationSection = feedback && currentElements ? `
  ## OPTIMIZATION INSTRUCTIONS (CRITICAL - INCREMENTAL UPDATE)
  用户正在对现有的画面风格指令进行**局部优化**。
  **当前已有指令**:
  \`\`\`json
  ${JSON.stringify({ elements: currentElements })}
  \`\`\`
  **用户反馈**:
  "${feedback}"
  ` : feedback ? `
  ## OPTIMIZATION REQUEST
  用户要求: "${feedback}"
  ` : '';

  const jsonFormatTemplate = `
  {
    "elements": [
      { "category": "...", "description": "...", "reference": "..." }
    ]
  }
  `;

  const prompt = `
  # Role: AI 漫剧指令纯净输出专家 (Role v5.0)

  # Task
  根据剧本涉及的类别（人物、道具、场景），输出预设的固定指令文本。
  
  ## Output Format (Strict JSON)
  You must output a single JSON object.
  Structure:
  ${jsonFormatTemplate}

  # 📥 固定输出内容

  ## 【人物固定块】(对应 category: "人物生成指令")
  超写实摄影，电影动画风格，3D动画， cinematic photography， skin texture, detailed eyes，电影级灯光，画面具有故事感和情绪张力，适合小说封面或关键场景。光影效果绝佳，光影颜色层次丰富，人物为亚洲形象，且符合大众审美，人物形象始终保持一致。人物服装具有质感，注重服装颜色、光影、细节，有视觉冲击力。
  生成人物四视图，包括正面全视图，侧视图，背视图，脸部特写。

  ## 【道具固定块】(对应 category: "道具生成指令")
  超写实摄影，电影动画风格，3D动画， cinematic photography， surface texture, material details，电影级灯光，画面具有故事感和情绪张力。光影效果绝佳，光影颜色层次丰富，物体构造严谨，且符合大众审美，物体形象始终保持一致。道具表面具有质感，注重颜色、光影、细节，有视觉冲击力。
  生成道具四视图，包括正面全视图，侧视图，背视图，手持视图（展示比例关系）。

  ## 【场景固定块】(对应 category: "场景生成指令")
  超写实摄影，电影动画风格，3D动画， cinematic photography， environment texture, spatial depth，电影级灯光，画面具有故事感和情绪张力。光影效果绝佳，光影颜色层次丰富，场景构图严谨，且符合大众审美，空间氛围始终保持一致。场景环境具有质感，注重颜色、光影、细节，有视觉冲击力。
  生成场景三视图，包括全景远视图（环境全貌）、中景平视图（叙事中心）、局部特写视图（环境细节）。

  ${optimizationSection}
  
  Screenplay Text (Reference only for existence check):
  ${scriptText.substring(0, maxCharLimit)}...`;

  if (isDeepSeek) {
    const systemInstruction = "你是一位AI漫剧指令纯净输出专家。请输出合法的 JSON。不要使用特殊符号。";
    const resultText = await callDeepSeek(modelName, prompt, systemInstruction);
    return cleanContent(JSON.parse(cleanJsonOutput(resultText)));
  }

  if (isClaude) {
    const systemInstruction = "你是一位AI漫剧指令纯净输出专家。请输出合法的 JSON。不要使用特殊符号。";
    const resultText = await callClaude(modelName, prompt, systemInstruction);
    return cleanContent(JSON.parse(cleanJsonOutput(resultText)));
  }

  // Gemini Path
  const schema: Schema = {
    type: Type.OBJECT,
    properties: {
      elements: {
        type: Type.ARRAY,
        items: {
          type: Type.OBJECT,
          properties: {
            category: { type: Type.STRING, description: "e.g., 人物生成指令" },
            description: { type: Type.STRING, description: "固定输出内容" },
            reference: { type: Type.STRING, description: "备注，如 'SD Prompt'" }
          }
        }
      }
    },
    required: ["elements"]
  };

  const response = await ai.models.generateContent({
    model: modelName,
    contents: prompt,
    config: {
      responseMimeType: "application/json",
      responseSchema: schema,
      systemInstruction: "你是一位AI漫剧指令纯净输出专家。不要输出特殊符号。"
    }
  });

  return cleanContent(JSON.parse(response.text || '{"elements": []}'));
};