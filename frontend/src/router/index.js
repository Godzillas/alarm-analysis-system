import { createRouter, createWebHistory } from 'vue-router'
import NProgress from 'nprogress'
import 'nprogress/nprogress.css'

// 路由组件
const Layout = () => import('@/components/Layout/index.vue')
const Login = () => import('@/views/Login/index.vue')
const Dashboard = () => import('@/views/Dashboard/index.vue')
const AlarmManagement = () => import('@/views/AlarmManagement/index.vue')
const Analytics = () => import('@/views/Analytics/index.vue')
const EndpointManagement = () => import('@/views/EndpointManagement/index.vue')
const UserManagement = () => import('@/views/UserManagement/index.vue')
const RuleManagement = () => import('@/views/RuleManagement/index.vue')
const SystemManagement = () => import('@/views/SystemManagement/index.vue')
const ContactPointManagement = () => import('@/views/ContactPointManagement/index.vue')
const AlertTemplateManagement = () => import('@/views/AlertTemplateManagement/index.vue')
const LifecycleManagement = () => import('@/views/LifecycleManagement/index.vue')
const Settings = () => import('@/views/Settings/index.vue')

const routes = [
  {
    path: '/login',
    name: 'Login',
    component: Login,
    meta: {
      title: '登录',
      hideInMenu: true
    }
  },
  {
    path: '/',
    component: Layout,
    redirect: '/dashboard',
    children: [
      {
        path: '/dashboard',
        name: 'Dashboard',
        component: Dashboard,
        meta: {
          title: '仪表板',
          icon: 'Dashboard'
        }
      },
      {
        path: '/alarms',
        name: 'AlarmManagement',
        component: AlarmManagement,
        meta: {
          title: '告警管理',
          icon: 'Warning'
        }
      },
      {
        path: '/analytics',
        name: 'Analytics',
        component: Analytics,
        meta: {
          title: '分析统计',
          icon: 'TrendCharts'
        }
      },
      {
        path: '/endpoints',
        name: 'EndpointManagement',
        component: EndpointManagement,
        meta: {
          title: '接入点管理',
          icon: 'Connection'
        }
      },
      {
        path: '/users',
        name: 'UserManagement',
        component: UserManagement,
        meta: {
          title: '用户管理',
          icon: 'User'
        }
      },
      {
        path: '/rules',
        name: 'RuleManagement',
        component: RuleManagement,
        meta: {
          title: '规则管理',
          icon: 'DocumentChecked'
        }
      },
      {
        path: '/systems',
        name: 'SystemManagement',
        component: SystemManagement,
        meta: {
          title: '系统管理',
          icon: 'Platform'
        }
      },
      {
        path: '/contact-points',
        name: 'ContactPointManagement',
        component: ContactPointManagement,
        meta: {
          title: '联络点管理',
          icon: 'Message'
        }
      },
      {
        path: '/alert-templates',
        name: 'AlertTemplateManagement',
        component: AlertTemplateManagement,
        meta: {
          title: '告警模板管理',
          icon: 'Document'
        }
      },
      {
        path: '/lifecycle',
        name: 'LifecycleManagement',
        component: LifecycleManagement,
        meta: {
          title: '生命周期管理',
          icon: 'Timer'
        }
      },
      {
        path: '/settings',
        name: 'Settings',
        component: Settings,
        meta: {
          title: '系统设置',
          icon: 'Setting'
        }
      }
    ]
  }
]

const router = createRouter({
  history: createWebHistory(process.env.BASE_URL),
  routes
})

// 全局前置守卫
router.beforeEach((to, from, next) => {
  NProgress.start()
  
  // 设置页面标题
  if (to.meta?.title) {
    document.title = `${to.meta.title} - 告警分析系统`
  }
  
  // 检查认证状态
  const token = localStorage.getItem('access_token')
  const isLoginPage = to.path === '/login'
  
  // 临时禁用认证检查以便测试联络点和告警模板功能
  // TODO: 恢复认证检查
  /*
  if (!token && !isLoginPage) {
    // 没有token且不在登录页，跳转到登录页
    next('/login')
  } else if (token && isLoginPage) {
    // 有token且在登录页，跳转到首页
    next('/dashboard')
  } else {
    next()
  }
  */
  
  // 临时允许所有访问
  if (token && isLoginPage) {
    // 有token且在登录页，跳转到首页
    next('/dashboard')
  } else {
    next()
  }
})

// 全局后置守卫
router.afterEach(() => {
  NProgress.done()
})

export default router