-- AI剧本批量拆解系统 - 数据库Schema
-- Version: 2.0
-- Created: 2026-02-07

-- ============================================
-- 0. 用户表 (Users)
-- ============================================
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    email TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    full_name TEXT,
    is_active BOOLEAN DEFAULT 1,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    last_login_at DATETIME
);

CREATE INDEX idx_users_username ON users(username);
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_active ON users(is_active);

-- ============================================
-- 0.1 用户会话表 (User Sessions)
-- ============================================
CREATE TABLE IF NOT EXISTS user_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    token_jti TEXT UNIQUE NOT NULL,
    ip_address TEXT,
    user_agent TEXT,
    expires_at DATETIME NOT NULL,
    is_revoked BOOLEAN DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE INDEX idx_sessions_user ON user_sessions(user_id);
CREATE INDEX idx_sessions_jti ON user_sessions(token_jti);
CREATE INDEX idx_sessions_expires ON user_sessions(expires_at);

-- ============================================
-- 1. 项目表 (Projects)
-- ============================================
CREATE TABLE IF NOT EXISTS projects (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    description TEXT,
    status TEXT NOT NULL CHECK(status IN (
        'ASSET_BUILDING',      -- 资产拆解阶段
        'ASSET_LOCKED',        -- 资产库已锁定
        'STORYBOARD_GENERATION', -- 分镜生成阶段
        'COMPLETED'            -- 全部完成
    )) DEFAULT 'ASSET_BUILDING',
    current_snapshot_id INTEGER,
    is_deleted BOOLEAN DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (current_snapshot_id) REFERENCES asset_snapshots(id),
    UNIQUE(user_id, name)
);

CREATE INDEX idx_projects_user ON projects(user_id);
CREATE INDEX idx_projects_status ON projects(status);
CREATE INDEX idx_projects_updated_at ON projects(updated_at);

-- ============================================
-- 2. 剧集表 (Episodes) - 按集上传
-- ============================================
CREATE TABLE IF NOT EXISTS episodes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL,
    episode_number INTEGER NOT NULL,
    title TEXT,
    script_content TEXT NOT NULL,
    upload_status TEXT NOT NULL CHECK(upload_status IN (
        'UPLOADED',
        'ANALYZING',
        'COMPLETED',
        'FAILED'
    )) DEFAULT 'UPLOADED',
    ai_analysis_result TEXT,  -- JSON格式存储深度分析结果
    uploaded_at DATETIME DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
    UNIQUE(project_id, episode_number)
);

CREATE INDEX idx_episodes_project ON episodes(project_id);
CREATE INDEX idx_episodes_number ON episodes(project_id, episode_number);

-- ============================================
-- 3. 资产主表 (Assets)
-- ============================================
CREATE TABLE IF NOT EXISTS assets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL,
    asset_type TEXT NOT NULL CHECK(asset_type IN (
        'CHARACTER',  -- 角色
        'PROP',       -- 道具
        'SCENE'       -- 场景
    )),
    name TEXT NOT NULL,
    description TEXT NOT NULL,

    -- 角色专用字段
    gender TEXT,
    age TEXT,
    voice TEXT,
    role TEXT,

    -- 元数据
    is_deleted BOOLEAN DEFAULT 0,
    merged_into_asset_id INTEGER,
    first_appeared_episode_id INTEGER,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
    FOREIGN KEY (merged_into_asset_id) REFERENCES assets(id),
    FOREIGN KEY (first_appeared_episode_id) REFERENCES episodes(id)
);

CREATE INDEX idx_assets_project_type ON assets(project_id, asset_type);
CREATE INDEX idx_assets_name ON assets(project_id, name);
CREATE INDEX idx_assets_deleted ON assets(is_deleted);
CREATE INDEX idx_assets_merged ON assets(merged_into_asset_id);

-- ============================================
-- 4. 资产提取记录 (Asset Extraction Records)
-- ============================================
CREATE TABLE IF NOT EXISTS asset_extraction_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    episode_id INTEGER NOT NULL,
    asset_id INTEGER,

    -- AI提取的原始信息
    extracted_name TEXT NOT NULL,
    extracted_description TEXT,
    extracted_type TEXT NOT NULL CHECK(extracted_type IN (
        'CHARACTER',
        'PROP',
        'SCENE'
    )),

    -- 去重状态
    dedup_status TEXT NOT NULL CHECK(dedup_status IN (
        'PENDING',           -- 待用户确认
        'CONFIRMED_NEW',     -- 确认为新资产
        'CONFIRMED_MERGE',   -- 确认合并到已有资产
        'AUTO_MATCHED'       -- AI自动匹配
    )) DEFAULT 'PENDING',

    suggested_merge_asset_id INTEGER,
    similarity_score REAL,

    confirmed_by_user BOOLEAN DEFAULT 0,
    confirmed_at DATETIME,

    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (episode_id) REFERENCES episodes(id) ON DELETE CASCADE,
    FOREIGN KEY (asset_id) REFERENCES assets(id),
    FOREIGN KEY (suggested_merge_asset_id) REFERENCES assets(id)
);

CREATE INDEX idx_extraction_episode ON asset_extraction_records(episode_id);
CREATE INDEX idx_extraction_status ON asset_extraction_records(dedup_status);
CREATE INDEX idx_extraction_asset ON asset_extraction_records(asset_id);

-- ============================================
-- 5. 资产合并历史 (Asset Merge History)
-- ============================================
CREATE TABLE IF NOT EXISTS asset_merge_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_asset_id INTEGER NOT NULL,
    target_asset_id INTEGER NOT NULL,
    merged_by_user BOOLEAN DEFAULT 1,
    merge_reason TEXT,
    source_asset_snapshot TEXT NOT NULL,  -- JSON格式
    merged_at DATETIME DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (source_asset_id) REFERENCES assets(id),
    FOREIGN KEY (target_asset_id) REFERENCES assets(id)
);

CREATE INDEX idx_merge_history_source ON asset_merge_history(source_asset_id);
CREATE INDEX idx_merge_history_target ON asset_merge_history(target_asset_id);

-- ============================================
-- 6. 资产库快照 (Asset Snapshots)
-- ============================================
CREATE TABLE IF NOT EXISTS asset_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL,
    snapshot_name TEXT NOT NULL,
    description TEXT,
    assets_data TEXT NOT NULL,  -- JSON格式的完整资产数据
    is_active BOOLEAN DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
);

CREATE INDEX idx_snapshots_project ON asset_snapshots(project_id);
CREATE INDEX idx_snapshots_active ON asset_snapshots(project_id, is_active);

-- ============================================
-- 7. 分镜表 (Storyboards)
-- ============================================
CREATE TABLE IF NOT EXISTS storyboards (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    episode_id INTEGER NOT NULL,
    snapshot_id INTEGER NOT NULL,

    shot_number INTEGER NOT NULL,
    voice_character TEXT,
    emotion TEXT,
    intensity TEXT,
    asset_mapping TEXT,  -- 场景角色道具(@MAPPING)，如：@萧云 @黑曜石灵魂 @灵剑宗广场
    dialogue TEXT,
    fusion_prompt TEXT,
    motion_prompt TEXT,

    generation_status TEXT NOT NULL CHECK(generation_status IN (
        'DRAFT',
        'GENERATED',
        'APPROVED'
    )) DEFAULT 'GENERATED',

    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (episode_id) REFERENCES episodes(id) ON DELETE CASCADE,
    FOREIGN KEY (snapshot_id) REFERENCES asset_snapshots(id),
    UNIQUE(episode_id, shot_number)
);

CREATE INDEX idx_storyboards_episode ON storyboards(episode_id);
CREATE INDEX idx_storyboards_snapshot ON storyboards(snapshot_id);

-- ============================================
-- 8. 分镜-资产关联表 (Storyboard Asset References)
-- ============================================
CREATE TABLE IF NOT EXISTS storyboard_asset_references (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    storyboard_id INTEGER NOT NULL,
    asset_id INTEGER NOT NULL,
    reference_type TEXT CHECK(reference_type IN (
        'PRIMARY',    -- 主要资产
        'SECONDARY'   -- 次要资产
    )) DEFAULT 'PRIMARY',

    FOREIGN KEY (storyboard_id) REFERENCES storyboards(id) ON DELETE CASCADE,
    FOREIGN KEY (asset_id) REFERENCES assets(id),
    UNIQUE(storyboard_id, asset_id)
);

CREATE INDEX idx_storyboard_refs_storyboard ON storyboard_asset_references(storyboard_id);
CREATE INDEX idx_storyboard_refs_asset ON storyboard_asset_references(asset_id);

-- ============================================
-- 9. 视觉风格表 (Visual Styles)
-- ============================================
CREATE TABLE IF NOT EXISTS visual_styles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL,
    category TEXT NOT NULL,
    description TEXT NOT NULL,
    reference TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
);

CREATE INDEX idx_visual_styles_project ON visual_styles(project_id);

-- ============================================
-- 10. 风格模板表 (Style Templates)
-- ============================================
CREATE TABLE IF NOT EXISTS style_templates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    description TEXT,

    -- 风格参数
    art_style TEXT NOT NULL,           -- 艺术风格（如：写实、动漫、水彩等）
    color_tone TEXT,                   -- 色调（如：暖色调、冷色调、黑白等）
    lighting TEXT,                     -- 光照（如：自然光、戏剧性光照等）
    camera_angle TEXT,                 -- 镜头角度偏好
    mood TEXT,                         -- 整体氛围

    -- 提示词模板
    prompt_template TEXT NOT NULL,     -- 用于AI生成的提示词模板
    negative_prompt TEXT,              -- 负面提示词

    -- 元数据
    is_public BOOLEAN DEFAULT 0,       -- 是否公开（供其他用户使用）
    usage_count INTEGER DEFAULT 0,     -- 使用次数
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE INDEX idx_style_templates_user ON style_templates(user_id);
CREATE INDEX idx_style_templates_public ON style_templates(is_public);

-- ============================================
-- 触发器 (Triggers)
-- ============================================

-- 更新projects表的updated_at字段
CREATE TRIGGER IF NOT EXISTS update_projects_timestamp
AFTER UPDATE ON projects
FOR EACH ROW
BEGIN
    UPDATE projects SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;

-- 更新assets表的updated_at字段
CREATE TRIGGER IF NOT EXISTS update_assets_timestamp
AFTER UPDATE ON assets
FOR EACH ROW
BEGIN
    UPDATE assets SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;

-- 更新storyboards表的updated_at字段
CREATE TRIGGER IF NOT EXISTS update_storyboards_timestamp
AFTER UPDATE ON storyboards
FOR EACH ROW
BEGIN
    UPDATE storyboards SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;
