import os
import requests
from flask import Flask, render_template_string, request, jsonify
from coordinator import coordinator, NODES

app = Flask(__name__)

# Giao diện HTML (Sử dụng Bootstrap để làm UI đẹp và nhanh)
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <title>ROWA Protocol Demo</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        body { background-color: #f8f9fa; }
        .node-card { transition: all 0.3s; border-radius: 15px; }
        .node-alive { border-left: 10px solid #28a745; background: white; }
        .node-dead { border-left: 10px solid #dc3545; background: #fff5f5; opacity: 0.8; }
        .log-container { height: 300px; overflow-y: auto; background: #212529; color: #00ff00; padding: 15px; font-family: monospace; border-radius: 10px; }
    </style>
</head>
<body>
<div class="container py-5">
    <h1 class="text-center mb-4">🌐 ROWA Protocol Visualizer</h1>
    <p class="text-center text-muted">Read-One-Write-All: Ưu tiên <b>Consistency (Nhất quán)</b> tuyệt đối</p>

    <div class="row mb-4" id="nodes-status">
        </div>

    <div class="row">
        <div class="col-md-6">
            <div class="card shadow-sm mb-4">
                <div class="card-body">
                    <h5 class="card-title">📝 Ghi dữ liệu (Write All)</h5>
                    <div class="mb-3">
                        <input type="text" id="userId" class="form-control mb-2" placeholder="User ID (ví dụ: U001)">
                        <input type="text" id="bio" class="form-control mb-2" placeholder="Bio">
                    </div>
                    <button onclick="handleWrite()" class="btn btn-primary w-100">Ghi vào tất cả các nút</button>
                </div>
            </div>

            <div class="card shadow-sm">
                <div class="card-body">
                    <h5 class="card-title">🔍 Đọc dữ liệu (Read One)</h5>
                    <div class="input-group">
                        <input type="text" id="readUserId" class="form-control" placeholder="User ID">
                        <button onclick="handleRead()" class="btn btn-success">Đọc từ 1 nút bất kỳ</button>
                    </div>
                </div>
            </div>
        </div>

        <div class="col-md-6">
            <h5>📜 Nhật ký Coordinator</h5>
            <div id="logs" class="log-container">
                <div>> Hệ thống đã sẵn sàng...</div>
            </div>
            <button onclick="clearLogs()" class="btn btn-sm btn-outline-secondary mt-2">Xóa log</button>
        </div>
    </div>
</div>

<script>
    function addLog(msg, type='info') {
        const logDiv = document.getElementById('logs');
        const color = type === 'error' ? '#ff6b6b' : (type === 'success' ? '#51cf66' : '#00ff00');
        logDiv.innerHTML += `<div style="color: ${color}">[${new Date().toLocaleTimeString()}] ${msg}</div>`;
        logDiv.scrollTop = logDiv.scrollHeight;
    }

    function clearLogs() { document.getElementById('logs').innerHTML = ''; }

    async function updateStatus() {
        const res = await fetch('/api/status');
        const data = await res.json();
        const container = document.getElementById('nodes-status');
        container.innerHTML = '';
        
        for (const [name, info] of Object.entries(data)) {
            const statusClass = info.alive ? 'node-alive' : 'node-dead';
            const statusText = info.alive ? '🟢 ĐANG CHẠY' : '🔴 NGỪNG HOẠT ĐỘNG';
            container.innerHTML += `
                <div class="col-md-4">
                    <div class="card node-card ${statusClass} shadow-sm p-3 mb-3">
                        <h4 class="mb-0">${name}</h4>
                        <small class="text-muted">${info.url}</small>
                        <hr>
                        <p class="mb-1"><b>Trạng thái:</b> ${statusText}</p>
                        <p><b>Số bản ghi:</b> ${info.records}</p>
                        <div class="d-flex gap-2">
                            <button class="btn btn-sm btn-danger" onclick="controlNode('${name}', 'kill')">Kill</button>
                            <button class="btn btn-sm btn-success" onclick="controlNode('${name}', 'revive')">Revive</button>
                        </div>
                    </div>
                </div>
            `;
        }
    }

    async function controlNode(name, action) {
        await fetch(`/api/node/${name}/${action}`, {method: 'POST'});
        addLog(`Hành động: ${action} trên ${name}`, 'info');
        updateStatus();
    }

    async function handleWrite() {
        const userId = document.getElementById('userId').value;
        const bio = document.getElementById('bio').value;
        if (!userId) return alert("Vui lòng nhập UserID");

        addLog(`Bắt đầu WRITE ALL cho user: ${userId}...`);
        const res = await fetch('/api/write', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({UserID: userId, Bio: bio, LastLogin: new Date().toISOString()})
        });
        const result = await res.json();
        
        if (result.status === 'ok') {
            addLog(`THÀNH CÔNG: Đã ghi lên ${result.nodes_written.join(', ')}`, 'success');
        } else {
            addLog(`THẤT BẠI: ${result.message}`, 'error');
            if(result.rolled_back_nodes) addLog(`Đã Rollback trên: ${result.rolled_back_nodes.join(', ')}`, 'error');
        }
        updateStatus();
    }

    async function handleRead() {
        const userId = document.getElementById('readUserId').value;
        const res = await fetch(`/api/read/${userId}`);
        const result = await res.json();
        
        if (result.status === 'ok') {
            addLog(`ĐỌC OK từ ${result.source_node}: ${JSON.stringify(result.data)}`, 'success');
        } else {
            addLog(`ĐỌC THẤT BẠI: Không tìm thấy hoặc nút lỗi`, 'error');
        }
    }

    setInterval(updateStatus, 3000); // Tự động cập nhật mỗi 3s
    updateStatus();
</script>
</body>
</html>
"""

# --- API Endpoints phục vụ giao diện ---

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/status')
def get_status():
    return jsonify(coordinator.health_check())

@app.route('/api/node/<name>/<action>', methods=['POST'])
def control_node(name, action):
    if action == 'kill':
        coordinator.kill_node(name)
    else:
        coordinator.revive_node(name)
    return jsonify({"status": "ok"})

@app.route('/api/write', methods=['POST'])
def web_write():
    data = request.json
    result = coordinator.write(data)
    return jsonify(result)

@app.route('/api/read/<user_id>')
def web_read(user_id):
    result = coordinator.read(user_id)
    return jsonify(result)

if __name__ == '__main__':
    print("Dashboard đang chạy tại http://localhost:8080")
    app.run(port=8080, debug=True)