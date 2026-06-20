from sqlalchemy import Column, Integer, String, Text, DateTime
from sqlalchemy.orm import DeclarativeBase
from datetime import datetime

class Base(DeclarativeBase):
    """SQLAlchemy 基类"""
    pass

class Topic(Base):
    """帖子数据表映射类"""
    __tablename__ = "topics"

    id = Column(Integer, primary_key=True)                 # 帖子唯一 ID (topic_id)
    title = Column(String(255), nullable=False)            # 帖子标题
    link = Column(String(255), nullable=False)             # 帖子详情链接
    excerpt = Column(Text, nullable=True)                  # 帖子内容摘要
    tags = Column(Text, nullable=True)                     # 帖子标签（存储为 JSON 字符串）
    is_relevant = Column(Integer, default=0)               # 是否相关 (1: 相关, 0: 不相关)
    category = Column(String(100), nullable=True)          # AI 分类 (公益API/中转服务/服务状态变更/福利优惠/其他)
    summary = Column(Text, nullable=True)                  # AI 一句话摘要
    value_score = Column(Integer, default=0)               # AI 价值评分 (1-5分)
    created_at = Column(DateTime, default=datetime.now)    # 爬取入库时间

    def to_dict(self):
        """将模型对象转换为字典格式方便 API 返回"""
        import json
        try:
            tags_list = json.loads(self.tags) if self.tags else []
        except:
            tags_list = []

        return {
            "id": self.id,
            "title": self.title,
            "link": self.link,
            "excerpt": self.excerpt,
            "tags": tags_list,
            "is_relevant": bool(self.is_relevant),
            "category": self.category or "其他",
            "summary": self.summary or "",
            "value_score": self.value_score or 0,
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M:%S") if self.created_at else ""
        }

class SystemConfig(Base):
    """系统动态配置与管理表"""
    __tablename__ = "system_configs"

    key = Column(String(50), primary_key=True)             # 配置键名
    value = Column(Text, nullable=True)                    # 配置键值

