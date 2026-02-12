import React, { useState, useEffect } from 'react';
import { ArrowLeft, Upload, FileText, Download, Copy, Plus, RefreshCw, Sparkles, Trash2 } from 'lucide-react';
import { Project } from '../services/projectService';
import { assetService, Asset } from '../services/assetService';
import { parseDocx } from '../services/fileUtils';
import Button from './Button';
import AssetTable from './AssetTable';
import { useAssetEdit } from '../hooks/useAssetEdit';
import Encoding from 'encoding-japanese';

interface AssetExtractionProps {
  project: Project;
  onBack: () => void;
}

interface AIModel {
  id: string;
  name: string;
  provider: string;
  description: string;
}

// 列配置
const CHARACTER_COLUMNS = [
  { key: 'name' as const, label: '名称', editable: true },
  { key: 'description' as const, label: '角色描述', editable: true },
  { key: 'gender' as const, label: '性别', editable: true },
  { key: 'age' as const, label: '年龄', editable: true },
  { key: 'voice' as const, label: '音色', editable: true },
];

const PROP_COLUMNS = [
  { key: 'name' as const, label: '名称', editable: true },
  { key: 'description' as const, label: '描述', editable: true },
  { key: 'gender' as const, label: '性别', editable: false },
  { key: 'age' as const, label: '年龄', editable: false },
  { key: 'voice' as const, label: '音色', editable: false },
];

const SCENE_COLUMNS = [
  { key: 'name' as const, label: '名称', editable: true },
  { key: 'description' as const, label: '描述', editable: true },
  { key: 'gender' as const, label: '性别', editable: false },
  { key: 'age' as const, label: '年龄', editable: false },
  { key: 'voice' as const, label: '音色', editable: false },
];

export default function AssetExtraction({ project, onBack }: AssetExtractionProps) {
  const [assets, setAssets] = useState<Asset[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isExtracting, setIsExtracting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [scriptText, setScriptText] = useState('');
  const [supplementText, setSupplementText] = useState('');
  const [showSupplement, setShowSupplement] = useState(false);
  const [selectedModel, setSelectedModel] = useState<string>('claude-sonnet-4-5');
  const [availableModels, setAvailableModels] = useState<AIModel[]>([]);
  const [showOptimization, setShowOptimization] = useState(false);
  const [optimizationFeedback, setOptimizationFeedback] = useState('');

  // 使用资产编辑Hook
  const {
    editingAssets,
    editedAssets,
    handleEditAsset,
    handleCancelEdit,
    handleFieldChange,
    handleSaveAsset,
  } = useAssetEdit({
    projectId: project.id,
    onSaveSuccess: (asset) => {
      setAssets(prev => prev.map(a => a.id === asset.id ? asset : a));
      alert('保存成功');
    },
    onSaveError: (error) => {
      setError(error);
    },
  });

  useEffect(() => {
    loadAssets();
    loadAvailableModels();
  }, [project.id]);

  const loadAvailableModels = async () => {
    try {
      const response = await fetch('/api/models', {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        }
      });
      const result = await response.json();
      if (result.success) {
        setAvailableModels(result.data.models);
      }
    } catch (err) {
      console.error('加载模型列表失败:', err);
      // 使用默认模型列表
      setAvailableModels([
        { id: 'claude-sonnet-4-5', name: 'Claude Sonnet 4.5', provider: 'Anthropic', description: '推荐' },
        { id: 'deepseek-chat', name: 'DeepSeek Chat', provider: 'DeepSeek', description: '性价比高' },
        { id: 'gemini-2.0-flash', name: 'Gemini 2.0 Flash', provider: 'Google', description: '快速' },
        { id: 'gpt-4', name: 'GPT-4', provider: 'OpenAI', description: '强大' }
      ]);
    }
  };

  const loadAssets = async () => {
    try {
      setIsLoading(true);
      setError(null);
      const data = await assetService.getAssets(project.id);
      setAssets(data);
      if (data.length > 0) {
        setShowSupplement(true);
      }
    } catch (err: any) {
      setError(err.message || '加载资产列表失败');
    } finally {
      setIsLoading(false);
    }
  };

  const handleExtractAssets = async () => {
    if (!scriptText.trim()) {
      setError('请输入剧本内容');
      return;
    }

    try {
      setIsExtracting(true);
      setError(null);
      const newAssets = await assetService.extractAssets(project.id, {
        script_content: scriptText.trim(),
        model: selectedModel,
      });
      setAssets(newAssets);
      setScriptText('');
      setShowSupplement(true);
    } catch (err: any) {
      setError(err.message || '资产提取失败');
    } finally {
      setIsExtracting(false);
    }
  };

  const handleSupplementExtract = async () => {
    if (!supplementText.trim()) {
      setError('请输入补充剧本内容');
      return;
    }

    try {
      setIsExtracting(true);
      setError(null);
      const newAssets = await assetService.extractAssets(project.id, {
        script_content: supplementText.trim(),
        model: selectedModel,
      });
      setAssets(newAssets);
      setSupplementText('');
    } catch (err: any) {
      setError(err.message || '补充拆解失败');
    } finally {
      setIsExtracting(false);
    }
  };

  const handleOptimizeAssets = async () => {
    if (!optimizationFeedback.trim()) {
      setError('请输入优化反馈');
      return;
    }

    try {
      setIsExtracting(true);
      setError(null);
      const optimizedAssets = await assetService.optimizeAssets(project.id, {
        feedback: optimizationFeedback.trim(),
        model: selectedModel,
      });
      setAssets(optimizedAssets);
      setOptimizationFeedback('');
      setShowOptimization(false);
      alert('资产优化成功！');
    } catch (err: any) {
      setError(err.message || '资产优化失败');
    } finally {
      setIsExtracting(false);
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

  const handleExportCSV = () => {
    const csv = assetService.exportToCSV(assets);
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    link.download = `${project.name}_资产列表.csv`;
    link.click();
  };

  const handleCopyTable = async () => {
    const text = assetService.copyToClipboard(assets);
    try {
      await navigator.clipboard.writeText(text);
      alert('已复制到剪贴板');
    } catch (err) {
      setError('复制失败');
    }
  };

  const handleDeleteAsset = async (assetId: number, assetName: string) => {
    if (!confirm(`确定要删除资产"${assetName}"吗？`)) {
      return;
    }

    try {
      await assetService.deleteAsset(project.id, assetId);
      // 从本地状态中移除
      setAssets(prev => prev.filter(a => a.id !== assetId));
    } catch (err: any) {
      setError(err.message || '删除失败');
    }
  };

  const characters = assets.filter(a => a.asset_type === 'CHARACTER');
  const props = assets.filter(a => a.asset_type === 'PROP');
  const scenes = assets.filter(a => a.asset_type === 'SCENE');

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
          <h1 className="text-3xl font-bold text-gray-900">{project.name} - 资产拆解</h1>
        </div>

        {error && (
          <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg mb-6">
            {error}
          </div>
        )}

        {/* Script Upload Section */}
        {!showSupplement && (
          <div className="bg-white rounded-xl shadow-sm p-6 mb-6 border border-gray-200">
            <h2 className="text-xl font-semibold text-gray-900 mb-4">上传剧本</h2>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  选择AI模型
                </label>
                <select
                  value={selectedModel}
                  onChange={(e) => setSelectedModel(e.target.value)}
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                  disabled={isExtracting}
                >
                  {availableModels.map(model => (
                    <option key={model.id} value={model.id}>
                      {model.name} ({model.provider}) - {model.description}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  上传文件或粘贴文本
                </label>
                <input
                  type="file"
                  accept=".txt,.docx"
                  onChange={handleFileUpload}
                  className="block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:text-sm file:font-semibold file:bg-indigo-50 file:text-indigo-700 hover:file:bg-indigo-100"
                />
              </div>
              <div>
                <textarea
                  value={scriptText}
                  onChange={(e) => setScriptText(e.target.value)}
                  rows={12}
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent resize-none"
                  placeholder="或直接粘贴剧本内容..."
                  disabled={isExtracting}
                />
              </div>
              <Button
                onClick={handleExtractAssets}
                variant="primary"
                disabled={isExtracting || !scriptText.trim()}
                className="w-full"
              >
                {isExtracting ? '正在拆解...' : '开始拆解'}
              </Button>
            </div>
          </div>
        )}

        {/* Supplement Section */}
        {showSupplement && (
          <div className="bg-white rounded-xl shadow-sm p-6 mb-6 border border-gray-200">
            <h2 className="text-xl font-semibold text-gray-900 mb-4">补充剧本</h2>
            <div className="space-y-4">
              <textarea
                value={supplementText}
                onChange={(e) => setSupplementText(e.target.value)}
                rows={6}
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent resize-none"
                placeholder="粘贴补充剧本内容，继续提取资产..."
                disabled={isExtracting}
              />
              <Button
                onClick={handleSupplementExtract}
                variant="primary"
                disabled={isExtracting || !supplementText.trim()}
                className="w-full"
              >
                {isExtracting ? '正在补充拆解...' : '补充拆解'}
              </Button>
            </div>
          </div>
        )}

        {/* Assets Display */}
        {assets.length > 0 && (
          <div className="bg-white rounded-xl shadow-sm p-6 border border-gray-200">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-xl font-semibold text-gray-900">资产列表</h2>
              <div className="flex gap-2">
                <Button
                  onClick={() => setShowOptimization(!showOptimization)}
                  variant="secondary"
                  className="flex items-center gap-2"
                >
                  <Sparkles className="w-4 h-4" />
                  {showOptimization ? '取消优化' : '优化资产'}
                </Button>
                <Button onClick={handleCopyTable} variant="secondary" className="flex items-center gap-2">
                  <Copy className="w-4 h-4" />
                  复制表格
                </Button>
                <Button onClick={handleExportCSV} variant="secondary" className="flex items-center gap-2">
                  <Download className="w-4 h-4" />
                  导出CSV
                </Button>
              </div>
            </div>

            {/* Optimization Section */}
            {showOptimization && (
              <div className="bg-indigo-50 rounded-lg p-4 mb-6 border border-indigo-200">
                <h3 className="text-sm font-semibold text-indigo-900 mb-3">优化资产拆解</h3>
                <div className="space-y-3">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      选择AI模型
                    </label>
                    <select
                      value={selectedModel}
                      onChange={(e) => setSelectedModel(e.target.value)}
                      className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                      disabled={isExtracting}
                    >
                      {availableModels.map(model => (
                        <option key={model.id} value={model.id}>
                          {model.name} ({model.provider}) - {model.description}
                        </option>
                      ))}
                    </select>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      优化反馈（描述需要改进的地方）
                    </label>
                    <textarea
                      value={optimizationFeedback}
                      onChange={(e) => setOptimizationFeedback(e.target.value)}
                      rows={4}
                      className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent resize-none"
                      placeholder="例如：角色描述不够详细，需要补充外貌特征；场景缺少氛围描述..."
                      disabled={isExtracting}
                    />
                  </div>
                  <Button
                    onClick={handleOptimizeAssets}
                    variant="primary"
                    disabled={isExtracting || !optimizationFeedback.trim()}
                    className="w-full"
                  >
                    {isExtracting ? '正在优化...' : '开始优化'}
                  </Button>
                </div>
              </div>
            )}

            {/* Characters */}
            <AssetTable
              assets={characters}
              assetType="CHARACTER"
              columns={CHARACTER_COLUMNS}
              editingAssets={editingAssets}
              editedAssets={editedAssets}
              onEdit={handleEditAsset}
              onSave={handleSaveAsset}
              onCancel={handleCancelEdit}
              onDelete={handleDeleteAsset}
              onFieldChange={handleFieldChange}
            />

            {/* Props */}
            <AssetTable
              assets={props}
              assetType="PROP"
              columns={PROP_COLUMNS}
              editingAssets={editingAssets}
              editedAssets={editedAssets}
              onEdit={handleEditAsset}
              onSave={handleSaveAsset}
              onCancel={handleCancelEdit}
              onDelete={handleDeleteAsset}
              onFieldChange={handleFieldChange}
            />

            {/* Scenes */}
            <AssetTable
              assets={scenes}
              assetType="SCENE"
              columns={SCENE_COLUMNS}
              editingAssets={editingAssets}
              editedAssets={editedAssets}
              onEdit={handleEditAsset}
              onSave={handleSaveAsset}
              onCancel={handleCancelEdit}
              onDelete={handleDeleteAsset}
              onFieldChange={handleFieldChange}
            />
          </div>
        )}
      </div>
    </div>
  );
}
