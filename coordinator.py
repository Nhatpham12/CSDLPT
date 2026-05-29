"""
=============================================================
  BƯỚC 2: ROWA COORDINATOR - Bộ điều phối trung tâm
=============================================================
Coordinator là "não" của hệ thống ROWA:

  READ:  Chọn 1 nút bất kỳ → hỏi → trả kết quả về client
  WRITE: Gửi đến TẤT CẢ nút cùng lúc →
           Tất cả OK?  → xác nhận thành công
           Bất kỳ lỗi? → rollback tất cả nút đã ghi → báo lỗi

Đây chính là cốt lõi của ROWA và của bài 41.
"""

import random
import logging
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [COORDINATOR] %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger("COORDINATOR")

# -------------------------------------------------------
# CẤU HÌNH: 3 nút, mỗi nút một cổng
# -------------------------------------------------------
NODES = {
    "NodeA": "http://localhost:5001",
    "NodeB": "http://localhost:5002",
    "NodeC": "http://localhost:5003",
}

TIMEOUT = 2.0  # Giây chờ tối đa mỗi nút phản hồi


class ROWACoordinator:
    """
    Điều phối giao thức Read-One-Write-All.

    Lý thuyết (Özsu & Valduriez):
      - ROWA là giao thức nhân bản nghiêm ngặt nhất.
      - Write quorum = N (tất cả bản sao)
      - Read quorum  = 1
      - Tính nhất quán được đảm bảo tuyệt đối vì mọi bản sao
        đều được cập nhật đồng bộ trước khi xác nhận ghi.
    """

    def __init__(self, nodes: dict):
        self.nodes = nodes

    # ---------------------------------------------------
    # ĐỌC: Gửi đến 1 nút ngẫu nhiên
    # ---------------------------------------------------
    def read(self, user_id: str) -> dict:
        """
        [ROWA] Read từ 1 nút bất kỳ.
        Vì ghi luôn thành công trên TẤT CẢ, nút nào cũng
        có dữ liệu nhất quán → đọc từ nút nào cũng được.
        """
        # Chọn ngẫu nhiên 1 nút
        node_name, base_url = random.choice(list(self.nodes.items()))
        logger.info(f"READ user={user_id} → chọn {node_name}")

        try:
            resp = requests.get(
                f"{base_url}/read/{user_id}",
                timeout=TIMEOUT
            )
            result = resp.json()
            if resp.status_code == 200:
                logger.info(f"READ thành công từ {node_name}: {result['data']}")
                return {"status": "ok", "source_node": node_name, "data": result["data"]}
            else:
                logger.warning(f"READ thất bại từ {node_name}: {result.get('message','không tìm thấy')}")
                return {"status": "not_found", "source_node": node_name}

        except requests.exceptions.RequestException as e:
            logger.error(f"READ lỗi kết nối tới {node_name}: {e}")
            return {"status": "error", "message": f"Không kết nối được {node_name}"}

    # ---------------------------------------------------
    # GHI: Gửi đến TẤT CẢ nút - ROWA Write-All
    # ---------------------------------------------------
    def write(self, profile: dict) -> dict:
        """
        [ROWA] Write-All Protocol:
          Bước 1: Gửi yêu cầu ghi đến TẤT CẢ nút song song
          Bước 2: Kiểm tra kết quả
                  - Tất cả OK → thành công
                  - Bất kỳ lỗi → rollback các nút đã ghi → thất bại

        Đây là điểm mấu chốt: hệ thống từ chối ghi nếu NGAY CẢ
        MỘT NÚT bị lỗi → đảm bảo Consistency tuyệt đối.
        """
        user_id = profile.get("UserID")
        logger.info(f"\n{'='*55}")
        logger.info(f"WRITE ALL bắt đầu: user={user_id}")
        logger.info(f"Gửi tới {len(self.nodes)} nút: {list(self.nodes.keys())}")

        # --- Bước 1: Gửi ghi song song tới tất cả nút ---
        results = {}
        with ThreadPoolExecutor(max_workers=len(self.nodes)) as executor:
            future_to_node = {
                executor.submit(self._write_to_node, name, url, profile): name
                for name, url in self.nodes.items()
            }
            for future in as_completed(future_to_node):
                node_name = future_to_node[future]
                results[node_name] = future.result()

        # --- Bước 2: Phân tích kết quả ---
        successful_nodes = [n for n, r in results.items() if r["ok"]]
        failed_nodes     = [n for n, r in results.items() if not r["ok"]]

        logger.info(f"Kết quả ghi: ✓ {successful_nodes} | ✗ {failed_nodes}")

        # Tất cả nút đều ghi thành công
        if not failed_nodes:
            logger.info(f"WRITE ALL THÀNH CÔNG ✓ | user={user_id} đã nhân bản trên {len(successful_nodes)} nút")
            return {
                "status": "ok",
                "message": "Ghi thành công trên tất cả nút",
                "nodes_written": successful_nodes
            }

        # Có ít nhất 1 nút thất bại → ROLLBACK
        logger.warning(f"\n[!] NÚT THẤT BẠI: {failed_nodes}")
        logger.warning(f"[!] Bắt đầu ROLLBACK trên {successful_nodes}...")
        self._rollback(user_id, successful_nodes)

        logger.error(f"WRITE BỊ TỪ CHỐI ✗ | Lý do: {failed_nodes} không phản hồi")
        return {
            "status": "error",
            "message": "Ghi bị từ chối: có nút thất bại",
            "failed_nodes": failed_nodes,
            "rolled_back_nodes": successful_nodes
        }

    # ---------------------------------------------------
    # HÀM NỘI BỘ: Ghi vào một nút cụ thể
    # ---------------------------------------------------
    def _write_to_node(self, node_name: str, base_url: str, profile: dict) -> dict:
        try:
            resp = requests.post(
                f"{base_url}/write",
                json=profile,
                timeout=TIMEOUT
            )
            if resp.status_code == 200:
                logger.info(f"  → {node_name}: GHI OK ✓")
                return {"ok": True, "node": node_name}
            else:
                logger.warning(f"  → {node_name}: GHI THẤT BẠI ✗ ({resp.status_code})")
                return {"ok": False, "node": node_name, "error": resp.json().get("message")}
        except requests.exceptions.RequestException as e:
            logger.error(f"  → {node_name}: KHÔNG KẾT NỐI ĐƯỢC ✗ ({e})")
            return {"ok": False, "node": node_name, "error": str(e)}

    # ---------------------------------------------------
    # HÀM NỘI BỘ: Rollback các nút đã ghi thành công
    # ---------------------------------------------------
    def _rollback(self, user_id: str, nodes_to_rollback: list):
        """
        Hoàn tác dữ liệu đã ghi trên các nút thành công.
        Đảm bảo hệ thống không bị ở trạng thái "nửa ghi".
        """
        for node_name in nodes_to_rollback:
            base_url = self.nodes[node_name]
            try:
                resp = requests.delete(
                    f"{base_url}/rollback/{user_id}",
                    timeout=TIMEOUT
                )
                if resp.status_code == 200:
                    logger.info(f"  ROLLBACK {node_name}: OK ✓")
                else:
                    logger.error(f"  ROLLBACK {node_name}: THẤT BẠI ✗")
            except requests.exceptions.RequestException as e:
                logger.error(f"  ROLLBACK {node_name}: LỖI KẾT NỐI ({e})")

    # ---------------------------------------------------
    # TIỆN ÍCH: Kiểm tra sức khỏe tất cả nút
    # ---------------------------------------------------
    def health_check(self) -> dict:
        """Kiểm tra trạng thái tất cả nút trong cluster."""
        status = {}
        for node_name, base_url in self.nodes.items():
            try:
                resp = requests.get(f"{base_url}/health", timeout=1.0)
                data = resp.json()
                status[node_name] = {
                    "alive": data.get("alive", False),
                    "records": data.get("record_count", 0),
                    "url": base_url
                }
            except Exception:
                status[node_name] = {"alive": False, "records": 0, "url": base_url}
        return status

    def kill_node(self, node_name: str) -> bool:
        """Gửi lệnh tắt (giả lập) tới một nút."""
        base_url = self.nodes.get(node_name)
        if not base_url:
            return False
        try:
            resp = requests.post(f"{base_url}/admin/kill", timeout=1.0)
            return resp.status_code == 200
        except Exception:
            return False

    def revive_node(self, node_name: str) -> bool:
        """Khôi phục một nút đã bị tắt."""
        base_url = self.nodes.get(node_name)
        if not base_url:
            return False
        try:
            resp = requests.post(f"{base_url}/admin/revive", timeout=1.0)
            return resp.status_code == 200
        except Exception:
            return False


# -------------------------------------------------------
# Tạo instance coordinator toàn cục để dùng trong demo
# -------------------------------------------------------
coordinator = ROWACoordinator(NODES)
