import React, { useState } from 'react';
import { Send, Sparkles } from 'lucide-react';
import Button from './Button';

interface FeedbackInputProps {
  onSend: (feedback: string) => void;
  isLoading: boolean;
  placeholder?: string;
  label?: string;
}

const FeedbackInput: React.FC<FeedbackInputProps> = ({ 
  onSend, 
  isLoading, 
  placeholder = "例如：请把所有角色的年龄都改大一点...", 
  label = "AI 优化调整"
}) => {
  const [text, setText] = useState('');

  const handleSubmit = () => {
    if (text.trim()) {
      onSend(text);
      setText('');
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) {
      handleSubmit();
    }
  };

  return (
    <div className="mt-6 bg-slate-50 p-4 rounded-xl border border-slate-200">
      <div className="flex items-center gap-2 mb-3 text-slate-800 font-medium">
        <Sparkles size={16} className="text-brand-600" />
        {label}
      </div>
      <div className="relative">
        <textarea
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={placeholder}
          className="w-full min-h-[80px] p-3 pr-4 border border-slate-300 rounded-lg focus:ring-2 focus:ring-brand-500 focus:border-transparent text-sm resize-y"
          disabled={isLoading}
        />
      </div>
      <div className="flex justify-between items-center mt-3">
        <span className="text-xs text-slate-400">按 Ctrl + Enter 发送</span>
        <Button 
          onClick={handleSubmit} 
          disabled={!text.trim() || isLoading} 
          isLoading={isLoading} 
          size="sm"
          className="bg-brand-600 hover:bg-brand-700"
        >
          <Send size={14} className="mr-2" /> 提交优化
        </Button>
      </div>
    </div>
  );
};

export default FeedbackInput;