import React from 'react';
import { FolderOpen, Palette, LogOut, User } from 'lucide-react';
import { authService } from '../services/authService';

interface NavBarProps {
  currentPage: 'projects' | 'visual-style';
  onNavigate: (page: 'projects' | 'visual-style') => void;
  onLogout: () => void;
}

export default function NavBar({ currentPage, onNavigate, onLogout }: NavBarProps) {
  const user = authService.getUser();

  return (
    <nav className="bg-white border-b border-gray-200 px-6 py-4">
      <div className="max-w-7xl mx-auto flex items-center justify-between">
        <div className="flex items-center gap-6">
          <h1 className="text-xl font-bold text-gray-900">AI剧本批量拆解系统</h1>
          <div className="flex gap-2">
            <button
              onClick={() => onNavigate('projects')}
              className={`flex items-center gap-2 px-4 py-2 rounded-lg transition-colors ${
                currentPage === 'projects'
                  ? 'bg-indigo-50 text-indigo-700 font-medium'
                  : 'text-gray-600 hover:bg-gray-50'
              }`}
            >
              <FolderOpen className="w-4 h-4" />
              项目管理
            </button>
            <button
              onClick={() => onNavigate('visual-style')}
              className={`flex items-center gap-2 px-4 py-2 rounded-lg transition-colors ${
                currentPage === 'visual-style'
                  ? 'bg-indigo-50 text-indigo-700 font-medium'
                  : 'text-gray-600 hover:bg-gray-50'
              }`}
            >
              <Palette className="w-4 h-4" />
              视觉风格工具
            </button>
          </div>
        </div>
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2 text-sm text-gray-600">
            <User className="w-4 h-4" />
            <span>{user?.username || '用户'}</span>
          </div>
          <button
            onClick={onLogout}
            className="flex items-center gap-2 px-4 py-2 text-sm text-gray-600 hover:text-gray-900 hover:bg-gray-50 rounded-lg transition-colors"
          >
            <LogOut className="w-4 h-4" />
            退出登录
          </button>
        </div>
      </div>
    </nav>
  );
}
