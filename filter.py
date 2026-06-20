import re
import json
import sys
from config import FILTER_KEYWORDS
import database

def keyword_filter(title, tags, excerpt):
    """
    本地关键词粗筛（不区分大小写）
    :param title: 帖子标题
    :param tags: 帖子标签列表
    :param excerpt: 帖子摘要
    :return: True 表示命中关键词（需要进一步LLM细筛），False 表示未命中（判定为不相关）
    """
    if not title:
        return False
        
    # 合并为大文本进行匹配
    tags_text = " ".join(tags) if isinstance(tags, list) else str(tags)
    content_to_check = f"{title} {tags_text} {excerpt}".lower()
    
    # 逐个检查关键词是否包含在内容中
    for keyword in FILTER_KEYWORDS:
        if keyword.lower() in content_to_check:
            print(f"[粗筛命中] 帖子 '{title}' 命中了关键词: '{keyword}'")
            return True
            
    return False

def llm_filter(title, tags, excerpt):
    """
    使用 LLM 精细筛选帖子，并获取结构化分类结果 (支持从数据库动态读取配置及 OpenAI / Anthropic 双协议切换)
    :param title: 帖子标题
    :param tags: 帖子标签列表
    :param excerpt: 帖子摘要
    :return: 包含 is_relevant, category, summary, value_score 的字典
    """
    tags_text = ", ".join(tags) if isinstance(tags, list) else str(tags)
    
    # 1. 动态加载最新 LLM 配置
    provider = database.get_config("llm_provider", "openai")
    api_key = database.get_config("llm_api_key", "")
    base_url = database.get_config("llm_base_url", "")
    model = database.get_config("llm_model", "")
    
    # 构建 Prompt
    system_prompt = (
        "你是一个专业的智能论坛信息分析助手。你的任务是分析 linux.do 论坛的一篇帖子的内容，"
        "并准确判定该帖子是否与“中转站、公益 API、免费 Claude/GPT/Gemini/Codex、API 额度发放、公益站运行状态（例如挂了、跑路、白嫖新站上线）”相关。\n\n"
        "你必须输出且仅输出以下格式的 JSON，不要包含任何多余解释或说明，不要写 markdown 块代码：\n"
        "{\n"
        "  \"is_relevant\": true/false,\n"
        "  \"category\": \"公益API\" / \"中转服务\" / \"服务状态变更\" / \"福利优惠\" / \"其他\",\n"
        "  \"summary\": \"30字内的一句话摘要\",\n"
        "  \"value_score\": 1-5 的整数评分(5表示最具价值的福利或最大状况，不相关则为1)\n"
        "}"
    )
    
    user_content = f"帖子标题：{title}\n帖子标签：{tags_text}\n内容摘要：{excerpt}"
    
    print(f"[LLM精筛] [{provider.upper()}协议] 正在评估帖子: '{title}' (模型: {model}) ...")
    
    try:
        raw_result = ""
        
        # 2. 分协议通道执行请求
        if provider == "anthropic":
            import requests
            headers = {
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json"
            }
            # 如果是中转地址，使用中转的 url；如果是空，走官方 Anthropic 端点
            url = base_url if base_url else "https://api.anthropic.com"
            if not url.endswith("/v1/messages") and not url.endswith("/messages"):
                url = url.rstrip("/") + "/v1/messages" if "/v1" not in url else url.rstrip("/") + "/messages"
                
            data = {
                "model": model,
                "max_tokens": 500,
                "messages": [
                    {"role": "user", "content": f"{system_prompt}\n\n{user_content}"}
                ]
            }
            
            response = requests.post(url, headers=headers, json=data, timeout=20)
            response.raise_for_status()
            resp_json = response.json()
            raw_result = resp_json["content"][0]["text"].strip()
        else:
            # 默认使用 OpenAI 兼容协议
            from openai import OpenAI
            client = OpenAI(api_key=api_key, base_url=base_url)
            
            # 部分大模型可能不支持 json_object 模式，做自适应 fallback
            response_format = None
            if "gemini" not in model.lower() and "claude" not in model.lower():
                response_format = {"type": "json_object"}
                
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_content}
                ],
                response_format=response_format,
                timeout=20
            )
            raw_result = response.choices[0].message.content.strip()
            
        # 3. 鲁棒性 JSON 正则提取与解析
        # 查找匹配第一个出现的大括号 {...} 包裹的内容，免受 ```json 包裹和其它解释杂音的影响
        json_match = re.search(r"(\{.*\})", raw_result, re.DOTALL)
        if json_match:
            raw_result = json_match.group(1)
            
        result_json = json.loads(raw_result)
        
        # 字段安全校验与清洗
        return {
            "is_relevant": bool(result_json.get("is_relevant", False)),
            "category": str(result_json.get("category", "其他")),
            "summary": str(result_json.get("summary", "无摘要")),
            "value_score": int(result_json.get("value_score", 1))
        }
        
    except Exception as e:
        print(f"[LLM错误] 动态通道调用/解析失败: {e}", file=sys.stderr)
        # 容错降级逻辑
        return {
            "is_relevant": True,
            "category": "待人工审核",
            "summary": f"接口超时或解析错误: {str(e)[:20]}，需手动核对",
            "value_score": 3
        }

if __name__ == "__main__":
    # 本地模块独立测试
    test_title = "【上新】Baby 纯血 ccmax 中转站端午福利，佬友 10 刀额度体验"
    test_tags = ["高级推广", "人工智能"]
    test_excerpt = "给大家分享一个纯血的中转站，端午节做活动，新注册账号送 10 刀额度，支持 claude-3-5 等模型..."
    
    # 1. 粗筛测试
    is_hit = keyword_filter(test_title, test_tags, test_excerpt)
    print(f"本地粗筛结果: {is_hit}")
    
    # 2. 精筛测试
    if is_hit:
        # LLM 鉴于 API 密钥需要真实调用，在此处可直观预览
        result = llm_filter(test_title, test_tags, test_excerpt)
        print("LLM 细筛结果:", json.dumps(result, ensure_ascii=False, indent=2))
