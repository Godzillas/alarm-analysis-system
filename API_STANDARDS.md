# 告警分析系统 API 代码规范

## 📋 目录
1. [API路径规范](#api路径规范)
2. [HTTP方法规范](#http方法规范) 
3. [响应格式规范](#响应格式规范)
4. [错误处理规范](#错误处理规范)
5. [前后端对应规范](#前后端对应规范)
6. [命名规范](#命名规范)
7. [文档规范](#文档规范)

## 🛤️ API路径规范

### 基础路径结构
```
http://localhost:8000/api/{resource}/{id?}/{action?}
```

### 路径格式规则

#### 1. 末尾斜杠规则
- **列表端点**: 必须使用末尾斜杠 `/`
- **单个资源端点**: 不使用末尾斜杠
- **操作端点**: 不使用末尾斜杠

```bash
✅ 正确示例:
GET  /api/alarms/           # 获取告警列表
GET  /api/alarms/{id}       # 获取单个告警
POST /api/alarms/{id}/acknowledge  # 确认告警

❌ 错误示例:
GET  /api/alarms            # 缺少末尾斜杠
GET  /api/alarms/{id}/      # 不应有末尾斜杠
POST /api/alarms/{id}/acknowledge/  # 不应有末尾斜杠
```

#### 2. 资源命名规则
- 使用复数形式: `alarms`, `endpoints`, `users`
- 使用小写字母和连字符: `contact-points`, `alert-templates`
- 避免下划线: ❌ `contact_points` ✅ `contact-points`

#### 3. 嵌套资源规则
```bash
# 标准嵌套格式
GET /api/users/{user_id}/subscriptions/
POST /api/endpoints/{id}/test
GET /api/teams/{team_id}/members/
```

### 完整路径映射表

| 功能模块 | 后端路由前缀 | 前端API文件 | 列表端点 | 备注 |
|---------|-------------|------------|----------|------|
| 告警管理 | `/api/alarms` | `alarm.js` | `/api/alarms/` | ✅ |
| 接入点管理 | `/api/endpoints` | `endpoint.js` | `/api/endpoints/` | ✅ |
| 用户管理 | `/api/users` | `user.js` | `/api/users/` | ✅ |
| 系统管理 | `/api/systems` | `system.js` | `/api/systems/` | ✅ |
| 联络点管理 | `/api/contact-points` | `contactPoint.js` | `/api/contact-points/` | ✅ |
| 告警模板 | `/api/alert-templates` | `alertTemplate.js` | `/api/alert-templates/` | ✅ |
| 解决方案 | `/api/solutions` | `solutions.js` | `/api/solutions/` | ✅ |
| 订阅管理 | `/api/subscriptions` | `subscriptions.js` | `/api/subscriptions/` | ✅ |
| 抑制管理 | `/api/suppressions` | `suppression.js` | `/api/suppressions/` | ✅ |
| 权限管理 | `/api/rbac` | `rbac.js` | 各子模块不同 | ✅ |
| 健康监控 | `/api/health` | `health.js` | `/api/health/` | ✅ |
| 分析统计 | `/api/analytics` | `analytics.js` | 多个端点 | ✅ |

## 🔧 HTTP方法规范

### RESTful方法映射
```bash
# 标准CRUD操作
GET    /api/resources/          # 获取资源列表
GET    /api/resources/{id}      # 获取单个资源
POST   /api/resources/          # 创建新资源
PUT    /api/resources/{id}      # 完整更新资源
PATCH  /api/resources/{id}      # 部分更新资源
DELETE /api/resources/{id}      # 删除资源

# 操作端点
POST   /api/resources/{id}/action    # 执行特定操作
GET    /api/resources/{id}/stats     # 获取统计信息
POST   /api/resources/{id}/test      # 测试资源
```

### 批量操作规范
```bash
POST /api/resources/batch           # 批量创建
PUT  /api/resources/batch           # 批量更新  
DELETE /api/resources/batch         # 批量删除
POST /api/resources/batch-test      # 批量测试
```

## 📊 响应格式规范

### 统一响应包装器

#### 1. 单个资源响应
```json
{
  "data": { /* 资源对象 */ },
  "message": "操作成功",
  "status": "success",
  "timestamp": "2025-06-27T08:00:00Z"
}
```

#### 2. 列表响应（分页）
```json
{
  "data": [ /* 资源数组 */ ],
  "total": 100,
  "page": 1,
  "page_size": 20,
  "pages": 5,
  "message": "获取成功",
  "status": "success"
}
```

#### 3. 操作响应
```json
{
  "data": { "id": 123, "affected_rows": 1 },
  "message": "操作成功",
  "status": "success"
}
```

### 分页参数标准
```bash
# 查询参数
?page=1              # 页码（从1开始）
&page_size=20        # 每页大小（默认20，最大100）
&search=keyword      # 搜索关键词
&sort=created_at     # 排序字段
&order=desc          # 排序方向（asc/desc）
```

## ❌ 错误处理规范

### HTTP状态码使用
```bash
200 OK              # 请求成功
201 Created         # 创建成功
204 No Content      # 删除成功
400 Bad Request     # 请求参数错误
401 Unauthorized    # 未授权
403 Forbidden       # 禁止访问
404 Not Found       # 资源不存在
422 Unprocessable Entity  # 数据验证失败
500 Internal Server Error # 服务器内部错误
```

### 错误响应格式
```json
{
  "detail": "错误详细信息",
  "message": "用户友好的错误消息",
  "status": "error",
  "error_code": "VALIDATION_ERROR",
  "timestamp": "2025-06-27T08:00:00Z",
  "errors": [  // 字段级别错误（可选）
    {
      "field": "email",
      "message": "邮箱格式不正确"
    }
  ]
}
```

## 🔄 前后端对应规范

### 1. API文件命名对应
```bash
后端路由文件: src/api/{module}.py
前端API文件: frontend/src/api/{module}.js
```

### 2. 方法命名对应
```javascript
// 前端API方法命名模式
export function get{Resources}(params = {})      // 获取列表
export function get{Resource}(id)               // 获取单个
export function create{Resource}(data)          // 创建
export function update{Resource}(id, data)      // 更新
export function delete{Resource}(id)            // 删除
export function {action}{Resource}(id, data)    // 操作方法
```

### 3. Store方法命名对应
```javascript
// Pinia Store方法命名模式
async fetch{Resources}(params = {})      // 获取列表
async fetch{Resource}(id)               // 获取单个  
async create{Resource}(data)            // 创建
async update{Resource}(id, data)        // 更新
async delete{Resource}(id)              // 删除
```

## 🏷️ 命名规范

### 1. 资源名称规范
```bash
# 英文资源名（URL用）
alarms          # 告警
endpoints       # 接入点
users           # 用户  
systems         # 系统
contact-points  # 联络点
alert-templates # 告警模板
solutions       # 解决方案
subscriptions   # 订阅
suppressions    # 抑制
analytics       # 分析
health          # 健康检查
```

### 2. 字段命名规范
```json
{
  "id": 1,                    // 主键ID
  "created_at": "...",        // 创建时间
  "updated_at": "...",        // 更新时间
  "is_enabled": true,         // 布尔值前缀is_
  "total_count": 100,         // 总数前缀total_
  "last_used_at": "...",      // 最后使用时间
  "endpoint_type": "webhook"  // 枚举类型后缀_type
}
```

### 3. 操作方法命名
```bash
# 标准操作动词
test            # 测试
enable/disable  # 启用/禁用
start/stop      # 启动/停止
pause/resume    # 暂停/恢复
acknowledge     # 确认
resolve         # 解决
approve         # 审批
retry           # 重试
export          # 导出
import          # 导入
sync            # 同步
refresh         # 刷新
```

## 📚 文档规范

### 1. API注释规范
```python
@router.get("/", response_model=PaginatedResponse[ResourceResponse])
async def list_resources(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页大小"),
    search: Optional[str] = Query(None, description="搜索关键词"),
    enabled: Optional[bool] = Query(None, description="是否启用")
):
    """
    获取资源列表
    
    支持分页查询和条件过滤
    """
```

### 2. 前端API注释规范
```javascript
/**
 * 获取资源列表
 * @param {Object} params - 查询参数
 * @param {number} params.page - 页码
 * @param {number} params.page_size - 每页大小
 * @param {string} params.search - 搜索关键词
 * @returns {Promise<Object>} 分页资源列表
 */
export function getResources(params = {}) {
  return request({
    url: '/resources/',
    method: 'get',
    params
  })
}
```

## 🔍 代码检查清单

### 后端检查项
- [ ] 路由路径是否符合末尾斜杠规则
- [ ] 响应格式是否使用标准包装器
- [ ] 分页参数是否标准化
- [ ] 错误处理是否完整
- [ ] API文档是否完善

### 前端检查项  
- [ ] API路径是否与后端完全匹配
- [ ] 方法命名是否遵循规范
- [ ] 错误处理是否完整
- [ ] 类型定义是否准确
- [ ] 注释文档是否完善

### 测试检查项
- [ ] API端点是否全部可访问
- [ ] 参数验证是否正确
- [ ] 错误场景是否覆盖
- [ ] 响应格式是否一致

---

## 🚀 实施步骤

1. **修复现有不一致问题**
2. **建立自动化检查工具**  
3. **更新开发文档**
4. **团队培训和宣贯**
5. **持续监控和改进**

遵循此规范可确保API的一致性、可维护性和开发效率。