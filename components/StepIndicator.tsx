import React from 'react';
import { Check, Circle } from 'lucide-react';
import { AppStep } from '../types';

interface StepIndicatorProps {
  currentStep: AppStep;
}

const steps = [
  { id: AppStep.UPLOAD, label: "上传剧本" },
  { id: AppStep.BASIC_ELEMENTS, label: "基础元素" },
  { id: AppStep.STORYBOARD, label: "分镜表" },
  { id: AppStep.VISUAL_STYLE, label: "画面风格" }
];

const StepIndicator: React.FC<StepIndicatorProps> = ({ currentStep }) => {
  return (
    <div className="w-full py-6">
      <div className="flex items-center justify-center">
        {steps.map((step, index) => {
          const isCompleted = currentStep > step.id;
          const isCurrent = currentStep === step.id;
          
          return (
            <React.Fragment key={step.id}>
              <div className="flex flex-col items-center relative z-10">
                <div 
                  className={`w-8 h-8 rounded-full flex items-center justify-center border-2 transition-all duration-300
                    ${isCompleted ? 'bg-brand-600 border-brand-600 text-white' : 
                      isCurrent ? 'bg-white border-brand-600 text-brand-600 shadow-[0_0_0_4px_rgba(14,165,233,0.2)]' : 
                      'bg-slate-100 border-slate-300 text-slate-400'}`}
                >
                  {isCompleted ? <Check size={16} /> : (index + 1)}
                </div>
                <span className={`mt-2 text-xs font-medium absolute top-full w-max text-center
                  ${isCurrent ? 'text-brand-600' : isCompleted ? 'text-slate-700' : 'text-slate-400'}`}>
                  {step.label}
                </span>
              </div>
              
              {index < steps.length - 1 && (
                <div className="w-12 sm:w-24 h-0.5 mx-2 bg-slate-200 relative -top-3">
                  <div 
                    className="absolute top-0 left-0 h-full bg-brand-600 transition-all duration-500"
                    style={{ width: isCompleted ? '100%' : '0%' }}
                  />
                </div>
              )}
            </React.Fragment>
          );
        })}
      </div>
    </div>
  );
};

export default StepIndicator;