<template>
  <!-- 视图 1：全屏登录页 -->
  <div v-if="currentView === 'login'" class="fullscreen-container">
    <div class="login-card-main">
      <div class="login-card-header">
        <span class="icon">📡</span>
        <h2>linux.do 监控系统登录</h2>
      </div>
      <div class="login-card-body">
        <p class="intro-text">首次运行请输入系统初始密码 <code>admin123</code> 登录后进行安全初始化配置。</p>
        <div class="filter-group">
          <input 
            type="password" 
            v-model="adminPassword" 
            placeholder="请输入登录密码..." 
            class="form-input"
            @keyup.enter="handleLogin"
          />
        </div>
        <button class="btn btn-login-submit" @click="handleLogin">
          🔓 验证并登录控制台
        </button>
      </div>
    </div>
  </div>

  <!-- 视图 2：系统初始化引导向导页 -->
  <div v-else-if="currentView === 'setup'" class="fullscreen-container">
    <div class="setup-card-main">
      <div class="setup-card-header">
        <h3>⚙️ 系统安全初始化向导</h3>
        <p class="subtitle">您当前仍在使用初始密码或未配置 API，必须完成以下配置才能解锁主监控看板。</p>
      </div>
      
      <div class="setup-card-body">
        <!-- 密码修改与强度指示 -->
        <div class="setup-section">
          <h4>1. 修改管理员登录密码</h4>
          <div class="filter-group">
            <label class="filter-label">设置新密码</label>
            <input 
              type="password" 
              v-model="setupNewPassword" 
              placeholder="请输入高强度新密码" 
              class="form-input"
            />
          </div>
          
          <!-- 密码强度前端动态提示 -->
          <div class="password-strength-checker">
            <div class="checker-item" :class="{ pass: passwordCheck.length }">
              <span class="checker-bullet">✔</span> 长度至少 8 位
            </div>
            <div class="checker-item" :class="{ pass: passwordCheck.uppercase }">
              <span class="checker-bullet">✔</span> 包含大写字母 (A-Z)
            </div>
            <div class="checker-item" :class="{ pass: passwordCheck.lowercase }">
              <span class="checker-bullet">✔</span> 包含小写字母 (a-z)
            </div>
            <div class="checker-item" :class="{ pass: passwordCheck.number }">
              <span class="checker-bullet">✔</span> 包含数字 (0-9)
            </div>
            <div class="checker-item" :class="{ pass: passwordCheck.special }">
              <span class="checker-bullet">✔</span> 包含特殊字符 (如 @#%^&* 等)
            </div>
          </div>
        </div>
        
        <hr class="setup-divider" />
        
        <!-- API 配置 -->
        <div class="setup-section">
          <h4>2. 配置大模型 API (支持 OpenAI / Anthropic)</h4>
          <p class="setup-notice">⚠️ 声明：本系统目前仅支持 OpenAI 和 Anthropic (Claude) 原生格式规范。</p>
          
          <div class="filter-group">
            <label class="filter-label">API 协议格式</label>
            <div class="provider-selector">
              <button 
                class="provider-tab" 
                :class="{ active: setupProvider === 'openai' }"
                @click="setupProvider = 'openai'"
              >OpenAI 协议</button>
              <button 
                class="provider-tab" 
                :class="{ active: setupProvider === 'anthropic' }"
                @click="setupProvider = 'anthropic'"
              >Anthropic 协议</button>
            </div>
          </div>
          
          <div class="filter-group">
            <label class="filter-label">API Key</label>
            <input 
              type="password" 
              v-model="setupApiKey" 
              placeholder="请输入 API 密钥 (不可泄露)" 
              class="form-input"
            />
          </div>
          
          <div class="filter-group">
            <label class="filter-label">Base URL (API 终结点)</label>
            <input 
              type="text" 
              v-model="setupBaseUrl" 
              :placeholder="setupProvider === 'openai' ? '默认: https://api.openai.com/v1' : '默认: https://api.anthropic.com/v1'" 
              class="form-input"
            />
          </div>
          
          <div class="filter-group">
            <label class="filter-label">LLM 模型名称</label>
            <input 
              type="text" 
              v-model="setupModel" 
              placeholder="例如: gpt-4o 或 claude-3-5-sonnet" 
              class="form-input"
            />
          </div>
        </div>
        
        <button 
          class="btn btn-setup-submit" 
          :disabled="!isSetupFormValid"
          @click="handleSetupSubmit"
        >
          💾 保存配置并进入主页
        </button>
        
        <p v-if="setupError" class="setup-error-msg">⚠️ {{ setupError }}</p>
      </div>
    </div>
  </div>

  <!-- 视图 3：监控看板主页面 -->
  <div v-else class="app-container">
    <!-- 侧边栏 -->
    <aside class="sidebar">
      <div class="sidebar-header">
        <span class="icon">📡</span>
        <h2>监控控制台</h2>
      </div>
      <hr class="divider" />

      <!-- 访问控制与系统配置 -->
      <section class="sidebar-section">
        <div class="admin-header-row">
          <h3>⚙️ 系统配置</h3>
          <button class="btn-logout" @click="handleLogout">安全退出</button>
        </div>
        
        <!-- 已登录：展示配置修改表单 -->
        <div class="admin-config-panel">
          <div class="filter-group">
            <label class="filter-label">API 协议格式</label>
            <div class="provider-selector">
              <button 
                class="provider-tab" 
                :class="{ active: configProvider === 'openai' }"
                @click="configProvider = 'openai'"
              >OpenAI</button>
              <button 
                class="provider-tab" 
                :class="{ active: configProvider === 'anthropic' }"
                @click="configProvider = 'anthropic'"
              >Anthropic</button>
            </div>
            <p class="provider-tip-text">
              {{ configProvider === 'openai' ? '通过 OpenAI 兼容协议发起大模型精筛评估' : '⚠️ 注意：当前采用 Anthropic 原生消息报文规范' }}
            </p>
          </div>
          
          <div class="filter-group">
            <label class="filter-label">API Key</label>
            <input 
              type="password" 
              v-model="configApiKey" 
              placeholder="请输入 API 密钥 (已加密保护)" 
              class="form-input text-small"
            />
          </div>
          
          <div class="filter-group">
            <label class="filter-label">Base URL (API 终结点)</label>
            <input 
              type="text" 
              v-model="configBaseUrl" 
              :placeholder="configProvider === 'openai' ? '默认: https://api.openai.com/v1' : '默认: https://api.anthropic.com/v1'" 
              class="form-input text-small"
            />
          </div>
          
          <div class="filter-group">
            <label class="filter-label">LLM 模型名称</label>
            <input 
              type="text" 
              v-model="configModel" 
              placeholder="例如: gpt-4o 或 claude-3-5-sonnet" 
              class="form-input text-small"
            />
          </div>
          
          <div class="filter-group">
            <label class="filter-label">修改管理员密码 (可选)</label>
            <input 
              type="password" 
              v-model="configNewPassword" 
              placeholder="留空表示不修改密码" 
              class="form-input text-small"
            />
          </div>
          
          <button class="btn btn-save-config" @click="saveConfig">
            💾 保存配置
          </button>
          
          <transition name="fade">
            <p v-if="configStatusMsg" class="config-status-msg" :class="configStatus === 'success' ? 'msg-success-inline' : 'msg-error-inline'">
              {{ configStatusMsg }}
            </p>
          </transition>
        </div>
      </section>
      <hr class="divider" />

      <!-- 数据同步 -->
      <section class="sidebar-section">
        <h3>数据同步</h3>
        <div class="sync-range-selector">
          <label class="radio-container" v-for="opt in syncOptions" :key="opt.value">
            <input type="radio" :value="opt.value" v-model="syncHours" :disabled="syncing" />
            <span class="radio-checkmark"></span>
            <span class="label-text">{{ opt.label }}</span>
          </label>
        </div>
        <button class="btn btn-sync" :disabled="syncing" @click="handleSync">
          <span v-if="syncing" class="spinner"></span>
          {{ syncing ? "正在调度同步任务..." : "⚡ 立即同步最新数据" }}
        </button>
        
        <!-- 同步进度面板 -->
        <transition name="fade">
          <div v-if="syncProgress.status !== 'idle'" class="sync-progress-panel">
            <div class="progress-info">
              <span class="progress-status-text" :title="syncProgress.message">
                {{ syncProgress.message }}
              </span>
              <span class="progress-percent-text">{{ syncProgress.percent }}%</span>
            </div>
            <div class="progress-bar-container" :class="'status-' + syncProgress.status">
              <div 
                class="progress-bar-fill" 
                :style="{ width: syncProgress.percent + '%' }"
              ></div>
            </div>
          </div>
        </transition>
      </section>
      <hr class="divider" />

      <!-- 过滤条件 -->
      <section class="sidebar-section">
        <h3>过滤条件</h3>
        
        <label class="checkbox-container">
          <input type="checkbox" v-model="showAll" />
          <span class="checkbox-checkmark"></span>
          <span class="label-text">显示所有帖子 (包括无关帖)</span>
        </label>

        <div class="filter-group">
          <label class="filter-label">最低价值评分 ({{ minScore }} 星)</label>
          <div class="star-rating-selector">
            <span 
              v-for="star in 5" 
              :key="star" 
              class="star-icon"
              :class="{ active: star <= minScore }"
              @click="minScore = star === minScore ? 1 : star"
            >
              ★
            </span>
          </div>
        </div>

        <div class="filter-group">
          <label class="filter-label">过滤帖子分类</label>
          <div class="category-buttons">
            <button 
              class="category-btn" 
              :class="{ active: selectedCategories.includes('全部') }"
              @click="toggleCategory('全部')"
            >
              全部
            </button>
            <button 
              v-for="cat in availableCategories" 
              :key="cat"
              class="category-btn"
              :class="{ active: selectedCategories.includes(cat) }"
              @click="toggleCategory(cat)"
            >
              {{ cat }}
            </button>
          </div>
        </div>

        <div class="filter-group">
          <label class="filter-label">🔍 模糊搜索关键词</label>
          <input 
            type="text" 
            v-model="searchQuery" 
            placeholder="输入关键字进行过滤..." 
            class="form-input"
          />
        </div>
      </section>
    </aside>

    <!-- 主展示区 -->
    <main class="main-content">
      <header class="main-header">
        <h1 class="main-title">📡 linux.do 中转与公益站监控</h1>
        <p class="subtitle">
          实时爬取最新主题帖子，通过本地正则初筛与大语言模型细筛，实时抓取中转站、公益 API 运行及异常状态。
        </p>
      </header>

      <!-- 大盘数据指标 -->
      <section class="stats-grid">
        <div class="stats-card stats-scanned">
          <div class="stats-icon">📂</div>
          <div class="stats-label">已扫描去重贴总数</div>
          <div class="stats-value">{{ stats.total_scanned || 0 }}</div>
        </div>
        <div class="stats-card stats-relevant">
          <div class="stats-icon">🤖</div>
          <div class="stats-label">AI 判定相关帖子</div>
          <div class="stats-value text-accent">{{ stats.relevant_count || 0 }}</div>
        </div>
        <div class="stats-card stats-high-value">
          <div class="stats-icon">⭐</div>
          <div class="stats-label">⭐ 4分及以上高价值帖</div>
          <div class="stats-value text-warning">{{ stats.high_value_count || 0 }}</div>
        </div>
        <div class="stats-card stats-avg-score">
          <div class="stats-icon">📈</div>
          <div class="stats-label">相关贴平均价值分</div>
          <div class="stats-value text-purple">{{ stats.avg_value_score || '0.00' }}</div>
        </div>
      </section>

      <!-- 帖子列表 -->
      <section class="list-section">
        <div class="list-header">
          <h3>📂 筛选出 {{ filteredTopics.length }} 条帖子结果：</h3>
          <button class="btn btn-refresh" @click="fetchData(false)">
            <span>🔄 刷新数据</span>
          </button>
        </div>

        <!-- 加载状态 -->
        <div v-if="loading" class="loading-state">
          <span class="big-spinner"></span>
          <p>正在努力从数据库加载数据，请稍候...</p>
        </div>

        <!-- 空数据状态 -->
        <div v-else-if="filteredTopics.length === 0" class="empty-state">
          <div class="empty-icon">💡</div>
          <p>暂无符合当前筛选条件的帖子。</p>
          <span class="empty-tip">您可以尝试切换左侧的时间范围并点击【立即同步最新数据】。</span>
        </div>

        <!-- 帖子卡片列表 -->
        <div v-else class="cards-flow">
          <div 
            v-for="topic in filteredTopics" 
            :key="topic.id" 
            class="topic-card"
          >
            <div class="card-meta">
              <div class="meta-left">
                <span class="badge" :class="'badge-' + getBadgeType(topic.category)">
                  {{ topic.category }}
                </span>
                <span class="stars-row">
                  <span v-for="star in topic.value_score" :key="star">★</span>
                  <span v-if="topic.value_score === 0" class="no-score">无评分</span>
                </span>
              </div>
              <div class="meta-right">⏱️ {{ formatTime(topic.created_at) }}</div>
            </div>

            <div class="card-title">
              <a :href="topic.link" target="_blank" rel="noopener noreferrer">
                {{ topic.title }}
              </a>
            </div>

            <div class="card-tags" v-if="topic.tags && topic.tags.length > 0">
              <span v-for="tag in topic.tags" :key="tag" class="tag-bubble">
                {{ tag }}
              </span>
            </div>

            <div class="ai-comment">
              <span class="ai-avatar">🤖</span>
              <div class="comment-body">
                <strong>AI 简评：</strong>{{ topic.summary || '暂无 AI 智能评定' }}
              </div>
            </div>

            <!-- 丝滑折叠展开原贴首楼摘要 -->
            <div class="excerpt-accordion" v-if="topic.excerpt">
              <div class="collapse-header" @click="topic.showExcerpt = !topic.showExcerpt">
                <span class="summary-text">
                  🔍 {{ topic.showExcerpt ? '收起' : '展开' }}查看原贴摘要首楼内容
                </span>
                <span class="arrow-icon" :class="{ rotated: topic.showExcerpt }">▼</span>
              </div>
              <transition name="slide-fade">
                <div class="collapse-content" v-show="topic.showExcerpt">
                  {{ topic.excerpt }}
                </div>
              </transition>
            </div>
          </div>
        </div>
      </section>
    </main>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import axios from 'axios'

// 数据同步选项
const syncOptions = [
  { label: '过去 1 小时', value: 1.0 },
  { label: '过去 24 小时', value: 24.0 },
  { label: '仅限第一页帖子 (无时间限制)', value: 0.0 }
]
const availableCategories = ["公益API", "中转服务", "服务状态变更", "福利优惠", "待人工审核", "其他"]

// 状态变量
const syncHours = ref(1.0)
const syncing = ref(false)
const syncProgress = ref({
  status: 'idle',
  percent: 0,
  message: '系统当前处于空闲状态'
})
const loading = ref(false)

let progressInterval = null

// 顶层视图切换：'login' | 'setup' | 'main'
const currentView = ref('login')
const isAdmin = ref(false)
const adminPassword = ref('')
const adminToken = ref(localStorage.getItem('admin_token') || '')

// 初始化引导向导数据
const setupProvider = ref('openai')
const setupApiKey = ref('')
const setupBaseUrl = ref('')
const setupModel = ref('')
const setupNewPassword = ref('')
const setupError = ref('')

// 动态配置参数 (主页面侧边栏)
const configProvider = ref('openai')
const configApiKey = ref('')
const configBaseUrl = ref('')
const configModel = ref('')
const configNewPassword = ref('')
const configStatusMsg = ref('')
const configStatus = ref('success')

// 前端强密码复杂度校验
const passwordCheck = computed(() => {
  const p = setupNewPassword.value || ''
  return {
    length: p.length >= 8,
    uppercase: /[A-Z]/.test(p),
    lowercase: /[a-z]/.test(p),
    number: /[0-9]/.test(p),
    special: /[!@#$%^&*()_+={}\[\]:;\"'<>,.?/|\\~`-]/.test(p)
  }
})

const isPasswordStrong = computed(() => {
  const c = passwordCheck.value
  return c.length && c.uppercase && c.lowercase && c.number && c.special
})

const isSetupFormValid = computed(() => {
  return isPasswordStrong.value && 
         setupApiKey.value && setupApiKey.value.trim() &&
         setupModel.value && setupModel.value.trim()
})

// 拼装鉴权 Header
const getAuthHeaders = () => {
  const token = adminToken.value || localStorage.getItem('admin_token')
  return token ? { 'Authorization': `Bearer ${token}` } : {}
}

// 获取当前的系统配置
const fetchConfig = async () => {
  try {
    const res = await axios.get('/api/admin/config', { headers: getAuthHeaders() })
    if (res.data && res.data.status === 'success') {
      const d = res.data.data
      configProvider.value = d.provider
      configApiKey.value = d.api_key
      configBaseUrl.value = d.base_url
      configModel.value = d.model
    }
  } catch (err) {
    console.error("加载系统配置失败:", err)
  }
}

// 统一根据初始化状态进行重定向引导
const checkSetupAndRedirect = async () => {
  try {
    const res = await axios.get('/api/admin/setup-status')
    if (res.data && res.data.status === 'success') {
      const d = res.data
      if (d.is_setup_completed) {
        currentView.value = 'main'
        fetchData(true)
        fetchConfig()
      } else {
        currentView.value = 'setup'
      }
    }
  } catch (err) {
    console.error("自检状态失败:", err)
    currentView.value = 'main' // Fallback
  }
}

// 管理员登录
const handleLogin = async () => {
  if (!adminPassword.value) return
  try {
    const res = await axios.post('/api/admin/login', { password: adminPassword.value })
    if (res.data && res.data.token) {
      adminToken.value = res.data.token
      localStorage.setItem('admin_token', res.data.token)
      isAdmin.value = true
      adminPassword.value = ''
      
      // 登录成功，决定进入 setup 或 main
      await checkSetupAndRedirect()
    }
  } catch (err) {
    alert(err.response?.data?.detail || "密码校验失败，请重试！")
  }
}

// 初始化引导表单提交
const handleSetupSubmit = async () => {
  if (!isSetupFormValid.value) return
  setupError.value = ''
  try {
    const data = {
      provider: setupProvider.value,
      api_key: setupApiKey.value.trim(),
      base_url: setupBaseUrl.value.trim() || (setupProvider.value === 'openai' ? 'https://api.openai.com/v1' : 'https://api.anthropic.com/v1'),
      model: setupModel.value.trim(),
      new_password: setupNewPassword.value
    }
    const res = await axios.post('/api/admin/setup', data, { headers: getAuthHeaders() })
    if (res.data && res.data.status === 'success') {
      currentView.value = 'main'
      fetchData(true)
      fetchConfig()
    }
  } catch (err) {
    setupError.value = err.response?.data?.detail || '保存配置失败，请检查参数复杂度'
  }
}

// 安全登出
const handleLogout = async () => {
  try {
    await axios.post('/api/admin/logout', {}, { headers: getAuthHeaders() })
  } catch (e) {
    console.error("登出出错:", e)
  } finally {
    adminToken.value = ''
    localStorage.removeItem('admin_token')
    isAdmin.value = false
    currentView.value = 'login' // 返回全屏登录页
  }
}

// 主页侧边栏配置修改保存
const saveConfig = async () => {
  configStatusMsg.value = ''
  try {
    const data = {
      provider: configProvider.value,
      api_key: configApiKey.value,
      base_url: configBaseUrl.value,
      model: configModel.value
    }
    if (configNewPassword.value && configNewPassword.value.trim()) {
      data.new_password = configNewPassword.value.trim()
    }
    const res = await axios.post('/api/admin/config', data, { headers: getAuthHeaders() })
    if (res.data && res.data.status === 'success') {
      configStatus.value = 'success'
      configStatusMsg.value = '🎉 配置保存成功！'
      configNewPassword.value = ''
      fetchConfig()
      setTimeout(() => configStatusMsg.value = '', 4000)
    }
  } catch (err) {
    configStatus.value = 'error'
    configStatusMsg.value = err.response?.data?.detail || '保存配置失败'
  }
}

// 轮询后台同步任务的进度
const startProgressPolling = () => {
  if (progressInterval) clearInterval(progressInterval)
  
  progressInterval = setInterval(async () => {
    try {
      const res = await axios.get('/api/sync/progress')
      if (res.data) {
        syncProgress.value = res.data
        
        // 当状态为 completed 或 error 时停止轮询
        if (res.data.status === 'completed') {
          clearInterval(progressInterval)
          syncing.value = false
          // 自动刷新数据大盘
          fetchData(false)
          
          // 5秒后淡出隐藏进度面板
          setTimeout(() => {
            if (syncProgress.value.status === 'completed') {
              syncProgress.value = { status: 'idle', percent: 0, message: '系统当前处于空闲状态' }
            }
          }, 5000)
        } else if (res.data.status === 'error') {
          clearInterval(progressInterval)
          syncing.value = false
          
          // 报错状态保留 12 秒，方便用户阅读具体报错内容
          setTimeout(() => {
            if (syncProgress.value.status === 'error') {
              syncProgress.value = { status: 'idle', percent: 0, message: '系统当前处于空闲状态' }
            }
          }, 12000)
        }
      }
    } catch (err) {
      console.error("获取同步进度失败:", err)
    }
  }, 1000)
}
const showAll = ref(false)
const minScore = ref(1)
const selectedCategories = ref(['全部'])
const searchQuery = ref('')

const topics = ref([])
const stats = ref({
  total_scanned: 0,
  relevant_count: 0,
  high_value_count: 0,
  avg_value_score: 0.0
})

// 计算属性
const syncStatusClass = computed(() => {
  return syncStatus.value === 'success' ? 'msg-success' : 'msg-error'
})

// 归一化 Badge 类名
const getBadgeType = (cat) => {
  if (cat === '公益API') return 'api'
  if (cat === '中转服务') return 'proxy'
  if (cat === '服务状态变更') return 'status'
  if (cat === '福利优惠') return 'welfare'
  if (cat === '待人工审核') return 'audit'
  return 'other'
}

// 侧边栏分类多选逻辑
const toggleCategory = (cat) => {
  if (cat === '全部') {
    selectedCategories.value = ['全部']
  } else {
    // 移去“全部”
    const allIdx = selectedCategories.value.indexOf('全部')
    if (allIdx > -1) {
      selectedCategories.value.splice(allIdx, 1)
    }
    
    const idx = selectedCategories.value.indexOf(cat)
    if (idx > -1) {
      selectedCategories.value.splice(idx, 1)
      if (selectedCategories.value.length === 0) {
        selectedCategories.value = ['全部']
      }
    } else {
      selectedCategories.value.push(cat)
    }
  }
}

// 内存级多重条件筛选
const filteredTopics = computed(() => {
  return topics.value.filter(t => {
    // 1. 相关性过滤
    if (!showAll.value && !t.is_relevant) {
      return false
    }
    // 2. 星级评分过滤
    if (t.value_score < minScore.value) {
      return false
    }
    // 3. 分类过滤
    if (!selectedCategories.value.includes('全部')) {
      if (!selectedCategories.value.includes(t.category)) {
        return false
      }
    }
    // 4. 模糊文本搜索
    if (searchQuery.value) {
      const q = searchQuery.value.toLowerCase()
      const titleMatch = t.title.toLowerCase().includes(q)
      const excerptMatch = (t.excerpt || '').toLowerCase().includes(q)
      const tagsMatch = t.tags ? t.tags.some(tag => tag.toLowerCase().includes(q)) : false
      if (!(titleMatch || excerptMatch || tagsMatch)) {
        return false
      }
    }
    return true
  })
})

// 时间格式化
const formatTime = (timeStr) => {
  if (!timeStr) return ''
  try {
    const parts = timeStr.split(' ')
    if (parts.length >= 2) {
      const dateParts = parts[0].split('-')
      const timeParts = parts[1].split(':')
      return `${dateParts[1]}-${dateParts[2]} ${timeParts[0]}:${timeParts[1]}`
    }
    return timeStr
  } catch {
    return timeStr
  }
}

// 从后端拉取最新帖子和大盘数据
const fetchData = async (showLoading = true) => {
  if (showLoading) loading.value = true
  try {
    const topicsRes = await axios.get('/api/topics', {
      params: { relevant_only: !showAll.value }
    })
    if (topicsRes.data && topicsRes.data.status === 'success') {
      // 注入用于做折叠动效的 showExcerpt 响应式字段
      topics.value = topicsRes.data.data.map(t => ({
        ...t,
        showExcerpt: false
      }))
    }
    
    const statsRes = await axios.get('/api/stats')
    if (statsRes.data && statsRes.data.status === 'success') {
      stats.value = statsRes.data.data
    }
  } catch (err) {
    console.error("加载后端数据失败:", err)
  } finally {
    if (showLoading) loading.value = false
  }
}

// 手动触发同步请求
const handleSync = async () => {
  if (!isAdmin.value) {
    currentView.value = 'login'
    alert("登录会话已失效，请重新登录管理员账号。")
    return
  }
  if (syncing.value) return
  syncing.value = true
  
  const hoursParam = syncHours.value === 0.0 ? null : syncHours.value
  
  try {
    // 立即更新进度状态，提示用户已发出指令
    syncProgress.value = { status: 'syncing', percent: 0, message: '正在初始化同步指令...' }
    
    const res = await axios.post('/api/sync', { hours: hoursParam }, { headers: getAuthHeaders() })
    if (res.data && res.data.status === 'success') {
      // 启动定时轮询
      startProgressPolling()
    } else {
      syncProgress.value = { 
        status: 'error', 
        percent: 100, 
        message: res.data.message || '调度同步任务失败。' 
      }
      syncing.value = false
    }
  } catch (err) {
    syncProgress.value = { 
      status: 'error', 
      percent: 100, 
      message: err.response?.data?.message || '下发同步指令失败，请检查后端状态。' 
    }
    syncing.value = false
  }
}

onMounted(async () => {
  // 1. 检查全局初始化状态
  let isSetupCompleted = false
  try {
    const statusRes = await axios.get('/api/admin/setup-status')
    if (statusRes.data && statusRes.data.status === 'success') {
      isSetupCompleted = statusRes.data.is_setup_completed
    }
  } catch (err) {
    console.error("检查系统初始化状态失败:", err)
  }

  // 2. 验证本地 Token 并决定重定向视图
  if (adminToken.value) {
    try {
      const authRes = await axios.get('/api/admin/auth-status', { headers: getAuthHeaders() })
      if (authRes.data && authRes.data.authorized) {
        isAdmin.value = true
        if (isSetupCompleted) {
          currentView.value = 'main'
          fetchData(true)
          fetchConfig()
        } else {
          currentView.value = 'setup'
        }
      } else {
        currentView.value = 'login'
      }
    } catch (err) {
      console.warn("登录凭证失效，自动清除")
      adminToken.value = ''
      localStorage.removeItem('admin_token')
      currentView.value = 'login'
    }
  } else {
    currentView.value = 'login'
  }
  
  // 3. 检查后台同步是否在运行
  try {
    const res = await axios.get('/api/sync/progress')
    if (res.data && res.data.status === 'syncing') {
      syncing.value = true
      syncProgress.value = res.data
      startProgressPolling()
    }
  } catch (err) {
    console.error("检查同步状态失败:", err)
  }
})
</script>

<style>
/* ==========================================================================
   VANILLA CSS DESIGN SYSTEM (HIGH AESTHETICS - GLASSMORPHISM & NEON GLOW)
   ========================================================================== */

:root {
  --bg-app: #090a0f;
  --bg-sidebar: rgba(14, 18, 30, 0.7);
  --bg-card: rgba(22, 29, 47, 0.45);
  --bg-card-hover: rgba(30, 39, 64, 0.6);
  --border-color: rgba(255, 255, 255, 0.04);
  --border-hover: rgba(99, 102, 241, 0.35);
  --text-main: #f3f4f6;
  --text-muted: #9ca3af;
  --text-dark: #6b7280;
  --neon-purple: #8b5cf6;
  --neon-blue: #3b82f6;
}

body {
  margin: 0;
  font-family: 'Outfit', 'Noto Sans SC', sans-serif;
  background-color: var(--bg-app);
  color: var(--text-main);
  overflow-x: hidden;
}

/* 渐变背景霓虹发光气泡效果 */
.app-container {
  display: flex;
  min-height: 100vh;
  position: relative;
  overflow: hidden;
}

.app-container::before {
  content: "";
  position: absolute;
  width: 600px;
  height: 600px;
  background: radial-gradient(circle, rgba(99, 102, 241, 0.08) 0%, rgba(0, 0, 0, 0) 70%);
  top: -200px;
  left: -150px;
  pointer-events: none;
  z-index: 1;
}

.app-container::after {
  content: "";
  position: absolute;
  width: 500px;
  height: 500px;
  background: radial-gradient(circle, rgba(139, 92, 246, 0.07) 0%, rgba(0, 0, 0, 0) 70%);
  bottom: -150px;
  right: -100px;
  pointer-events: none;
  z-index: 1;
}

/* 侧边栏 (玻璃态) */
.sidebar {
  width: 330px;
  background: var(--bg-sidebar);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  border-right: 1px solid var(--border-color);
  padding: 40px 24px;
  box-sizing: border-box;
  flex-shrink: 0;
  overflow-y: auto;
  z-index: 10;
}

.sidebar-header {
  display: flex;
  align-items: center;
  gap: 12px;
}

.sidebar-header .icon {
  font-size: 1.6rem;
  filter: drop-shadow(0 0 8px rgba(59, 130, 246, 0.5));
}

.sidebar-header h2 {
  font-size: 1.35rem;
  font-weight: 800;
  margin: 0;
  letter-spacing: 0.5px;
  background: linear-gradient(135deg, #fff 30%, var(--text-muted) 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}

.divider {
  border: 0;
  height: 1px;
  background: radial-gradient(circle, rgba(255, 255, 255, 0.08) 0%, transparent 100%);
  margin: 30px 0;
}

.sidebar-section h3 {
  font-size: 0.88rem;
  font-weight: 800;
  color: var(--text-muted);
  margin-top: 0;
  margin-bottom: 18px;
  text-transform: uppercase;
  letter-spacing: 1px;
}

/* 炫酷的单选按钮美化 */
.sync-range-selector {
  display: flex;
  flex-direction: column;
  gap: 14px;
  margin-bottom: 22px;
}

.radio-container {
  display: flex;
  align-items: center;
  position: relative;
  padding-left: 28px;
  cursor: pointer;
  font-size: 0.88rem;
  color: var(--text-muted);
  user-select: none;
  transition: color 0.2s ease;
}

.radio-container:hover {
  color: #fff;
}

.radio-container input {
  position: absolute;
  opacity: 0;
}

.radio-checkmark {
  position: absolute;
  left: 0;
  height: 16px;
  width: 16px;
  background-color: rgba(255, 255, 255, 0.02);
  border: 1px solid var(--border-color);
  border-radius: 50%;
  transition: all 0.25s ease;
}

.radio-container:hover input ~ .radio-checkmark {
  border-color: var(--border-hover);
  box-shadow: 0 0 8px rgba(99, 102, 241, 0.2);
}

.radio-checkmark:after {
  content: "";
  position: absolute;
  display: none;
  top: 4px;
  left: 4px;
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--neon-blue);
  box-shadow: 0 0 6px var(--neon-blue);
}

.radio-container input:checked ~ .radio-checkmark:after {
  display: block;
}

.radio-container input:checked ~ .radio-checkmark {
  border-color: var(--neon-blue);
  background-color: rgba(59, 130, 246, 0.08);
}

/* 炫酷的复选框美化 */
.checkbox-container {
  display: flex;
  align-items: center;
  position: relative;
  padding-left: 28px;
  margin-bottom: 25px;
  cursor: pointer;
  font-size: 0.88rem;
  color: var(--text-muted);
  user-select: none;
  transition: color 0.2s ease;
}

.checkbox-container:hover {
  color: #fff;
}

.checkbox-container input {
  position: absolute;
  opacity: 0;
}

.checkbox-checkmark {
  position: absolute;
  left: 0;
  height: 16px;
  width: 16px;
  background-color: rgba(255, 255, 255, 0.02);
  border: 1px solid var(--border-color);
  border-radius: 4px;
  transition: all 0.25s ease;
}

.checkbox-container:hover input ~ .checkbox-checkmark {
  border-color: rgba(72, 187, 120, 0.5);
  box-shadow: 0 0 8px rgba(72, 187, 120, 0.15);
}

.checkbox-checkmark:after {
  content: "";
  position: absolute;
  display: none;
  left: 5px;
  top: 1px;
  width: 4px;
  height: 8px;
  border: solid #48bb78;
  border-width: 0 2px 2px 0;
  transform: rotate(45deg);
}

.checkbox-container input:checked ~ .checkbox-checkmark:after {
  display: block;
}

.checkbox-container input:checked ~ .checkbox-checkmark {
  border-color: #48bb78;
  background-color: rgba(72, 187, 120, 0.08);
}

/* 过滤组件间距 */
.filter-group {
  margin-bottom: 22px;
}

.filter-label {
  display: block;
  font-size: 0.82rem;
  color: var(--text-dark);
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin-bottom: 8px;
}

/* 闪耀五星评分条 */
.star-rating-selector {
  display: flex;
  gap: 6px;
}

.star-icon {
  font-size: 1.6rem;
  color: rgba(255, 255, 255, 0.08);
  cursor: pointer;
  user-select: none;
  transition: all 0.2s cubic-bezier(0.175, 0.885, 0.32, 1.275);
}

.star-icon:hover {
  transform: scale(1.2);
}

.star-icon.active {
  color: #ecc94b;
  text-shadow: 0 0 10px rgba(236, 201, 75, 0.4);
}

/* 微光分类按钮 */
.category-buttons {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.category-btn {
  background: rgba(255, 255, 255, 0.02);
  border: 1px solid var(--border-color);
  color: var(--text-muted);
  padding: 6px 12px;
  border-radius: 20px;
  font-size: 0.78rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.25s ease;
}

.category-btn:hover {
  border-color: rgba(255, 255, 255, 0.2);
  color: #fff;
}

.category-btn.active {
  background: rgba(99, 102, 241, 0.1);
  border-color: rgba(99, 102, 241, 0.5);
  color: #a5b4fc;
  box-shadow: 0 0 12px rgba(99, 102, 241, 0.15);
}

/* 高雅输入框 */
.form-input {
  width: 100%;
  background: rgba(0, 0, 0, 0.25);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  padding: 11px 14px;
  box-sizing: border-box;
  color: #fff;
  font-size: 0.85rem;
  transition: all 0.2s ease;
}

.form-input:focus {
  outline: none;
  border-color: rgba(99, 102, 241, 0.5);
  box-shadow: 0 0 10px rgba(99, 102, 241, 0.15);
}

/* 按钮设计 */
.btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 8px;
  font-weight: 600;
  border: none;
  cursor: pointer;
  transition: all 0.25s ease;
}

.btn-sync {
  width: 100%;
  padding: 13px;
  background: linear-gradient(135deg, #4f46e5 0%, #7c3aed 100%);
  color: white;
  font-size: 0.88rem;
  box-shadow: 0 4px 15px rgba(79, 70, 229, 0.3);
}

.btn-sync:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: 0 6px 20px rgba(79, 70, 229, 0.5);
}

.btn-sync:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}

.btn-refresh {
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid var(--border-color);
  color: var(--text-muted);
  padding: 8px 16px;
  font-size: 0.8rem;
}

.btn-refresh:hover {
  background: rgba(255, 255, 255, 0.07);
  color: #fff;
  border-color: var(--border-hover);
}

/* 主展示区 */
.main-content {
  flex-grow: 1;
  padding: 45px 55px;
  box-sizing: border-box;
  overflow-y: auto;
  z-index: 5;
}

.main-header {
  margin-bottom: 35px;
}

.main-title {
  font-size: 2.7rem;
  font-weight: 800;
  margin: 0 0 10px 0;
  letter-spacing: -0.5px;
  background: linear-gradient(135deg, #c7d2fe 0%, #fbcfe8 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}

.subtitle {
  color: var(--text-muted);
  font-size: 0.98rem;
  margin: 0;
}

/* 指标统计栅格 */
.stats-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 24px;
  margin-bottom: 40px;
}

.stats-card {
  background: var(--bg-card);
  backdrop-filter: blur(8px);
  -webkit-backdrop-filter: blur(8px);
  border: 1px solid var(--border-color);
  border-radius: 16px;
  padding: 24px;
  position: relative;
  overflow: hidden;
  box-sizing: border-box;
}

.stats-icon {
  position: absolute;
  right: 20px;
  bottom: 12px;
  font-size: 2.8rem;
  opacity: 0.04;
  pointer-events: none;
}

.stats-label {
  font-size: 0.8rem;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin-bottom: 8px;
}

.stats-value {
  font-size: 2.2rem;
  font-weight: 800;
}

/* 指标卡顶部修饰细线 */
.stats-scanned::before { content: ""; position: absolute; top: 0; left: 0; right: 0; height: 3px; background: linear-gradient(90deg, transparent, rgba(255,255,255,0.08), transparent); }
.stats-relevant::before { content: ""; position: absolute; top: 0; left: 0; right: 0; height: 3px; background: linear-gradient(90deg, transparent, rgba(72,187,120,0.4), transparent); }
.stats-high-value::before { content: ""; position: absolute; top: 0; left: 0; right: 0; height: 3px; background: linear-gradient(90deg, transparent, rgba(236,201,75,0.4), transparent); }
.stats-avg-score::before { content: ""; position: absolute; top: 0; left: 0; right: 0; height: 3px; background: linear-gradient(90deg, transparent, rgba(168,85,247,0.4), transparent); }

/* 帖子卡片列表 */
.list-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 22px;
}

.list-header h3 {
  font-size: 1.15rem;
  font-weight: 700;
  margin: 0;
}

.cards-flow {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

/* 高雅帖子卡片 */
.topic-card {
  background: var(--bg-card);
  backdrop-filter: blur(10px);
  -webkit-backdrop-filter: blur(10px);
  border: 1px solid var(--border-color);
  border-radius: 16px;
  padding: 26px;
  box-sizing: border-box;
  transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1);
}

.topic-card:hover {
  transform: translateY(-3px) scale(1.001);
  background: var(--bg-card-hover);
  border-color: var(--border-hover);
  box-shadow: 0 12px 35px rgba(99, 102, 241, 0.12), 0 2px 8px rgba(0, 0, 0, 0.4);
}

.card-meta {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 14px;
}

.meta-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.meta-right {
  font-size: 0.8rem;
  color: var(--text-dark);
}

.stars-row {
  color: #ecc94b;
  font-size: 0.95rem;
  text-shadow: 0 0 5px rgba(236,201,75,0.25);
}

.no-score {
  color: var(--text-dark);
  font-size: 0.78rem;
}

/* 分类微标 (Badges) */
.badge {
  padding: 4px 12px;
  border-radius: 20px;
  font-size: 0.7rem;
  font-weight: 700;
  letter-spacing: 0.5px;
  box-shadow: inset 0 1px 1px rgba(255, 255, 255, 0.08);
}

.badge-api { background: rgba(72, 187, 120, 0.1); color: #48bb78; border: 1px solid rgba(72, 187, 120, 0.2); }
.badge-proxy { background: rgba(59, 130, 246, 0.1); color: #3b82f6; border: 1px solid rgba(59, 130, 246, 0.2); }
.badge-status { background: rgba(239, 68, 68, 0.1); color: #ef4444; border: 1px solid rgba(239, 68, 68, 0.2); }
.badge-welfare { background: rgba(245, 158, 11, 0.1); color: #f59e0b; border: 1px solid rgba(245, 158, 11, 0.2); }
.badge-audit { background: rgba(139, 92, 246, 0.1); color: #8b5cf6; border: 1px solid rgba(139, 92, 246, 0.2); }
.badge-other { background: rgba(107, 114, 128, 0.1); color: #9ca3af; border: 1px solid rgba(107, 114, 128, 0.2); }

.card-title a {
  font-size: 1.3rem;
  font-weight: 700;
  color: #fff;
  text-decoration: none;
  line-height: 1.4;
  transition: color 0.15s ease;
}

.card-title a:hover {
  color: #a5b4fc;
}

.card-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 14px;
}

.tag-bubble {
  background: rgba(255, 255, 255, 0.03);
  color: var(--text-muted);
  border: 1px solid var(--border-color);
  padding: 3px 8px;
  border-radius: 4px;
  font-size: 0.68rem;
}

/* AI 简评框 */
.ai-comment {
  display: flex;
  gap: 12px;
  align-items: flex-start;
  background: rgba(255, 255, 255, 0.015);
  border: 1px solid rgba(255, 255, 255, 0.02);
  padding: 15px 18px;
  border-radius: 10px;
  margin-top: 20px;
}

.ai-avatar {
  font-size: 1.25rem;
  filter: drop-shadow(0 0 5px rgba(139, 92, 246, 0.3));
}

.comment-body {
  font-size: 0.88rem;
  line-height: 1.55;
  color: #e5e7eb;
}

/* 丝滑折叠展开面板 (Accordion) */
.excerpt-accordion {
  margin-top: 16px;
}

.collapse-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 14px;
  font-size: 0.8rem;
  color: var(--text-muted);
  cursor: pointer;
  user-select: none;
  background: rgba(0, 0, 0, 0.12);
  border: 1px solid var(--border-color);
  border-radius: 6px;
  transition: all 0.2s ease;
}

.collapse-header:hover {
  background: rgba(255, 255, 255, 0.02);
  color: #fff;
  border-color: rgba(255,255,255,0.08);
}

.arrow-icon {
  font-size: 0.6rem;
  transition: transform 0.25s cubic-bezier(0.4, 0, 0.2, 1);
  color: var(--text-dark);
}

.arrow-icon.rotated {
  transform: rotate(180deg);
  color: var(--text-muted);
}

.collapse-content {
  padding: 14px;
  font-size: 0.85rem;
  color: var(--text-muted);
  background: rgba(0, 0, 0, 0.18);
  border: 1px solid var(--border-color);
  border-top: none;
  border-radius: 0 0 6px 6px;
  line-height: 1.6;
  white-space: pre-wrap;
}

/* 丝滑高度展开收起动画 */
.slide-fade-enter-active {
  transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1);
}
.slide-fade-leave-active {
  transition: all 0.2s cubic-bezier(0.5, 0, 1, 1);
}
.slide-fade-enter-from,
.slide-fade-leave-to {
  transform: translateY(-8px);
  opacity: 0;
}

/* 消息提示框动画 (Fade) */
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.3s ease;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

/* 炫酷的侧边栏同步进度条面板 */
.sync-progress-panel {
  margin-top: 16px;
  background: rgba(0, 0, 0, 0.2);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  padding: 12px;
  box-sizing: border-box;
}

.progress-info {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
  font-size: 0.78rem;
}

.progress-status-text {
  color: var(--text-muted);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 80%;
}

.progress-percent-text {
  font-weight: 700;
  color: #a5b4fc;
}

/* 进度条轨道 */
.progress-bar-container {
  width: 100%;
  height: 6px;
  background: rgba(255, 255, 255, 0.03);
  border-radius: 3px;
  overflow: hidden;
  position: relative;
}

/* 进度条填充 */
.progress-bar-fill {
  height: 100%;
  width: 0%;
  border-radius: 3px;
  transition: width 0.4s cubic-bezier(0.4, 0, 0.2, 1);
  background: linear-gradient(90deg, #4f46e5, #8b5cf6);
  box-shadow: 0 0 8px rgba(139, 92, 246, 0.5);
}

/* 状态色定制 */
.progress-bar-container.status-completed .progress-bar-fill {
  background: linear-gradient(90deg, #10b981, #34d399);
  box-shadow: 0 0 8px rgba(52, 211, 153, 0.5);
}

.progress-bar-container.status-error .progress-bar-fill {
  background: linear-gradient(90deg, #ef4444, #f87171);
  box-shadow: 0 0 8px rgba(248, 113, 113, 0.5);
}

/* 正在 syncing 时，为填充条增加渐变扫光效果 */
.status-syncing .progress-bar-fill {
  position: relative;
  overflow: hidden;
}

.status-syncing .progress-bar-fill::after {
  content: "";
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: linear-gradient(
    90deg,
    rgba(255, 255, 255, 0) 0%,
    rgba(255, 255, 255, 0.3) 50%,
    rgba(255, 255, 255, 0) 100%
  );
  animation: progress-shimmer 1.5s infinite;
  transform: translateX(-100%);
}

@keyframes progress-shimmer {
  100% {
    transform: translateX(100%);
  }
}

/* 空状态和加载 */
.loading-state, .empty-state {
  text-align: center;
  padding: 60px 20px;
  color: var(--text-muted);
}

.empty-icon {
  font-size: 3rem;
  margin-bottom: 12px;
  opacity: 0.25;
}

.empty-tip {
  display: block;
  font-size: 0.8rem;
  color: var(--text-dark);
  margin-top: 6px;
}

/* 菊花加载 */
.spinner {
  width: 14px;
  height: 14px;
  border: 2px solid rgba(255, 255, 255, 0.25);
  border-top-color: #fff;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
  margin-right: 8px;
  display: inline-block;
}

.big-spinner {
  width: 44px;
  height: 44px;
  border: 3px solid rgba(255, 255, 255, 0.04);
  border-top-color: var(--neon-purple);
  border-radius: 50%;
  animation: spin 1s linear infinite;
  display: inline-block;
  margin-bottom: 15px;
  box-shadow: 0 0 10px rgba(139, 92, 246, 0.1);
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

/* 滚动条美化 */
::-webkit-scrollbar {
  width: 8px;
  height: 8px;
}

::-webkit-scrollbar-track {
  background: var(--bg-app);
}

::-webkit-scrollbar-thumb {
  background: rgba(255, 255, 255, 0.08);
  border-radius: 4px;
}

::-webkit-scrollbar-thumb:hover {
  background: rgba(255, 255, 255, 0.15);
}
/* 管理员配置模块 CSS */
.admin-header-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.btn-logout {
  background: transparent;
  border: 1px solid rgba(239, 68, 68, 0.4);
  color: #ef4444;
  font-size: 0.72rem;
  padding: 3px 8px;
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.btn-logout:hover {
  background: rgba(239, 68, 68, 0.1);
  box-shadow: 0 0 6px rgba(239, 68, 68, 0.2);
}

.admin-login-promo {
  background: rgba(255, 255, 255, 0.015);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  padding: 14px;
  box-sizing: border-box;
}

.promo-text {
  font-size: 0.76rem;
  color: var(--text-muted);
  line-height: 1.45;
  margin: 0 0 12px 0;
}

.btn-login-trigger {
  width: 100%;
  padding: 9px;
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid var(--border-color);
  color: var(--text-main);
  font-size: 0.8rem;
  box-shadow: inset 0 1px 1px rgba(255, 255, 255, 0.05);
}

.btn-login-trigger:hover {
  background: rgba(255, 255, 255, 0.08);
  border-color: rgba(99, 102, 241, 0.4);
}

/* 配置表单 */
.admin-config-panel {
  background: rgba(0, 0, 0, 0.2);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  padding: 14px;
  box-sizing: border-box;
}

.provider-selector {
  display: flex;
  gap: 8px;
  margin-bottom: 6px;
}

.provider-tab {
  flex: 1;
  background: rgba(255, 255, 255, 0.02);
  border: 1px solid var(--border-color);
  color: var(--text-muted);
  padding: 6px;
  border-radius: 6px;
  font-size: 0.76rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s ease;
}

.provider-tab.active {
  background: rgba(139, 92, 246, 0.1);
  border-color: rgba(139, 92, 246, 0.4);
  color: #c084fc;
}

.provider-tip-text {
  font-size: 0.65rem;
  color: var(--text-dark);
  margin: 4px 0 0 0;
  line-height: 1.3;
}

.text-small {
  padding: 8px 10px;
  font-size: 0.78rem;
}

.btn-save-config {
  width: 100%;
  padding: 9px;
  background: linear-gradient(135deg, #6366f1 0%, #a855f7 100%);
  color: white;
  font-size: 0.8rem;
  margin-top: 6px;
  box-shadow: 0 3px 10px rgba(99, 102, 241, 0.25);
}

.btn-save-config:hover {
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(99, 102, 241, 0.4);
}

.config-status-msg {
  font-size: 0.72rem;
  margin-top: 8px;
  margin-bottom: 0;
  text-align: center;
}

.msg-success-inline { color: #34d399; }
.msg-error-inline { color: #f87171; }

/* 模态框 Modal */
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.6);
  backdrop-filter: blur(8px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal-card {
  width: 400px;
  background: rgba(14, 18, 30, 0.85);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 16px;
  padding: 24px;
  box-shadow: 0 20px 50px rgba(0, 0, 0, 0.6), 0 0 30px rgba(99, 102, 241, 0.1);
  box-sizing: border-box;
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.modal-header h3 {
  font-size: 1.1rem;
  margin: 0;
  color: #fff;
  font-weight: 700;
}

.btn-close-modal {
  background: transparent;
  border: none;
  color: var(--text-muted);
  font-size: 1.4rem;
  cursor: pointer;
  transition: color 0.2s ease;
}

.btn-close-modal:hover {
  color: #fff;
}

.modal-intro {
  font-size: 0.82rem;
  color: var(--text-muted);
  line-height: 1.5;
  margin: 0 0 18px 0;
}

.modal-footer {
  display: flex;
  gap: 12px;
  justify-content: flex-end;
  margin-top: 24px;
}

.btn-modal-cancel {
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid var(--border-color);
  color: var(--text-muted);
  padding: 8px 16px;
  font-size: 0.8rem;
}

.btn-modal-cancel:hover {
  background: rgba(255, 255, 255, 0.06);
  color: #fff;
}

.btn-modal-login {
  background: linear-gradient(135deg, #4f46e5 0%, #7c3aed 100%);
  color: #fff;
  padding: 8px 18px;
  font-size: 0.8rem;
  box-shadow: 0 4px 12px rgba(79, 70, 229, 0.25);
}

.btn-modal-login:hover {
  transform: translateY(-1px);
  box-shadow: 0 6px 15px rgba(79, 70, 229, 0.4);
}
/* 满屏登录和配置向导 CSS 样式表追加 */
.fullscreen-container {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 100vh;
  width: 100vw;
  background-color: var(--bg-app);
  position: relative;
  overflow: hidden;
  box-sizing: border-box;
}

.fullscreen-container::before {
  content: "";
  position: absolute;
  width: 600px;
  height: 600px;
  background: radial-gradient(circle, rgba(139, 92, 246, 0.08) 0%, rgba(0, 0, 0, 0) 70%);
  top: -10vh;
  left: 20vw;
  pointer-events: none;
}

.fullscreen-container::after {
  content: "";
  position: absolute;
  width: 500px;
  height: 500px;
  background: radial-gradient(circle, rgba(99, 102, 241, 0.07) 0%, rgba(0, 0, 0, 0) 70%);
  bottom: -10vh;
  right: 25vw;
  pointer-events: none;
}

/* 登录卡片 */
.login-card-main {
  width: 420px;
  background: rgba(14, 18, 30, 0.65);
  backdrop-filter: blur(25px);
  -webkit-backdrop-filter: blur(25px);
  border: 1px solid rgba(255, 255, 255, 0.06);
  border-radius: 20px;
  padding: 35px 30px;
  box-shadow: 0 30px 60px rgba(0, 0, 0, 0.6), 0 0 40px rgba(99, 102, 241, 0.08);
  box-sizing: border-box;
  z-index: 10;
}

.login-card-header {
  text-align: center;
  margin-bottom: 25px;
}

.login-card-header .icon {
  font-size: 2.8rem;
  display: block;
  margin-bottom: 12px;
  filter: drop-shadow(0 0 10px rgba(99, 102, 241, 0.4));
}

.login-card-header h2 {
  font-size: 1.55rem;
  margin: 0;
  background: linear-gradient(135deg, #fff 40%, var(--text-muted) 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  font-weight: 800;
}

.intro-text {
  font-size: 0.82rem;
  color: var(--text-muted);
  line-height: 1.5;
  text-align: center;
  margin: 0 0 24px 0;
}

.intro-text code {
  color: #a5b4fc;
  background: rgba(255,255,255,0.04);
  padding: 2px 6px;
  border-radius: 4px;
  font-family: monospace;
}

.btn-login-submit {
  width: 100%;
  padding: 13px;
  background: linear-gradient(135deg, #4f46e5 0%, #7c3aed 100%);
  color: white;
  font-size: 0.9rem;
  margin-top: 10px;
  box-shadow: 0 5px 15px rgba(79, 70, 229, 0.35);
}

.btn-login-submit:hover {
  transform: translateY(-1px);
  box-shadow: 0 6px 20px rgba(79, 70, 229, 0.5);
}

/* 初始化引导向导卡片 */
.setup-card-main {
  width: 580px;
  background: rgba(14, 18, 30, 0.7);
  backdrop-filter: blur(25px);
  -webkit-backdrop-filter: blur(25px);
  border: 1px solid rgba(255, 255, 255, 0.06);
  border-radius: 24px;
  padding: 40px 35px;
  box-shadow: 0 35px 70px rgba(0, 0, 0, 0.65), 0 0 50px rgba(139, 92, 246, 0.08);
  box-sizing: border-box;
  z-index: 10;
}

.setup-card-header {
  margin-bottom: 28px;
}

.setup-card-header h3 {
  font-size: 1.55rem;
  margin: 0 0 8px 0;
  font-weight: 800;
  background: linear-gradient(135deg, #c7d2fe 0%, #fbcfe8 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}

.setup-card-header .subtitle {
  font-size: 0.85rem;
  color: var(--text-muted);
  line-height: 1.5;
  margin: 0;
}

.setup-section h4 {
  font-size: 0.95rem;
  color: #fff;
  margin: 0 0 16px 0;
  font-weight: 700;
  border-left: 3px solid var(--neon-purple);
  padding-left: 10px;
}

.setup-divider {
  border: 0;
  height: 1px;
  background: radial-gradient(circle, rgba(255, 255, 255, 0.08) 0%, transparent 100%);
  margin: 25px 0;
}

.setup-notice {
  font-size: 0.74rem;
  color: #ecc94b;
  background: rgba(236, 201, 75, 0.05);
  border: 1px solid rgba(236, 201, 75, 0.12);
  padding: 8px 12px;
  border-radius: 6px;
  margin-top: 0;
  margin-bottom: 16px;
  line-height: 1.4;
}

.btn-setup-submit {
  width: 100%;
  padding: 13px;
  background: linear-gradient(135deg, #6366f1 0%, #a855f7 100%);
  color: white;
  font-size: 0.9rem;
  margin-top: 25px;
  box-shadow: 0 5px 15px rgba(99, 102, 241, 0.3);
}

.btn-setup-submit:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: 0 6px 20px rgba(99, 102, 241, 0.45);
}

.btn-setup-submit:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}

.setup-error-msg {
  font-size: 0.8rem;
  color: #ef4444;
  margin-top: 14px;
  margin-bottom: 0;
  text-align: center;
}

/* 密码强度指示器 */
.password-strength-checker {
  display: flex;
  flex-wrap: wrap;
  gap: 10px 18px;
  margin-top: 12px;
  background: rgba(0, 0, 0, 0.15);
  padding: 12px 16px;
  border-radius: 8px;
  border: 1px solid var(--border-color);
}

.checker-item {
  font-size: 0.75rem;
  color: var(--text-dark);
  display: flex;
  align-items: center;
  gap: 5px;
  transition: color 0.25s ease;
}

.checker-bullet {
  font-weight: bold;
  opacity: 0.4;
  font-size: 0.8rem;
}

.checker-item.pass {
  color: #34d399;
}

.checker-item.pass .checker-bullet {
  opacity: 1;
  color: #34d399;
}
</style>
