import { BasicElementsData, StoryboardShot, ScriptAnalysis } from "../types";

/**
 * 分段生成分镜表辅助函数
 * 用于处理大量分镜需求
 */

// 从 gemini.ts 导入需要的辅助函数
const cleanJsonOutput = (text: string): string => {
  let cleaned = text.trim();
  if (cleaned.startsWith('```')) {
    cleaned = cleaned.replace(/^```(?:json)?\n/, '').replace(/\n```$/, '');
  }
  cleaned = cleaned.replace(/<think>[\s\S]*?<\/think>/g, '').trim();

  // 移除可能的 BOM 和其他不可见字符
  cleaned = cleaned.replace(/^\uFEFF/, '').replace(/^\u00EF\u00BB\u00BF/, '');

  // 尝试找到第一个 { 和最后一个 }，提取 JSON 部分
  const firstBrace = cleaned.indexOf('{');
  const lastBrace = cleaned.lastIndexOf('}');
  if (firstBrace !== -1 && lastBrace !== -1 && lastBrace > firstBrace) {
    cleaned = cleaned.substring(firstBrace, lastBrace + 1);
  }

  return cleaned;
};

const cleanContent = (data: any): any => {
  if (typeof data === 'string') {
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

// 类型定义
interface Progress {
  current: number;
  total: number;
  message: string;
}

/**
 * 分段生成分镜表（用于大量分镜需求）
 * 策略：将总分镜数拆分成多个批次，每批15-20个分镜
 */
export const generateStoryboardInChunks = async (
  scriptText: string,
  basicElements: BasicElementsData | null,
  minShots: number,
  maxShots: number,
  modelName: string,
  analysisContext: ScriptAnalysis | null,
  apiKey: string,
  baseUrl: string,
  callClaude: Function,
  callOpenAI: Function,
  onProgress?: (progress: Progress) => void,
  callGemini?: Function,
  callDeepSeek?: Function
): Promise<{ shots: StoryboardShot[] }> => {

  // 优化分段策略：大幅增加单批次生成数量，减少分段次数
  const targetShots = Math.floor((minShots + maxShots) / 2);
  const CHUNK_SIZE = targetShots > 100 ? 30 : (targetShots > 60 ? 40 : 50); // 大幅提高单批生成量
  const numChunks = Math.ceil(targetShots / CHUNK_SIZE);

  let allShots: StoryboardShot[] = [];

  // 第一步：生成剧本大纲（将剧本分段）
  if (onProgress) {
    onProgress({ current: 0, total: numChunks, message: `正在分析剧本结构...（共${numChunks}批，每批约${CHUNK_SIZE}个分镜）` });
  }

  const scriptSections = await splitScriptIntoSections(scriptText, numChunks, modelName, analysisContext, callClaude, callOpenAI, callGemini, callDeepSeek);

  // 第二步：为每个段落生成分镜
  for (let i = 0; i < numChunks; i++) {
    const chunkMin = Math.floor(CHUNK_SIZE * 0.8); // 12
    const chunkMax = Math.floor(CHUNK_SIZE * 1.2); // 18

    if (onProgress) {
      onProgress({
        current: i + 1,
        total: numChunks,
        message: `正在生成第 ${i + 1}/${numChunks} 批分镜 (已完成${allShots.length}个，每批${CHUNK_SIZE}个，预计还需${(numChunks - i - 1) * 2}分钟)...`
      });
    }

    try {
      // 为当前段落生成分镜，传递已有分镜作为上下文
      const chunkResult = await generateStoryboardChunk(
        scriptSections[i],
        scriptText,
        basicElements,
        chunkMin,
        chunkMax,
        allShots.length + 1, // 起始镜头号
        modelName,
        analysisContext,
        allShots, // 前面已生成的分镜
        callClaude,
        callOpenAI,
        callGemini,
        callDeepSeek
      );

      allShots = allShots.concat(chunkResult.shots);

      // 成功后显示进度
      if (onProgress) {
        onProgress({
          current: i + 1,
          total: numChunks,
          message: `✓ 第 ${i + 1}/${numChunks} 批已完成（${chunkResult.shots.length}个分镜），累计${allShots.length}个`
        });
      }
    } catch (error: any) {
      console.error(`分段 ${i + 1} 生成失败:`, error);

      // 如果已经生成了一些分镜，给用户选择
      if (allShots.length > 0) {
        const continueMsg = `分段生成在第 ${i + 1}/${numChunks} 批时失败，但已成功生成${allShots.length}个分镜。错误：${error.message}`;
        throw new Error(continueMsg);
      } else {
        throw new Error(`分段生成在第 ${i + 1}/${numChunks} 批时失败: ${error.message}。建议：1) 缩短剧本长度 2) 减少分镜数量 3) 检查网络连接`);
      }
    }
  }

  // 重新编号确保连续性
  allShots = allShots.map((shot, index) => ({
    ...shot,
    shotNumber: index + 1
  }));

  return { shots: allShots };
};

/**
 * 将剧本分割成多个段落（用于分段生成）
 */
const splitScriptIntoSections = async (
  scriptText: string,
  numSections: number,
  modelName: string,
  analysisContext: ScriptAnalysis | null,
  callClaude: Function,
  callOpenAI: Function,
  callGemini?: Function,
  callDeepSeek?: Function
): Promise<string[]> => {

  const isClaude = modelName.startsWith('claude');
  const isOpenAI = modelName.startsWith('gpt-');
  const isDeepSeek = modelName.startsWith('deepseek');
  const isGemini = !isClaude && !isOpenAI && !isDeepSeek;

  const prompt = `
  # 任务：将剧本分割成 ${numSections} 个连续的段落

  剧本总结: ${analysisContext?.plotSummary || ''}

  请将以下剧本按照情节自然分割成 ${numSections} 个段落。每个段落应该：
  1. 包含完整的情节片段（不要在对话中间截断）
  2. 尽量均匀分配长度
  3. 在情节转折点或场景切换处分割
  4. **严格按照剧本的时间顺序**，确保段落1是开头，段落${numSections}是结尾
  5. 确保每个段落的剧情承接紧密，不遗漏任何情节

  输出格式（JSON）：
  {
    "sections": ["段落1内容", "段落2内容", ...]
  }

  剧本内容：
  ${scriptText.substring(0, 300000)}
  `;

  const systemInstruction = "你是剧本分析专家。请输出合法的 JSON。";

  try {
    let resultText: string;
    if (isClaude) {
      resultText = await callClaude(modelName, prompt, systemInstruction, 300000); // 增加到5分钟超时
    } else if (isOpenAI) {
      resultText = await callOpenAI(modelName, prompt, systemInstruction, 300000);
    } else if (isDeepSeek && callDeepSeek) {
      resultText = await callDeepSeek(modelName, prompt, systemInstruction);
    } else if (isGemini && callGemini) {
      resultText = await callGemini(modelName, prompt, systemInstruction, 300000);
    } else {
      // 降级方案：简单等分（按字符数切割）
      const sectionLength = Math.ceil(scriptText.length / numSections);
      const sections: string[] = [];
      for (let i = 0; i < numSections; i++) {
        const start = i * sectionLength;
        const end = Math.min((i + 1) * sectionLength, scriptText.length);
        sections.push(scriptText.substring(start, end));
      }
      return sections;
    }

    const cleaned = cleanJsonOutput(resultText);
    console.log('[Debug] 剧本分割返回:', cleaned.substring(0, 200));
    const parsed = JSON.parse(cleaned);
    return parsed.sections || [];
  } catch (error) {
    console.warn('AI分割失败，使用简单分割:', error);
    // 降级方案：简单等分
    const sectionLength = Math.ceil(scriptText.length / numSections);
    const sections: string[] = [];
    for (let i = 0; i < numSections; i++) {
      const start = i * sectionLength;
      const end = Math.min((i + 1) * sectionLength, scriptText.length);
      sections.push(scriptText.substring(start, end));
    }
    return sections;
  }
};

/**
 * 生成单个分镜批次
 */
const generateStoryboardChunk = async (
  sectionText: string,
  fullScriptText: string,
  basicElements: BasicElementsData | null,
  minShots: number,
  maxShots: number,
  startShotNumber: number,
  modelName: string,
  analysisContext: ScriptAnalysis | null,
  previousShots: StoryboardShot[],
  callClaude: Function,
  callOpenAI: Function,
  callGemini?: Function,
  callDeepSeek?: Function
): Promise<{ shots: StoryboardShot[] }> => {

  const isClaude = modelName.startsWith('claude');
  const isOpenAI = modelName.startsWith('gpt-');
  const isDeepSeek = modelName.startsWith('deepseek');
  const isGemini = !isClaude && !isOpenAI && !isDeepSeek;

  // 构建资产约束
  let assetConstraints = "";
  if (basicElements) {
    const chars = basicElements.characters.map(c => c.name).join(', ');
    const props = basicElements.props.map(p => p.name).join(', ');
    const scenes = basicElements.scenes.map(s => s.name).join(', ');

    assetConstraints = `
    ⚠️ **CRITICAL: ASSET MAPPING CONSISTENCY**
    - **Available Characters**: ${chars}
    - **Available Props**: ${props}
    - **Available Scenes**: ${scenes}
    `;
  }

  // 前文提示（如果有前面的分镜）
  let previousContext = "";
  if (previousShots.length > 0) {
    const lastFewShots = previousShots.slice(-5); // 增加到5个分镜作为上下文，提高连贯性
    previousContext = `
    ## 📌 前文分镜参考（保持连贯性）
    前面已生成 ${previousShots.length} 个分镜。最近的分镜：
    ${lastFewShots.map(s => `#${s.shotNumber}: ${s.dialogue}`).join('\n')}

    **CRITICAL - 顺序要求**：
    1. 你的起始镜头号是 ${startShotNumber}，必须严格从这个编号开始
    2. 当前段落必须紧接前文剧情，不能跳跃或重复
    3. 确保剧情发展的时间顺序正确
    `;
  }

  // 构建深度分析上下文
  const deepAnalysisContext = analysisContext ? `
  📖 **Deep Script Understanding (来自剧本深度解析)**
  - **情节梗概**: ${analysisContext.plotSummary || ''}
  - **情绪锚点**: ${analysisContext.emotionalAnchors || ''}
  - **隐藏细节**: ${analysisContext.hiddenDetails?.join('; ') || ''}
  ` : '';

  // 镜头数量约束
  const shotCountConstraint = `
  🔢 **CRITICAL: SHOT COUNT CONSTRAINT**
  You MUST generate a storyboard with a total number of shots between **${minShots}** and **${maxShots}**.
  起始镜头号必须是 **${startShotNumber}**。
  `;

  const jsonFormatTemplate = `
  {
    "shots": [
      {
        "shotNumber": ${startShotNumber},
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

  // 完整的prompt模板（与主文件保持一致）
  const prompt = `
  # Role: 顶级导演分镜视觉系统 (System Prompt) - v13.0 工业资产匿名化版

  🎭 **角色定位**
  你是一位精通电影视觉工程与 AI 工业流提示词的顶级导演。你通过"图号占位符"与"视觉特征锚点"构建一套不依赖人名的、具备极高一致性的视觉系统。

  ${deepAnalysisContext}

  ${assetConstraints}

  ${shotCountConstraint}

  ${previousContext}

  ⚠️ **CRITICAL - 剧情顺序要求**
  1. 必须严格按照提供的剧本片段的时间顺序生成分镜
  2. 不得跳过任何情节或对话
  3. 不得重复之前已生成的内容
  4. 确保与前文分镜的剧情连贯性

  📐 **核心全局协议 (The Iron Rules)**

  1. **资产映射与匿名化 (Asset Anonymization)**
     - **标签定义**：【场景角色道具】栏使用 \`@资产名\` 格式，标签间以空格区分。
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
  - **严格遵守**：视频提示词前半段为镜头运行轨迹，后半段为动作描述。以"动作"为分割线。

  ## Output Format (Strict JSON)
  You must output a single JSON object.
  Structure:
  ${jsonFormatTemplate}

  剧本片段：
  ${sectionText}
  `;

  const systemInstruction = "你是一位精通电影视觉工程的顶级导演。你必须严格遵守'分镜骨架复刻模版'。严禁脑补剧情，必须忠实于剧本原意。请输出合法的 JSON。不要使用 Markdown 符号或【】符号。";

  // 添加重试机制
  let resultText: string;
  let retryCount = 0;
  const MAX_RETRIES = 2;

  while (retryCount <= MAX_RETRIES) {
    try {
      if (isClaude) {
        resultText = await callClaude(modelName, prompt, systemInstruction, 600000); // 增加到10分钟超时，支持更多分镜
      } else if (isOpenAI) {
        resultText = await callOpenAI(modelName, prompt, systemInstruction, 600000);
      } else if (isDeepSeek && callDeepSeek) {
        resultText = await callDeepSeek(modelName, prompt, systemInstruction);
      } else if (isGemini && callGemini) {
        resultText = await callGemini(modelName, prompt, systemInstruction, 600000);
      } else {
        throw new Error('不支持的模型类型或缺少 API 调用函数');
      }
      break; // 成功则跳出循环
    } catch (error: any) {
      retryCount++;
      if (retryCount > MAX_RETRIES) {
        throw new Error(`分镜生成失败（已重试${MAX_RETRIES}次）: ${error.message}`);
      }
      console.warn(`第${retryCount}次重试...`);
      await new Promise(resolve => setTimeout(resolve, 2000)); // 等待2秒后重试
    }
  }

  try {
    const cleaned = cleanJsonOutput(resultText!);
    console.log('[Debug] 分镜批次生成返回:', cleaned.substring(0, 300));
    return cleanContent(JSON.parse(cleaned));
  } catch (error: any) {
    console.error('[Error] 分镜批次 JSON 解析失败:', error.message);
    throw new Error(`分镜生成失败: JSON 解析错误 - ${error.message}`);
  }
};
