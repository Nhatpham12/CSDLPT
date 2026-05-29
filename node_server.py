"""
=============================================================
  BƯỚC 1: NODE SERVER - Mỗi nút là một "máy chủ nhỏ"
=============================================================
Mỗi Node (A, B, C) là một tiến trình Flask riêng biệt,
lắng nghe trên một cổng khác nhau.

Cấu trúc bảng User_Profiles:
  UserID | Bio | AvatarURL | LastLogin
"""

import sys
import json
import time
import signal
import logging
from flask import Flask, request, jsonify

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(name)s] %(message)s',
    datefmt='%H:%M:%S'
)

app = Flask(__name__)

# -------------------------------------------------------
# DỮ LIỆU: Lưu trữ trong bộ nhớ (giả lập database)
# -------------------------------------------------------
user_profiles = {}

# Tên nút (truyền qua biến môi trường hoặc tham số)
node_name = "Node-?"
is_alive = True   # Cờ kiểm soát: True = sống, False = giả lập "chết"

logger = logging.getLogger(node_name)


# -------------------------------------------------------
# ENDPOINT 1: Đọc hồ sơ người dùng
# [ROWA] Đọc chỉ cần 1 nút → bất kỳ nút nào cũng phục vụ
# -------------------------------------------------------
@app.route('/read/<user_id>', methods=['GET'])
def read_profile(user_id):
    global is_alive, logger

    # Kiểm tra nút còn sống không
    if not is_alive:
        logger.warning(f"TỪ CHỐI đọc user={user_id} (nút đang chết)")
        return jsonify({
            "status": "error",
            "node": node_name,
            "message": f"{node_name} đang chết - không thể phục vụ"
        }), 503

    profile = user_profiles.get(user_id)
    if profile is None:
        return jsonify({
            "status": "not_found",
            "node": node_name,
            "user_id": user_id
        }), 404

    logger.info(f"ĐỌC user={user_id} thành công")
    return jsonify({
        "status": "ok",
        "node": node_name,
        "data": profile
    }), 200


# -------------------------------------------------------
# ENDPOINT 2: Ghi hồ sơ người dùng
# [ROWA] Coordinator sẽ gọi endpoint này trên TẤT CẢ nút
# Nếu nút "chết" → trả về lỗi → Coordinator rollback
# -------------------------------------------------------
@app.route('/write', methods=['POST'])
def write_profile():
    global is_alive, logger

    # Kiểm tra nút còn sống không
    if not is_alive:
        logger.warning("TỪ CHỐI ghi (nút đang chết)")
        return jsonify({
            "status": "error",
            "node": node_name,
            "message": f"{node_name} đang chết - không thể nhận ghi"
        }), 503

    # Giả lập thời gian ghi vào "đĩa"
    time.sleep(0.05)

    data = request.get_json()
    user_id = data.get("UserID")
    if not user_id:
        return jsonify({"status": "error", "message": "Thiếu UserID"}), 400

    # Lưu vào "database" trong bộ nhớ
    user_profiles[user_id] = {
        "UserID": user_id,
        "Bio": data.get("Bio", ""),
        "AvatarURL": data.get("AvatarURL", ""),
        "LastLogin": data.get("LastLogin", "")
    }
    logger.info(f"GHI user={user_id} thành công → {user_profiles[user_id]}")

    return jsonify({
        "status": "ok",
        "node": node_name,
        "message": "Đã ghi thành công"
    }), 200


# -------------------------------------------------------
# ENDPOINT 3: Rollback (xóa dữ liệu vừa ghi - dùng khi
# một nút khác thất bại, cần hoàn tác)
# -------------------------------------------------------
@app.route('/rollback/<user_id>', methods=['DELETE'])
def rollback(user_id):
    global logger
    if user_id in user_profiles:
        del user_profiles[user_id]
        logger.info(f"ROLLBACK user={user_id} hoàn tất")
    return jsonify({"status": "ok", "node": node_name, "message": "Đã rollback"}), 200


# -------------------------------------------------------
# ENDPOINT 4: Điều khiển trạng thái nút (dùng để test)
# POST /admin/kill   → giả lập nút bị tắt
# POST /admin/revive → khôi phục nút
# -------------------------------------------------------
@app.route('/admin/kill', methods=['POST'])
def kill_node():
    global is_alive, logger
    is_alive = False
    logger.warning(f">>> {node_name} ĐÃ BỊ TẮT (giả lập sự cố) <<<")
    return jsonify({"status": "ok", "node": node_name, "alive": False}), 200


@app.route('/admin/revive', methods=['POST'])
def revive_node():
    global is_alive, logger
    is_alive = True
    logger.info(f">>> {node_name} ĐÃ ĐƯỢC KHÔI PHỤC <<<")
    return jsonify({"status": "ok", "node": node_name, "alive": True}), 200


# -------------------------------------------------------
# ENDPOINT 5: Kiểm tra trạng thái sức khỏe
# -------------------------------------------------------
@app.route('/health', methods=['GET'])
def health():
    return jsonify({
        "node": node_name,
        "alive": is_alive,
        "record_count": len(user_profiles)
    }), 200


# -------------------------------------------------------
# KHỞI ĐỘNG NÚT
# -------------------------------------------------------
if __name__ == '__main__':
    if len(sys.argv) < 3:
        print("Cách dùng: python node_server.py <tên_nút> <cổng>")
        print("Ví dụ:     python node_server.py NodeA 5001")
        sys.exit(1)

    node_name = sys.argv[1]
    port = int(sys.argv[2])
    logger = logging.getLogger(node_name)

    logger.info(f"Đang khởi động {node_name} trên cổng {port}...")
    app.run(host='0.0.0.0', port=port, debug=False)
