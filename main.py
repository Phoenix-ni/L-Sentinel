import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from config import CRAWL_LIMIT
import database
import crawler
import filter

def run_pipeline(hours=None, progress_callback=None):
    """运行整个帖子抓取、过滤与入库的流水线"""
    print("=" * 60)
    print(" 开始运行 linux.do 中转与公益站信息收集系统 ")
    print("=" * 60)
    
    def update_progress(status, percent, message):
        if progress_callback:
            progress_callback(status, percent, message)

    update_progress("syncing", 5, "正在初始化数据库并准备请求论坛数据...")
    
    # 1. 初始化数据库
    database.init_db()
    
    # 动态验证 API 密钥是否为空
    api_key = database.get_config("llm_api_key", "")
    if not api_key or not api_key.strip():
        print("[错误] 未检测到有效的 LLM API 密钥，同步终止。请以管理员登录配置 API Key。")
        update_progress("error", 100, "同步失败：未配置有效的 API 密钥，请先登录管理员页面配置！")
        return
        
    update_progress("syncing", 10, "正在连接 L 站 API 爬取最新主题列表中...")
    
    # 2. 从论坛爬取最新帖子
    raw_topics = crawler.fetch_latest_topics(hours=hours, limit=CRAWL_LIMIT)
    if not raw_topics:
        print("[错误] 未能成功获取到任何论坛帖子，流水线终止。")
        update_progress("error", 100, "抓取失败：未能获取到任何帖子，可能触发了频控或网络代理不可达。")
        return
        
    total = len(raw_topics)
    print(f"\n[爬取完成] 成功获取到 {total} 条最新帖子。")
    print("正在进行增量去重与筛选过滤...")
    print("-" * 60)
    
    update_progress("syncing", 20, f"成功获取到 {total} 条最新帖子，开始进行增量去重与 AI 智能筛选...")
    
    new_inserted_count = 0
    relevant_count = 0
    skipped_count = 0
    to_eval_topics = []
    
    # 3. 快速前置筛选（去重和本地粗筛，由于在本地且速度极快，直接串行过滤）
    for idx, topic in enumerate(raw_topics, 1):
        topic_id = topic["id"]
        title = topic["title"]
        
        # 检查是否已处理过
        if database.check_exists(topic_id):
            skipped_count += 1
            continue
            
        # 本地粗筛
        is_keyword_hit = filter.keyword_filter(
            title=topic["title"],
            tags=topic["tags"],
            excerpt=topic["excerpt"]
        )
        
        if not is_keyword_hit:
            # 粗筛不命中，直接以“不相关”状态存库，防止以后重复处理
            topic["is_relevant"] = False
            topic["category"] = "其他"
            topic["summary"] = "本地关键词粗筛未命中"
            topic["value_score"] = 0
            database.insert_topic(topic)
            new_inserted_count += 1
            print(f" -> 帖子 '{title}' 本地粗筛判定为：不相关。已直接去重存库。")
        else:
            # 粗筛命中，放入待大模型精筛队列
            to_eval_topics.append(topic)

    # 4. 并发调用大模型评估（使用线程池并发，并发数设为 8）
    eval_total = len(to_eval_topics)
    print(f"\n[初筛结束] 共有 {eval_total} 篇帖子命中了关键词，即将启动 AI 多线程并发研判...")
    
    # 定义线程共享锁和已处理计数
    lock = threading.Lock()
    processed_count = skipped_count + new_inserted_count # 已经处理完的帖子计数
    
    # 主动推一次中间进度
    initial_percent = int(20 + (processed_count / total) * 75) if total > 0 else 95
    update_progress("syncing", initial_percent, f"去重与粗筛完成。共 {eval_total} 篇需 AI 研判，正在启动多并发处理池...")

    def process_single_topic(topic):
        nonlocal processed_count, new_inserted_count, relevant_count
        
        title = topic["title"]
        
        # 调用大语言模型进行细筛（内部已内置 429 频控及超时重试）
        llm_result = filter.llm_filter(
            title=topic["title"],
            tags=topic["tags"],
            excerpt=topic["excerpt"]
        )
        
        topic.update(llm_result)
        
        # 写入数据库去重 (线程安全，使用独立的 Session)
        success = database.insert_topic(topic)
        
        with lock:
            processed_count += 1
            percent = int(20 + (processed_count / total) * 75) if total > 0 else 95
            
            if success:
                new_inserted_count += 1
                if topic["is_relevant"]:
                    relevant_count += 1
                    print(f" -> [AI判定相关] 分类: {topic['category']}, 评分: {topic['value_score']} 分 | 标题: {title}")
                    update_progress("syncing", percent, f"[{processed_count}/{total}] 🤖 AI判定相关 ({topic['category']}): {title}")
                else:
                    print(f" -> [AI判定无关] 已存入数据库去重 | 标题: {title}")
                    update_progress("syncing", percent, f"[{processed_count}/{total}] 🤖 AI判定无关: {title}")
            else:
                print(f" -> [数据库写入失败] 帖子 ID: {topic['id']} | 标题: {title}")
                update_progress("syncing", percent, f"[{processed_count}/{total}] 处理完毕(数据库写入失败): {title}")

    # 并发数设置在 5-10 之间，默认使用 8 线程
    MAX_WORKERS = 8
    
    if eval_total > 0:
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            # 开启并发 map
            executor.map(process_single_topic, to_eval_topics)
            
    # 5. 输出报告
    print("-" * 60)
    print(" 运行报告 ")
    print(f" - 本次扫描帖子数: {total} 条")
    print(f" - 历史已存在跳过: {skipped_count} 条")
    print(f" - 新增入库记录数: {new_inserted_count} 条")
    print(f" - 新增判定相关帖: {relevant_count} 条")
    print("=" * 60)
    
    update_progress(
        "completed", 
        100, 
        f"同步完成！本次共扫描 {total} 条帖子（跳过已存在 {skipped_count} 条，新增入库 {new_inserted_count} 条，AI 筛选出相关贴 {relevant_count} 条）。"
    )

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="linux.do 帖子抓取与 AI 筛选工具")
    parser.add_argument(
        "--hours", 
        type=float, 
        default=1.0, 
        help="抓取过去多少小时内的帖子 (例如 1.0 表示 1 小时，24.0 表示 24 小时)"
    )
    args = parser.parse_args()
    run_pipeline(hours=args.hours)
