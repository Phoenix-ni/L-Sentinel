# 📡 linux.do 中转与公益站监控系统

本系统是一套专为 `linux.do` 论坛打造的帖子增量爬取、去重与 AI 筛选监控系统。主要用于实时/定时抓取中转站、公益 API 运行、福利优惠等帖子信息，并通过大语言模型（LLM）进行智能语义过滤和分类打分。

前端采用 **Vue 3 + Vite** 构建，后端基于 **FastAPI + SQLAlchemy + APScheduler**，支持 SQLite 与 TiDB 双端无缝切换，并实现了一体化多阶段 Docker 容器化部署。

---

## 🛠️ 项目文件结构

```text
.
├── config.py             # 统一配置文件 (LLM Key、大盘粗筛词、数据库配置)
├── models.py             # SQLAlchemy ORM 实体建模 (Topic 映射)
├── database.py           # 数据库会话上下文管理及 CURD 封装 (去重与插入)
├── crawler.py            # 基于时序与防置顶干扰的 Discourse API 增量爬虫
├── filter.py             # 本地粗筛 (正则) + AI 智能精筛 (LongCat-2.0-Preview)
├── scheduler.py          # 定时调度模块 (APScheduler，每天 08:00 定时收集 24h 数据)
├── main.py               # 命令行模式流水线入口 (支持 --hours 运行时参)
├── server.py             # RESTful API 后端服务 (挂载静态 dist 目录并暴露进度轮询)
├── Dockerfile            # 生产级多阶段构建容器配置
├── requirements.txt      # 后端依赖声明
├── target.md             # 项目需求与设计指南 (备忘)
└── frontend/             # Vue 3 独立前端工程
    ├── src/
    │   ├── App.vue       # 深色玻璃态微光看板核心页面 (包含 Shimmer 进度条)
    │   └── main.js       # 前端渲染主入口
    ├── index.html        # 单页面承载 HTML5
    └── vite.config.js    # Vite 配置文件
```

---

## 🔐 双视图隔离、强密码校验与隐私安全

为了便于将项目安全发布至 GitHub 公开仓库，系统引入了严密的**双视图隔离与强制初始化向导**机制，防止任何敏感信息泄漏。

### 1. 🔒 顶级视图硬隔离流程
未登录或未完成初始配置的用户将**绝对无法访问任何帖子数据和大盘指标**，整个系统将被锁定在全屏登录或配置向导页面中：
1. **视图 1：全屏登录页**：系统启动后，首访仅展示居中的毛玻璃登录界面。请输入默认密码 `admin123` 进行登录。
2. **视图 2：系统初始化向导**：当检测到使用的是默认密码，或者 API 密钥为空时，页面将强制进入“初始化配置”向导。
   * **强制密码修改**：管理员必须设置高强度密码。密码必须**至少 8 位，且必须同时包含大写字母、小写字母、数字以及特殊字符**（例如 `@#$%^&*()` 等）。
   * **强制配置 API**：您必须配置 LLM 的协议提供商（支持 OpenAI 或 Anthropic 原生协议）、API Key、Base URL 以及模型名称。
3. **视图 3：系统主看板**：只有当上述两项全部保存成功后，系统才会重定向跳转至正常的帖子看板主页面。

### 2. 🛡️ 隐私安全保护 (零密钥残留)
* **代码去密钥化**：系统在 `database.py` 中初始化灌入数据库的默认 API 密钥已置为 **`""` (空值)**，去除任何敏感信息残留。您可以安全地将代码推送到公开 GitHub 仓库，任何访客在没有密码和手动配置的情况下均无法获取您的 LLM 额度。
* **接口权限双重校验**：不仅前端在表单输入时提供密码强度的实时验证打勾，后端 API（`/api/admin/setup` 及 `/api/admin/config`）也内置了正则表达式强校验。非管理员访问或非法同步请求（`/api/sync`）会被后端直接返回 `401 Unauthorized` 拦截。

---

## 🐳 本地 Docker 部署教程

### 1. 编译 Docker 镜像
在项目根目录下，执行以下命令进行本地多阶段打包编译：
```bash
docker build -t linuxdo-monitor .
```
*(已配置国内 NPM 与 Pip 镜像源，通常可在 1 分钟内急速完成编译缓存)*

### 2. 运行 Docker 容器 (推荐挂载本地持久化)
由于 Docker 容器销毁后内部数据会丢失，我们使用 `-v` 将本地的 SQLite 数据库 `data.db` 映射到容器中。

> [!IMPORTANT]
> 1. 为了兼容 Bash 与 Fish 终端，我们使用 `$PWD` 获取绝对路径（避免使用 Fish 特有的 `(pwd)` 导致 Bash 报错）。
> 2. Docker 对容器名有严格限制，请避免使用中文字符，统一命名为 `linuxdo-monitor`。

运行以下命令：
```bash
# 创建一个空白数据库文件，防止 Docker 误将其挂载为目录
touch data.db

# 启动容器
docker run -d \
  -p 8501:8501 \
  --name linuxdo-monitor \
  -v "$PWD/data.db":/app/data.db \
  linuxdo-monitor
```

### 3. 日志与生命周期管理
* **查看容器实时运行日志（观察每日定时调度或爬取详情）**：
  ```bash
  docker logs -f linuxdo-monitor
  ```
* **停止与启动容器**：
  ```bash
  docker stop linuxdo-monitor
  docker start linuxdo-monitor
  ```
* **彻底删除容器**：
  ```bash
  docker rm -f linuxdo-monitor
  ```

---

## ☁️ 云端 Render + TiDB Serverless 部署教程

本系统天然适配云端一键式部署。为了让数据获得生产级持久化，并保证容器 24 小时在线不休眠，我们可以采用 **Render 免费托管** + **TiDB Cloud 免费云数据库** + **UptimeRobot 免费测活保活** 的黄金组合方案。

### 第一步：创建 TiDB Serverless 数据库 (免费)
1. 访问 [PingCAP / TiDB Cloud](https://pingcap.com/products/tidb-id) 注册一个免费的 **TiDB Serverless** 实例。
2. 创建实例后，进入控制台，在 **Connect** 面板选择 **SQLAlchemy** 或是普通的 **MySQL** 连接方式，复制您的连接字符串，其格式一般为：
   `mysql+pymysql://<USER>:<PASSWORD>@<HOST>:<PORT>/<DB_NAME>?ssl_verify_cert=true&ssl_ca=/etc/ssl/certs/ca-certificates.crt`
3. 记下这个字符串，稍后需要将其填入 Render 的环境变量中。

### 第二步：将代码推送至 GitHub
将您本地修剪干净的仓库代码推送至您的私有或公开 GitHub 仓库。

### 第三步：在 Render 部署服务 (Web Service)
1. 登录 [Render](https://render.com) 控制台，点击 **New +** 并选择 **Web Service**。
2. 关联您刚刚上传的 GitHub 仓库。
3. **关键配置参数**：
   * **Language**：选择 **Docker**（Render 将会自动识别根目录的 `Dockerfile`，并执行多阶段云端编译，无需任何额外配置）。
   * **Instance Type**：选择 **Free**（完全免费）。
4. **配置环境变量 (Environment Variables)**：
   点击 Environment 选项卡，添加以下变量：
   * `DATABASE_URL`：填入上面第一步复制的 TiDB 连接字符串。*(程序只要检测到该变量，就会自动无缝切换至 TiDB 集群运行)*
   * `ADMIN_PASSWORD`：设置您的管理员初始密码。*(系统首次启动时会自动将其哈希后存入数据库；如果后续需要重置密码，直接修改此环境变量即可)*
   * `OPENAI_API_KEY`：填入您的 LLM API 密钥 *(例如默认的 `ak_2Iz7Ww4KH2440E19yI3n69RN0er2I`)*。
   * `OPENAI_BASE_URL`：填入大模型的中转地址 *(例如 `https://api.longcat.chat/openai`)*。
5. 点击 **Deploy Web Service** 触发构建。Render 会全自动拉取代码并部署在公网。

---

## ⏰ 云端保活与每日定时 (UptimeRobot)

> [!WARNING]
> **Render 免费版休眠痛点**：
> Render 的免费容器（Free tier）如果在 **15 分钟内无任何 HTTP 请求** 传入，会自动进入**休眠状态 (Spin down)**。
> 一旦容器休眠，后台线程 `APScheduler` 也随之冻结。这会导致每天早晨 8 点的定时抓取任务无法按时触发，必须由人工重新点击网页才能唤醒。

### 💡 解决方案：使用 UptimeRobot 外部测活保活
我们可以使用免费的 UptimeRobot 每隔 5 分钟向 Render 服务发送一次请求，迫使其**永久保持活跃、绝不休眠**，从而让定时 Cron 任务完美工作：

1. 登录 Render 控制台，复制您服务的公网访问域名（例如：`https://linuxdo-monitor.onrender.com`）。
2. 注册并登录 [UptimeRobot](https://uptimerobot.com) 官网（完全免费）。
3. 点击 **Add New Monitor** 添加一个新监控项：
   * **Monitor Type**：选择 **HTTP(s)**。
   * **Friendly Name**：起名为 `L站监控服务保活`。
   * **URL (or IP)**：填入您的公网接口地址，推荐使用大盘统计的只读端点：
     `https://<YOUR-RENDER-SUBDOMAIN>.onrender.com/api/stats`
   * **Monitoring Interval**：选择 **Every 5 minutes** (每 5 分钟 Ping 一次)。
4. 保存监控。UptimeRobot 将持续监控并访问您的服务，容器将**永久保持唤醒状态**，您的 APScheduler 每日早 8 点定时同步便可在后台稳健执行！
