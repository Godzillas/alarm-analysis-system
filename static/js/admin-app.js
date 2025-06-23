/**
 * 管理后台应用逻辑
 */

class AdminApp {
    constructor() {
        this.currentSection = 'dashboard';
        this.refreshInterval = 30000; // 30秒
        this.charts = new Map();
        this.tables = new Map();
        this.refreshTimers = new Map();
        this.websocket = null;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
        this.init();
    }

    init() {
        this.setupNavigation();
        this.setupEventListeners();
        this.loadInitialData();
        this.startAutoRefresh();
        this.setupWebSocket();
    }

    setupNavigation() {
        document.querySelectorAll('.nav-item').forEach(item => {
            item.addEventListener('click', (e) => {
                e.preventDefault();
                const section = item.dataset.section;
                this.showSection(section);
            });
        });
    }

    setupEventListeners() {
        // 主题切换
        const themeSelect = document.getElementById('theme-select');
        if (themeSelect) {
            themeSelect.value = window.framework.getState('theme') || 'light';
            themeSelect.addEventListener('change', (e) => {
                window.framework.setTheme(e.target.value);
            });
        }

        // 刷新间隔设置
        const refreshSelect = document.getElementById('refresh-interval');
        if (refreshSelect) {
            refreshSelect.value = this.refreshInterval / 1000;
            refreshSelect.addEventListener('change', (e) => {
                this.refreshInterval = parseInt(e.target.value) * 1000;
                this.restartAutoRefresh();
            });
        }
    }

    showSection(section) {
        // 更新导航状态
        document.querySelectorAll('.nav-item').forEach(item => {
            item.classList.remove('active');
            if (item.dataset.section === section) {
                item.classList.add('active');
            }
        });

        // 隐藏所有区域
        document.querySelectorAll('.section').forEach(s => s.classList.add('hidden'));

        // 显示选中区域
        const sectionElement = document.getElementById(section + '-section');
        if (sectionElement) {
            sectionElement.classList.remove('hidden');
        }

        // 更新页面标题
        const titles = {
            dashboard: '仪表板概览',
            alarms: '告警管理',
            analytics: '分析统计',
            endpoints: '接入点管理',
            users: '用户管理',
            rules: '规则管理',
            settings: '系统设置'
        };
        
        const pageTitle = document.getElementById('page-title');
        if (pageTitle) {
            pageTitle.textContent = titles[section] || '告警管理平台';
        }

        this.currentSection = section;

        // 加载对应区域的数据
        this.loadSectionData(section);
    }

    async loadInitialData() {
        await this.loadDashboardData();
    }

    async loadSectionData(section) {
        switch (section) {
            case 'dashboard':
                await this.loadDashboardData();
                break;
            case 'alarms':
                await this.loadAlarmsData();
                break;
            case 'analytics':
                await this.loadAnalyticsData();
                break;
            case 'endpoints':
                await this.loadEndpointsData();
                break;
            case 'users':
                await this.loadUsersData();
                break;
            case 'rules':
                await this.loadRulesData();
                break;
        }
    }

    async loadDashboardData() {
        try {
            // 加载告警统计
            const stats = await window.framework.request('/api/alarms/stats/summary');
            this.updateDashboardStats(stats);

            // 加载最新告警
            const recentAlarms = await window.framework.request('/api/alarms/?limit=10');
            this.updateRecentAlarmsTable(recentAlarms);

            // 加载图表数据
            await this.loadDashboardCharts();

        } catch (error) {
            console.error('Failed to load dashboard data:', error);
            window.framework.showNotification('加载仪表板数据失败', 'error');
        }
    }

    updateDashboardStats(stats) {
        document.getElementById('total-alarms').textContent = window.framework.formatNumber(stats.total || 0);
        document.getElementById('active-alarms').textContent = window.framework.formatNumber(stats.active || 0);
        document.getElementById('resolved-alarms').textContent = window.framework.formatNumber(stats.resolved || 0);
        document.getElementById('critical-alarms').textContent = window.framework.formatNumber(stats.critical || 0);

        // 更新侧边栏徽章
        const badge = document.getElementById('active-alarms-badge');
        if (badge) {
            badge.textContent = stats.active || 0;
            badge.style.display = stats.active > 0 ? 'inline' : 'none';
        }
    }

    updateRecentAlarmsTable(alarms) {
        const container = document.getElementById('recent-alarms-table');
        if (!container) return;

        const columns = [
            { key: 'title', title: '告警标题' },
            { key: 'source', title: '来源' },
            { key: 'severity', title: '严重程度', type: 'badge' },
            { key: 'status', title: '状态', type: 'badge' },
            { key: 'created_at', title: '创建时间', type: 'date' },
            { 
                key: 'actions', 
                title: '操作',
                render: (value, row) => `
                    <button class="btn btn-sm btn-primary" onclick="viewAlarmDetail(${row.id})">查看</button>
                    ${row.status === 'active' ? `<button class="btn btn-sm btn-success" onclick="resolveAlarm(${row.id})">解决</button>` : ''}
                `
            }
        ];

        if (!this.tables.has('recent-alarms')) {
            this.tables.set('recent-alarms', new DataTable(container, {
                data: alarms,
                columns: columns,
                pageSize: 5,
                filterable: false
            }));
        } else {
            this.tables.get('recent-alarms').updateData(alarms);
        }
    }

    async loadDashboardCharts() {
        try {
            // 告警趋势图
            const trendsData = await window.framework.request('/api/analytics/trends?time_range=24h&interval=1h');
            this.renderTrendChart(trendsData);

            // 严重程度分布图
            const summaryData = await window.framework.request('/api/analytics/summary?time_range=24h');
            this.renderSeverityChart(summaryData);

        } catch (error) {
            console.error('Failed to load chart data:', error);
        }
    }

    renderTrendChart(data) {
        const container = document.getElementById('alarm-trend-chart');
        if (!container || !data.timeline) return;

        const chartData = data.timeline.map(item => item.count);
        const labels = data.timeline.map(item => {
            const date = new Date(item.time);
            return date.getHours() + ':00';
        });

        if (!this.charts.has('trend')) {
            this.charts.set('trend', new SimpleChart(container, {
                type: 'bar',
                data: chartData,
                labels: labels,
                colors: ['#2563eb', '#10b981', '#f59e0b', '#ef4444']
            }));
        } else {
            this.charts.get('trend').updateData(chartData, labels);
        }
    }

    renderSeverityChart(data) {
        const container = document.getElementById('severity-chart');
        if (!container || !data.by_severity) return;

        const severityData = data.by_severity;
        const chartData = [
            severityData.critical || 0,
            severityData.high || 0,
            severityData.medium || 0,
            severityData.low || 0,
            severityData.info || 0
        ];
        const labels = ['严重', '高级', '中级', '低级', '信息'];
        const colors = ['#dc2626', '#ea580c', '#d97706', '#16a34a', '#0891b2'];

        if (!this.charts.has('severity')) {
            this.charts.set('severity', new SimpleChart(container, {
                type: 'pie',
                data: chartData,
                labels: labels,
                colors: colors
            }));
        } else {
            this.charts.get('severity').updateData(chartData, labels);
        }
    }

    async loadAlarmsData() {
        try {
            const alarms = await window.framework.request('/api/alarms/?limit=50');
            this.updateAlarmsTable(alarms);
        } catch (error) {
            console.error('Failed to load alarms data:', error);
            window.framework.showNotification('加载告警数据失败', 'error');
        }
    }

    updateAlarmsTable(alarms) {
        const container = document.getElementById('alarms-table');
        if (!container) return;

        const columns = [
            { key: 'id', title: 'ID' },
            { key: 'title', title: '告警标题' },
            { key: 'source', title: '来源' },
            { key: 'severity', title: '严重程度', type: 'badge' },
            { key: 'status', title: '状态', type: 'badge' },
            { key: 'host', title: '主机' },
            { key: 'created_at', title: '创建时间', type: 'date' },
            { 
                key: 'actions', 
                title: '操作',
                render: (value, row) => `
                    <button class="btn btn-sm btn-primary" onclick="viewAlarmDetail(${row.id})">查看</button>
                    ${row.status === 'active' ? `<button class="btn btn-sm btn-success" onclick="resolveAlarm(${row.id})">解决</button>` : ''}
                    <button class="btn btn-sm btn-danger" onclick="deleteAlarm(${row.id})">删除</button>
                `
            }
        ];

        if (!this.tables.has('alarms')) {
            this.tables.set('alarms', new DataTable(container, {
                data: alarms,
                columns: columns,
                pageSize: 20
            }));
        } else {
            this.tables.get('alarms').updateData(alarms);
        }
    }

    async loadAnalyticsData() {
        try {
            // 加载TOP告警源
            const topData = await window.framework.request('/api/analytics/top?time_range=24h&limit=10');
            this.renderTopSourcesChart(topData);

        } catch (error) {
            console.error('Failed to load analytics data:', error);
            window.framework.showNotification('加载分析数据失败', 'error');
        }
    }

    renderTopSourcesChart(data) {
        const container = document.getElementById('top-sources-chart');
        if (!container || !data.frequent_alarms) return;

        const chartData = data.frequent_alarms.slice(0, 5).map(item => item.count);
        const labels = data.frequent_alarms.slice(0, 5).map(item => item.source);

        if (!this.charts.has('top-sources')) {
            this.charts.set('top-sources', new SimpleChart(container, {
                type: 'bar',
                data: chartData,
                labels: labels,
                colors: ['#2563eb', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6']
            }));
        } else {
            this.charts.get('top-sources').updateData(chartData, labels);
        }
    }

    async loadEndpointsData() {
        try {
            const endpoints = await window.framework.request('/api/endpoints/');
            this.updateEndpointsTable(endpoints);
        } catch (error) {
            console.error('Failed to load endpoints data:', error);
            window.framework.showNotification('加载接入点数据失败', 'error');
        }
    }

    updateEndpointsTable(endpoints) {
        const container = document.getElementById('endpoints-table');
        if (!container) return;

        const columns = [
            { key: 'name', title: '名称' },
            { key: 'endpoint_type', title: '类型' },
            { key: 'enabled', title: '状态', render: (value) => value ? '<span class="badge badge-low">启用</span>' : '<span class="badge badge-medium">禁用</span>' },
            { key: 'created_at', title: '创建时间', type: 'date' },
            { 
                key: 'actions', 
                title: '操作',
                render: (value, row) => `
                    <button class="btn btn-sm btn-primary" onclick="testEndpoint(${row.id})">测试</button>
                    <button class="btn btn-sm btn-secondary" onclick="editEndpoint(${row.id})">编辑</button>
                    <button class="btn btn-sm btn-danger" onclick="deleteEndpoint(${row.id})">删除</button>
                `
            }
        ];

        if (!this.tables.has('endpoints')) {
            this.tables.set('endpoints', new DataTable(container, {
                data: endpoints,
                columns: columns,
                pageSize: 15
            }));
        } else {
            this.tables.get('endpoints').updateData(endpoints);
        }
    }

    async loadUsersData() {
        try {
            const users = await window.framework.request('/api/users/');
            this.updateUsersTable(users);
        } catch (error) {
            console.error('Failed to load users data:', error);
            window.framework.showNotification('加载用户数据失败', 'error');
        }
    }

    updateUsersTable(users) {
        const container = document.getElementById('users-table');
        if (!container) return;

        const columns = [
            { key: 'username', title: '用户名' },
            { key: 'email', title: '邮箱' },
            { key: 'full_name', title: '全名' },
            { key: 'is_active', title: '状态', render: (value) => value ? '<span class="badge badge-low">活跃</span>' : '<span class="badge badge-medium">禁用</span>' },
            { key: 'is_admin', title: '角色', render: (value) => value ? '<span class="badge badge-high">管理员</span>' : '<span class="badge badge-info">用户</span>' },
            { key: 'created_at', title: '创建时间', type: 'date' },
            { 
                key: 'actions', 
                title: '操作',
                render: (value, row) => `
                    <button class="btn btn-sm btn-secondary" onclick="editUser(${row.id})">编辑</button>
                    <button class="btn btn-sm btn-danger" onclick="deleteUser(${row.id})">删除</button>
                `
            }
        ];

        if (!this.tables.has('users')) {
            this.tables.set('users', new DataTable(container, {
                data: users,
                columns: columns,
                pageSize: 15
            }));
        } else {
            this.tables.get('users').updateData(users);
        }
    }

    async loadRulesData() {
        try {
            const stats = await window.framework.request('/api/rules/stats');
            this.updateRuleStats(stats);
        } catch (error) {
            console.error('Failed to load rules data:', error);
            window.framework.showNotification('加载规则数据失败', 'error');
        }
    }

    updateRuleStats(stats) {
        const container = document.getElementById('rule-stats');
        if (!container) return;

        container.innerHTML = `
            <div class="grid grid-cols-3">
                <div class="stat-card">
                    <div class="stat-header">
                        <div class="stat-title">规则组数量</div>
                        <div class="stat-icon">
                            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                <path d="M9 12l2 2 4-4"></path>
                                <path d="M21 12c-1 0-3-1-3-3s2-3 3-3 3 1 3 3-2 3-3 3"></path>
                                <path d="M3 12c1 0 3-1 3-3s-2-3-3-3-3 1-3 3 2 3 3 3"></path>
                                <path d="M13 12h3"></path>
                                <path d="M8 12H5"></path>
                            </svg>
                        </div>
                    </div>
                    <div class="stat-value">${stats.active_groups || 0}</div>
                </div>
                
                <div class="stat-card">
                    <div class="stat-header">
                        <div class="stat-title">活跃规则</div>
                        <div class="stat-icon">
                            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                <polyline points="9,11 12,14 22,4"></polyline>
                                <path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11"></path>
                            </svg>
                        </div>
                    </div>
                    <div class="stat-value">${stats.active_rules || 0}</div>
                </div>
                
                <div class="stat-card">
                    <div class="stat-header">
                        <div class="stat-title">规则状态</div>
                        <div class="stat-icon">
                            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                <circle cx="12" cy="12" r="10"></circle>
                                <polyline points="12,6 12,12 16,14"></polyline>
                            </svg>
                        </div>
                    </div>
                    <div class="stat-value">
                        <span class="badge badge-low">运行中</span>
                    </div>
                </div>
            </div>
            
            <div style="margin-top: 2rem;">
                <h4>规则组列表</h4>
                <p class="text-gray-600">暂无规则组数据，可通过API创建规则组。</p>
            </div>
        `;
    }

    startAutoRefresh() {
        this.stopAutoRefresh();
        
        const refreshTimer = setInterval(() => {
            if (this.currentSection === 'dashboard') {
                this.loadDashboardData();
            }
        }, this.refreshInterval);
        
        this.refreshTimers.set('main', refreshTimer);
    }

    stopAutoRefresh() {
        this.refreshTimers.forEach(timer => clearInterval(timer));
        this.refreshTimers.clear();
    }

    restartAutoRefresh() {
        this.stopAutoRefresh();
        this.startAutoRefresh();
    }

    setupWebSocket() {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws/ws/dashboard`;
        
        try {
            this.websocket = new WebSocket(wsUrl);
            
            this.websocket.onopen = () => {
                console.log('WebSocket连接建立');
                this.reconnectAttempts = 0;
                window.framework.showNotification('实时数据连接建立', 'success');
            };
            
            this.websocket.onmessage = (event) => {
                try {
                    const message = JSON.parse(event.data);
                    this.handleWebSocketMessage(message);
                } catch (error) {
                    console.error('处理WebSocket消息失败:', error);
                }
            };
            
            this.websocket.onclose = () => {
                console.log('WebSocket连接关闭');
                this.attemptReconnect();
            };
            
            this.websocket.onerror = (error) => {
                console.error('WebSocket错误:', error);
            };
            
        } catch (error) {
            console.error('WebSocket连接失败:', error);
        }
    }

    handleWebSocketMessage(message) {
        switch (message.type) {
            case 'connected':
                console.log('WebSocket连接确认:', message.message);
                break;
                
            case 'stats_update':
                if (this.currentSection === 'dashboard') {
                    this.updateDashboardStats(message.data);
                }
                break;
                
            case 'alarm_update':
                if (this.currentSection === 'dashboard' || this.currentSection === 'alarms') {
                    this.handleAlarmUpdate(message.data);
                }
                break;
                
            case 'system_notification':
                window.framework.showNotification(
                    message.data.message, 
                    message.data.type || 'info'
                );
                break;
                
            default:
                console.log('收到未知WebSocket消息:', message);
        }
    }

    handleAlarmUpdate(alarmData) {
        // 如果是新告警，刷新相关数据
        if (alarmData.status === 'active') {
            // 更新侧边栏徽章
            const badge = document.getElementById('active-alarms-badge');
            if (badge) {
                const currentCount = parseInt(badge.textContent) || 0;
                badge.textContent = currentCount + 1;
                badge.style.display = 'inline';
            }
            
            // 显示新告警通知
            window.framework.showNotification(
                `新告警: ${alarmData.title}`, 
                alarmData.severity === 'critical' ? 'error' : 'warning'
            );
        }
    }

    attemptReconnect() {
        if (this.reconnectAttempts < this.maxReconnectAttempts) {
            this.reconnectAttempts++;
            const delay = Math.pow(2, this.reconnectAttempts) * 1000; // 指数退避
            
            console.log(`尝试重连WebSocket (${this.reconnectAttempts}/${this.maxReconnectAttempts}) 延迟: ${delay}ms`);
            
            setTimeout(() => {
                this.setupWebSocket();
            }, delay);
        } else {
            console.log('WebSocket重连次数超限，停止重连');
            window.framework.showNotification('实时数据连接中断，请刷新页面', 'error');
        }
    }

    closeWebSocket() {
        if (this.websocket) {
            this.websocket.close();
            this.websocket = null;
        }
    }
}

// 全局函数
window.showCreateEndpointModal = function() {
    window.framework.showModal('create-endpoint-modal');
};

window.showCreateUserModal = function() {
    window.framework.showModal('create-user-modal');
};

window.createEndpoint = async function() {
    const name = document.getElementById('endpoint-name').value;
    const type = document.getElementById('endpoint-type').value;
    const description = document.getElementById('endpoint-description').value;

    if (!name || !type) {
        window.framework.showNotification('请填写必要字段', 'warning');
        return;
    }

    try {
        await window.framework.request('/api/endpoints/', {
            method: 'POST',
            body: JSON.stringify({
                name: name,
                endpoint_type: type,
                description: description,
                config: {}
            })
        });

        window.framework.showNotification('接入点创建成功', 'success');
        window.framework.closeModal();
        
        // 清空表单
        document.getElementById('endpoint-name').value = '';
        document.getElementById('endpoint-type').value = '';
        document.getElementById('endpoint-description').value = '';
        
        // 刷新数据
        if (window.adminApp.currentSection === 'endpoints') {
            window.adminApp.loadEndpointsData();
        }
    } catch (error) {
        window.framework.showNotification('创建接入点失败', 'error');
    }
};

window.createUser = async function() {
    const username = document.getElementById('user-username').value;
    const email = document.getElementById('user-email').value;
    const password = document.getElementById('user-password').value;
    const fullname = document.getElementById('user-fullname').value;

    if (!username || !email || !password) {
        window.framework.showNotification('请填写必要字段', 'warning');
        return;
    }

    try {
        await window.framework.request('/api/users/', {
            method: 'POST',
            body: JSON.stringify({
                username: username,
                email: email,
                password: password,
                full_name: fullname
            })
        });

        window.framework.showNotification('用户创建成功', 'success');
        window.framework.closeModal();
        
        // 清空表单
        document.getElementById('user-username').value = '';
        document.getElementById('user-email').value = '';
        document.getElementById('user-password').value = '';
        document.getElementById('user-fullname').value = '';
        
        // 刷新数据
        if (window.adminApp.currentSection === 'users') {
            window.adminApp.loadUsersData();
        }
    } catch (error) {
        window.framework.showNotification('创建用户失败', 'error');
    }
};

window.testEndpoint = async function(endpointId) {
    try {
        const result = await window.framework.request(`/api/endpoints/${endpointId}/test`, {
            method: 'POST'
        });

        if (result.success) {
            window.framework.showNotification('接入点测试成功', 'success');
        } else {
            window.framework.showNotification(`接入点测试失败: ${result.error || result.message}`, 'error');
        }
    } catch (error) {
        window.framework.showNotification('测试接入点失败', 'error');
    }
};

window.deleteEndpoint = async function(endpointId) {
    if (!confirm('确定要删除这个接入点吗？')) {
        return;
    }

    try {
        await window.framework.request(`/api/endpoints/${endpointId}`, {
            method: 'DELETE'
        });

        window.framework.showNotification('接入点删除成功', 'success');
        window.adminApp.loadEndpointsData();
    } catch (error) {
        window.framework.showNotification('删除接入点失败', 'error');
    }
};

window.deleteUser = async function(userId) {
    if (!confirm('确定要删除这个用户吗？')) {
        return;
    }

    try {
        await window.framework.request(`/api/users/${userId}`, {
            method: 'DELETE'
        });

        window.framework.showNotification('用户删除成功', 'success');
        window.adminApp.loadUsersData();
    } catch (error) {
        window.framework.showNotification('删除用户失败', 'error');
    }
};

window.resolveAlarm = async function(alarmId) {
    try {
        await window.framework.request(`/api/alarms/${alarmId}`, {
            method: 'PUT',
            body: JSON.stringify({
                status: 'resolved'
            })
        });

        window.framework.showNotification('告警已解决', 'success');
        
        // 刷新数据
        if (window.adminApp.currentSection === 'dashboard') {
            window.adminApp.loadDashboardData();
        } else if (window.adminApp.currentSection === 'alarms') {
            window.adminApp.loadAlarmsData();
        }
    } catch (error) {
        window.framework.showNotification('解决告警失败', 'error');
    }
};

window.viewAlarmDetail = function(alarmId) {
    window.framework.showNotification(`查看告警详情 #${alarmId}`, 'info');
    // 这里可以打开详情模态框或跳转到详情页面
};

window.deleteAlarm = async function(alarmId) {
    if (!confirm('确定要删除这个告警吗？')) {
        return;
    }

    try {
        await window.framework.request(`/api/alarms/${alarmId}`, {
            method: 'DELETE'
        });

        window.framework.showNotification('告警删除成功', 'success');
        
        if (window.adminApp.currentSection === 'alarms') {
            window.adminApp.loadAlarmsData();
        }
    } catch (error) {
        window.framework.showNotification('删除告警失败', 'error');
    }
};

window.editEndpoint = function(endpointId) {
    window.framework.showNotification(`编辑接入点 #${endpointId}`, 'info');
    // 这里可以打开编辑模态框
};

window.editUser = function(userId) {
    window.framework.showNotification(`编辑用户 #${userId}`, 'info');
    // 这里可以打开编辑模态框
};

// 初始化应用
document.addEventListener('DOMContentLoaded', function() {
    window.adminApp = new AdminApp();
});