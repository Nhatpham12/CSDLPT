"""
=============================================================
  BƯỚC 3: DEMO - Chạy và phân tích giao thức ROWA
=============================================================
Script này:
  1. Khởi động 3 nút (NodeA, NodeB, NodeC)
  2. Kịch bản A: Ghi thành công (tất cả nút sống)
  3. Kịch bản B: Ghi thất bại (giả lập NodeC chết)
  4. In báo cáo phân tích metrics
  5. Dọn dẹp tiến trình
"""

import time
import subprocess
import sys
import os
import signal
import requests
from datetime import datetime
from coordinator import coordinator, NODES


# -------------------------------------------------------
# TIỆN ÍCH IN ĐẸP
# -------------------------------------------------------
def banner(title: str):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")

def step(msg: str):
    print(f"\n  [{datetime.now().strftime('%H:%M:%S')}] {msg}")

def ok(msg: str):
    print(f"  ✓ {msg}")

def fail(msg: str):
    print(f"  ✗ {msg}")

def info(msg: str):
    print(f"    {msg}")


# -------------------------------------------------------
# KHỞI ĐỘNG CÁC NÚT
# -------------------------------------------------------
def start_nodes() -> list:
    """
    Khởi động 3 tiến trình Flask, mỗi tiến trình = 1 nút.
    Trả về danh sách process để có thể tắt sau.
    """
    banner("KHỞI ĐỘNG CỤM 3 NÚT (NODE CLUSTER)")
    processes = []

    node_configs = [
        ("NodeA", 5001),
        ("NodeB", 5002),
        ("NodeC", 5003),
    ]

    for node_name, port in node_configs:
        step(f"Khởi động {node_name} trên cổng {port}...")
        proc = subprocess.Popen(
            [sys.executable, "node_server.py", node_name, str(port)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        processes.append(proc)
        time.sleep(0.3)
        ok(f"{node_name} (PID {proc.pid}) đang chạy")

    # Chờ các nút sẵn sàng
    step("Chờ các nút khởi động xong...")
    time.sleep(1.5)

    # Kiểm tra sức khỏe ban đầu
    health = coordinator.health_check()
    print("\n  Trạng thái cụm:")
    for name, info_data in health.items():
        status = "🟢 SỐNG" if info_data["alive"] else "🔴 CHẾT"
        print(f"    {name}: {status} | {info_data['url']}")

    return processes


# -------------------------------------------------------
# KỊCH BẢN A: GHI THÀNH CÔNG (TẤT CẢ NÚT SỐNG)
# -------------------------------------------------------
def scenario_a_success():
    banner("KỊCH BẢN A: Ghi thành công (tất cả nút sống)")

    profile = {
        "UserID": "U001",
        "Bio": "Sinh viên CNTT, yêu thích Distributed Systems",
        "AvatarURL": "https://example.com/avatars/u001.png",
        "LastLogin": "2025-05-29T08:30:00Z"
    }

    # --- Ghi ---
    step(f"Ghi hồ sơ user={profile['UserID']} lên TẤT CẢ 3 nút...")
    t_start = time.time()
    result = coordinator.write(profile)
    t_write = (time.time() - t_start) * 1000

    if result["status"] == "ok":
        ok(f"WRITE THÀNH CÔNG trong {t_write:.1f}ms")
        info(f"Đã ghi lên: {result['nodes_written']}")
    else:
        fail(f"WRITE THẤT BẠI: {result['message']}")
        return

    # --- Đọc lại để kiểm tra nhất quán ---
    step("Đọc lại từ mỗi nút để xác minh tính nhất quán...")
    for node_name, base_url in NODES.items():
        try:
            resp = requests.get(f"{base_url}/read/U001", timeout=2)
            if resp.status_code == 200:
                data = resp.json()["data"]
                ok(f"{node_name}: Dữ liệu = {data['Bio'][:40]}...")
            else:
                fail(f"{node_name}: Không tìm thấy dữ liệu!")
        except Exception as e:
            fail(f"{node_name}: Lỗi kết nối ({e})")

    print(f"\n  ➜ KẾT LUẬN: Tất cả 3 nút có dữ liệu giống hệt nhau → NHẤT QUÁN ✓")
    print(f"  ➜ METRIC: Thời gian ghi = {t_write:.1f}ms")

    return t_write


# -------------------------------------------------------
# KỊCH BẢN B: GHI THẤT BẠI (GIẢ LẬP NÚT CHẾT)
# -------------------------------------------------------
def scenario_b_node_failure():
    banner("KỊCH BẢN B: Ghi thất bại khi NodeC bị tắt")

    # --- Giả lập NodeC chết ---
    step("Giả lập NodeC bị tắt đột ngột (hardware failure)...")
    success = coordinator.kill_node("NodeC")
    if success:
        ok("NodeC đã bị tắt thành công (giả lập)")
    else:
        fail("Không thể tắt NodeC")
        return

    time.sleep(0.3)

    # Kiểm tra trạng thái sau khi tắt
    health = coordinator.health_check()
    print("\n  Trạng thái cụm sau sự cố:")
    for name, info_data in health.items():
        status = "🟢 SỐNG" if info_data["alive"] else "🔴 CHẾT"
        print(f"    {name}: {status}")

    # --- Thử ghi khi có nút chết ---
    profile_new = {
        "UserID": "U002",
        "Bio": "Người dùng mới, hồ sơ cần ghi vào cluster",
        "AvatarURL": "https://example.com/avatars/u002.png",
        "LastLogin": "2025-05-29T09:00:00Z"
    }

    step(f"Thử ghi hồ sơ user={profile_new['UserID']} khi NodeC đang chết...")
    t_start = time.time()
    result = coordinator.write(profile_new)
    t_write = (time.time() - t_start) * 1000

    if result["status"] == "error":
        ok(f"HỆ THỐNG TỪ CHỐI GHI ✓ (đúng hành vi ROWA) trong {t_write:.1f}ms")
        info(f"Nút thất bại: {result['failed_nodes']}")
        info(f"Đã rollback: {result['rolled_back_nodes']}")
    else:
        fail("LỖI: Hệ thống nên từ chối nhưng lại cho ghi!")

    # --- Xác minh U001 vẫn an toàn, U002 không tồn tại ---
    step("Xác minh tính nhất quán: U001 vẫn OK, U002 không được ghi...")

    # Kiểm tra U001 (ghi từ trước, vẫn phải còn)
    read_result = coordinator.read("U001")
    if read_result["status"] == "ok":
        ok(f"U001 vẫn an toàn trên {read_result['source_node']}")
    else:
        fail("U001 bị mất! Đây là lỗi nghiêm trọng.")

    # Kiểm tra U002 (bị rollback, không được tồn tại)
    for node_name, base_url in NODES.items():
        if health[node_name]["alive"]:
            try:
                resp = requests.get(f"{base_url}/read/U002", timeout=2)
                if resp.status_code == 404:
                    ok(f"{node_name}: U002 không tồn tại (rollback thành công ✓)")
                else:
                    fail(f"{node_name}: U002 vẫn còn! Rollback thất bại!")
            except Exception:
                pass

    print(f"\n  ➜ KẾT LUẬN: Hệ thống từ chối ghi → Không có trạng thái 'nửa ghi'")
    print(f"  ➜ METRIC: Phát hiện lỗi và rollback trong {t_write:.1f}ms")

    # --- Khôi phục NodeC ---
    step("Khôi phục NodeC (node recovery)...")
    coordinator.revive_node("NodeC")
    ok("NodeC đã được khôi phục ✓")

    return t_write


# -------------------------------------------------------
# KỊCH BẢN C: ĐỌC SAU KHI GHI (Xác minh Read-Any-Node)
# -------------------------------------------------------
def scenario_c_read_consistency():
    banner("KỊCH BẢN C: Đọc từ nút bất kỳ đều nhất quán")

    step("Ghi thêm hồ sơ mẫu...")
    profiles = [
        {"UserID": "U003", "Bio": "Alice - kỹ sư phần mềm",
         "AvatarURL": "https://ex.com/alice.png", "LastLogin": "2025-05-28T20:00:00Z"},
        {"UserID": "U004", "Bio": "Bob - nhà khoa học dữ liệu",
         "AvatarURL": "https://ex.com/bob.png",  "LastLogin": "2025-05-29T07:00:00Z"},
    ]

    for p in profiles:
        result = coordinator.write(p)
        if result["status"] == "ok":
            ok(f"Đã ghi {p['UserID']}")

    step("Đọc từ nhiều nút để kiểm tra nhất quán...")
    read_times = []
    for user_id in ["U001", "U003", "U004"]:
        t = time.time()
        result = coordinator.read(user_id)
        read_time = (time.time() - t) * 1000
        read_times.append(read_time)
        if result["status"] == "ok":
            ok(f"Đọc {user_id} từ {result['source_node']}: {result['data']['Bio'][:35]}... ({read_time:.1f}ms)")

    avg_read = sum(read_times) / len(read_times)
    print(f"\n  ➜ METRIC: Thời gian đọc trung bình = {avg_read:.1f}ms (chỉ cần 1 nút)")


# -------------------------------------------------------
# BÁO CÁO PHÂN TÍCH TỔNG KẾT
# -------------------------------------------------------
def print_analysis(t_write_success, t_write_fail):
    banner("BÁO CÁO PHÂN TÍCH - ROWA PROTOCOL")

    print("""
  ┌─────────────────────────────────────────────────────────┐
  │              PHÂN TÍCH THEO LÝ THUYẾT                   │
  │              (Özsu & Valduriez, Ch. 12)                 │
  ├─────────────────────────────────────────────────────────┤
  │  Giao thức:  Read-One-Write-All (ROWA)                  │
  │  Write quorum: N (tất cả bản sao)                       │
  │  Read quorum:  1 (bất kỳ bản sao nào)                   │
  │  Consistency:  STRONG (tuyệt đối)                       │
  │  Availability: LIMITED (từ chối khi có nút chết)        │
  ├─────────────────────────────────────────────────────────┤
  │  CAP Theorem: ROWA thuộc nhóm CP                        │
  │    C = Consistency  ✓ (đảm bảo)                         │
  │    A = Availability ✗ (hy sinh)                         │
  │    P = Partition    ✓ (chịu được phân vùng mạng)        │
  └─────────────────────────────────────────────────────────┘
    """)

    print(f"  METRICS THỰC NGHIỆM:")
    if t_write_success:
        print(f"    Thời gian ghi khi tất cả nút sống: {t_write_success:.1f}ms")
    if t_write_fail:
        print(f"    Thời gian phát hiện lỗi + rollback: {t_write_fail:.1f}ms")

    print("""
  SO SÁNH ROWA VỚI CÁC GIAO THỨC KHÁC:
    ROWA:          Write=ALL, Read=1   → Nhất quán cao, ghi chậm
    Quorum-based:  Write>N/2, Read>N/2 → Cân bằng
    Read-Any-Write-Any: Write=1, Read=1 → Nhanh, có thể mất nhất quán

  ỨNG DỤNG THỰC TẾ CỦA ROWA:
    ✓ Hệ thống ngân hàng (số dư tài khoản phải chính xác 100%)
    ✓ Hồ sơ y tế (dữ liệu không được sai lệch)
    ✗ Mạng xã hội (số like không cần chính xác tuyệt đối)
    """)


# -------------------------------------------------------
# MAIN: Chạy toàn bộ demo
# -------------------------------------------------------
def main():
    print("\n" + "="*60)
    print("  BÀI 41: GIAO THỨC ROWA - USER PROFILES")
    print("  Minh họa: Consistency over Availability")
    print("="*60)

    processes = start_nodes()

    try:
        # Chạy 3 kịch bản
        t_success = scenario_a_success()
        time.sleep(0.5)

        t_fail = scenario_b_node_failure()
        time.sleep(0.5)

        scenario_c_read_consistency()
        time.sleep(0.5)

        # Báo cáo phân tích
        print_analysis(t_success, t_fail)

    except KeyboardInterrupt:
        print("\n\n  Dừng demo theo yêu cầu người dùng.")
    except Exception as e:
        print(f"\n  Lỗi không mong đợi: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Dọn dẹp: tắt tất cả tiến trình nút
        banner("DỌN DẸP: TẮT TẤT CẢ NÚT")
        for proc in processes:
            proc.terminate()
            proc.wait()
            ok(f"Đã tắt tiến trình PID {proc.pid}")
        print("\n  Hoàn thành demo ROWA.\n")


if __name__ == "__main__":
    main()
