import sys
from datetime import datetime, timezone

# 优先尝试导入 curl_cffi 来绕过 Cloudflare 5秒盾；如果未安装，则回退到标准 requests 库
try:
    from curl_cffi import requests
    HAS_CURL_CFFI = True
except ImportError:
    import requests
    HAS_CURL_CFFI = False

# 本地代理配置。如果使用全局代理（如 Clash TUN）遇到网络问题，可在此处指定代理地址
# 例如：PROXIES = {"http": "http://127.0.0.1:7890", "https": "http://127.0.0.1:7890"}
PROXIES = None


def fetch_latest_topics(hours=None, limit=10, proxies=PROXIES):
    """
    获取 linux.do 最新的帖子
    :param hours: 过滤过去多少小时内的帖子（例如 1 或 24）。若为 None，则按 limit 数量仅获取第一页
    :param limit: 获取的帖子条数，仅在 hours 为 None 时生效
    :param proxies: 代理配置
    :return: 帖子列表，每个元素包含 id, title, link, excerpt, tags, created_at_raw
    """
    # 模拟常见浏览器的请求头
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Referer": "https://linux.do/",
        "X-Requested-With": "XMLHttpRequest"
    }

    results = []
    page = 0
    max_pages = 15  # 防御性限制最大请求页数以防异常无限循环
    should_stop = False
    
    # 获取当前 UTC 时间
    now_utc = datetime.now(timezone.utc)

    # 封装一个单页抓取辅助函数
    def fetch_page(page_num):
        url = f"https://linux.do/latest.json?page={page_num}"
        print(f"正在尝试请求第 {page_num} 页: {url} ...")
        if HAS_CURL_CFFI:
            try:
                response = requests.get(url, headers=headers, impersonate="chrome120", timeout=15, proxies=proxies)  # type: ignore
                return response
            except Exception as e:
                err_msg = str(e)
                print(f"[错误] 使用 curl_cffi 请求第 {page_num} 页失败: {e}", file=sys.stderr)
                if "unrecognized name" in err_msg or "UNRECOGNIZED_NAME" in err_msg:
                    print("\n[排查提示] 检测到 SSL 'unrecognized name' 错误！\n"
                          "这通常是因为您启用了全局代理软件（如 Clash TUN/Fake-IP 模式），但当前选中的代理节点或路由策略无法正确连接到 linux.do。\n"
                          "建议解决方法：\n"
                          "  1. 尝试在代理软件中切换其他节点（例如香港、日本、新加坡等）。\n"
                          "  2. 将 linux.do 域名加入到代理软件的直连（DIRECT）名单中。\n"
                          "  3. 在 crawler.py 中配置本地代理端口。\n", file=sys.stderr)
                return None
        else:
            try:
                response = requests.get(url, headers=headers, timeout=15, proxies=proxies)
                return response
            except Exception as e:
                print(f"[错误] 使用 requests 请求第 {page_num} 页失败: {e}", file=sys.stderr)
                return None

    while page < max_pages:
        response = fetch_page(page)
        if not response:
            break

        if response.status_code == 403:
            print("[失败] 遭遇 Cloudflare 403 拦截。建议安装或确认 curl_cffi 配置是否正确。", file=sys.stderr)
            break
        elif response.status_code == 429:
            print("[限流提示] 触发了论坛的访问频率限制 (HTTP 429)。为了避免 IP 被封禁，我们将使用目前已成功抓取到的帖子数据进行后续处理。", file=sys.stderr)
            break
        elif response.status_code != 200:
            print(f"[失败] 请求返回异常状态码: {response.status_code}", file=sys.stderr)
            break

        try:
            data = response.json()
        except Exception as e:
            print(f"[错误] 解析 JSON 数据失败: {e}", file=sys.stderr)
            break

        topics = data.get("topic_list", {}).get("topics", [])
        if not topics:
            print(f"[提示] 第 {page} 页没有更多帖子。")
            break

        # 遍历页内帖子
        for topic in topics:
            # 提取字段
            topic_id = topic.get("id")
            title = topic.get("title")
            excerpt = topic.get("excerpt", "")
            created_at_raw = topic.get("created_at")
            
            # 解析 tags
            raw_tags = topic.get("tags", [])
            tags = []
            if isinstance(raw_tags, list):
                for tag in raw_tags:
                    if isinstance(tag, str):
                        tags.append(tag)
                    elif isinstance(tag, dict):
                        tag_name = tag.get("name") or tag.get("id") or str(tag)
                        tags.append(str(tag_name))
                    else:
                        tags.append(str(tag))

            link = f"https://linux.do/t/topic/{topic_id}"

            # 时间判断逻辑
            if hours is not None:
                created_at_raw = topic.get("created_at")
                bumped_at_raw = topic.get("bumped_at") or created_at_raw
                
                if not bumped_at_raw:
                    continue
                
                try:
                    bumped_time = datetime.fromisoformat(bumped_at_raw.replace("Z", "+00:00"))
                except Exception as e:
                    print(f"[警告] 解析最后活跃时间失败 (bumped_at={bumped_at_raw}): {e}")
                    continue

                # 计算最后活跃时间的小时差
                bump_diff_hours = (now_utc - bumped_time).total_seconds() / 3600.0

                is_pinned = topic.get("pinned", False) or topic.get("pinned_globally", False)
                
                # 1. 只有最后活跃时间在指定时间范围内的帖子才被收集
                if bump_diff_hours <= hours:
                    results.append({
                        "id": topic_id,
                        "title": title,
                        "link": link,
                        "excerpt": excerpt,
                        "tags": tags,
                        "created_at_raw": bumped_at_raw  # 传递给上层并存入数据库的是最后活跃时间
                    })
                
                # 2. 用最后活动时间（Bumped At）作为提前停止爬取的唯一判断依据
                if is_pinned:
                    print(f"[跳过置顶] 帖子 '{title}' 为置顶帖，不作为活动时间截止依据。")
                elif bump_diff_hours > hours:
                    print(f"[过滤停止] 常规帖子 '{title}' 的最后活动时间为 {bump_diff_hours:.2f} 小时前，已超出 {hours} 小时活跃范围。停止爬取。")
                    should_stop = True
                    break
            else:
                # 若 hours 为 None，则只按原始 limit 数量仅截取第一页即可
                created_at_raw = topic.get("created_at")
                bumped_at_raw = topic.get("bumped_at") or created_at_raw
                results.append({
                    "id": topic_id,
                    "title": title,
                    "link": link,
                    "excerpt": excerpt,
                    "tags": tags,
                    "created_at_raw": bumped_at_raw
                })
                if len(results) >= limit:
                    should_stop = True
                    break

        if should_stop:
            break

        page += 1
        # 翻页加个小延时以示友好，增加为 2 秒以降低被 429 的风险
        import time
        time.sleep(2.0)

    return results


if __name__ == "__main__":
    topics = fetch_latest_topics(limit=10)
    
    if topics:
        print(f"\n成功获取到前 {len(topics)} 条最新帖子：")
        print("-" * 60)
        for idx, t in enumerate(topics, 1):
            print(f"[{idx}] {t['title']}")
            print(f"    链接: {t['link']}")
            if t['tags']:
                print(f"    标签: {', '.join(t['tags'])}")
            if t['excerpt']:
                # 限制摘要显示长度
                clean_excerpt = t['excerpt'].replace("\n", " ").strip()
                print(f"    摘要: {clean_excerpt[:80]}...")
            print("-" * 60)
    else:
        print("\n抓取失败，未能获取到任何帖子。")
