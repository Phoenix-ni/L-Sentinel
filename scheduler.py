import logging
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
import main

# 初始化日志输出
logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    level=logging.INFO
)
logger = logging.getLogger("Scheduler")

# 创建后台调度器，显式指定时区为东八区（Asia/Shanghai），防止部署到 UTC 服务器时时间偏差
scheduler = BackgroundScheduler(timezone="Asia/Shanghai")

def daily_crawl_job():
    """每日定时爬取与分类过滤的具体任务函数"""
    logger.info("⏱️ [定时任务开始] 正在触发每日 24 小时增量帖子数据收集...")
    try:
        main.run_pipeline(hours=24.0)
        logger.info("✅ [定时任务成功] 每日增量抓取及 AI 筛选流水线执行完毕！")
    except Exception as e:
        logger.error(f"❌ [定时任务失败] 任务运行期间遭遇异常: {e}")

def start_scheduler():
    """启动调度器并注册 Cron 定时任务"""
    if not scheduler.running:
        # 配置 Cron 触发器：每天早上 08:00 触发一次
        trigger = CronTrigger(hour=8, minute=0)
        scheduler.add_job(
            daily_crawl_job,
            trigger=trigger,
            id="daily_24h_crawl",
            name="每天早晨8点爬取过去24小时帖子",
            replace_existing=True
        )
        scheduler.start()
        logger.info("⏱️ [调度器已激活] 定时任务机制成功启动！(每天 08:00 自动执行，时区: Asia/Shanghai)")
    else:
        logger.warning("⏱️ [调度器警告] 调度器已经处于运行状态，无需重复启动。")

def shutdown_scheduler():
    """关闭调度器释放线程资源"""
    if scheduler.running:
        scheduler.shutdown()
        logger.info("⏱️ [调度器已关闭] 后台定时器已成功卸载。")
