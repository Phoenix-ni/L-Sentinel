import os
import sys
import logging
import uuid
import hashlib
from contextlib import asynccontextmanager
from fastapi import FastAPI, BackgroundTasks, Query, Header, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

import database
import scheduler
import main

# 内存活跃 Token 会话池
active_sessions = set()

def verify_admin(authorization: str = Header(default=None)):
    """鉴权拦截依赖项：验证 Authorization 请求头中的 Bearer Token"""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="请以管理员身份登录后操作")
        
    token = authorization.split(" ")[1]
    if token not in active_sessions:
        raise HTTPException(status_code=401, detail="登录会话已过期，请重新登录")
    return token

# 设置日志格式
logger = logging.getLogger("API")

# 1. 采用 Lifespan 管理应用的启动和关闭生命周期
@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动前执行：初始化数据库表，启动后台定时调度器
    logger.info("🚀 正在启动 FastAPI 后端服务...")
    database.init_db()
    scheduler.start_scheduler()
    yield
    # 关闭前执行：关闭定时器释放线程
    logger.info("🛑 正在关闭 FastAPI 后端服务...")
    scheduler.shutdown_scheduler()

# 2. 实例化 FastAPI
app = FastAPI(
    title="linux.do 信息监控后端 API",
    lifespan=lifespan
)

# 3. 配置跨域中间件 (CORS)，方便本地 Vue 独立运行开发时的 API 调用
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

import re

def check_password_strength(password: str):
    """强密码校验：包含大小写字母、数字、特殊字符且至少8位"""
    if len(password) < 8:
        raise HTTPException(status_code=400, detail="密码长度必须至少为 8 位字符")
    if not re.search(r"[A-Z]", password):
        raise HTTPException(status_code=400, detail="密码必须包含至少一个大写字母 (A-Z)")
    if not re.search(r"[a-z]", password):
        raise HTTPException(status_code=400, detail="密码必须包含至少一个小写字母 (a-z)")
    if not re.search(r"[0-9]", password):
        raise HTTPException(status_code=400, detail="密码必须包含至少一个阿拉伯数字 (0-9)")
    if not re.search(r"[!@#$%^&*()_+={}\[\]:;\"'<>,.?/|\\~`-]", password):
        raise HTTPException(status_code=400, detail="密码必须包含至少一个特殊字符 (例如 @、#、$、% 等)")

# 4. 请求与响应模型
class SyncRequest(BaseModel):
    hours: float = 1.0

class LoginRequest(BaseModel):
    password: str

class SetupRequest(BaseModel):
    provider: str
    api_key: str
    base_url: str
    model: str
    new_password: str

class ConfigUpdateRequest(BaseModel):
    provider: str
    api_key: str
    base_url: str
    model: str
    new_password: str = None

# 5. 定义 REST API 路由

@app.get("/api/admin/setup-status")
def get_setup_status():
    """获取当前系统是否已完成初始化密码修改和 API 配置（公开只读端点，无需 Token）"""
    api_key = database.get_config("llm_api_key", "")
    db_hash = database.get_config("admin_password_hash")
    default_hash = hashlib.sha256(b"admin123").hexdigest()
    
    # 只要使用的是默认密码，或者 API 密钥为空，就判定为未初始化
    is_password_changed = db_hash != default_hash
    is_api_configured = bool(api_key and api_key.strip() and "*" not in api_key)
    
    return {
        "status": "success",
        "is_password_changed": is_password_changed,
        "is_api_configured": is_api_configured,
        "is_setup_completed": is_password_changed and is_api_configured
    }

@app.post("/api/admin/setup")
def admin_setup(req: SetupRequest, token: str = Depends(verify_admin)):
    """首次登录强制配置与密码修改接口 (需登录 Token 校验)"""
    # 1. 后端强校验新密码复杂度
    check_password_strength(req.new_password)
    
    # 2. 校验 API Key 不能为空
    if not req.api_key or not req.api_key.strip():
        raise HTTPException(status_code=400, detail="API 密钥不能为空，请填写有效 Key")
        
    # 3. 校验新密码不能为初始密码
    if req.new_password == "admin123":
        raise HTTPException(status_code=400, detail="新密码不能为系统初始默认密码！")
        
    # 4. 写入新密码哈希
    new_hash = hashlib.sha256(req.new_password.encode("utf-8")).hexdigest()
    database.set_config("admin_password_hash", new_hash)
    
    # 5. 写入配置信息
    database.set_config("llm_provider", req.provider)
    database.set_config("llm_api_key", req.api_key)
    database.set_config("llm_base_url", req.base_url)
    database.set_config("llm_model", req.model)
    
    logger.info("🔑 管理员已顺利完成系统首访初始化！")
    return {
        "status": "success",
        "message": "初始化配置完成！已成功开启系统主看板访问权限。"
    }

@app.post("/api/admin/login")
def admin_login(req: LoginRequest):
    """管理员登录接口"""
    pwd_hash = hashlib.sha256(req.password.encode("utf-8")).hexdigest()
    db_hash = database.get_config("admin_password_hash")
    
    if pwd_hash != db_hash:
        raise HTTPException(status_code=400, detail="管理员密码校验未通过，请重试")
        
    token = uuid.uuid4().hex
    active_sessions.add(token)
    logger.info("🔑 管理员已成功登录，授权 Token 写入会话池")
    return {
        "status": "success",
        "token": token,
        "message": "管理员身份认证通过！"
    }

@app.post("/api/admin/logout")
def admin_logout(token: str = Depends(verify_admin)):
    """管理员登出接口"""
    if token in active_sessions:
        active_sessions.remove(token)
    logger.info("🔒 管理员已登出并作废 Token")
    return {
        "status": "success",
        "message": "已成功退出管理员会话"
    }

@app.get("/api/admin/auth-status")
def get_auth_status(token: str = Depends(verify_admin)):
    """获取当前登录状态接口"""
    return {
        "status": "success",
        "authorized": True
    }

@app.get("/api/admin/config")
def get_admin_config(token: str = Depends(verify_admin)):
    """获取当前的 LLM 配置接口（对 API Key 敏感信息脱敏）"""
    provider = database.get_config("llm_provider", "openai")
    api_key = database.get_config("llm_api_key", "")
    base_url = database.get_config("llm_base_url", "")
    model = database.get_config("llm_model", "")
    
    masked_key = ""
    if api_key:
        if len(api_key) > 8:
            masked_key = api_key[:4] + "*" * (len(api_key) - 8) + api_key[-4:]
        else:
            masked_key = "********"
            
    return {
        "status": "success",
        "data": {
            "provider": provider,
            "api_key": masked_key,
            "base_url": base_url,
            "model": model
        }
    }

@app.post("/api/admin/config")
def update_admin_config(req: ConfigUpdateRequest, token: str = Depends(verify_admin)):
    """更新当前的系统配置与修改密码接口"""
    # 校验：若是修改密码，需验证复杂度
    if req.new_password and req.new_password.strip():
        check_password_strength(req.new_password)
        new_hash = hashlib.sha256(req.new_password.encode("utf-8")).hexdigest()
        database.set_config("admin_password_hash", new_hash)
        logger.info("🔑 管理员已更新登录密码")

    database.set_config("llm_provider", req.provider)
    database.set_config("llm_base_url", req.base_url)
    database.set_config("llm_model", req.model)
    
    # 仅在输入了 API Key 且没有脱敏通配符 * 时进行更新
    if req.api_key and "*" not in req.api_key:
        database.set_config("llm_api_key", req.api_key)
        
    logger.info("⚙️ 管理员系统配置已成功保存到数据库")
    return {
        "status": "success",
        "message": "配置已成功保存！"
    }

@app.get("/api/topics")
def get_topics(relevant_only: bool = Query(default=True, description="是否仅获取相关的帖子")):
    """获取帖子列表接口 (只读端点无需鉴权)"""
    logger.info(f"📋 收到获取帖子列表请求，参数 relevant_only={relevant_only}")
    topics = database.fetch_all_topics(relevant_only=relevant_only)
    return {
        "status": "success",
        "count": len(topics),
        "data": topics
    }

@app.get("/api/stats")
def get_stats():
    """获取数据简报与大盘数据统计接口 (只读端点无需鉴权)"""
    logger.info("📊 收到获取统计数据请求")
    all_topics = database.fetch_all_topics(relevant_only=False)
    
    total_count = len(all_topics)
    relevant_total = sum(1 for t in all_topics if t["is_relevant"])
    high_value_total = sum(1 for t in all_topics if t["value_score"] >= 4)
    avg_score = sum(t["value_score"] for t in all_topics) / total_count if total_count > 0 else 0.0
    
    return {
        "status": "success",
        "data": {
            "total_scanned": total_count,
            "relevant_count": relevant_total,
            "high_value_count": high_value_total,
            "avg_value_score": round(avg_score, 2)
        }
    }

# 全局同步状态与进度管理器
sync_progress = {
    "status": "idle",       # "idle", "syncing", "completed", "error"
    "percent": 0,           # 0 到 100 的整数
    "message": "系统当前处于空闲状态"
}

is_syncing = False

def progress_callback(status: str, percent: int, message: str):
    """更新全局进度状态的回调函数"""
    global sync_progress
    sync_progress.update({
        "status": status,
        "percent": percent,
        "message": message
    })

def run_sync_in_background(hours: float):
    """后台运行数据抓取的逻辑"""
    global is_syncing
    try:
        main.run_pipeline(hours=hours, progress_callback=progress_callback)
    except Exception as e:
        logger.exception("❌ 后台同步流水线抛出异常！")
        progress_callback("error", 100, f"同步失败：{str(e)}")
    finally:
        is_syncing = False

@app.get("/api/sync/progress")
def get_sync_progress():
    """获取当前后台同步任务进度接口"""
    global sync_progress
    return sync_progress

@app.post("/api/sync")
def trigger_sync(req: SyncRequest, background_tasks: BackgroundTasks, token: str = Depends(verify_admin)):
    """手动触发数据同步接口 (需管理员鉴权，异步后台运行，杜绝 HTTP 挂起超时)"""
    global is_syncing
    if is_syncing:
        return {
            "status": "error",
            "message": "同步任务已经在后台运行中，请勿重复提交。"
        }
    
    is_syncing = True
    logger.info(f"🔄 手动触发同步任务请求: 收集过去 {req.hours} 小时内的数据")
    
    # 触发时立即重置状态为 0%
    progress_callback("syncing", 0, "正在连接并拉取同步请求...")
    
    # 挂载后台任务
    background_tasks.add_task(run_sync_in_background, req.hours)
    
    return {
        "status": "success",
        "message": "同步指令已成功下发，后台任务已启动。"
    }

# 6. 防御性静态文件挂载：将 Vue 3 的编译目录 dist 托管在根路径 / 
# 为了不遮挡 API 路由，必须在所有路由声明之后挂载静态路由
dist_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dist")
if os.path.exists(dist_dir):
    app.mount("/", StaticFiles(directory=dist_dir, html=True), name="static")
    logger.info(f"📂 [前端挂载] 已成功挂载前端静态静态资源目录: {dist_dir}")
else:
    logger.warning(f"⚠️ [前端警告] 未找到静态目录: {dist_dir}。本地独立调试后端 API 中。")

if __name__ == "__main__":
    import uvicorn
    # 本地直接启动服务测试，默认端口 8501
    port = int(os.getenv("PORT", 8501))
    uvicorn.run("server:app", host="0.0.0.0", port=port, reload=True)
