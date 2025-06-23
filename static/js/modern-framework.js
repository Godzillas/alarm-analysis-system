/**
 * 现代化企业级前端框架
 */

class ModernFramework {
    constructor() {
        this.components = new Map();
        this.state = new Proxy({}, {
            set: (target, property, value) => {
                target[property] = value;
                this.notifyStateChange(property, value);
                return true;
            }
        });
        this.eventBus = new EventTarget();
        this.init();
    }

    init() {
        this.setupGlobalEvents();
        this.setupTheme();
        this.setupResponsive();
    }

    // 状态管理
    setState(key, value) {
        this.state[key] = value;
    }

    getState(key) {
        return this.state[key];
    }

    notifyStateChange(key, value) {
        this.eventBus.dispatchEvent(new CustomEvent('stateChange', {
            detail: { key, value }
        }));
    }

    // 组件注册
    registerComponent(name, component) {
        this.components.set(name, component);
    }

    getComponent(name) {
        return this.components.get(name);
    }

    // 全局事件设置
    setupGlobalEvents() {
        // 移动端菜单切换
        document.addEventListener('click', (e) => {
            if (e.target.matches('[data-toggle="sidebar"]')) {
                this.toggleSidebar();
            }
            
            if (e.target.matches('[data-dismiss="modal"]') || e.target.closest('[data-dismiss="modal"]')) {
                this.closeModal();
            }
        });

        // ESC键关闭模态框
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                this.closeModal();
            }
        });
    }

    // 主题管理
    setupTheme() {
        const savedTheme = localStorage.getItem('theme') || 'light';
        this.setTheme(savedTheme);
    }

    setTheme(theme) {
        document.documentElement.setAttribute('data-theme', theme);
        localStorage.setItem('theme', theme);
        this.setState('theme', theme);
    }

    toggleTheme() {
        const currentTheme = this.getState('theme') || 'light';
        const newTheme = currentTheme === 'light' ? 'dark' : 'light';
        this.setTheme(newTheme);
    }

    // 响应式处理
    setupResponsive() {
        const mediaQuery = window.matchMedia('(max-width: 768px)');
        this.handleResponsive(mediaQuery);
        mediaQuery.addListener(this.handleResponsive.bind(this));
    }

    handleResponsive(e) {
        const sidebar = document.querySelector('.sidebar');
        const mainContent = document.querySelector('.main-content');
        
        if (e.matches) {
            // 移动端
            sidebar?.classList.add('mobile-hidden');
            mainContent?.classList.add('sidebar-mobile-hidden');
        } else {
            // 桌面端
            sidebar?.classList.remove('mobile-hidden', 'mobile-open');
            mainContent?.classList.remove('sidebar-mobile-hidden');
        }
    }

    // 侧边栏控制
    toggleSidebar() {
        const sidebar = document.querySelector('.sidebar');
        const mainContent = document.querySelector('.main-content');
        
        if (window.innerWidth <= 768) {
            // 移动端
            sidebar?.classList.toggle('mobile-open');
        } else {
            // 桌面端
            sidebar?.classList.toggle('collapsed');
            mainContent?.classList.toggle('sidebar-collapsed');
        }
    }

    // 模态框管理
    showModal(modalId) {
        const modal = document.getElementById(modalId);
        if (modal) {
            modal.classList.remove('hidden');
            document.body.style.overflow = 'hidden';
        }
    }

    closeModal() {
        const modals = document.querySelectorAll('.modal-overlay');
        modals.forEach(modal => {
            modal.classList.add('hidden');
        });
        document.body.style.overflow = '';
    }

    // 通知系统
    showNotification(message, type = 'info', duration = 5000) {
        const notification = this.createNotification(message, type);
        document.body.appendChild(notification);
        
        // 动画显示
        setTimeout(() => notification.classList.add('show'), 100);
        
        // 自动隐藏
        setTimeout(() => {
            this.hideNotification(notification);
        }, duration);
    }

    createNotification(message, type) {
        const notification = document.createElement('div');
        notification.className = `notification notification-${type}`;
        notification.innerHTML = `
            <div class="notification-content">
                <div class="notification-icon">
                    ${this.getNotificationIcon(type)}
                </div>
                <div class="notification-message">${message}</div>
                <button class="notification-close" onclick="window.framework.hideNotification(this.parentElement)">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <line x1="18" y1="6" x2="6" y2="18"></line>
                        <line x1="6" y1="6" x2="18" y2="18"></line>
                    </svg>
                </button>
            </div>
        `;
        return notification;
    }

    getNotificationIcon(type) {
        const icons = {
            success: '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="20,6 9,17 4,12"></polyline></svg>',
            error: '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"></circle><line x1="15" y1="9" x2="9" y2="15"></line><line x1="9" y1="9" x2="15" y2="15"></line></svg>',
            warning: '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3Z"></path><line x1="12" y1="9" x2="12" y2="13"></line><line x1="12" y1="17" x2="12.01" y2="17"></line></svg>',
            info: '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="16" x2="12" y2="12"></line><line x1="12" y1="8" x2="12.01" y2="8"></line></svg>'
        };
        return icons[type] || icons.info;
    }

    hideNotification(notification) {
        notification.classList.add('hide');
        setTimeout(() => {
            notification.remove();
        }, 300);
    }

    // API请求处理
    async request(url, options = {}) {
        const defaultOptions = {
            headers: {
                'Content-Type': 'application/json',
            },
        };

        const finalOptions = { ...defaultOptions, ...options };
        
        try {
            const response = await fetch(url, finalOptions);
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            return await response.json();
        } catch (error) {
            console.error('Request failed:', error);
            this.showNotification(`请求失败: ${error.message}`, 'error');
            throw error;
        }
    }

    // 工具函数
    formatDate(date, format = 'YYYY-MM-DD HH:mm:ss') {
        const d = new Date(date);
        const year = d.getFullYear();
        const month = String(d.getMonth() + 1).padStart(2, '0');
        const day = String(d.getDate()).padStart(2, '0');
        const hours = String(d.getHours()).padStart(2, '0');
        const minutes = String(d.getMinutes()).padStart(2, '0');
        const seconds = String(d.getSeconds()).padStart(2, '0');

        return format
            .replace('YYYY', year)
            .replace('MM', month)
            .replace('DD', day)
            .replace('HH', hours)
            .replace('mm', minutes)
            .replace('ss', seconds);
    }

    formatNumber(num, locale = 'zh-CN') {
        return new Intl.NumberFormat(locale).format(num);
    }

    debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    }

    throttle(func, limit) {
        let inThrottle;
        return function() {
            const args = arguments;
            const context = this;
            if (!inThrottle) {
                func.apply(context, args);
                inThrottle = true;
                setTimeout(() => inThrottle = false, limit);
            }
        };
    }
}

// 数据表格组件
class DataTable {
    constructor(container, options = {}) {
        this.container = typeof container === 'string' ? document.querySelector(container) : container;
        this.options = {
            data: [],
            columns: [],
            pageSize: 10,
            sortable: true,
            filterable: true,
            ...options
        };
        this.currentPage = 1;
        this.sortColumn = null;
        this.sortDirection = 'asc';
        this.filterText = '';
        this.init();
    }

    init() {
        this.render();
        this.bindEvents();
    }

    render() {
        const filteredData = this.getFilteredData();
        const sortedData = this.getSortedData(filteredData);
        const paginatedData = this.getPaginatedData(sortedData);

        this.container.innerHTML = `
            <div class="table-controls">
                ${this.options.filterable ? this.renderFilter() : ''}
                <div class="table-info">
                    显示 ${(this.currentPage - 1) * this.options.pageSize + 1}-${Math.min(this.currentPage * this.options.pageSize, filteredData.length)} 条，共 ${filteredData.length} 条
                </div>
            </div>
            <div class="table-container">
                <table class="table">
                    <thead>
                        <tr>
                            ${this.options.columns.map(col => this.renderHeader(col)).join('')}
                        </tr>
                    </thead>
                    <tbody>
                        ${paginatedData.map(row => this.renderRow(row)).join('')}
                    </tbody>
                </table>
            </div>
            ${this.renderPagination(filteredData.length)}
        `;
    }

    renderFilter() {
        return `
            <div class="table-filter">
                <input type="text" class="form-input" placeholder="搜索..." value="${this.filterText}">
            </div>
        `;
    }

    renderHeader(column) {
        const sortClass = this.sortColumn === column.key ? `sorted-${this.sortDirection}` : '';
        const sortIcon = this.getSortIcon(column.key);
        
        return `
            <th class="sortable ${sortClass}" data-column="${column.key}">
                ${column.title}
                ${this.options.sortable ? sortIcon : ''}
            </th>
        `;
    }

    renderRow(row) {
        return `
            <tr>
                ${this.options.columns.map(col => this.renderCell(row, col)).join('')}
            </tr>
        `;
    }

    renderCell(row, column) {
        let value = row[column.key];
        
        if (column.render) {
            value = column.render(value, row);
        } else if (column.type === 'date') {
            value = window.framework.formatDate(value);
        } else if (column.type === 'badge') {
            value = `<span class="badge badge-${value}">${value}</span>`;
        }
        
        return `<td>${value}</td>`;
    }

    renderPagination(totalItems) {
        const totalPages = Math.ceil(totalItems / this.options.pageSize);
        if (totalPages <= 1) return '';

        let pagination = '<div class="pagination">';
        
        // 上一页
        pagination += `<button class="btn btn-secondary btn-sm" ${this.currentPage === 1 ? 'disabled' : ''} data-page="${this.currentPage - 1}">上一页</button>`;
        
        // 页码
        for (let i = 1; i <= totalPages; i++) {
            if (i === this.currentPage) {
                pagination += `<button class="btn btn-primary btn-sm" disabled>${i}</button>`;
            } else {
                pagination += `<button class="btn btn-secondary btn-sm" data-page="${i}">${i}</button>`;
            }
        }
        
        // 下一页
        pagination += `<button class="btn btn-secondary btn-sm" ${this.currentPage === totalPages ? 'disabled' : ''} data-page="${this.currentPage + 1}">下一页</button>`;
        
        pagination += '</div>';
        return pagination;
    }

    getSortIcon(columnKey) {
        if (this.sortColumn !== columnKey) {
            return '<span class="sort-icon">↕</span>';
        }
        return this.sortDirection === 'asc' ? '<span class="sort-icon">↑</span>' : '<span class="sort-icon">↓</span>';
    }

    bindEvents() {
        this.container.addEventListener('click', (e) => {
            // 排序
            if (e.target.matches('.sortable') || e.target.closest('.sortable')) {
                const column = e.target.closest('.sortable').dataset.column;
                this.sort(column);
            }
            
            // 分页
            if (e.target.matches('[data-page]')) {
                const page = parseInt(e.target.dataset.page);
                this.goToPage(page);
            }
        });

        // 搜索
        const filterInput = this.container.querySelector('.table-filter input');
        if (filterInput) {
            filterInput.addEventListener('input', window.framework.debounce((e) => {
                this.filter(e.target.value);
            }, 300));
        }
    }

    sort(columnKey) {
        if (this.sortColumn === columnKey) {
            this.sortDirection = this.sortDirection === 'asc' ? 'desc' : 'asc';
        } else {
            this.sortColumn = columnKey;
            this.sortDirection = 'asc';
        }
        this.currentPage = 1;
        this.render();
    }

    filter(text) {
        this.filterText = text;
        this.currentPage = 1;
        this.render();
    }

    goToPage(page) {
        this.currentPage = page;
        this.render();
    }

    getFilteredData() {
        if (!this.filterText) return this.options.data;
        
        return this.options.data.filter(row => {
            return this.options.columns.some(col => {
                const value = row[col.key];
                return String(value).toLowerCase().includes(this.filterText.toLowerCase());
            });
        });
    }

    getSortedData(data) {
        if (!this.sortColumn) return data;
        
        return [...data].sort((a, b) => {
            const aVal = a[this.sortColumn];
            const bVal = b[this.sortColumn];
            
            if (aVal < bVal) return this.sortDirection === 'asc' ? -1 : 1;
            if (aVal > bVal) return this.sortDirection === 'asc' ? 1 : -1;
            return 0;
        });
    }

    getPaginatedData(data) {
        const start = (this.currentPage - 1) * this.options.pageSize;
        const end = start + this.options.pageSize;
        return data.slice(start, end);
    }

    updateData(newData) {
        this.options.data = newData;
        this.currentPage = 1;
        this.render();
    }
}

// 图表组件（简化版）
class SimpleChart {
    constructor(container, options = {}) {
        this.container = typeof container === 'string' ? document.querySelector(container) : container;
        this.options = {
            type: 'line',
            data: [],
            labels: [],
            colors: ['#2563eb', '#10b981', '#f59e0b', '#ef4444'],
            ...options
        };
        this.init();
    }

    init() {
        this.render();
    }

    render() {
        if (this.options.type === 'bar') {
            this.renderBarChart();
        } else if (this.options.type === 'pie') {
            this.renderPieChart();
        } else {
            this.renderLineChart();
        }
    }

    renderBarChart() {
        const maxValue = Math.max(...this.options.data);
        const bars = this.options.data.map((value, index) => {
            const height = (value / maxValue) * 200;
            const color = this.options.colors[index % this.options.colors.length];
            
            return `
                <div class="chart-bar" style="height: ${height}px; background-color: ${color};">
                    <div class="chart-bar-value">${value}</div>
                </div>
            `;
        }).join('');

        this.container.innerHTML = `
            <div class="simple-chart bar-chart">
                <div class="chart-bars">${bars}</div>
                <div class="chart-labels">
                    ${this.options.labels.map(label => `<div class="chart-label">${label}</div>`).join('')}
                </div>
            </div>
        `;
    }

    renderPieChart() {
        const total = this.options.data.reduce((sum, value) => sum + value, 0);
        let currentAngle = 0;
        
        const segments = this.options.data.map((value, index) => {
            const percentage = (value / total) * 100;
            const angle = (value / total) * 360;
            const color = this.options.colors[index % this.options.colors.length];
            
            const segment = {
                percentage: percentage.toFixed(1),
                color,
                label: this.options.labels[index],
                value
            };
            
            currentAngle += angle;
            return segment;
        });

        this.container.innerHTML = `
            <div class="simple-chart pie-chart">
                <div class="chart-legend">
                    ${segments.map(segment => `
                        <div class="legend-item">
                            <div class="legend-color" style="background-color: ${segment.color};"></div>
                            <span>${segment.label}: ${segment.value} (${segment.percentage}%)</span>
                        </div>
                    `).join('')}
                </div>
            </div>
        `;
    }

    renderLineChart() {
        // 简化的线图实现
        this.container.innerHTML = `
            <div class="simple-chart line-chart">
                <p>线图需要完整的图表库支持</p>
            </div>
        `;
    }

    updateData(newData, newLabels) {
        this.options.data = newData;
        if (newLabels) this.options.labels = newLabels;
        this.render();
    }
}

// 初始化框架
window.framework = new ModernFramework();

// 导出组件类
window.DataTable = DataTable;
window.SimpleChart = SimpleChart;