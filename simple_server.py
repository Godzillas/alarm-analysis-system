#!/usr/bin/env python3
"""
简化版告警系统服务器
"""

import json
import sqlite3
import asyncio
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import threading

class AlarmDatabase:
    def __init__(self, db_path="alarm_system.db"):
        self.db_path = db_path
        self.init_db()
    
    def init_db(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS alarms (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source TEXT NOT NULL,
                title TEXT NOT NULL,
                description TEXT,
                severity TEXT NOT NULL,
                status TEXT DEFAULT 'active',
                category TEXT,
                host TEXT,
                service TEXT,
                environment TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                count INTEGER DEFAULT 1
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def create_alarm(self, alarm_data):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO alarms (source, title, description, severity, category, host, service, environment)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            alarm_data.get('source', 'unknown'),
            alarm_data.get('title', 'Unknown Alarm'),
            alarm_data.get('description', ''),
            alarm_data.get('severity', 'medium'),
            alarm_data.get('category', ''),
            alarm_data.get('host', ''),
            alarm_data.get('service', ''),
            alarm_data.get('environment', '')
        ))
        
        alarm_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return alarm_id
    
    def get_alarms(self, limit=100):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, source, title, description, severity, status, category, 
                   host, service, environment, created_at, count
            FROM alarms ORDER BY created_at DESC LIMIT ?
        ''', (limit,))
        
        alarms = []
        for row in cursor.fetchall():
            alarms.append({
                'id': row[0],
                'source': row[1],
                'title': row[2],
                'description': row[3],
                'severity': row[4],
                'status': row[5],
                'category': row[6],
                'host': row[7],
                'service': row[8],
                'environment': row[9],
                'created_at': row[10],
                'count': row[11]
            })
        
        conn.close()
        return alarms
    
    def get_stats(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN status = 'active' THEN 1 ELSE 0 END) as active,
                SUM(CASE WHEN status = 'resolved' THEN 1 ELSE 0 END) as resolved,
                SUM(CASE WHEN severity = 'critical' THEN 1 ELSE 0 END) as critical,
                SUM(CASE WHEN severity = 'high' THEN 1 ELSE 0 END) as high,
                SUM(CASE WHEN severity = 'medium' THEN 1 ELSE 0 END) as medium,
                SUM(CASE WHEN severity = 'low' THEN 1 ELSE 0 END) as low
            FROM alarms
        ''')
        
        row = cursor.fetchone()
        conn.close()
        
        return {
            'total': row[0] or 0,
            'active': row[1] or 0,
            'resolved': row[2] or 0,
            'critical': row[3] or 0,
            'high': row[4] or 0,
            'medium': row[5] or 0,
            'low': row[6] or 0
        }

class AlarmHandler(BaseHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        self.db = AlarmDatabase()
        super().__init__(*args, **kwargs)
    
    def do_GET(self):
        parsed_url = urlparse(self.path)
        path = parsed_url.path
        
        if path == '/':
            self.send_dashboard()
        elif path == '/api/alarms':
            self.send_alarms()
        elif path == '/api/stats':
            self.send_stats()
        else:
            self.send_404()
    
    def do_POST(self):
        if self.path == '/api/alarms':
            self.create_alarm()
        else:
            self.send_404()
    
    def send_dashboard(self):
        html = '''
        <!DOCTYPE html>
        <html>
        <head>
            <title>告警分析系统</title>
            <meta charset="utf-8">
            <style>
                body { font-family: Arial, sans-serif; margin: 20px; }
                .card { border: 1px solid #ddd; padding: 20px; margin: 10px 0; border-radius: 5px; }
                .stat { display: inline-block; margin: 10px; padding: 10px; background: #f5f5f5; border-radius: 3px; }
                .alarm { padding: 10px; margin: 5px 0; border-left: 4px solid #ccc; }
                .critical { border-left-color: #f44336; background: #ffebee; }
                .high { border-left-color: #ff9800; background: #fff3e0; }
                .medium { border-left-color: #2196f3; background: #e3f2fd; }
                .low { border-left-color: #4caf50; background: #e8f5e8; }
                .refresh-btn { padding: 10px 20px; background: #2196f3; color: white; border: none; border-radius: 3px; cursor: pointer; }
            </style>
        </head>
        <body>
            <h1>告警分析系统</h1>
            <button class="refresh-btn" onclick="loadData()">刷新数据</button>
            
            <div class="card">
                <h3>系统统计</h3>
                <div id="stats">加载中...</div>
            </div>
            
            <div class="card">
                <h3>最新告警</h3>
                <div id="alarms">加载中...</div>
            </div>
            
            <div class="card">
                <h3>创建测试告警</h3>
                <button onclick="createTestAlarm()" class="refresh-btn">生成测试告警</button>
            </div>
            
            <script>
                function loadStats() {
                    fetch('/api/stats')
                        .then(response => response.json())
                        .then(data => {
                            document.getElementById('stats').innerHTML = `
                                <div class="stat">总数: ${data.total}</div>
                                <div class="stat">活跃: ${data.active}</div>
                                <div class="stat">已解决: ${data.resolved}</div>
                                <div class="stat critical">严重: ${data.critical}</div>
                                <div class="stat high">高级: ${data.high}</div>
                                <div class="stat medium">中级: ${data.medium}</div>
                                <div class="stat low">低级: ${data.low}</div>
                            `;
                        });
                }
                
                function loadAlarms() {
                    fetch('/api/alarms')
                        .then(response => response.json())
                        .then(data => {
                            let html = '';
                            data.forEach(alarm => {
                                html += `
                                    <div class="alarm ${alarm.severity}">
                                        <strong>${alarm.title}</strong> - ${alarm.source}
                                        <br>状态: ${alarm.status} | 级别: ${alarm.severity} | 主机: ${alarm.host || 'N/A'}
                                        <br>时间: ${alarm.created_at} | 次数: ${alarm.count}
                                    </div>
                                `;
                            });
                            document.getElementById('alarms').innerHTML = html || '暂无告警';
                        });
                }
                
                function loadData() {
                    loadStats();
                    loadAlarms();
                }
                
                function createTestAlarm() {
                    const testAlarms = [
                        { source: 'nginx', title: 'CPU使用率过高', severity: 'high', host: 'web-01' },
                        { source: 'mysql', title: '数据库连接超时', severity: 'critical', host: 'db-01' },
                        { source: 'redis', title: '内存使用率告警', severity: 'medium', host: 'cache-01' },
                        { source: 'app', title: '应用响应缓慢', severity: 'low', host: 'app-01' }
                    ];
                    
                    const alarm = testAlarms[Math.floor(Math.random() * testAlarms.length)];
                    alarm.description = '测试告警 - ' + new Date().toLocaleString();
                    
                    fetch('/api/alarms', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify(alarm)
                    }).then(() => {
                        setTimeout(loadData, 500);
                    });
                }
                
                loadData();
                setInterval(loadData, 30000); // 每30秒刷新
            </script>
        </body>
        </html>
        '''
        
        self.send_response(200)
        self.send_header('Content-type', 'text/html; charset=utf-8')
        self.end_headers()
        self.wfile.write(html.encode('utf-8'))
    
    def send_alarms(self):
        alarms = self.db.get_alarms()
        self.send_json_response(alarms)
    
    def send_stats(self):
        stats = self.db.get_stats()
        self.send_json_response(stats)
    
    def create_alarm(self):
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        
        try:
            alarm_data = json.loads(post_data.decode('utf-8'))
            alarm_id = self.db.create_alarm(alarm_data)
            self.send_json_response({'id': alarm_id, 'message': '告警创建成功'})
        except Exception as e:
            self.send_error_response(400, str(e))
    
    def send_json_response(self, data):
        self.send_response(200)
        self.send_header('Content-type', 'application/json; charset=utf-8')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode('utf-8'))
    
    def send_error_response(self, code, message):
        self.send_response(code)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps({'error': message}).encode('utf-8'))
    
    def send_404(self):
        self.send_response(404)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        self.wfile.write(b'404 Not Found')
    
    def log_message(self, format, *args):
        print(f"[{datetime.now()}] {format % args}")

def run_server(port=8000):
    server_address = ('', port)
    httpd = HTTPServer(server_address, AlarmHandler)
    print(f"告警分析系统启动成功!")
    print(f"访问地址: http://localhost:{port}")
    print(f"API文档: http://localhost:{port}/api/alarms")
    print("按 Ctrl+C 停止服务器")
    
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n正在停止服务器...")
        httpd.shutdown()

if __name__ == "__main__":
    run_server()