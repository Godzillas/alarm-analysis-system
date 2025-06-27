#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
API路径一致性检查工具

检查前后端API路径是否一致，确保遵循API规范
"""

import os
import re
import json
import glob

def extract_backend_routes():
    """提取后端API路由"""
    routes = {}
    
    # 检查主要的API路由文件
    api_files = [
        'src/api/routers.py',
        'src/api/system.py', 
        'src/api/contact_point.py',
        'src/api/alert_template.py',
        'src/api/oncall.py',
        'src/api/auth.py',
        'src/api/solutions.py',
        'src/api/subscriptions.py',
        'src/api/suppression.py',
        'src/api/rbac.py',
        'src/api/health.py',
    ]
    
    for file_path in api_files:
        if not os.path.exists(file_path):
            continue
            
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # 提取路由装饰器
        route_pattern = r'@\w+\.(?:get|post|put|delete|patch)\(["\']([^"\']+)["\']'
        matches = re.findall(route_pattern, content)
        
        module_name = os.path.basename(file_path).replace('.py', '')
        routes[module_name] = matches
    
    return routes

def extract_frontend_api_calls():
    """提取前端API调用"""
    api_calls = {}
    
    # 检查前端API文件
    frontend_api_dir = 'frontend/src/api'
    if not os.path.exists(frontend_api_dir):
        return api_calls
        
    for file_path in glob.glob(frontend_api_dir + '/*.js'):
        if 'request.js' in file_path:
            continue
            
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # 提取API调用的URL
        url_pattern = r'url:\s*[\'"`]([^\'"`]+)[\'"`]'
        matches = re.findall(url_pattern, content)
        
        module_name = os.path.basename(file_path).replace('.js', '')
        api_calls[module_name] = matches
    
    return api_calls

def check_trailing_slash_consistency(paths):
    """检查末尾斜杠一致性"""
    issues = []
    
    for path in paths:
        # 列表端点应该有末尾斜杠
        if path.count('/') == 1 and not path.endswith('/'):
            issues.append(f"列表端点缺少末尾斜杠: {path}")
        
        # 单个资源端点不应该有末尾斜杠
        if re.match(r'^/\w+/\{[^}]+\}/$', path):
            issues.append(f"单个资源端点不应有末尾斜杠: {path}")
            
        # 操作端点不应该有末尾斜杠
        if re.match(r'^/\w+/\{[^}]+\}/\w+/$', path):
            issues.append(f"操作端点不应有末尾斜杠: {path}")
    
    return issues

def check_naming_conventions(paths):
    """检查命名规范"""
    issues = []
    
    for path in paths:
        # 检查是否使用下划线而不是连字符
        if '_' in path and not re.search(r'\{[^}]*_[^}]*\}', path):
            issues.append(f"应使用连字符而不是下划线: {path}")
        
        # 检查是否使用复数形式
        parts = path.strip('/').split('/')
        if parts and not parts[0].endswith('s') and parts[0] not in ['auth', 'health', 'config']:
            issues.append(f"资源名应使用复数形式: {path}")
    
    return issues

def compare_frontend_backend(frontend_calls, backend_routes):
    """比较前后端API一致性"""
    issues = []
    
    # 提取所有后端路由路径
    all_backend_paths = set()
    for module, paths in backend_routes.items():
        all_backend_paths.update(paths)
    
    # 检查前端调用是否有对应的后端路由
    for module, calls in frontend_calls.items():
        for call in calls:
            # 移除参数占位符进行比较
            normalized_call = re.sub(r'\$\{[^}]+\}', '{id}', call)
            
            # 检查是否存在对应的后端路由
            if normalized_call not in all_backend_paths:
                # 检查是否有类似的路径（不考虑末尾斜杠）
                similar_path = normalized_call.rstrip('/') if normalized_call.endswith('/') else normalized_call + '/'
                if similar_path not in all_backend_paths:
                    issues.append(f"前端API调用缺少后端路由: {call} (在 {module}.js 中)")
    
    return issues

def main():
    """主函数"""
    print("🔍 API路径一致性检查")
    print("=" * 50)
    
    # 提取路由信息
    backend_routes = extract_backend_routes()
    frontend_calls = extract_frontend_api_calls()
    
    print(f"📊 发现后端模块: {len(backend_routes)}")
    for module, routes in backend_routes.items():
        print(f"  - {module}: {len(routes)} 个路由")
    
    print(f"\n📊 发现前端模块: {len(frontend_calls)}")
    for module, calls in frontend_calls.items():
        print(f"  - {module}: {len(calls)} 个API调用")
    
    # 检查各种一致性问题
    all_issues = []
    
    # 检查后端路由规范
    print("\n🔧 检查后端路由规范...")
    for module, routes in backend_routes.items():
        issues = check_trailing_slash_consistency(routes)
        all_issues.extend([f"[后端-{module}] {issue}" for issue in issues])
        
        issues = check_naming_conventions(routes)
        all_issues.extend([f"[后端-{module}] {issue}" for issue in issues])
    
    # 检查前端API调用规范
    print("🔧 检查前端API调用规范...")
    for module, calls in frontend_calls.items():
        issues = check_trailing_slash_consistency(calls)
        all_issues.extend([f"[前端-{module}] {issue}" for issue in issues])
        
        issues = check_naming_conventions(calls)
        all_issues.extend([f"[前端-{module}] {issue}" for issue in issues])
    
    # 检查前后端一致性
    print("🔧 检查前后端一致性...")
    consistency_issues = compare_frontend_backend(frontend_calls, backend_routes)
    all_issues.extend(consistency_issues)
    
    # 输出结果
    print("\n📋 检查结果")
    print("=" * 50)
    
    if not all_issues:
        print("✅ 所有API路径都符合规范！")
    else:
        print(f"❌ 发现 {len(all_issues)} 个问题:")
        for i, issue in enumerate(all_issues, 1):
            print(f"  {i}. {issue}")
    
    # 生成修复建议
    if all_issues:
        print("\n💡 修复建议")
        print("=" * 50)
        print("1. 参考 API_STANDARDS.md 中的规范")
        print("2. 列表端点必须使用末尾斜杠 (如: /api/alarms/)")
        print("3. 单个资源和操作端点不使用末尾斜杠")
        print("4. 使用连字符而不是下划线")
        print("5. 资源名使用复数形式")
        print("6. 确保前端API调用有对应的后端路由")
    
    return len(all_issues)

if __name__ == '__main__':
    exit_code = main()
    exit(exit_code)