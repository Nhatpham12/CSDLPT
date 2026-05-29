# Bài 41 - Giao thức ROWA: User Profiles

## Mô tả
Triển khai giao thức **Read-One-Write-All (ROWA)** trên bộ dữ liệu `User_Profiles`
nhân bản trên 3 nút, minh họa tính ưu tiên **Consistency over Availability**.

## Cấu trúc dự án
```
rowa_project/
├── node_server.py    # Mỗi nút là một Flask server độc lập
├── coordinator.py    # Bộ điều phối thực thi ROWA
├── demo.py           # Script chạy toàn bộ kịch bản demo
├── web_app.py        # Giao diện web trực quan
└── requirements.txt
```

## Cài đặt
```bash
pip install -r requirements.txt
```

## Cách chạy

### Cách 1: Chạy demo tự động (khuyến nghị)
```bash
python demo.py
```
Script sẽ tự động khởi động 3 nút và chạy toàn bộ kịch bản.

### Cách 2: Chạy thủ công (để quan sát log từng nút)
Mở 4 terminal riêng biệt:

**Terminal 1 - NodeA:**
```bash
python node_server.py NodeA 5001
```

**Terminal 2 - NodeB:**
```bash
python node_server.py NodeB 5002
```

**Terminal 3 - NodeC:**
```bash
python node_server.py NodeC 5003
```

**Terminal 4 - Demo:**
```bash
python demo.py
```

### Cách 3: Chạy giao diện Web (trực quan - khuyến nghị)
Mở 4 terminal riêng biệt:

**Terminal 1 - NodeA:**
```bash
python node_server.py NodeA 5001
```

**Terminal 2 - NodeB:**
```bash
python node_server.py NodeB 5002
```

**Terminal 3 - NodeC:**
```bash
python node_server.py NodeC 5003
```

**Terminal 4 - Web App:**
```bash
python web_app.py
```

Sau đó, mở trình duyệt và truy cập vào:
```
http://localhost:5000
```

**Lợi ích của giao diện Web:**
- 📊 **Hiển thị trực quan** trạng thái của 3 nút (NodeA, NodeB, NodeC)
- 🔄 **Theo dõi real-time** các thao tác đọc/ghi trên hệ thống
- 🎯 **Thao tác dễ dàng** với giao diện đồ họa thay vì dòng lệnh
- 💾 **Xem dữ liệu trực tiếp** trên các nút và tính nhất quán
- ⚡ **Kiểm tra hiệu năng** của giao thức ROWA một cách trực quan

## Kịch bản Demo

| Kịch bản | Mô tả | Kết quả mong đợi |
|----------|-------|------------------|
| A | Ghi khi tất cả nút sống | Thành công - 3 nút đều có dữ liệu |
| B | Ghi khi NodeC bị tắt | Từ chối + Rollback tự động |
| C | Đọc từ nút bất kỳ | Dữ liệu nhất quán trên mọi nút |

## Giải thích ROWA theo Özsu & Valduriez
- **Write quorum = N**: Ghi phải thành công trên TẤT CẢ bản sao
- **Read quorum = 1**: Đọc chỉ cần 1 bản sao bất kỳ
- **Hệ quả**: Consistency tuyệt đối, Availability bị giới hạn (CP system)
