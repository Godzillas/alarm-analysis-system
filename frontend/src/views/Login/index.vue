<template>
  <div class="login-container">
    <div class="login-form">
      <div class="logo-section">
        <h1>告警分析系统</h1>
        <p>Alarm Analysis System</p>
      </div>
      
      <el-form 
        ref="loginFormRef" 
        :model="loginForm" 
        :rules="rules" 
        class="login-form-content"
        @submit.prevent="handleLogin"
      >
        <el-form-item prop="username">
          <el-input
            v-model="loginForm.username"
            placeholder="用户名"
            size="large"
            :prefix-icon="User"
            @keyup.enter="handleLogin"
          />
        </el-form-item>
        
        <el-form-item prop="password">
          <el-input
            v-model="loginForm.password"
            type="password"
            placeholder="密码"
            size="large"
            :prefix-icon="Lock"
            show-password
            @keyup.enter="handleLogin"
          />
        </el-form-item>
        
        <el-form-item>
          <el-button 
            type="primary" 
            size="large" 
            class="login-btn"
            :loading="loading"
            @click="handleLogin"
          >
            {{ loading ? '登录中...' : '登录' }}
          </el-button>
        </el-form-item>
      </el-form>
      
      <div class="quick-login">
        <el-divider>快速登录</el-divider>
        <el-button 
          size="small" 
          type="info" 
          @click="quickLogin"
        >
          使用默认管理员账户
        </el-button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { User, Lock } from '@element-plus/icons-vue'
import request from '@/api/request'

const router = useRouter()
const loginFormRef = ref()
const loading = ref(false)

const loginForm = reactive({
  username: '',
  password: ''
})

const rules = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' }
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, message: '密码长度不能少于6位', trigger: 'blur' }
  ]
}

const handleLogin = async () => {
  if (!loginFormRef.value) return
  
  try {
    await loginFormRef.value.validate()
    loading.value = true
    
    const response = await request.post('/auth/login', {
      username: loginForm.username,
      password: loginForm.password
    })
    
    // 存储token
    localStorage.setItem('access_token', response.access_token)
    localStorage.setItem('token_type', response.token_type)
    
    ElMessage.success('登录成功')
    router.push('/dashboard')
    
  } catch (error) {
    console.error('登录失败:', error)
    if (error.response && error.response.status === 401) {
      ElMessage.error('用户名或密码错误')
    } else {
      ElMessage.error('登录失败，请稍后重试')
    }
  } finally {
    loading.value = false
  }
}

const quickLogin = () => {
  loginForm.username = 'admin'
  loginForm.password = 'admin123'
  handleLogin()
}
</script>

<style scoped>
.login-container {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}

.login-form {
  width: 400px;
  padding: 40px;
  background: white;
  border-radius: 10px;
  box-shadow: 0 10px 25px rgba(0, 0, 0, 0.1);
}

.logo-section {
  text-align: center;
  margin-bottom: 30px;
}

.logo-section h1 {
  margin: 0;
  font-size: 24px;
  color: #333;
  font-weight: 600;
}

.logo-section p {
  margin: 5px 0 0 0;
  color: #666;
  font-size: 14px;
}

.login-form-content {
  margin-bottom: 20px;
}

.login-btn {
  width: 100%;
}

.quick-login {
  text-align: center;
}

.quick-login .el-button {
  font-size: 12px;
}
</style>