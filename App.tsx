import React, { useState } from 'react';
import AuthForm from './components/AuthForm';
import NavBar from './components/NavBar';
import ProjectList from './components/ProjectList';
import ProjectDetail from './components/ProjectDetail';
import AssetExtraction from './components/AssetExtraction';
import StoryboardGeneration from './components/StoryboardGeneration';
import CreateProjectModal from './components/CreateProjectModal';
import { authService } from './services/authService';
import { projectService, Project } from './services/projectService';

// 页面类型
type Page =
  | { type: 'projects' }
  | { type: 'project-detail'; project: Project }
  | { type: 'asset-extraction'; project: Project }
  | { type: 'storyboard-generation'; project: Project }
  | { type: 'visual-style' };

function App() {
  const [isAuthenticated, setIsAuthenticated] = useState(authService.isAuthenticated());
  const [currentPage, setCurrentPage] = useState<Page>({ type: 'projects' });
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [projectListKey, setProjectListKey] = useState(0); // 用于强制刷新ProjectList

  const handleLogin = async (username: string, password: string) => {
    await authService.login(username, password);
    setIsAuthenticated(true);
  };

  const handleRegister = async (username: string, email: string, password: string, fullName: string) => {
    await authService.register(username, email, password, fullName);
    setIsAuthenticated(true);
  };

  const handleLogout = () => {
    authService.logout();
    setIsAuthenticated(false);
    setCurrentPage({ type: 'projects' });
  };

  const handleCreateProject = async (name: string, description: string) => {
    const project = await projectService.createProject({ name, description });
    setCurrentPage({ type: 'project-detail', project });
  };

  if (!isAuthenticated) {
    return <AuthForm onLogin={handleLogin} onRegister={handleRegister} />;
  }

  // 渲染当前页面
  const renderPage = () => {
    switch (currentPage.type) {
      case 'projects':
        return (
          <ProjectList
            key={projectListKey} // 添加key强制重新挂载
            onSelectProject={(project) => setCurrentPage({ type: 'project-detail', project })}
            onCreateProject={() => setShowCreateModal(true)}
          />
        );

      case 'project-detail':
        return (
          <ProjectDetail
            project={currentPage.project}
            onBack={() => {
              setCurrentPage({ type: 'projects' });
              setProjectListKey(prev => prev + 1); // 刷新项目列表
            }}
            onNavigateToAssets={() => setCurrentPage({ type: 'asset-extraction', project: currentPage.project })}
            onNavigateToStoryboards={() => setCurrentPage({ type: 'storyboard-generation', project: currentPage.project })}
          />
        );

      case 'asset-extraction':
        return (
          <AssetExtraction
            project={currentPage.project}
            onBack={() => setCurrentPage({ type: 'project-detail', project: currentPage.project })}
          />
        );

      case 'storyboard-generation':
        return (
          <StoryboardGeneration
            project={currentPage.project}
            onBack={() => setCurrentPage({ type: 'project-detail', project: currentPage.project })}
          />
        );

      case 'visual-style':
        return (
          <div className="min-h-screen bg-gray-50 p-6">
            <div className="max-w-5xl mx-auto">
              <div className="bg-white rounded-xl shadow-sm p-8 border border-gray-200 text-center">
                <h2 className="text-2xl font-bold text-gray-900 mb-4">视觉风格工具</h2>
                <p className="text-gray-600">此功能即将推出...</p>
              </div>
            </div>
          </div>
        );

      default:
        return null;
    }
  };

  const getNavPage = (): 'projects' | 'visual-style' => {
    return currentPage.type === 'visual-style' ? 'visual-style' : 'projects';
  };

  return (
    <div className="min-h-screen bg-gray-50">
      <NavBar
        currentPage={getNavPage()}
        onNavigate={(page) => setCurrentPage({ type: page })}
        onLogout={handleLogout}
      />
      {renderPage()}
      <CreateProjectModal
        isOpen={showCreateModal}
        onClose={() => setShowCreateModal(false)}
        onSubmit={handleCreateProject}
      />
    </div>
  );
}

export default App;
