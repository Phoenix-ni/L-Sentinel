import os

# 项目基础根目录
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# 数据库文件保存路径
DB_PATH = os.path.join(BASE_DIR, "data.db")

# 统一数据库连接字符串 (默认使用 SQLite，云端或 TiDB 可通过 DATABASE_URL 环境变量配置)
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{DB_PATH}")

# 兼容性处理：如果配置为 mysql:// 或 mysql+mysqldb://，SQLAlchemy 默认会寻找 MySQLdb 驱动而报错
# 我们通过代码将其自动重定向至 mysql+pymysql:// 以使用 pymysql 驱动
if DATABASE_URL.startswith("mysql://"):
    DATABASE_URL = DATABASE_URL.replace("mysql://", "mysql+pymysql://", 1)
elif DATABASE_URL.startswith("mysql+"):
    if "://" in DATABASE_URL:
        _, rest = DATABASE_URL.split("://", 1)
        DATABASE_URL = "mysql+pymysql://" + rest

# 自动处理 SSL CA 证书路径，并剔除 PyMySQL 驱动不支持的 file:// 协议前缀
if "ssl_ca=" in DATABASE_URL:
    import re
    match = re.search(r"ssl_ca=([^&]+)", DATABASE_URL)
    if match:
        ca_path = match.group(1)
        # 1. 取得干净的绝对物理路径（去除 PyMySQL 不支持的 file:// 前缀）
        clean_path = ca_path.replace("file://", "")
        # 2. 如果该路径在当前环境不存在（例如容器中没有 /home/zyb/Downloads/），自动指向容器内的系统 CA 证书
        if not os.path.exists(clean_path):
            system_ca = "/etc/ssl/certs/ca-certificates.crt"
            if os.path.exists(system_ca):
                clean_path = system_ca
        # 3. 在 URL 中用干净的纯绝对路径替换原有的 ca_path
        DATABASE_URL = DATABASE_URL.replace(ca_path, clean_path)


# 过滤掉 pymysql 驱动不支持的 ssl_mode 参数，防止报错: got an unexpected keyword argument 'ssl_mode'
if "ssl_mode=" in DATABASE_URL:
    import re
    DATABASE_URL = re.sub(r"ssl_mode=[^&]+&?", "", DATABASE_URL)
    DATABASE_URL = DATABASE_URL.rstrip("&").rstrip("?")




# LLM（OpenAI 兼容接口）默认配置。实际运行配置优先通过管理界面写入数据库。
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4o")

# 粗筛关键词（用于先期过滤无关帖子，降低 LLM 调用 Token 消耗）
# 匹配帖子标题、标签和正文摘要
FILTER_KEYWORDS = [
    "claude", "codex", "gpt", "gemini", "llama", "deepseek", "qwen",
    "中转", "公益", "免费", "key", "api", "额度", "分享", 
    "注册", "站长", "挂了", "跑路", "福利", "可用", "白嫖"
]

# 每次抓取的最大帖子条数
CRAWL_LIMIT = 50
