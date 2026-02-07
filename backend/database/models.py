"""
数据库模型定义
使用SQLAlchemy ORM
"""
from datetime import datetime
from typing import Optional, List
from sqlalchemy import (
    create_engine, Column, Integer, String, Text, Boolean,
    Float, DateTime, ForeignKey, CheckConstraint, UniqueConstraint
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, Session

Base = declarative_base()


class Project(Base):
    """项目模型"""
    __tablename__ = 'projects'

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False, unique=True)
    description = Column(Text)
    status = Column(String, nullable=False, default='ASSET_BUILDING')
    current_snapshot_id = Column(Integer, ForeignKey('asset_snapshots.id'))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 关系
    episodes = relationship("Episode", back_populates="project", cascade="all, delete-orphan")
    assets = relationship("Asset", back_populates="project", cascade="all, delete-orphan")
    snapshots = relationship("AssetSnapshot", back_populates="project", cascade="all, delete-orphan")
    visual_styles = relationship("VisualStyle", back_populates="project", cascade="all, delete-orphan")

    __table_args__ = (
        CheckConstraint(
            status.in_(['ASSET_BUILDING', 'ASSET_LOCKED', 'STORYBOARD_GENERATION', 'COMPLETED']),
            name='check_project_status'
        ),
    )


class Episode(Base):
    """剧集模型"""
    __tablename__ = 'episodes'

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(Integer, ForeignKey('projects.id'), nullable=False)
    episode_number = Column(Integer, nullable=False)
    title = Column(String)
    script_content = Column(Text, nullable=False)
    upload_status = Column(String, nullable=False, default='UPLOADED')
    ai_analysis_result = Column(Text)  # JSON字符串
    uploaded_at = Column(DateTime, default=datetime.utcnow)

    # 关系
    project = relationship("Project", back_populates="episodes")
    extraction_records = relationship("AssetExtractionRecord", back_populates="episode", cascade="all, delete-orphan")
    storyboards = relationship("Storyboard", back_populates="episode", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint('project_id', 'episode_number', name='uq_project_episode'),
        CheckConstraint(
            upload_status.in_(['UPLOADED', 'ANALYZING', 'COMPLETED', 'FAILED']),
            name='check_upload_status'
        ),
    )


class Asset(Base):
    """资产模型"""
    __tablename__ = 'assets'

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(Integer, ForeignKey('projects.id'), nullable=False)
    asset_type = Column(String, nullable=False)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=False)

    # 角色专用字段
    gender = Column(String)
    age = Column(String)
    voice = Column(String)
    role = Column(String)

    # 元数据
    is_deleted = Column(Boolean, default=False)
    merged_into_asset_id = Column(Integer, ForeignKey('assets.id'))
    first_appeared_episode_id = Column(Integer, ForeignKey('episodes.id'))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 关系
    project = relationship("Project", back_populates="assets")
    extraction_records = relationship("AssetExtractionRecord", foreign_keys="AssetExtractionRecord.asset_id")
    storyboard_references = relationship("StoryboardAssetReference", back_populates="asset")

    __table_args__ = (
        CheckConstraint(
            asset_type.in_(['CHARACTER', 'PROP', 'SCENE']),
            name='check_asset_type'
        ),
    )


class AssetExtractionRecord(Base):
    """资产提取记录"""
    __tablename__ = 'asset_extraction_records'

    id = Column(Integer, primary_key=True, autoincrement=True)
    episode_id = Column(Integer, ForeignKey('episodes.id'), nullable=False)
    asset_id = Column(Integer, ForeignKey('assets.id'))

    # AI提取的原始信息
    extracted_name = Column(String, nullable=False)
    extracted_description = Column(Text)
    extracted_type = Column(String, nullable=False)

    # 去重状态
    dedup_status = Column(String, nullable=False, default='PENDING')
    suggested_merge_asset_id = Column(Integer, ForeignKey('assets.id'))
    similarity_score = Column(Float)

    confirmed_by_user = Column(Boolean, default=False)
    confirmed_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)

    # 关系
    episode = relationship("Episode", back_populates="extraction_records")

    __table_args__ = (
        CheckConstraint(
            extracted_type.in_(['CHARACTER', 'PROP', 'SCENE']),
            name='check_extracted_type'
        ),
        CheckConstraint(
            dedup_status.in_(['PENDING', 'CONFIRMED_NEW', 'CONFIRMED_MERGE', 'AUTO_MATCHED']),
            name='check_dedup_status'
        ),
    )


class AssetMergeHistory(Base):
    """资产合并历史"""
    __tablename__ = 'asset_merge_history'

    id = Column(Integer, primary_key=True, autoincrement=True)
    source_asset_id = Column(Integer, ForeignKey('assets.id'), nullable=False)
    target_asset_id = Column(Integer, ForeignKey('assets.id'), nullable=False)
    merged_by_user = Column(Boolean, default=True)
    merge_reason = Column(Text)
    source_asset_snapshot = Column(Text, nullable=False)  # JSON字符串
    merged_at = Column(DateTime, default=datetime.utcnow)


class AssetSnapshot(Base):
    """资产库快照"""
    __tablename__ = 'asset_snapshots'

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(Integer, ForeignKey('projects.id'), nullable=False)
    snapshot_name = Column(String, nullable=False)
    description = Column(Text)
    assets_data = Column(Text, nullable=False)  # JSON字符串
    is_active = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # 关系
    project = relationship("Project", back_populates="snapshots")
    storyboards = relationship("Storyboard", back_populates="snapshot")


class Storyboard(Base):
    """分镜"""
    __tablename__ = 'storyboards'

    id = Column(Integer, primary_key=True, autoincrement=True)
    episode_id = Column(Integer, ForeignKey('episodes.id'), nullable=False)
    snapshot_id = Column(Integer, ForeignKey('asset_snapshots.id'), nullable=False)

    shot_number = Column(Integer, nullable=False)
    voice_character = Column(String)
    emotion = Column(String)
    intensity = Column(String)
    dialogue = Column(Text)
    fusion_prompt = Column(Text)
    motion_prompt = Column(Text)

    generation_status = Column(String, nullable=False, default='GENERATED')
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 关系
    episode = relationship("Episode", back_populates="storyboards")
    snapshot = relationship("AssetSnapshot", back_populates="storyboards")
    asset_references = relationship("StoryboardAssetReference", back_populates="storyboard", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint('episode_id', 'shot_number', name='uq_episode_shot'),
        CheckConstraint(
            generation_status.in_(['DRAFT', 'GENERATED', 'APPROVED']),
            name='check_generation_status'
        ),
    )


class StoryboardAssetReference(Base):
    """分镜-资产关联"""
    __tablename__ = 'storyboard_asset_references'

    id = Column(Integer, primary_key=True, autoincrement=True)
    storyboard_id = Column(Integer, ForeignKey('storyboards.id'), nullable=False)
    asset_id = Column(Integer, ForeignKey('assets.id'), nullable=False)
    reference_type = Column(String, default='PRIMARY')

    # 关系
    storyboard = relationship("Storyboard", back_populates="asset_references")
    asset = relationship("Asset", back_populates="storyboard_references")

    __table_args__ = (
        UniqueConstraint('storyboard_id', 'asset_id', name='uq_storyboard_asset'),
        CheckConstraint(
            reference_type.in_(['PRIMARY', 'SECONDARY']),
            name='check_reference_type'
        ),
    )


class VisualStyle(Base):
    """视觉风格"""
    __tablename__ = 'visual_styles'

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(Integer, ForeignKey('projects.id'), nullable=False)
    category = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    reference = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

    # 关系
    project = relationship("Project", back_populates="visual_styles")


# 数据库初始化函数
def init_db(db_path: str = "storage/projects/default.db"):
    """初始化数据库"""
    engine = create_engine(f'sqlite:///{db_path}', echo=True)
    Base.metadata.create_all(engine)
    return engine


def get_session(engine) -> Session:
    """获取数据库会话"""
    from sqlalchemy.orm import sessionmaker
    Session = sessionmaker(bind=engine)
    return Session()
