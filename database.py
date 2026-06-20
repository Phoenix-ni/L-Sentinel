import json
from contextlib import contextmanager
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from config import DATABASE_URL
import hashlib
import os
from models import Base, Topic, SystemConfig

# 初始化 SQLAlchemy 引擎
# 对于 SQLite，添加 connect_args={"check_same_thread": False} 以支持多线程（如 FastAPI/Streamlit）
if DATABASE_URL.startswith("sqlite"):
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
else:
    # 针对 MySQL / TiDB 等，开启连接池回收参数，防止长期闲置连接断开
    engine = create_engine(DATABASE_URL, pool_recycle=3600, pool_pre_ping=True)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@contextmanager
def get_session():
    """获取数据库 Session 上下文管理器，确保会话安全关闭"""
    session = SessionLocal()
    try:
        yield session
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()

def get_config(key, default=None):
    """获取系统动态配置参数"""
    with get_session() as session:
        try:
            config = session.query(SystemConfig).filter(SystemConfig.key == key).first()
            if config is not None:
                return config.value
            return default
        except Exception as e:
            print(f"[数据库错误] 读取配置 {key} 失败: {e}")
            return default

def set_config(key, value):
    """写入/更新系统动态配置参数"""
    with get_session() as session:
        try:
            config = session.query(SystemConfig).filter(SystemConfig.key == key).first()
            if config is not None:
                config.value = str(value)
            else:
                config = SystemConfig(key=key, value=str(value))
                session.add(config)
            session.commit()
            return True
        except Exception as e:
            session.rollback()
            print(f"[数据库错误] 写入配置 {key} 失败: {e}")
            return False

def init_system_configs():
    """配置项默认初始化"""
    from config import OPENAI_API_KEY, OPENAI_BASE_URL, LLM_MODEL
    
    # 默认明文密码（如果无环境变量传入，默认使用 admin123）
    default_pwd = os.getenv("ADMIN_PASSWORD", "admin123")
    default_pwd_hash = hashlib.sha256(default_pwd.encode("utf-8")).hexdigest()
    
    defaults = {
        "admin_password_hash": default_pwd_hash,
        "llm_provider": "openai",
        "llm_api_key": "",
        "llm_base_url": "https://api.openai.com/v1",
        "llm_model": "gpt-4o"
    }
    
    # 若配置了 ADMIN_PASSWORD 环境变量，则每次启动时强制更新哈希，方便用户在云端部署重置密码
    if "ADMIN_PASSWORD" in os.environ:
        set_config("admin_password_hash", default_pwd_hash)
        print(f"[数据库] 自动检测到系统环境变量 ADMIN_PASSWORD，已同步更新管理员密码哈希！")
        
    for k, v in defaults.items():
        if k == "admin_password_hash" and "ADMIN_PASSWORD" in os.environ:
            continue
        if get_config(k) is None:
            set_config(k, v)
            print(f"[数据库] 自动初始化了配置项: {k}")

def init_db():
    """初始化数据库并根据模型创建表结构"""
    print(f"[数据库] 正在连接数据库: {DATABASE_URL}")
    try:
        Base.metadata.create_all(bind=engine)
        print("[数据库] 表结构创建/同步成功！")
        # 执行系统变量灌注
        init_system_configs()
    except Exception as e:
        print(f"[数据库错误] 初始化表结构失败: {e}")

def check_exists(topic_id):
    """
    检查帖子是否已经存在于数据库中
    :param topic_id: 帖子唯一 ID
    :return: True 存在, False 不存在
    """
    with get_session() as session:
        exists = session.query(Topic).filter(Topic.id == topic_id).first() is not None
        return exists

def insert_topic(topic_data):
    """
    向数据库中插入一条帖子记录 (如果已存在则忽略)
    :param topic_data: 包含帖子的结构化字典
    :return: True 插入成功, False 插入失败或已存在
    """
    topic_id = topic_data.get("id")
    if check_exists(topic_id):
        return False

    # 归一化 tags 字段
    tags_str = json.dumps(topic_data.get("tags", []))
    is_relevant_val = 1 if topic_data.get("is_relevant", False) else 0

    with get_session() as session:
        try:
            db_topic = Topic(
                id=topic_id,
                title=topic_data.get("title"),
                link=topic_data.get("link"),
                excerpt=topic_data.get("excerpt", ""),
                tags=tags_str,
                is_relevant=is_relevant_val,
                category=topic_data.get("category", ""),
                summary=topic_data.get("summary", ""),
                value_score=topic_data.get("value_score", 0)
            )
            session.add(db_topic)
            session.commit()
            return True
        except Exception as e:
            session.rollback()
            print(f"[数据库错误] 插入帖子 {topic_id} 失败: {e}")
            return False

def fetch_all_topics(relevant_only=True):
    """
    获取已保存的帖子列表
    :param relevant_only: 是否仅获取相关的帖子，默认 True
    :return: 帖子字典列表
    """
    with get_session() as session:
        try:
            query = session.query(Topic)
            if relevant_only:
                query = query.filter(Topic.is_relevant == 1)
            
            # 按入库时间倒序
            query = query.order_by(Topic.created_at.desc())
            db_topics = query.all()
            
            # 序列化为 dict 列表返回
            return [t.to_dict() for t in db_topics]
        except Exception as e:
            print(f"[数据库错误] 查询帖子列表失败: {e}")
            return []

if __name__ == "__main__":
    init_db()
