import sys
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
    
    # 3. 遍历帖子进行增量处理
    for idx, topic in enumerate(raw_topics, 1):
        topic_id = topic["id"]
        title = topic["title"]
        
        # 进度百分比从 20% 渐进到 95%
        percent = int(20 + (idx / total) * 75)
        
        # 检查是否已处理过
        if database.check_exists(topic_id):
            skipped_count += 1
            update_progress("syncing", percent, f"[{idx}/{total}] 帖子已存在，跳过: {title}")
            continue
            
        print(f"\n>>> 正在处理新帖子 [{idx}/{len(raw_topics)}]: {title}")
        update_progress("syncing", percent, f"[{idx}/{total}] 正在本地粗筛: {title}")
        
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
            print(" -> 本地粗筛判定为：不相关。已记录到数据库去重表中。")
            update_progress("syncing", percent, f"[{idx}/{total}] 粗筛未命中(判定无关): {title}")
            continue
            
        # 粗筛命中，调用 LLM 精细筛选
        update_progress("syncing", percent, f"[{idx}/{total}] 粗筛命中！正在请求 AI 进行语义精筛: {title}")
        llm_result = filter.llm_filter(
            title=topic["title"],
            tags=topic["tags"],
            excerpt=topic["excerpt"]
        )
        
        # 将 LLM 筛选结果合并进帖子数据
        topic.update(llm_result)
        
        # 插入数据库
        success = database.insert_topic(topic)
        if success:
            new_inserted_count += 1
            if topic["is_relevant"]:
                relevant_count += 1
                print(f" -> [LLM判定相关] 分类: {topic['category']}, 评分: {topic['value_score']} 分")
                print(f"    AI 摘要: {topic['summary']}")
                update_progress("syncing", percent, f"[{idx}/{total}] 🤖 AI判定相关 ({topic['category']}): {title}")
            else:
                print(" -> [LLM判定不相关] 已存入数据库去重")
                update_progress("syncing", percent, f"[{idx}/{total}] 🤖 AI判定无关: {title}")
        
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
        f"同步完成！本次扫描 {total} 条帖子（跳过已存在 {skipped_count} 条，新增入库 {new_inserted_count} 条，AI 筛选出相关贴 {relevant_count} 条）。"
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
