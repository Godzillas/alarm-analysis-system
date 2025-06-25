<template>
  <div class="settings">
    <!-- 通用设置 -->
    <el-card class="setting-card">
      <template #header>
        <h3>通用设置</h3>
      </template>
      
      <el-form :model="generalSettings" label-width="150px">
        <el-form-item label="系统名称">
          <el-input v-model="generalSettings.system_name" placeholder="告警分析系统" />
        </el-form-item>
        
        <el-form-item label="系统描述">
          <el-input 
            v-model="generalSettings.system_description" 
            type="textarea" 
            :rows="3"
            placeholder="智能告警收集、分析和展示系统"
          />
        </el-form-item>
        
        <el-form-item label="时区设置">
          <el-select v-model="generalSettings.timezone" placeholder="选择时区">
            <el-option label="中国标准时间 (UTC+8)" value="Asia/Shanghai" />
            <el-option label="协调世界时 (UTC)" value="UTC" />
            <el-option label="东京时间 (UTC+9)" value="Asia/Tokyo" />
            <el-option label="纽约时间 (UTC-5)" value="America/New_York" />
          </el-select>
        </el-form-item>
        
        <el-form-item label="默认语言">
          <el-select v-model="generalSettings.default_language" placeholder="选择语言">
            <el-option label="中文" value="zh-CN" />
            <el-option label="English" value="en-US" />
            <el-option label="日本語" value="ja-JP" />
          </el-select>
        </el-form-item>
        
        <el-form-item label="数据保留时间">
          <el-input-number 
            v-model="generalSettings.data_retention_days" 
            :min="1" 
            :max="365"
            style="width: 150px"
          />
          <span style="margin-left: 10px; color: var(--el-text-color-secondary)">天</span>
        </el-form-item>
        
        <el-form-item label="启用维护模式">
          <el-switch v-model="generalSettings.maintenance_mode" />
          <el-text size="small" type="info" style="margin-left: 10px">
            开启后仅管理员可以访问系统
          </el-text>
        </el-form-item>
      </el-form>
      
      <div class="form-actions">
        <el-button type="primary" @click="saveGeneralSettings">保存设置</el-button>
        <el-button @click="resetGeneralSettings">重置</el-button>
      </div>
    </el-card>

    <!-- 告警设置 -->
    <el-card class="setting-card">
      <template #header>
        <h3>告警设置</h3>
      </template>
      
      <el-form :model="alarmSettings" label-width="150px">
        <el-form-item label="默认严重程度">
          <el-select v-model="alarmSettings.default_severity" placeholder="选择默认严重程度">
            <el-option label="严重" value="critical" />
            <el-option label="高" value="high" />
            <el-option label="中" value="medium" />
            <el-option label="低" value="low" />
          </el-select>
        </el-form-item>
        
        <el-form-item label="自动解决时间">
          <el-input-number 
            v-model="alarmSettings.auto_resolve_hours" 
            :min="1" 
            :max="168"
            style="width: 150px"
          />
          <span style="margin-left: 10px; color: var(--el-text-color-secondary)">小时</span>
        </el-form-item>
        
        <el-form-item label="重复告警阈值">
          <el-input-number 
            v-model="alarmSettings.duplicate_threshold" 
            :min="1" 
            :max="100"
            style="width: 150px"
          />
          <span style="margin-left: 10px; color: var(--el-text-color-secondary)">次</span>
        </el-form-item>
        
        <el-form-item label="关联窗口时间">
          <el-input-number 
            v-model="alarmSettings.correlation_window" 
            :min="1" 
            :max="60"
            style="width: 150px"
          />
          <span style="margin-left: 10px; color: var(--el-text-color-secondary)">分钟</span>
        </el-form-item>
        
        <el-form-item label="启用智能分组">
          <el-switch v-model="alarmSettings.enable_grouping" />
          <el-text size="small" type="info" style="margin-left: 10px">
            自动将相似告警进行分组
          </el-text>
        </el-form-item>
        
        <el-form-item label="启用告警抑制">
          <el-switch v-model="alarmSettings.enable_suppression" />
          <el-text size="small" type="info" style="margin-left: 10px">
            在维护窗口期间抑制告警
          </el-text>
        </el-form-item>
      </el-form>
      
      <div class="form-actions">
        <el-button type="primary" @click="saveAlarmSettings">保存设置</el-button>
        <el-button @click="resetAlarmSettings">重置</el-button>
      </div>
    </el-card>

    <!-- 通知设置 -->
    <el-card class="setting-card">
      <template #header>
        <h3>通知设置</h3>
      </template>
      
      <el-form :model="notificationSettings" label-width="150px">
        <el-form-item label="启用邮件通知">
          <el-switch v-model="notificationSettings.email_enabled" @change="onEmailToggle" />
        </el-form-item>
        
        <div v-if="notificationSettings.email_enabled" class="setting-group">
          <el-form-item label="SMTP服务器">
            <el-input v-model="notificationSettings.smtp_host" placeholder="smtp.example.com" />
          </el-form-item>
          
          <el-form-item label="SMTP端口">
            <el-input-number v-model="notificationSettings.smtp_port" :min="1" :max="65535" />
          </el-form-item>
          
          <el-form-item label="发送者邮箱">
            <el-input v-model="notificationSettings.smtp_from" placeholder="noreply@example.com" />
          </el-form-item>
          
          <el-form-item label="SMTP用户名">
            <el-input v-model="notificationSettings.smtp_username" placeholder="用户名" />
          </el-form-item>
          
          <el-form-item label="SMTP密码">
            <el-input v-model="notificationSettings.smtp_password" type="password" show-password placeholder="密码" />
          </el-form-item>
          
          <el-form-item label="启用TLS">
            <el-switch v-model="notificationSettings.smtp_tls" />
          </el-form-item>
        </div>
        
        <el-form-item label="启用飞书通知">
          <el-switch v-model="notificationSettings.feishu_enabled" @change="onFeishuToggle" />
        </el-form-item>
        
        <div v-if="notificationSettings.feishu_enabled" class="setting-group">
          <el-form-item label="Webhook URL">
            <el-input v-model="notificationSettings.feishu_webhook" placeholder="https://open.feishu.cn/open-apis/bot/v2/hook/..." />
          </el-form-item>
          
          <el-form-item label="签名密钥">
            <el-input v-model="notificationSettings.feishu_secret" type="password" show-password placeholder="签名密钥" />
          </el-form-item>
        </div>
        
        <el-form-item label="默认通知方式">
          <el-checkbox-group v-model="notificationSettings.default_methods">
            <el-checkbox label="email">邮件</el-checkbox>
            <el-checkbox label="feishu">飞书</el-checkbox>
            <el-checkbox label="sms">短信</el-checkbox>
            <el-checkbox label="webhook">Webhook</el-checkbox>
          </el-checkbox-group>
        </el-form-item>
        
        <el-form-item label="通知频率限制">
          <el-input-number 
            v-model="notificationSettings.rate_limit" 
            :min="1" 
            :max="100"
            style="width: 150px"
          />
          <span style="margin-left: 10px; color: var(--el-text-color-secondary)">次/分钟</span>
        </el-form-item>
      </el-form>
      
      <div class="form-actions">
        <el-button type="primary" @click="saveNotificationSettings">保存设置</el-button>
        <el-button @click="testNotification">测试通知</el-button>
        <el-button @click="resetNotificationSettings">重置</el-button>
      </div>
    </el-card>

    <!-- 性能设置 -->
    <el-card class="setting-card">
      <template #header>
        <h3>性能设置</h3>
      </template>
      
      <el-form :model="performanceSettings" label-width="150px">
        <el-form-item label="缓存过期时间">
          <el-input-number 
            v-model="performanceSettings.cache_ttl" 
            :min="60" 
            :max="3600"
            style="width: 150px"
          />
          <span style="margin-left: 10px; color: var(--el-text-color-secondary)">秒</span>
        </el-form-item>
        
        <el-form-item label="数据库连接池">
          <el-input-number 
            v-model="performanceSettings.db_pool_size" 
            :min="5" 
            :max="100"
            style="width: 150px"
          />
          <span style="margin-left: 10px; color: var(--el-text-color-secondary)">连接</span>
        </el-form-item>
        
        <el-form-item label="批量处理大小">
          <el-input-number 
            v-model="performanceSettings.batch_size" 
            :min="10" 
            :max="1000"
            style="width: 150px"
          />
          <span style="margin-left: 10px; color: var(--el-text-color-secondary)">条</span>
        </el-form-item>
        
        <el-form-item label="并发处理数">
          <el-input-number 
            v-model="performanceSettings.worker_threads" 
            :min="1" 
            :max="32"
            style="width: 150px"
          />
          <span style="margin-left: 10px; color: var(--el-text-color-secondary)">线程</span>
        </el-form-item>
        
        <el-form-item label="启用数据压缩">
          <el-switch v-model="performanceSettings.enable_compression" />
          <el-text size="small" type="info" style="margin-left: 10px">
            传输数据时启用gzip压缩
          </el-text>
        </el-form-item>
        
        <el-form-item label="启用查询优化">
          <el-switch v-model="performanceSettings.enable_query_optimization" />
          <el-text size="small" type="info" style="margin-left: 10px">
            自动优化数据库查询
          </el-text>
        </el-form-item>
      </el-form>
      
      <div class="form-actions">
        <el-button type="primary" @click="savePerformanceSettings">保存设置</el-button>
        <el-button @click="resetPerformanceSettings">重置</el-button>
      </div>
    </el-card>

    <!-- 安全设置 -->
    <el-card class="setting-card">
      <template #header>
        <h3>安全设置</h3>
      </template>
      
      <el-form :model="securitySettings" label-width="150px">
        <el-form-item label="会话过期时间">
          <el-input-number 
            v-model="securitySettings.session_timeout" 
            :min="30" 
            :max="1440"
            style="width: 150px"
          />
          <span style="margin-left: 10px; color: var(--el-text-color-secondary)">分钟</span>
        </el-form-item>
        
        <el-form-item label="密码最小长度">
          <el-input-number 
            v-model="securitySettings.password_min_length" 
            :min="6" 
            :max="32"
            style="width: 150px"
          />
          <span style="margin-left: 10px; color: var(--el-text-color-secondary)">位</span>
        </el-form-item>
        
        <el-form-item label="密码复杂度">
          <el-checkbox-group v-model="securitySettings.password_requirements">
            <el-checkbox label="uppercase">大写字母</el-checkbox>
            <el-checkbox label="lowercase">小写字母</el-checkbox>
            <el-checkbox label="numbers">数字</el-checkbox>
            <el-checkbox label="symbols">特殊字符</el-checkbox>
          </el-checkbox-group>
        </el-form-item>
        
        <el-form-item label="最大登录尝试">
          <el-input-number 
            v-model="securitySettings.max_login_attempts" 
            :min="3" 
            :max="10"
            style="width: 150px"
          />
          <span style="margin-left: 10px; color: var(--el-text-color-secondary)">次</span>
        </el-form-item>
        
        <el-form-item label="账户锁定时间">
          <el-input-number 
            v-model="securitySettings.lockout_duration" 
            :min="5" 
            :max="60"
            style="width: 150px"
          />
          <span style="margin-left: 10px; color: var(--el-text-color-secondary)">分钟</span>
        </el-form-item>
        
        <el-form-item label="启用双因子认证">
          <el-switch v-model="securitySettings.enable_2fa" />
          <el-text size="small" type="info" style="margin-left: 10px">
            推荐在生产环境中启用
          </el-text>
        </el-form-item>
        
        <el-form-item label="API访问频率限制">
          <el-input-number 
            v-model="securitySettings.api_rate_limit" 
            :min="100" 
            :max="10000"
            style="width: 150px"
          />
          <span style="margin-left: 10px; color: var(--el-text-color-secondary)">请求/小时</span>
        </el-form-item>
      </el-form>
      
      <div class="form-actions">
        <el-button type="primary" @click="saveSecuritySettings">保存设置</el-button>
        <el-button @click="resetSecuritySettings">重置</el-button>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { reactive } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'

// 通用设置
const generalSettings = reactive({
  system_name: '告警分析系统',
  system_description: '智能告警收集、分析和展示系统',
  timezone: 'Asia/Shanghai',
  default_language: 'zh-CN',
  data_retention_days: 90,
  maintenance_mode: false
})

// 告警设置
const alarmSettings = reactive({
  default_severity: 'medium',
  auto_resolve_hours: 24,
  duplicate_threshold: 3,
  correlation_window: 5,
  enable_grouping: true,
  enable_suppression: false
})

// 通知设置
const notificationSettings = reactive({
  email_enabled: true,
  smtp_host: 'smtp.example.com',
  smtp_port: 587,
  smtp_from: 'noreply@example.com',
  smtp_username: '',
  smtp_password: '',
  smtp_tls: true,
  feishu_enabled: false,
  feishu_webhook: '',
  feishu_secret: '',
  default_methods: ['email'],
  rate_limit: 60
})

// 性能设置
const performanceSettings = reactive({
  cache_ttl: 300,
  db_pool_size: 20,
  batch_size: 100,
  worker_threads: 4,
  enable_compression: true,
  enable_query_optimization: true
})

// 安全设置
const securitySettings = reactive({
  session_timeout: 120,
  password_min_length: 8,
  password_requirements: ['lowercase', 'numbers'],
  max_login_attempts: 5,
  lockout_duration: 15,
  enable_2fa: false,
  api_rate_limit: 1000
})

// 保存通用设置
const saveGeneralSettings = async () => {
  try {
    console.log('保存通用设置:', generalSettings)
    ElMessage.success('通用设置保存成功')
  } catch (error) {
    console.error('保存通用设置失败:', error)
    ElMessage.error('保存失败')
  }
}

// 重置通用设置
const resetGeneralSettings = () => {
  Object.assign(generalSettings, {
    system_name: '告警分析系统',
    system_description: '智能告警收集、分析和展示系统',
    timezone: 'Asia/Shanghai',
    default_language: 'zh-CN',
    data_retention_days: 90,
    maintenance_mode: false
  })
}

// 保存告警设置
const saveAlarmSettings = async () => {
  try {
    console.log('保存告警设置:', alarmSettings)
    ElMessage.success('告警设置保存成功')
  } catch (error) {
    console.error('保存告警设置失败:', error)
    ElMessage.error('保存失败')
  }
}

// 重置告警设置
const resetAlarmSettings = () => {
  Object.assign(alarmSettings, {
    default_severity: 'medium',
    auto_resolve_hours: 24,
    duplicate_threshold: 3,
    correlation_window: 5,
    enable_grouping: true,
    enable_suppression: false
  })
}

// 保存通知设置
const saveNotificationSettings = async () => {
  try {
    console.log('保存通知设置:', notificationSettings)
    ElMessage.success('通知设置保存成功')
  } catch (error) {
    console.error('保存通知设置失败:', error)
    ElMessage.error('保存失败')
  }
}

// 测试通知
const testNotification = async () => {
  try {
    console.log('测试通知设置')
    ElMessage.success('测试通知发送成功')
  } catch (error) {
    console.error('测试通知失败:', error)
    ElMessage.error('测试通知失败')
  }
}

// 重置通知设置
const resetNotificationSettings = () => {
  Object.assign(notificationSettings, {
    email_enabled: true,
    smtp_host: 'smtp.example.com',
    smtp_port: 587,
    smtp_from: 'noreply@example.com',
    smtp_username: '',
    smtp_password: '',
    smtp_tls: true,
    feishu_enabled: false,
    feishu_webhook: '',
    feishu_secret: '',
    default_methods: ['email'],
    rate_limit: 60
  })
}

// 保存性能设置
const savePerformanceSettings = async () => {
  try {
    console.log('保存性能设置:', performanceSettings)
    ElMessage.success('性能设置保存成功')
  } catch (error) {
    console.error('保存性能设置失败:', error)
    ElMessage.error('保存失败')
  }
}

// 重置性能设置
const resetPerformanceSettings = () => {
  Object.assign(performanceSettings, {
    cache_ttl: 300,
    db_pool_size: 20,
    batch_size: 100,
    worker_threads: 4,
    enable_compression: true,
    enable_query_optimization: true
  })
}

// 保存安全设置
const saveSecuritySettings = async () => {
  try {
    console.log('保存安全设置:', securitySettings)
    ElMessage.success('安全设置保存成功')
  } catch (error) {
    console.error('保存安全设置失败:', error)
    ElMessage.error('保存失败')
  }
}

// 重置安全设置
const resetSecuritySettings = () => {
  Object.assign(securitySettings, {
    session_timeout: 120,
    password_min_length: 8,
    password_requirements: ['lowercase', 'numbers'],
    max_login_attempts: 5,
    lockout_duration: 15,
    enable_2fa: false,
    api_rate_limit: 1000
  })
}

// 邮件切换处理
const onEmailToggle = (enabled) => {
  if (!enabled) {
    notificationSettings.default_methods = notificationSettings.default_methods.filter(m => m !== 'email')
  } else if (!notificationSettings.default_methods.includes('email')) {
    notificationSettings.default_methods.push('email')
  }
}

// 飞书切换处理
const onFeishuToggle = (enabled) => {
  if (!enabled) {
    notificationSettings.default_methods = notificationSettings.default_methods.filter(m => m !== 'feishu')
  } else if (!notificationSettings.default_methods.includes('feishu')) {
    notificationSettings.default_methods.push('feishu')
  }
}
</script>

<style lang="scss" scoped>
.settings {
  .setting-card {
    margin-bottom: 20px;
    
    h3 {
      margin: 0;
      color: var(--el-text-color-primary);
    }
    
    .setting-group {
      margin-left: 20px;
      padding: 15px;
      background-color: var(--el-fill-color-lighter);
      border-radius: 8px;
      border-left: 3px solid var(--el-color-primary);
    }
    
    .form-actions {
      margin-top: 20px;
      padding-top: 20px;
      border-top: 1px solid var(--el-border-color);
      text-align: right;
      
      .el-button {
        margin-left: 10px;
      }
    }
  }
}
</style>