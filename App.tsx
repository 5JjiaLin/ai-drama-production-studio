import React, { useState, useRef, useEffect } from 'react';
import { Upload, FileText, ArrowRight, Wand2, RefreshCcw, Film, Palette, Users, Check, Settings2, Sparkles, BrainCircuit } from 'lucide-react';
import StepIndicator from './components/StepIndicator';
import Button from './components/Button';
import DataTable from './components/DataTable';
import FeedbackInput from './components/FeedbackInput';
import { parseDocx } from './services/fileUtils';
import { generateBasicElements, generateStoryboard, generateVisualStyle, analyzeScriptDeeply } from './services/gemini';
import { setApiConfig } from './services/apiConfig';
import { AppStep, BasicElementsData, StoryboardShot, VisualStyleElement, ScriptAnalysis } from './types';

function App() {
  const [step, setStep] = useState<AppStep>(AppStep.UPLOAD);
  const [scriptText, setScriptText] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [loadingMessage, setLoadingMessage] = useState('');
  const [error, setError] = useState<string | null>(null);
  
  // Model State
  const [modelName, setModelName] = useState("claude-sonnet-4-5-20250929");
  const [apiKey, setApiKey] = useState("");
  const [apiBaseUrl, setApiBaseUrl] = useState("/api"); // 默认使用 Vite 代理

  // Data States
  const [scriptAnalysis, setScriptAnalysis] = useState<ScriptAnalysis | null>(null);
  const [basicElements, setBasicElements] = useState<BasicElementsData | null>(null);
  const [storyboard, setStoryboard] = useState<StoryboardShot[] | null>(null);
  const [visualStyle, setVisualStyle] = useState<VisualStyleElement[] | null>(null);

  // Storyboard Configuration State
  const [minShots, setMinShots] = useState<number>(10);
  const [maxShots, setMaxShots] = useState<number>(30);

  // Progress State for chunked generation
  const [progress, setProgress] = useState<{ current: number; total: number; message: string } | null>(null);

  const fileInputRef = useRef<HTMLInputElement>(null);

  // Load API key on component mount
  useEffect(() => {
    const loadApiKey = async () => {
      try {
        const response = await fetch('/apikey.txt');
        if (response.ok) {
          const key = await response.text();
          const trimmedKey = key.trim();
          setApiKey(trimmedKey);
          setApiConfig(trimmedKey);
        }
      } catch (error) {
        console.warn('无法自动加载apikey.txt，请手动输入API Key');
      }
    };
    loadApiKey();
  }, []);

  // Update API config when apiKey or baseUrl changes
  useEffect(() => {
    if (apiKey) {
      setApiConfig(apiKey, apiBaseUrl);
    }
  }, [apiKey, apiBaseUrl]);

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setIsLoading(true);
    setLoadingMessage('正在读取文件...');
    setError(null);
    try {
      if (file.name.endsWith('.docx')) {
        const text = await parseDocx(file);
        setScriptText(text);
      } else {
        // Simple text file read
        const text = await file.text();
        setScriptText(text);
      }
    } catch (err) {
      setError("无法读取文件。请确保是有效的 .docx 或文本文件。");
      console.error(err);
    } finally {
      setIsLoading(false);
      setLoadingMessage('');
    }
  };

  const handleNextStep = () => {
    if (step === AppStep.VISUAL_STYLE) return;
    setStep((prev) => prev + 1);
    window.scrollTo(0, 0);
  };

  // --- Breakdown Handlers ---

  const handleAnalyzeBasicElements = async (feedback?: string) => {
    if (!scriptText) return;
    setIsLoading(true);
    setError(null);
    
    try {
      let currentAnalysis = scriptAnalysis;

      // 1. Deep Analysis Phase (Perform only if not present, or if this is not a feedback optimization loop)
      // Note: If user is giving feedback, we usually stick to original analysis unless we want to re-analyze.
      // For now, we assume analysis happens once at the start.
      if (!currentAnalysis && !feedback) {
         setLoadingMessage(`AI (${modelName}) 正在深度通读剧本（理解剧情、挖掘细节、分析情绪）...`);
         currentAnalysis = await analyzeScriptDeeply(scriptText, modelName);
         setScriptAnalysis(currentAnalysis);
      }

      // 2. Asset Generation Phase
      setLoadingMessage(feedback ? '正在根据反馈优化资产...' : '正在拆解人物、道具与场景...');
      
      // Pass basicElements (current data) if it exists, so AI can optimize incrementally
      const data = await generateBasicElements(scriptText, feedback, basicElements, modelName, currentAnalysis);
      setBasicElements(data);
    } catch (err: any) {
      setError(err.message || "AI 分析失败，请重试。");
      console.error(err);
    } finally {
      setIsLoading(false);
      setLoadingMessage('');
    }
  };

  const handleAnalyzeStoryboard = async (feedback?: string) => {
    if (!scriptText) return;
    setIsLoading(true);
    setLoadingMessage(feedback ? '正在根据反馈优化分镜...' : '正在基于深度理解生成导演级分镜（可能需要1-3分钟）...');
    setError(null);
    setProgress(null); // Reset progress

    try {
      // Pass scriptAnalysis for strict plot adherence
      const data = await generateStoryboard(
        scriptText,
        basicElements,
        feedback,
        minShots,
        maxShots,
        storyboard,
        modelName,
        scriptAnalysis,
        // Progress callback
        (progressData) => {
          setProgress(progressData);
          setLoadingMessage(progressData.message);
        }
      );
      setStoryboard(data.shots);
      setProgress(null); // Clear progress on success
    } catch (err: any) {
      let errorMessage = err.message || "AI 分析失败，请重试。";
      if (err.message?.includes('Failed to fetch') || err.name === 'TypeError') {
        errorMessage = "网络请求失败或超时。分镜生成需要较长时间，建议：1) 减少分镜数量范围 2) 缩短剧本长度 3) 检查网络连接后重试";
      }
      setError(errorMessage);
      setProgress(null); // Clear progress on error
      console.error(err);
    } finally {
      setIsLoading(false);
      setLoadingMessage('');
    }
  };

  const handleAnalyzeStyle = async (feedback?: string) => {
    if (!scriptText) return;
    setIsLoading(true);
    setLoadingMessage('正在生成画面风格指令...');
    setError(null);
    try {
      // Pass current visualStyle for incremental optimization
      const data = await generateVisualStyle(scriptText, feedback, visualStyle, modelName);
      setVisualStyle(data.elements);
    } catch (err: any) {
      setError(err.message || "AI 分析失败，请重试。");
      console.error(err);
    } finally {
      setIsLoading(false);
      setLoadingMessage('');
    }
  };

  // --- Render Sections ---

  const renderUploadSection = () => (
    <div className="max-w-3xl mx-auto space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
      <div className="bg-white p-8 rounded-xl shadow-sm border border-slate-200 text-center">
        <div className="mx-auto w-16 h-16 bg-brand-50 text-brand-600 rounded-full flex items-center justify-center mb-4">
          <Upload size={32} />
        </div>
        <h2 className="text-2xl font-bold text-slate-900 mb-2">上传您的剧本</h2>
        <p className="text-slate-500 mb-6">支持 .docx 和 .txt 文件。或者在下方直接粘贴文本。</p>
        
        <input 
          type="file" 
          ref={fileInputRef} 
          onChange={handleFileUpload} 
          accept=".docx,.txt" 
          className="hidden" 
        />
        
        <Button onClick={() => fileInputRef.current?.click()} variant="outline" className="mb-6">
          选择文件
        </Button>

        <div className="relative">
          <div className="absolute inset-0 flex items-center">
            <div className="w-full border-t border-slate-200"></div>
          </div>
          <div className="relative flex justify-center text-sm">
            <span className="px-2 bg-white text-slate-500">或者粘贴文本</span>
          </div>
        </div>

        <textarea
          className="mt-6 w-full h-64 p-4 border border-slate-300 rounded-lg focus:ring-2 focus:ring-brand-500 focus:border-transparent resize-y font-mono text-sm leading-relaxed"
          placeholder="内景 咖啡馆 - 日..."
          value={scriptText}
          onChange={(e) => setScriptText(e.target.value)}
        />
      </div>

      <div className="flex justify-end">
        <Button 
          disabled={!scriptText.trim()} 
          onClick={handleNextStep}
          className="w-full sm:w-auto"
        >
          开始拆解 <ArrowRight size={16} className="ml-2" />
        </Button>
      </div>
    </div>
  );

  const renderBasicElementsSection = () => {
    // Helper to format data with index and requested columns
    const getCharacterData = () => {
        if (!basicElements) return [];
        return basicElements.characters.map((item, index) => ({
            index: index + 1,
            name: item.name,
            description: item.description,
            gender: item.gender,
            age: item.age,
            voice: item.voice
        }));
    };

    const getPropSceneData = (items: any[]) => {
        if (!items) return [];
        return items.map((item, index) => ({
            index: index + 1,
            name: item.name,
            description: item.description,
            neutral: '',
            youth: '',
            none: ''
        }));
    };

    return (
      <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
        <div className="bg-white p-6 rounded-xl shadow-sm border border-slate-200">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-purple-100 text-purple-600 rounded-lg">
                <Users size={24} />
              </div>
              <div>
                <h2 className="text-xl font-bold text-slate-900">第一步：基础资产拆解</h2>
                <p className="text-sm text-slate-500">AI 漫剧全资产一致性分析（人物、核心道具、核心场景）。</p>
              </div>
            </div>
            {!basicElements && (
              <Button onClick={() => handleAnalyzeBasicElements()} isLoading={isLoading}>
                <Wand2 size={16} className="mr-2" /> 开始资产拆解
              </Button>
            )}
            {basicElements && (
               <Button variant="outline" onClick={() => handleAnalyzeBasicElements()} isLoading={isLoading}>
                <RefreshCcw size={16} className="mr-2" /> 重新拆解
              </Button>
            )}
          </div>

          {/* Analysis Status Banner */}
          {scriptAnalysis && (
            <div className="mb-6 p-4 bg-emerald-50 rounded-lg border border-emerald-100 flex items-start gap-3 text-sm text-emerald-800">
               <BrainCircuit size={18} className="mt-0.5 shrink-0" />
               <div>
                  <p className="font-semibold mb-1">剧本深度研读已完成</p>
                  <p className="opacity-80">AI ({modelName}) 已提取剧情核心逻辑与 {scriptAnalysis.hiddenDetails.length} 个关键细节，正在用于资产一致性控制。</p>
               </div>
            </div>
          )}

          {!basicElements && !isLoading && (
            <div className="text-center py-12 bg-slate-50 rounded-lg border border-dashed border-slate-300">
              <p className="text-slate-500">点击“开始资产拆解”。系统将首先深度研读剧本，然后提取标准化资产。</p>
            </div>
          )}
          
          {isLoading && loadingMessage && (
             <div className="text-center py-12 bg-slate-50 rounded-lg border border-dashed border-slate-300 flex flex-col items-center justify-center">
               <div className="animate-spin mb-4 text-brand-600">
                 <RefreshCcw size={32} />
               </div>
               <p className="text-slate-600 font-medium">{loadingMessage}</p>
             </div>
          )}

          {basicElements && !isLoading && (
            <div className="space-y-8 mt-6">
              <DataTable 
                title="1. 人物拆解表（参考视觉标准）"
                filename="人物拆解表"
                data={getCharacterData()}
                columns={[
                  { key: 'index', header: '序号', width: 'w-16' },
                  { key: 'name', header: '名称', width: 'w-32' },
                  { key: 'description', header: '角色描述', width: 'w-auto' },
                  { key: 'gender', header: '性别', width: 'w-20' },
                  { key: 'age', header: '年龄', width: 'w-20' },
                  { key: 'voice', header: '音色', width: 'w-32' },
                ]}
              />
               <DataTable 
                title="2. 核心代表性道具表（一致性控制项）"
                filename="核心道具表"
                data={getPropSceneData(basicElements.props)}
                columns={[
                  { key: 'index', header: '序号', width: 'w-16' },
                  { key: 'name', header: '名称', width: 'w-48' },
                  { key: 'description', header: '描述', width: 'w-auto' },
                  { key: 'neutral', header: '中性', width: 'w-20' },
                  { key: 'youth', header: '青年', width: 'w-20' },
                  { key: 'none', header: '无', width: 'w-20' },
                ]}
              />
               <DataTable 
                title="3. 核心场景表（空间资产项）"
                filename="核心场景表"
                data={getPropSceneData(basicElements.scenes)}
                columns={[
                  { key: 'index', header: '序号', width: 'w-16' },
                  { key: 'name', header: '名称', width: 'w-48' },
                  { key: 'description', header: '描述', width: 'w-auto' },
                  { key: 'neutral', header: '中性', width: 'w-20' },
                  { key: 'youth', header: '青年', width: 'w-20' },
                  { key: 'none', header: '无', width: 'w-20' },
                ]}
              />

              <FeedbackInput 
                isLoading={isLoading} 
                onSend={handleAnalyzeBasicElements} 
                placeholder="例如：请把主角的年龄改为30岁，增加一些赛博朋克风格的道具..." 
              />
            </div>
          )}
        </div>

        <div className="flex justify-end gap-3">
           <Button variant="secondary" onClick={() => setStep(step - 1)}>返回</Button>
           <Button 
            disabled={!basicElements} 
            onClick={handleNextStep}
          >
            确认并下一步 <ArrowRight size={16} className="ml-2" />
          </Button>
        </div>
      </div>
    );
  };

  const renderStoryboardSection = () => (
    <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
      <div className="bg-white p-6 rounded-xl shadow-sm border border-slate-200">
        <div className="flex items-center justify-between mb-4 flex-wrap gap-4">
           <div className="flex items-center gap-3">
            <div className="p-2 bg-blue-100 text-blue-600 rounded-lg">
              <Film size={24} />
            </div>
            <div>
              <h2 className="text-xl font-bold text-slate-900">第二步：分镜表</h2>
              <p className="text-sm text-slate-500">顶级导演分镜视觉系统（6.0 资产映射版）。生成时间：1-3分钟</p>
            </div>
          </div>
          
          <div className="flex items-center gap-2">
            {!storyboard && (
              <>
              <div className="flex items-center gap-2 mr-4 bg-slate-50 px-3 py-1.5 rounded-lg border border-slate-200">
                  <Settings2 size={16} className="text-slate-500" />
                  <span className="text-sm font-medium text-slate-600">分镜数量范围:</span>
                  <input 
                      type="number" 
                      min="1"
                      value={minShots}
                      onChange={(e) => setMinShots(parseInt(e.target.value) || 0)}
                      className="w-16 px-2 py-1 border border-slate-300 rounded text-sm text-center"
                      placeholder="Min"
                  />
                  <span className="text-slate-400">-</span>
                  <input 
                      type="number" 
                      min="1"
                      value={maxShots}
                      onChange={(e) => setMaxShots(parseInt(e.target.value) || 0)}
                      className="w-16 px-2 py-1 border border-slate-300 rounded text-sm text-center"
                      placeholder="Max"
                  />
              </div>
              <Button onClick={() => handleAnalyzeStoryboard()} isLoading={isLoading}>
                <Wand2 size={16} className="mr-2" /> 生成分镜表
              </Button>
              </>
            )}
            {storyboard && (
               <Button variant="outline" onClick={() => handleAnalyzeStoryboard()} isLoading={isLoading}>
                <RefreshCcw size={16} className="mr-2" /> 重新生成
              </Button>
            )}
          </div>
        </div>

        {!storyboard && !isLoading && (
          <div className="text-center py-12 bg-slate-50 rounded-lg border border-dashed border-slate-300">
            <p className="text-slate-600 font-medium mb-2">点击"生成分镜表"进行资产映射和提示词生成。</p>
            <p className="text-slate-500 text-sm">提示：分镜数量越多，生成时间越长。建议首次使用时设置 10-20 个分镜。</p>
          </div>
        )}

        {isLoading && loadingMessage && (
             <div className="text-center py-12 bg-slate-50 rounded-lg border border-dashed border-slate-300 flex flex-col items-center justify-center">
               <div className="animate-spin mb-4 text-brand-600">
                 <RefreshCcw size={32} />
               </div>
               <p className="text-slate-600 font-medium mb-4">{loadingMessage}</p>

               {/* Progress Bar */}
               {progress && progress.total > 0 && (
                 <div className="w-full max-w-md px-4">
                   <div className="flex justify-between text-sm text-slate-600 mb-2">
                     <span>进度: {progress.current} / {progress.total}</span>
                     <span>{Math.round((progress.current / progress.total) * 100)}%</span>
                   </div>
                   <div className="w-full bg-slate-200 rounded-full h-2.5">
                     <div
                       className="bg-brand-600 h-2.5 rounded-full transition-all duration-300"
                       style={{ width: `${(progress.current / progress.total) * 100}%` }}
                     ></div>
                   </div>
                   <p className="text-slate-500 text-sm mt-2">{progress.message}</p>
                 </div>
               )}
             </div>
          )}

        {storyboard && !isLoading && (
          <div className="mt-6">
            <DataTable 
              title="分镜脚本 (Director's Cut)"
              filename="分镜表"
              data={storyboard}
              columns={[
                { key: 'shotNumber', header: '序号', width: 'w-10' },
                { key: 'voiceCharacter', header: '配音角色', width: 'w-20' },
                { key: 'emotion', header: '情绪', width: 'w-20' },
                { key: 'intensity', header: '强度', width: 'w-16' },
                { key: 'assets', header: '场景角色道具 (@Mapping)', width: 'w-48' },
                { key: 'dialogue', header: '文案', width: 'w-48' },
                { key: 'fusionPrompt', header: '关键帧提示词 (Fusion)', width: 'w-64' },
                { key: 'motionPrompt', header: '动态提示词 (Motion)', width: 'w-64' },
              ]}
            />

            <FeedbackInput 
                isLoading={isLoading} 
                onSend={handleAnalyzeStoryboard} 
                placeholder="例如：请增加更多特写镜头，调整第3镜的情绪强度..." 
              />
          </div>
        )}
      </div>

      <div className="flex justify-end gap-3">
        <Button variant="secondary" onClick={() => setStep(step - 1)}>返回</Button>
        <Button 
          disabled={!storyboard} 
          onClick={handleNextStep}
        >
          确认并下一步 <ArrowRight size={16} className="ml-2" />
        </Button>
      </div>
    </div>
  );

  const renderStyleSection = () => (
    <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
      <div className="bg-white p-6 rounded-xl shadow-sm border border-slate-200">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-amber-100 text-amber-600 rounded-lg">
              <Palette size={24} />
            </div>
            <div>
              <h2 className="text-xl font-bold text-slate-900">第三步：画面风格</h2>
              <p className="text-sm text-slate-500">获取资产生成提示词指令。</p>
            </div>
          </div>
          {!visualStyle && (
            <Button onClick={() => handleAnalyzeStyle()} isLoading={isLoading}>
              <Wand2 size={16} className="mr-2" /> 生成指令
            </Button>
          )}
           {visualStyle && (
             <Button variant="outline" onClick={() => handleAnalyzeStyle()} isLoading={isLoading}>
              <RefreshCcw size={16} className="mr-2" /> 重新生成
            </Button>
          )}
        </div>

        {!visualStyle && !isLoading && (
          <div className="text-center py-12 bg-slate-50 rounded-lg border border-dashed border-slate-300">
            <p className="text-slate-500">点击“生成指令”获取标准化的画面生成提示词。</p>
          </div>
        )}

        {isLoading && loadingMessage && (
             <div className="text-center py-12 bg-slate-50 rounded-lg border border-dashed border-slate-300 flex flex-col items-center justify-center">
               <div className="animate-spin mb-4 text-brand-600">
                 <RefreshCcw size={32} />
               </div>
               <p className="text-slate-600 font-medium">{loadingMessage}</p>
             </div>
          )}

        {visualStyle && !isLoading && (
          <div className="mt-6">
             <DataTable 
              title="画面风格生成指令"
              filename="画面风格"
              data={visualStyle}
              columns={[
                { key: 'category', header: '类别', width: 'w-1/6' },
                { key: 'description', header: '提示词指令 (Prompt)', width: 'w-2/3' },
                { key: 'reference', header: '备注', width: 'w-1/6' },
              ]}
            />
            <FeedbackInput 
              isLoading={isLoading} 
              onSend={handleAnalyzeStyle} 
              placeholder="例如：请将风格调整为赛博朋克..." 
            />
          </div>
        )}
      </div>

       <div className="flex justify-end gap-3">
        <Button variant="secondary" onClick={() => setStep(step - 1)}>返回</Button>
        <Button 
          disabled={!visualStyle} 
          onClick={() => alert("拆解完成！请使用表格上方的导出按钮保存您的数据。")}
        >
          完成 <Check size={16} className="ml-2" />
        </Button>
      </div>
    </div>
  );

  return (
    <div className="min-h-screen pb-20">
      <header className="bg-white border-b border-slate-200 sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between h-16 items-center">
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 bg-brand-600 rounded-lg flex items-center justify-center text-white">
                <FileText size={20} />
              </div>
              <span className="font-bold text-xl text-slate-900">剧本拆解工具</span>
            </div>
             
             <div className="flex items-center gap-4 flex-wrap">
                <div className="flex items-center gap-2 text-sm text-slate-600 bg-slate-50 px-3 py-1.5 rounded-lg border border-slate-200">
                   <Settings2 size={16} className="text-brand-500" />
                   <input
                      type="password"
                      placeholder="输入API Key"
                      value={apiKey}
                      onChange={(e) => setApiKey(e.target.value)}
                      className="bg-transparent border-none text-slate-900 text-sm font-medium focus:ring-0 p-0 w-32"
                    />
                </div>
                <div className="flex items-center gap-2 text-sm text-slate-600 bg-slate-50 px-3 py-1.5 rounded-lg border border-slate-200">
                   <Sparkles size={16} className="text-brand-500" />
                   <label htmlFor="model-select" className="hidden sm:block font-medium">模型:</label>
                   <select
                      id="model-select"
                      value={modelName}
                      onChange={(e) => setModelName(e.target.value)}
                      className="bg-transparent border-none text-slate-900 text-sm font-medium focus:ring-0 p-0 cursor-pointer"
                    >
                      <optgroup label="Claude (Anthropic)">
                        <option value="claude-sonnet-4-5-20250929">Sonnet 4.5 (20250929) - 推荐</option>
                        <option value="claude-sonnet-4-5">Sonnet 4.5</option>
                        <option value="claude-sonnet-4-5-thinking">Sonnet 4.5 Thinking</option>
                        <option value="claude-sonnet-4-5-20250929-thinking">Sonnet 4.5 (20250929) Thinking</option>
                        <option value="claude-opus-4-5-20251101">Opus 4.5 (20251101) - 最强</option>
                        <option value="claude-opus-4-5">Opus 4.5</option>
                        <option value="claude-opus-4-5-thinking">Opus 4.5 Thinking</option>
                        <option value="claude-opus-4-5-20251101-thinking">Opus 4.5 (20251101) Thinking</option>
                        <option value="claude-haiku-4-5-20251001">Haiku 4.5 (20251001) - 经济</option>
                        <option value="claude-haiku-4-5">Haiku 4.5</option>
                      </optgroup>
                      <optgroup label="DeepSeek (深度求索)">
                        <option value="deepseek-chat">DeepSeek V3 - 推荐</option>
                        <option value="deepseek-reasoner">DeepSeek R1 - 推理模型</option>
                      </optgroup>
                      <optgroup label="Gemini (Google)">
                        <option value="gemini-2.5-flash">Gemini 2.5 Flash - 快速</option>
                        <option value="gemini-2.5-flash-lite">Gemini 2.5 Flash Lite</option>
                        <option value="gemini-3-flash">Gemini 3 Flash</option>
                        <option value="gemini-3-pro-high">Gemini 3 Pro High - 高性能</option>
                        <option value="gemini-3-pro-image">Gemini 3 Pro Image</option>
                      </optgroup>
                      <optgroup label="GPT (OpenAI)">
                        <option value="gpt-oss-120b-medium">GPT OSS 120B Medium</option>
                        <option value="gpt-4o">GPT-4o</option>
                        <option value="gpt-4o-mini">GPT-4o Mini</option>
                      </optgroup>
                    </select>
                </div>
                <div className="flex items-center gap-2 text-sm text-slate-600 bg-slate-50 px-3 py-1.5 rounded-lg border border-slate-200">
                   <Settings2 size={16} className="text-amber-500" />
                   <select
                      value={apiBaseUrl}
                      onChange={(e) => setApiBaseUrl(e.target.value)}
                      className="bg-transparent border-none text-slate-900 text-sm font-medium focus:ring-0 p-0 cursor-pointer"
                      title="API服务器地址"
                    >
                      <option value="/api">代理 (第三方API)</option>
                      <option value="https://generativelanguage.googleapis.com">Google 官方 API</option>
                      <option value="https://api.anthropic.com">Anthropic 官方 API</option>
                      <option value="https://api.openai.com">OpenAI 官方 API</option>
                      <option value="https://api.deepseek.com">DeepSeek 官方 API</option>
                    </select>
                </div>
             </div>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 mt-8">
        <StepIndicator currentStep={step} />
        
        <div className="mt-8">
          {error && (
            <div className="mb-6 p-4 bg-red-50 text-red-700 rounded-lg border border-red-200 flex items-center">
              <span className="font-medium mr-2">错误:</span> {error}
            </div>
          )}

          {step === AppStep.UPLOAD && renderUploadSection()}
          {step === AppStep.BASIC_ELEMENTS && renderBasicElementsSection()}
          {step === AppStep.STORYBOARD && renderStoryboardSection()}
          {step === AppStep.VISUAL_STYLE && renderStyleSection()}
        </div>
      </main>
    </div>
  );
}

export default App;