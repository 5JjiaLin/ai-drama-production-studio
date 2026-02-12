import React, { useState, useEffect } from 'react';
import { ArrowLeft, Upload, Download, Copy, Settings, Film, Trash2 } from 'lucide-react';
import { Project } from '../services/projectService';
import { episodeService, Episode } from '../services/episodeService';
import { storyboardService, Storyboard } from '../services/storyboardService';
import { parseDocx } from '../services/fileUtils';
import Button from './Button';
import Encoding from 'encoding-japanese';

interface AIModel {
  id: string;
  name: string;
  provider: string;
  description: string;
}

interface StoryboardGenerationProps {
  project: Project;
  onBack: () => void;
}

export default function StoryboardGeneration({ project, onBack }: StoryboardGenerationProps) {
  const [episodes, setEpisodes] = useState<Episode[]>([]);
  const [storyboards, setStoryboards] = useState<Storyboard[]>([]);
  const [selectedEpisode, setSelectedEpisode] = useState<Episode | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isGenerating, setIsGenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Upload form
  const [showUploadForm, setShowUploadForm] = useState(false);
  const [episodeNumber, setEpisodeNumber] = useState('');
  const [episodeTitle, setEpisodeTitle] = useState('');
  const [scriptText, setScriptText] = useState('');

  // Generation params
  const [showParams, setShowParams] = useState(false);
  const [minShots, setMinShots] = useState(10);
  const [maxShots, setMaxShots] = useState(30);
  const [selectedModel, setSelectedModel] = useState<string>('claude-sonnet-4-5');
  const [availableModels, setAvailableModels] = useState<AIModel[]>([]);

  // Edit state
  const [editingStoryboards, setEditingStoryboards] = useState<Set<number>>(new Set());
  const [editedStoryboards, setEditedStoryboards] = useState<Map<number, Storyboard>>(new Map());

  useEffect(() => {
    loadEpisodes();
    loadAvailableModels();
  }, [project.id]);

  const loadAvailableModels = async () => {
    try {
      const response = await fetch('http://127.0.0.1:5000/api/models', {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`,
        },
      });
      const result = await response.json();
      if (result.success) {
        setAvailableModels(result.data.models);
      }
    } catch (err) {
      console.error('Failed to load models:', err);
    }
  };

  const loadEpisodes = async () => {
    try {
      setIsLoading(true);
      setError(null);
      const data = await episodeService.getEpisodes(project.id);
      setEpisodes(data);
    } catch (err: any) {
      setError(err.message || '加载剧集列表失败');
    } finally {
      setIsLoading(false);
    }
  };

  const loadStoryboards = async (episodeId: number) => {
    try {
      setIsLoading(true);
      setError(null);
      const data = await storyboardService.getStoryboards(project.id, episodeId);

      // 调试日志
      console.log('[loadStoryboards] 接收到的数据:', data);
      console.log('[loadStoryboards] 数据长度:', data.length);

      // 去重处理 - 基于ID去重
      const uniqueData = Array.from(
        new Map(data.map(item => [item.id, item])).values()
      );

      console.log('[loadStoryboards] 去重后长度:', uniqueData.length);

      if (data.length !== uniqueData.length) {
        console.warn('[loadStoryboards] 检测到重复数据！', {
          原始长度: data.length,
          去重后长度: uniqueData.length
        });
      }

      setStoryboards(uniqueData);
    } catch (err: any) {
      setError(err.message || '加载分镜列表失败');
    } finally {
      setIsLoading(false);
    }
  };

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    try {
      // 检查文件类型
      if (file.name.endsWith('.docx')) {
        // 处理.docx文件
        const text = await parseDocx(file);
        setScriptText(text);
      } else {
        // 处理文本文件（.txt等）
        const arrayBuffer = await file.arrayBuffer();
        const uint8Array = new Uint8Array(arrayBuffer);

        // 自动检测编码
        const detectedEncoding = Encoding.detect(uint8Array);

        // 转换为Unicode字符串
        const unicodeArray = Encoding.convert(uint8Array, {
          to: 'UNICODE',
          from: detectedEncoding || 'AUTO'
        });

        // 转换为字符串
        const text = Encoding.codeToString(unicodeArray);
        setScriptText(text);
      }
    } catch (err) {
      setError('文件读取失败');
    }
  };

  const handleUploadEpisode = async () => {
    if (!episodeNumber || !episodeTitle || !scriptText.trim()) {
      setError('请填写所有必填字段');
      return;
    }

    try {
      setIsLoading(true);
      setError(null);
      const newEpisode = await episodeService.createEpisode(project.id, {
        episode_number: parseInt(episodeNumber),
        title: episodeTitle,
        script_content: scriptText.trim(),
      });
      setEpisodes([...episodes, newEpisode]);
      setEpisodeNumber('');
      setEpisodeTitle('');
      setScriptText('');
      setShowUploadForm(false);
    } catch (err: any) {
      setError(err.message || '上传剧集失败');
    } finally {
      setIsLoading(false);
    }
  };

  const handleGenerateStoryboards = async (episodeId: number) => {
    try {
      setIsGenerating(true);
      setError(null);
      const data = await storyboardService.generateStoryboards(project.id, {
        episode_id: episodeId,
        min_shots: minShots,
        max_shots: maxShots,
        model: selectedModel,
      });

      // 调试日志
      console.log('[handleGenerateStoryboards] 接收到的数据:', data);
      console.log('[handleGenerateStoryboards] 数据长度:', data.length);

      // 去重处理 - 基于ID去重
      const uniqueData = Array.from(
        new Map(data.map(item => [item.id, item])).values()
      );

      console.log('[handleGenerateStoryboards] 去重后长度:', uniqueData.length);

      if (data.length !== uniqueData.length) {
        console.warn('[handleGenerateStoryboards] 检测到重复数据！', {
          原始长度: data.length,
          去重后长度: uniqueData.length
        });
      }

      setStoryboards(uniqueData);
      setShowParams(false);
    } catch (err: any) {
      setError(err.message || '生成分镜失败');
    } finally {
      setIsGenerating(false);
    }
  };

  const handleSelectEpisode = async (episode: Episode) => {
    setSelectedEpisode(episode);
    await loadStoryboards(episode.id);
  };

  const handleExportCSV = () => {
    const csv = storyboardService.exportToCSV(storyboards);
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    link.download = `${project.name}_第${selectedEpisode?.episode_number}集_分镜表.csv`;
    link.click();
  };

  const handleCopyTable = async () => {
    const text = storyboardService.copyToClipboard(storyboards);
    try {
      await navigator.clipboard.writeText(text);
      alert('已复制到剪贴板');
    } catch (err) {
      setError('复制失败');
    }
  };

  const handleEditStoryboard = (storyboard: Storyboard) => {
    setEditingStoryboards(prev => new Set(prev).add(storyboard.id));
    setEditedStoryboards(prev => new Map(prev).set(storyboard.id, { ...storyboard }));
  };

  const handleCancelEdit = (storyboardId: number) => {
    setEditingStoryboards(prev => {
      const next = new Set(prev);
      next.delete(storyboardId);
      return next;
    });
    setEditedStoryboards(prev => {
      const next = new Map(prev);
      next.delete(storyboardId);
      return next;
    });
  };

  const handleStoryboardFieldChange = (storyboardId: number, field: keyof Storyboard, value: string | number) => {
    setEditedStoryboards(prev => {
      const next = new Map(prev);
      const storyboard = next.get(storyboardId);
      if (storyboard) {
        next.set(storyboardId, { ...storyboard, [field]: value });
      }
      return next;
    });
  };

  const handleSaveStoryboard = async (storyboardId: number) => {
    const editedStoryboard = editedStoryboards.get(storyboardId);
    if (!editedStoryboard || !selectedEpisode) return;

    try {
      await storyboardService.updateStoryboard(project.id, selectedEpisode.id, storyboardId, {
        voice_character: editedStoryboard.voice_character,
        emotion: editedStoryboard.emotion,
        intensity: editedStoryboard.intensity,
        dialogue: editedStoryboard.dialogue,
        fusion_prompt: editedStoryboard.fusion_prompt,
        motion_prompt: editedStoryboard.motion_prompt,
      });

      // 更新本地状态
      setStoryboards(prev => prev.map(sb => sb.id === storyboardId ? editedStoryboard : sb));
      handleCancelEdit(storyboardId);
      alert('保存成功');
    } catch (err: any) {
      setError(err.message || '保存失败');
    }
  };

  const handleDeleteEpisode = async (episodeId: number, episodeTitle: string) => {
    if (!confirm(`确定要删除剧集"${episodeTitle}"吗？删除后将无法恢复。`)) {
      return;
    }

    try {
      await episodeService.deleteEpisode(project.id, episodeId);
      // 从本地状态中移除
      setEpisodes(prev => prev.filter(e => e.id !== episodeId));
      // 如果删除的是当前选中的剧集，清空选中状态
      if (selectedEpisode?.id === episodeId) {
        setSelectedEpisode(null);
        setStoryboards([]);
      }
    } catch (err: any) {
      setError(err.message || '删除剧集失败');
    }
  };

  const handleDeleteStoryboard = async (storyboardId: number) => {
    if (!confirm('确定要删除这个分镜吗？')) {
      return;
    }

    if (!selectedEpisode) return;

    try {
      await storyboardService.deleteStoryboard(project.id, selectedEpisode.id, storyboardId);
      // 从本地状态中移除
      setStoryboards(prev => prev.filter(sb => sb.id !== storyboardId));
    } catch (err: any) {
      setError(err.message || '删除分镜失败');
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-6">
          <button
            onClick={onBack}
            className="flex items-center text-gray-600 hover:text-gray-900 mb-4"
          >
            <ArrowLeft className="w-5 h-5 mr-2" />
            返回项目详情
          </button>
          <h1 className="text-3xl font-bold text-gray-900">{project.name} - 分镜拆解</h1>
        </div>

        {error && (
          <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg mb-6">
            {error}
          </div>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Left: Episodes List */}
          <div className="lg:col-span-1">
            <div className="bg-white rounded-xl shadow-sm p-6 border border-gray-200">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-lg font-semibold text-gray-900">剧集列表</h2>
                <Button
                  onClick={() => setShowUploadForm(!showUploadForm)}
                  variant="secondary"
                  className="text-sm"
                >
                  {showUploadForm ? '取消' : '上传'}
                </Button>
              </div>

              {showUploadForm && (
                <div className="mb-4 p-4 bg-gray-50 rounded-lg space-y-3">
                  <input
                    type="number"
                    value={episodeNumber}
                    onChange={(e) => setEpisodeNumber(e.target.value)}
                    placeholder="集数"
                    className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg"
                  />
                  <input
                    type="text"
                    value={episodeTitle}
                    onChange={(e) => setEpisodeTitle(e.target.value)}
                    placeholder="标题"
                    className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg"
                  />
                  <div>
                    <label className="block text-xs font-medium text-gray-700 mb-1">
                      上传文件
                    </label>
                    <input
                      type="file"
                      accept=".txt,.docx"
                      onChange={handleFileUpload}
                      className="block w-full text-xs text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:text-xs file:font-semibold file:bg-indigo-50 file:text-indigo-700 hover:file:bg-indigo-100"
                    />
                  </div>
                  <textarea
                    value={scriptText}
                    onChange={(e) => setScriptText(e.target.value)}
                    rows={4}
                    placeholder="或直接粘贴剧本内容"
                    className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg resize-none"
                  />
                  <Button
                    onClick={handleUploadEpisode}
                    variant="primary"
                    className="w-full text-sm"
                    disabled={isLoading}
                  >
                    {isLoading ? '上传中...' : '确认上传'}
                  </Button>
                </div>
              )}

              <div className="space-y-2">
                {episodes.map((episode) => (
                  <div
                    key={episode.id}
                    className={`p-3 rounded-lg transition-colors relative ${
                      selectedEpisode?.id === episode.id
                        ? 'bg-indigo-50 border-2 border-indigo-500'
                        : 'bg-gray-50 border-2 border-transparent hover:bg-gray-100'
                    }`}
                  >
                    <div
                      onClick={() => handleSelectEpisode(episode)}
                      className="cursor-pointer pr-8"
                    >
                      <div className="font-medium text-gray-900">第{episode.episode_number}集</div>
                      <div className="text-sm text-gray-600">{episode.title}</div>
                    </div>
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        handleDeleteEpisode(episode.id, episode.title);
                      }}
                      className="absolute top-3 right-3 text-red-600 hover:text-red-800"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                ))}
                {episodes.length === 0 && !showUploadForm && (
                  <div className="text-center py-8 text-gray-500 text-sm">
                    还没有剧集，点击上传按钮添加
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* Right: Storyboards */}
          <div className="lg:col-span-2">
            {selectedEpisode ? (
              <div className="bg-white rounded-xl shadow-sm p-6 border border-gray-200">
                <div className="flex items-center justify-between mb-6">
                  <h2 className="text-lg font-semibold text-gray-900">
                    第{selectedEpisode.episode_number}集 - 分镜表
                  </h2>
                  <div className="flex gap-2">
                    {storyboards.length === 0 ? (
                      <Button
                        onClick={() => setShowParams(!showParams)}
                        variant="primary"
                        className="flex items-center gap-2"
                      >
                        <Film className="w-4 h-4" />
                        生成分镜
                      </Button>
                    ) : (
                      <>
                        <Button
                          onClick={() => setShowParams(!showParams)}
                          variant="secondary"
                          className="flex items-center gap-2"
                        >
                          <Settings className="w-4 h-4" />
                          重新生成
                        </Button>
                        <Button
                          onClick={handleCopyTable}
                          variant="secondary"
                          className="flex items-center gap-2"
                        >
                          <Copy className="w-4 h-4" />
                          复制
                        </Button>
                        <Button
                          onClick={handleExportCSV}
                          variant="secondary"
                          className="flex items-center gap-2"
                        >
                          <Download className="w-4 h-4" />
                          导出
                        </Button>
                      </>
                    )}
                  </div>
                </div>

                {showParams && (
                  <div className="mb-6 p-4 bg-gray-50 rounded-lg">
                    <h3 className="font-medium text-gray-900 mb-3">分镜参数</h3>
                    <div className="space-y-4">
                      <div>
                        <label className="block text-sm text-gray-700 mb-1">AI模型</label>
                        <select
                          value={selectedModel}
                          onChange={(e) => setSelectedModel(e.target.value)}
                          className="w-full px-3 py-2 border border-gray-300 rounded-lg bg-white"
                        >
                          {availableModels.map((model) => (
                            <option key={model.id} value={model.id}>
                              {model.name} ({model.provider}) - {model.description}
                            </option>
                          ))}
                        </select>
                      </div>
                      <div className="grid grid-cols-2 gap-4">
                        <div>
                          <label className="block text-sm text-gray-700 mb-1">最少镜头数</label>
                          <input
                            type="number"
                            value={minShots}
                            onChange={(e) => setMinShots(parseInt(e.target.value))}
                            className="w-full px-3 py-2 border border-gray-300 rounded-lg"
                          />
                        </div>
                        <div>
                          <label className="block text-sm text-gray-700 mb-1">最多镜头数</label>
                          <input
                            type="number"
                            value={maxShots}
                            onChange={(e) => setMaxShots(parseInt(e.target.value))}
                            className="w-full px-3 py-2 border border-gray-300 rounded-lg"
                          />
                        </div>
                      </div>
                    </div>
                    <Button
                      onClick={() => handleGenerateStoryboards(selectedEpisode.id)}
                      variant="primary"
                      className="w-full mt-4"
                      disabled={isGenerating}
                    >
                      {isGenerating ? '生成中...' : '开始生成'}
                    </Button>
                  </div>
                )}

                {storyboards.length > 0 ? (
                  <div className="overflow-x-auto">
                    <table className="min-w-full divide-y divide-gray-200">
                      <thead className="bg-gray-50">
                        <tr>
                          <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">序号</th>
                          <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">配音角色</th>
                          <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">情绪</th>
                          <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">强度</th>
                          <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">场景角色道具</th>
                          <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">文案</th>
                          <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">关键帧提示词</th>
                          <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">动态提示词</th>
                          <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">操作</th>
                        </tr>
                      </thead>
                      <tbody className="bg-white divide-y divide-gray-200">
                        {storyboards.map((sb) => {
                          const isEditing = editingStoryboards.has(sb.id);
                          const editedSb = editedStoryboards.get(sb.id) || sb;
                          return (
                            <tr key={sb.id}>
                              <td className="px-4 py-3 text-sm text-gray-900">{sb.shot_number}</td>
                              <td className="px-4 py-3 text-sm">
                                {isEditing ? (
                                  <input
                                    type="text"
                                    value={editedSb.voice_character}
                                    onChange={(e) => handleStoryboardFieldChange(sb.id, 'voice_character', e.target.value)}
                                    className="w-full px-2 py-1 border border-gray-300 rounded"
                                  />
                                ) : (
                                  <span className="text-gray-600">{sb.voice_character}</span>
                                )}
                              </td>
                              <td className="px-4 py-3 text-sm">
                                {isEditing ? (
                                  <input
                                    type="text"
                                    value={editedSb.emotion}
                                    onChange={(e) => handleStoryboardFieldChange(sb.id, 'emotion', e.target.value)}
                                    className="w-full px-2 py-1 border border-gray-300 rounded"
                                  />
                                ) : (
                                  <span className="text-gray-600">{sb.emotion}</span>
                                )}
                              </td>
                              <td className="px-4 py-3 text-sm">
                                {isEditing ? (
                                  <input
                                    type="text"
                                    value={editedSb.intensity}
                                    onChange={(e) => handleStoryboardFieldChange(sb.id, 'intensity', e.target.value)}
                                    className="w-full px-2 py-1 border border-gray-300 rounded"
                                  />
                                ) : (
                                  <span className="text-gray-600">{sb.intensity}</span>
                                )}
                              </td>
                              <td className="px-4 py-3 text-sm">
                                {isEditing ? (
                                  <input
                                    type="text"
                                    value={editedSb.asset_mapping}
                                    onChange={(e) => handleStoryboardFieldChange(sb.id, 'asset_mapping', e.target.value)}
                                    className="w-full px-2 py-1 border border-gray-300 rounded"
                                  />
                                ) : (
                                  <span className="text-gray-600">{sb.asset_mapping}</span>
                                )}
                              </td>
                              <td className="px-4 py-3 text-sm">
                                {isEditing ? (
                                  <input
                                    type="text"
                                    value={editedSb.dialogue}
                                    onChange={(e) => handleStoryboardFieldChange(sb.id, 'dialogue', e.target.value)}
                                    className="w-full px-2 py-1 border border-gray-300 rounded"
                                  />
                                ) : (
                                  <span className="text-gray-600">{sb.dialogue}</span>
                                )}
                              </td>
                              <td className="px-4 py-3 text-sm">
                                {isEditing ? (
                                  <input
                                    type="text"
                                    value={editedSb.fusion_prompt}
                                    onChange={(e) => handleStoryboardFieldChange(sb.id, 'fusion_prompt', e.target.value)}
                                    className="w-full px-2 py-1 border border-gray-300 rounded"
                                  />
                                ) : (
                                  <span className="text-gray-600">{sb.fusion_prompt}</span>
                                )}
                              </td>
                              <td className="px-4 py-3 text-sm">
                                {isEditing ? (
                                  <input
                                    type="text"
                                    value={editedSb.motion_prompt}
                                    onChange={(e) => handleStoryboardFieldChange(sb.id, 'motion_prompt', e.target.value)}
                                    className="w-full px-2 py-1 border border-gray-300 rounded"
                                  />
                                ) : (
                                  <span className="text-gray-600">{sb.motion_prompt}</span>
                                )}
                              </td>
                              <td className="px-4 py-3 text-sm">
                                {isEditing ? (
                                  <div className="flex gap-2">
                                    <button
                                      onClick={() => handleSaveStoryboard(sb.id)}
                                      className="text-green-600 hover:text-green-800"
                                    >
                                      保存
                                    </button>
                                    <button
                                      onClick={() => handleCancelEdit(sb.id)}
                                      className="text-gray-600 hover:text-gray-800"
                                    >
                                      取消
                                    </button>
                                  </div>
                                ) : (
                                  <div className="flex gap-2">
                                    <button
                                      onClick={() => handleEditStoryboard(sb)}
                                      className="text-indigo-600 hover:text-indigo-800"
                                    >
                                      编辑
                                    </button>
                                    <button
                                      onClick={() => handleDeleteStoryboard(sb.id)}
                                      className="text-red-600 hover:text-red-800"
                                    >
                                      <Trash2 className="w-4 h-4" />
                                    </button>
                                  </div>
                                )}
                              </td>
                            </tr>
                          );
                        })}
                      </tbody>
                    </table>
                  </div>
                ) : (
                  <div className="text-center py-12 text-gray-500">
                    {showParams ? '设置参数后点击开始生成' : '点击生成分镜按钮开始'}
                  </div>
                )}
              </div>
            ) : (
              <div className="bg-white rounded-xl shadow-sm p-6 border border-gray-200 h-full flex items-center justify-center">
                <div className="text-center text-gray-500">
                  <Film className="w-16 h-16 mx-auto mb-4 text-gray-400" />
                  <p>请先选择一个剧集</p>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
