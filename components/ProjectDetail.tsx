import React, { useState } from 'react';
import { ArrowLeft, FileText, Image, Film, Settings, Trash2 } from 'lucide-react';
import { Project, projectService } from '../services/projectService';
import Button from './Button';

interface ProjectDetailProps {
  project: Project;
  onBack: () => void;
  onNavigateToAssets: () => void;
  onNavigateToStoryboards: () => void;
}

export default function ProjectDetail({
  project,
  onBack,
  onNavigateToAssets,
  onNavigateToStoryboards,
}: ProjectDetailProps) {
  const [error, setError] = useState<string | null>(null);
  const [isDeleting, setIsDeleting] = useState(false);

  const handleDeleteProject = async () => {
    if (!confirm(`确定要删除项目"${project.name}"吗？删除后将无法恢复，包括所有资产和分镜数据。`)) {
      return;
    }

    try {
      setIsDeleting(true);
      setError(null);
      await projectService.deleteProject(project.id);
      // 删除成功后返回项目列表
      onBack();
    } catch (err: any) {
      setError(err.message || '删除项目失败');
      setIsDeleting(false);
    }
  };

  const getStatusText = (status: Project['status']) => {
    const statusMap = {
      'ASSET_BUILDING': '资产拆解中',
      'ASSET_LOCKED': '资产已锁定',
      'STORYBOARD_GENERATION': '分镜生成中',
      'COMPLETED': '已完成',
    };
    return statusMap[status];
  };

  const getStatusColor = (status: Project['status']) => {
    const colorMap = {
      'ASSET_BUILDING': 'bg-blue-100 text-blue-700',
      'ASSET_LOCKED': 'bg-purple-100 text-purple-700',
      'STORYBOARD_GENERATION': 'bg-yellow-100 text-yellow-700',
      'COMPLETED': 'bg-green-100 text-green-700',
    };
    return colorMap[status];
  };

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <div className="max-w-5xl mx-auto">
        {/* Header */}
        <div className="mb-6">
          <button
            onClick={onBack}
            className="flex items-center text-gray-600 hover:text-gray-900 mb-4"
          >
            <ArrowLeft className="w-5 h-5 mr-2" />
            返回项目列表
          </button>
          <div className="flex items-start justify-between">
            <div>
              <h1 className="text-3xl font-bold text-gray-900 mb-2">{project.name}</h1>
              <p className="text-gray-600">{project.description || '暂无描述'}</p>
            </div>
            <span
              className={`inline-flex items-center px-3 py-1 rounded-full text-sm font-medium ${getStatusColor(
                project.status
              )}`}
            >
              {getStatusText(project.status)}
            </span>
          </div>
        </div>

        {/* Error Message */}
        {error && (
          <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg mb-6">
            {error}
          </div>
        )}

        {/* Action Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
          {/* Asset Extraction Card */}
          <div className="bg-white rounded-xl shadow-sm p-6 border border-gray-200">
            <div className="flex items-center mb-4">
              <div className="w-12 h-12 bg-blue-100 rounded-lg flex items-center justify-center mr-4">
                <FileText className="w-6 h-6 text-blue-600" />
              </div>
              <div>
                <h3 className="text-lg font-semibold text-gray-900">资产拆解</h3>
                <p className="text-sm text-gray-600">提取角色、道具、场景</p>
              </div>
            </div>
            <p className="text-gray-600 text-sm mb-4">
              上传剧本，AI自动提取资产信息，支持补充剧本继续拆解
            </p>
            <Button onClick={onNavigateToAssets} variant="primary" className="w-full">
              进入资产拆解
            </Button>
          </div>

          {/* Storyboard Generation Card */}
          <div className="bg-white rounded-xl shadow-sm p-6 border border-gray-200">
            <div className="flex items-center mb-4">
              <div className="w-12 h-12 bg-purple-100 rounded-lg flex items-center justify-center mr-4">
                <Film className="w-6 h-6 text-purple-600" />
              </div>
              <div>
                <h3 className="text-lg font-semibold text-gray-900">分镜拆解</h3>
                <p className="text-sm text-gray-600">生成分镜表</p>
              </div>
            </div>
            <p className="text-gray-600 text-sm mb-4">
              上传单集剧本，自动匹配资产库，生成详细分镜表
            </p>
            <Button onClick={onNavigateToStoryboards} variant="primary" className="w-full">
              进入分镜拆解
            </Button>
          </div>
        </div>

        {/* Project Info */}
        <div className="bg-white rounded-xl shadow-sm p-6 border border-gray-200">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">项目信息</h3>
          <div className="grid grid-cols-2 gap-4 text-sm">
            <div>
              <span className="text-gray-600">创建时间：</span>
              <span className="text-gray-900">
                {new Date(project.created_at).toLocaleString('zh-CN')}
              </span>
            </div>
            <div>
              <span className="text-gray-600">更新时间：</span>
              <span className="text-gray-900">
                {new Date(project.updated_at).toLocaleString('zh-CN')}
              </span>
            </div>
          </div>

          {/* Delete Project Button */}
          <div className="mt-6 pt-6 border-t border-gray-200">
            <Button
              onClick={handleDeleteProject}
              variant="secondary"
              disabled={isDeleting}
              className="w-full flex items-center justify-center gap-2 text-red-600 hover:text-red-700 hover:bg-red-50"
            >
              <Trash2 className="w-4 h-4" />
              {isDeleting ? '删除中...' : '删除项目'}
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}
