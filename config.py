import os

# 项目基础根目录
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# 数据库文件保存路径
DB_PATH = os.path.join(BASE_DIR, "data.db")

# 统一数据库连接字符串 (默认使用 SQLite，云端或 TiDB 可通过 DATABASE_URL 环境变量配置)
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{DB_PATH}")

# 兼容性处理：如果配置为 mysql://，SQLAlchemy 默认会寻找 MySQLdb 驱动而报错
# 我们通过代码将其自动重定向至 mysql+pymysql:// 以使用 pymysql 驱动
if DATABASE_URL.startswith("mysql://"):
    DATABASE_URL = DATABASE_URL.replace("mysql://", "mysql+pymysql://", 1)


# LLM（OpenAI 兼容接口）配置
# 需求提供：baseurl: https://api.longcat.chat/openai, api_key: ak_2Iz7Ww4KH2440E19yI3n69RN0er2I
OPENAI_API_KEY = "ak_2Iz7Ww4KH2440E19yI3n69RN0er2I"
OPENAI_BASE_URL = "https://api.longcat.chat/openai"
LLM_MODEL = "LongCat-2.0-Preview"

# 粗筛关键词（用于先期过滤无关帖子，降低 LLM 调用 Token 消耗）
# 匹配帖子标题、标签和正文摘要
FILTER_KEYWORDS = [
    "claude", "codex", "gpt", "gemini", "llama", "deepseek", "qwen",
    "中转", "公益", "免费", "key", "api", "额度", "分享", 
    "注册", "站长", "挂了", "跑路", "福利", "可用", "白嫖"
]

# 每次抓取的最大帖子条数
CRAWL_LIMIT = 50
