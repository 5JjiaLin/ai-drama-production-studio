
export interface Character {
  name: string;
  role: string; // 角色
  description: string; // 角色描述 (包含视觉Prompt)
  gender: string; // 性别
  age: string; // 年龄
  voice: string; // 音色
}

export interface Prop {
  name: string;
  description: string; // 描述 (纯物理样貌，去身份化)
}

export interface Scene {
  name: string;
  description: string; // 描述 (纯物理样貌，去身份化)
}

export interface BasicElementsData {
  characters: Character[];
  props: Prop[];
  scenes: Scene[];
}

export interface StoryboardShot {
  shotNumber: number; // 序号
  voiceCharacter: string; // 配音角色
  emotion: string; // 情绪
  intensity: string; // 强度
  assets: string; // 场景角色道具 (以 @ 开头，空格分隔)
  dialogue: string; // 文案
  fusionPrompt: string; // 关键帧图片提示词 (Fusion Prompt)
  motionPrompt: string; // 视频动态提示词 (Motion Prompt)
}

export interface VisualStyleElement {
  category: string;
  description: string;
  reference: string;
}

// New interface for deep analysis
export interface ScriptAnalysis {
  plotSummary: string; // 剧情深度理解
  hiddenDetails: string[]; // 挖掘出的细节
  emotionalAnchors: string; // 情绪锚点流
}

export enum AppStep {
  UPLOAD = 0,
  BASIC_ELEMENTS = 1,
  STORYBOARD = 2,
  VISUAL_STYLE = 3
}

// Global declaration for CDN libraries
declare global {
  interface Window {
    mammoth: any;
    XLSX: any;
  }
}
