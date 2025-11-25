# Mô Hình Mối Đe Dọa của UIT-Go

Phân tích mối đe dọa cho hệ thống UIT-Go ride-sharing platform sử dụng phương pháp STRIDE.

## 📊 Sơ Đồ Luồng Dữ Liệu (DFD)

### DFD Level 0: Sơ Đồ Ngữ Cảnh

```
┌──────────────┐
│   Khách hàng │
│   Ứng dụng   │
└──────┬───────┘
       │
       │ HTTPS
       ▼
┌─────────────────────────────────────────────┐
│                                             │
│           Nền tảng UIT-Go                   │
│  (5 Microservices trên Azure AKS)           │
│                                             │
└────┬─────────┬──────────┬──────────┬───────┘
     │         │          │          │
     │         │          │          │
┌────▼────┐ ┌──▼──────┐ ┌▼────────┐ ┌▼──────┐
│ Tài xế  │ │  VNPay  │ │ Mapbox  │ │ Azure │
│ Ứng dụng│ │ Thanh to│ │   API   │ │  DBs  │
└─────────┘ └─────────┘ └─────────┘ └───────┘
```

**Các Thực Thể Bên Ngoài:**
1. **Ứng dụng Khách hàng** - Ứng dụng Mobile/Web cho hành khách
2. **Ứng dụng Tài xế** - Ứng dụng mobile cho tài xế
3. **VNPay** - Cổng thanh toán (bên thứ ba)
4. **Mapbox API** - Dịch vụ định vị (bên thứ ba)
5. **Azure Databases** - PostgreSQL, CosmosDB, Redis

---

### DFD Level 1: Tương Tác Dịch Vụ

```
                        Internet (HTTPS)
                              │
                              ▼
                    ┌──────────────────┐
                    │  NGINX Ingress   │
                    │  + Linkerd Mesh  │ ← Service Mesh + mTLS
                    │    LoadBalancer  │
                    └────────┬─────────┘
                             │
           ┌─────────────────┼──────────────────┐
           │                 │                  │
           ▼                 ▼                  ▼
    ┌─────────────┐   ┌─────────────┐   ┌─────────────┐
    │ UserService │   │ TripService │   │LocationSvc  │
    │   (REST)    │   │   (REST)    │   │(REST+WS)    │
    └──────┬──────┘   └──────┬──────┘   └──────┬──────┘
           │                 │                  │
           ▼                 ▼                  ▼
    ┌───────────┐     ┌───────────┐     ┌───────────┐
    │PostgreSQL │     │ CosmosDB  │     │   Redis   │
    │  (VNet)   │     │(Service EP)     │(Service EP)│
    └───────────┘     └───────────┘     └───────────┘

           │                 │
           ▼                 ▼
    ┌─────────────┐   ┌──────────────┐
    │DriverService│   │PaymentService│
    │   (REST)    │   │   (REST)     │
    └──────┬──────┘   └──────┬───────┘
           │                 │
           ▼                 │
    ┌───────────┐           │
    │ CosmosDB  │           │
    │(Service EP)           │
    └───────────┘           │
                            ▼
                     ┌─────────────┐
                     │ VNPay API   │
                     │  (Bên ngoài) │
                     └─────────────┘
```

**Luồng Dữ Liệu Chính:**
1. **Xác thực**: Khách hàng/Tài xế → UserService → PostgreSQL
2. **Đặt chuyến**: Khách hàng → TripService → CosmosDB
3. **Theo dõi vị trí**: Tài xế → LocationService → Redis (thời gian thực)
4. **Thanh toán**: Khách hàng → PaymentService → VNPay → CosmosDB
5. **Quản lý tài xế**: Admin → DriverService → CosmosDB

---

### DFD Level 2: Luồng Dữ Liệu Quan Trọng

#### Luồng 1: Xác Thực Người Dùng

```
┌─────────┐
│ Client  │
└────┬────┘
     │ POST /api/users/login
     │ {username, password}
     ▼
┌──────────────┐
│   Ingress    │ ← Giới hạn tốc độ (5 login/min)
│ + Linkerd    │ ← Service Mesh + mTLS
└──────┬───────┘
       │
       ▼
┌──────────────┐
│ UserService  │
│  1. Xác thực│
│  2. Hash pwd │
│  3. Query DB │
└──────┬───────┘
       │
       ▼
┌──────────────┐
│ PostgreSQL   │
│  users table │
└──────┬───────┘
       │
       │ Return user + hashed password
       ▼
┌──────────────┐
│ UserService  │
│ 1. Verify pwd│
│ 2. Gen JWT   │
└──────┬───────┘
       │
       │ JWT token (30min expiry)
       ▼
┌─────────┐
│ Client  │
└─────────┘
```

**Mối đe dọa:**
- Tấn công brute force
- Credential stuffing
- Đánh cắp JWT token
- Man-in-the-middle

#### Luồng 2: Đặt Chuyến

```
┌─────────┐
│ Khách hàng│
└────┬────┘
     │ POST /api/trips
     │ {pickup, destination}
     ▼
┌──────────────┐
│   Ingress    │ ← Kiểm tra xác thực
│ + Linkerd    │ ← Service Mesh + mTLS
└──────┬───────┘
       │
       ▼
┌──────────────┐
│ TripService  │
│ 1. Xác thực  │
│ 2. Tìm tài xế│
│ 3. Lưu vào DB │
└──────┬───────┘
       │
       ▼
┌──────────────┐
│   CosmosDB   │
│  trips table │
└──────┬───────┘
       │
       │ Return trip ID + status
       ▼
┌──────────────┐
│ TripService  │
│ Thông báo Tài xế│
│ Cập nhật Redis │
└──────┬───────┘
       │
       │ WebSocket + HTTP
       ▼
┌────────────────────────────┐
│        Ứng dụng Tài xế     │
│     Thông báo              │
└────────────────────────────┘
```

**Mối đe dọa:**
- Tạo chuyến trái phép
- Gán tài xế giả
- Canh cóp dữ liệu chuyến đi
- Từ chối dịch vụ

#### Luồng 3: Xử Lý Thanh Toán

```
┌─────────┐
│ Client  │
└────┬────┘
     │ POST /api/payments
     │ {trip_id, amount}
     ▼
┌──────────────┐
│   Ingress    │ ← Kiểm tra đầu vào
│ + Linkerd    │ ← Service Mesh + mTLS
└──────┬───────┘
       │
       ▼
┌──────────────┐
│PaymentService│
│ 1. Xác thực  │
│ 2. Gọi VNPay │
└──────┬───────┘
       │
       │ HTTPS + API Key
       ▼
┌─────────────────────────────┐
│         Cổng VNPay          │
│  Xử lý thanh toán           │
└─────────────┬───────────────┘
              │
              │ URL thanh toán
              ▼
┌─────────────────────────────┐
│         Client              │
│  Chuyển hướng đến VNPay     │
└─────────────────────────────┘
```

**Mối đe dọa:**
- Can thiệp số tiền thanh toán
- Hoàn tiền trái phép
- Lạm dụng API thanh toán
- Tấn công replay giao dịch

---

## 🎯 Phân Tích STRIDE

### Thành phần 1: NGINX Ingress Controller + Linkerd Service Mesh

| Mối đe dọa | Mô tả | Khả năng | Tác động | Giải pháp | Ưu tiên |
|--------|-------------|------------|--------|------------|----------|
| **Giả mạo** | Kẻ tấn công mạo danh client hợp lệ | Trung bình | Cao | TLS certificates, JWT validation | CAO |
| **Can thiệp** | Sửa đổi request trong quá trình truyền | Thấp | Cao | HTTPS/TLS 1.3 + Service Mesh mTLS | TRUNG BÌNH |
| **Chối bỏ** | Chối gửi request độc hại | Trung bình | Thấp | Access logs, Service Mesh audit logs | THẤP |
| **Tiết lộ thông tin** | Phơi bày IP dịch vụ nội bộ | Thấp | Trung bình | Network policies chặn truy cập trực tiếp | TRUNG BÌNH |
| **Từ chối dịch vụ** | Flood với requests | Cao | Cao | Rate limiting (NGINX), connection limits | CAO |
| **Nâng cao quyền** | Bỏ qua kiểm soát bảo mật | Trung bình | Cao | Network policies + Zero Trust | CAO |

**Giải pháp đề xuất:**
- ✅ Bật Linkerd Service Mesh với automatic mTLS
- ✅ Rate limiting: 100 req/min chung, 5 login/min
- ✅ Network policies: Chặn tất cả theo mặc định
- ✅ Mã hóa service-to-service theo mặc định
- ✅ Giới hạn kích thước request body: 10MB

---

### Thành phần 2: UserService (Xác thực)

| Mối đe dọa | Mô tả | Khả năng | Tác động | Giải pháp | Ưu tiên |
|--------|-------------|------------|--------|------------|----------|
| **Giả mạo** | Thông tin đăng nhập giả | Cao | Cao | Mã hóa password mạnh, rate limiting | CAO |
| **Can thiệp** | Sửa đổi dữ liệu người dùng | Trung bình | Cao | Kiểm tra đầu vào, ràng buộc DB | CAO |
| **Chối bỏ** | Chối thực hiện giao dịch | Cao | Trung bình | Logs audit toàn diện | TRUNG BÌNH |
| **Tiết lộ thông tin** | Lọt PII người dùng | Trung bình | NGHIÊM TRỌNG | Mã hóa dữ liệu, kiểm soát truy cập | NGHIÊM TRỌNG |
| **Từ chối dịch vụ** | Authentication DoS | Cao | Trung bình | Rate limiting, khóa tài khoản | TRUNG BÌNH |
| **Nâng cao quyền** | Leo thang đặc quyền | Thấp | NGHIÊM TRỌNG | RBAC, đặc quyền tối thiểu | NGHIÊM TRỌNG |

**Giải pháp đề xuất:**
- ✅ Mã hóa password Argon2
- ✅ JWT với thời gian hết hạn 30 phút
- ✅ Rate limiting: 5 lần/phút
- ✅ Khóa tài khoản sau 10 lần thất bại
- ✅ Mã hóa PII khi lưu trữ

---

### Thành phần 3: TripService (Logic kinh doanh chính)

| Mối đe dọa | Mô tả | Khả năng | Tác động | Giải pháp | Ưu tiên |
|--------|-------------|------------|--------|------------|----------|
| **Giả mạo** | Request chuyến đi giả | Cao | Cao | Authentication + authorization | CAO |
| **Can thiệp** | Sửa đổi dữ liệu chuyến đi | Trung bình | Cao | Kiểm tra đầu vào, quy tắc kinh doanh | CAO |
| **Chối bỏ** | Chối các hành động chuyến đi | Trung bình | Trung bình | Logs chuyến đi bất biến | TRUNG BÌNH |
| **Tiết lộ thông tin** | Lọt thông tin chuyến đi | Trung bình | Trung bình | Kiểm soát truy cập, ẩn dữ liệu | TRUNG BÌNH |
| **Từ chối dịch vụ** | Flood tạo chuyến đi | Trung bình | Trung bình | Rate limiting, quotas | TRUNG BÌNH |
| **Nâng cao quyền** | Lạm dụng quyền admin | Thấp | Cao | RBAC, logs audit | CAO |

**Giải pháp đề xuất:**
- ✅ Kiểm tra quy tắc kinh doanh
- ✅ Kiểm tra giới hạn địa lý
- ✅ Rate limiting cho mỗi người dùng
- ✅ Records chuyến đi bất biến
- ✅ Tích hợp đánh giá tài xế

---

### Thành phần 4: PaymentService (Tài chính)

| Mối đe dọa | Mô tả | Khả năng | Tác động | Giải pháp | Ưu tiên |
|--------|-------------|------------|--------|------------|----------|
| **Giả mạo** | Request thanh toán giả | Cao | NGHIÊM TRỌNG | Multi-factor auth, digital signatures | NGHIÊM TRỌNG |
| **Can thiệp** | Sửa đổi số tiền thanh toán | Trung bình | NGHIÊM TRỌNG | Kiểm tra số tiền, digital signatures | NGHIÊM TRỌNG |
| **Chối bỏ** | Chối giao dịch thanh toán | Cao | Cao | Logs giao dịch bất biến | CAO |
| **Tiết lộ thông tin** | Lọt chi tiết thanh toán | Thấp | NGHIÊM TRỌNG | Mã hóa dữ liệu thẻ, tuân thủ PCI-DSS | NGHIÊM TRỌNG |
| **Từ chối dịch vụ** | Flood API thanh toán | Trung bình | Cao | Rate limiting trên endpoints thanh toán | CAO |
| **Nâng cao quyền** | Hoàn tiền trái phép | Thấp | NGHIÊM TRỌNG | Multi-factor auth cho hoàn tiền, role-based access | NGHIÊM TRỌNG |

**Giải pháp đề xuất:**
- ✅ Chỉ HTTPS đến VNPay
- ✅ Kiểm tra signature request/response
- ✅ Kiểm tra định dạng số tiền trong Service Mesh
- ✅ Kiểm tra tính duy nhất ID giao dịch
- ✅ Logs audit cho tất cả operations thanh toán

---

### Thành phần 5: LocationService (Thời gian thực)

| Mối đe dọa | Mô tả | Khả năng | Tác động | Giải pháp | Ưu tiên |
|--------|-------------|------------|--------|------------|----------|
| **Giả mạo** | Dữ liệu vị trí giả | Cao | Cao | Kiểm tra GPS, chống giả mạo | CAO |
| **Can thiệp** | Sửa đổi vị trí | Trung bình | Trung bình | Kiểm tra vị trí, tương quan chuyến đi | TRUNG BÌNH |
| **Chối bỏ** | Chối vị trí | Thấp | Thấp | Logs vị trí | THẤP |
| **Tiết lộ thông tin** | Lọt dữ liệu vị trí | Trung bình | Cao | Mã hóa vị trí, kiểm soát truy cập | CAO |
| **Từ chối dịch vụ** | Flood cập nhật vị trí | Cao | Trung bình | Rate limiting, giới hạn dữ liệu | TRUNG BÌNH |
| **Nâng cao quyền** | Truy cập tất cả vị trí | Thấp | Cao | RBAC, phân chia dữ liệu | CAO |

**Giải pháp đề xuất:**
- ✅ Xác thực WebSocket
- ✅ Kiểm tra giới hạn vị trí
- ✅ Rate limiting: 10 cập nhật/phút
- ✅ Mã hóa dữ liệu vị trí
- ✅ Controls bảo mật (sự đồng ý của tài xế)

---

## 🔐 Phân Tích Xác Thực & Phân Quyền

### 1. Xác Thực API Endpoints

| Endpoint | Protocol | Phương thức | Mã hóa | Ưu tiên |
|----------|----------|-------------|------------|----------|
| `/api/users/*` | HTTPS | JWT | Không có | CAO |
| `/api/trips/*` | HTTPS | JWT | Không có | CAO |
| `/api/drivers/*` | HTTPS | JWT | Không có | CAO |
| `/api/locations/*` | HTTPS | JWT | Không có | TRUNG BÌNH |
| `/api/payments/*` | HTTPS | JWT | Không có | NGHIÊM TRỌNG |
| `/ws` | WSS | JWT | Không có | CAO |

**Sau Phase 2 (Service Mesh):**
- Mức độ rủi ro giảm xuống TRUNG BÌNH/THẤP
- Service mesh mã hóa giữa các services

### 2. Giao Tiếp Service-to-Service

| Nguồn | Đích | Protocol | Xác thực | Mã hóa |
|--------|-------------|----------|----------------|------------|
| TripService | UserService | HTTP | Linkerd mTLS | mTLS encrypted |
| PaymentService | TripService | HTTP | Linkerd mTLS | mTLS encrypted |
| LocationService | TripService | HTTP | Linkerd mTLS | mTLS encrypted |

**Mối đe dọa:**
- Giả mạo service (ĐÃ GIẢI QUYẾT ✅)
- Các cuộc gọi dịch vụ trái phép (ĐÃ GIẢI QUYẾT ✅)

**Giải pháp (ĐÃ TRIỂN KHAI):**
- ✅ Linkerd Service Mesh cho mTLS
- ✅ Zero Trust Network Policies
- ✅ Tự động chuyển đổi chứng chỉ

### 3. Truy Cập Database

| Database | Phương thức | Xác thực | Mã hóa |
|----------|----------------|----------------|------------|
| PostgreSQL | VNet | Azure AD + Connection String | TLS 1.3 |
| CosmosDB | Service Endpoint | Azure AD | mTLS |
| Redis | Service Endpoint | Access Key | TLS 1.3 |

---

## 📊 Ma Trận Đánh Giá Rủi Ro

### Các Mức Độ Rủi Ro
- 🔴 **NGHIÊM TRỌNG**: Cần hành động ngay
- 🟠 **CAO**: Giải quyết trong 1 tuần
- 🟡 **TRUNG BÌNH**: Giải quyết trong 1 tháng
- 🟢 **THẤP**: Giải quyết trong chu kỳ lập kế hoạch tiếp theo

### Rủi Ro Đã Xác Định

| Rủi ro | Thành phần | Giai đoạn Giải pháp | Trạng thái |
|------|-----------|------------------|--------|
| CosmosDB có thể truy cập công khai | Databases | Phase 1.2 | 🔴 Ưu tiên Cao |
| Redis có thể truy cập công khai | Databases | Phase 1.2 | 🔴 Ưu tiên Cao |
| Không có Service Mesh protection | Ingress | Phase 2 | ✅ ĐÃ GIẢI QUYẾT (Linkerd đã triển khai) |
| Payment API dễ bị can thiệp | PaymentService | Phase 2 | 🔴 Ưu tiên Cao |
| Mã hóa password yếu | UserService | Phase 3 | 🟡 Ưu tiên Trung bình |
| Không có API rate limiting | Ingress | Phase 2 | 🟡 Ưu tiên Trung bình |
| Logging không đủ | All services | Phase 5 | 🟡 Ưu tiên Trung bình |

### Rủi Ro Cao

1. **Phơi Bày Database Công Khai** (NGHIÊM TRỌNG)
   - CosmosDB & Redis có thể truy cập từ internet
   - **Giải pháp**: VNet Service Endpoints + NSGs

2. **Can Thiệp API Thanh Toán** (CAO)
   - Không có kiểm tra số tiền thanh toán
   - **Giải pháp**: Service mesh + kiểm tra đầu vào

3. **Xác Thất Không Đủ** (CAO)
   - Không có rate limiting trên endpoints xác thực
   - **Giải pháp**: NGINX rate limiting + khóa tài khoản

---

## 🛡️ Chiến Lược Giải Quyết

### Phase 1: Bảo Mạng & Dữ Liệu (Tuần 1-2)
- ✅ Private endpoints database (VNet Service Endpoints)
- ✅ Network Security Groups (NSGs)
- ✅ Mã hóa secrets tại rest

### Phase 2: Zero Trust (Tuần 3)
- ✅ Triển khai service mesh (Linkerd)
- ✅ Mã hóa mTLS giữa services
- ✅ Network policies (chặn theo mặc định)

### Phase 3: Bảo Mật Ứng Dụng (Tuần 4-5)
- ✅ Kiểm tra & làm sạch đầu vào
- ✅ Rate limiting & throttling
- ✅ Cứng rắc hóa xác thực
- ✅ Cải thiện xử lý lỗi

### Phase 4: Giám Sát & Phản Hồi (Tuần 6)
- ✅ Giám sát bảo mật & cảnh báo
- ✅ Tổng hợp & phân tích logs
- ✅ Quy trình phản hồi sự cố
- ✅ Báo cáo tuân thủ

---

## 📋 Yêu Cầu Tuân Thủ

### Bảo Mật Dữ Liệu
- **Mã hóa PII**: Dữ liệu người dùng được mã hóa khi lưu trữ và truyền tải
- **Quyền Riêng Tư Vị Trí**: Theo dõi vị trí tài xế với sự đồng ý
- **Bảo Mật Thanh Toán**: Tuân thủ PCI-DSS cho xử lý thanh toán

### Tiêu Chuẩn Bảo Mật
- **OWASP Top 10**: Giải pháp cho tất cả 10 categories
- **Zero Trust**: Không bao giờ tin, luôn xác thực
- **Phòng Thủ Đa Lớp**: Multiple security layers

### Kiểm Toán & Giám Sát
- **Logging Toàn Diện**: Tất cả sự kiện bảo mật được ghi lại
- **Giám Sát Thời Gian Thực**: Phát hiện và phản hồi mối đe dọa
- **Đánh Giá Định Kỳ**: Đánh giá bảo mật hàng quý

---

## 🎯 Tiêu Chí Thành Công

### Metrics Bảo Mật
- ✅ **100%** traffic inter-service được mã hóa với mTLS
- ✅ **Zero** database endpoints công khai
- ✅ **< 5 phút** thời gian phản hồi sự cố trung bình
- ✅ **Zero** lỗ hổng nghiêm trọng trong production

### Tác Động Kinh Doanh
- ✅ **Giảm Rủi Ro**: 95% giảm bề mặt tấn công
- ✅ **Tuân Thủ**: Sẵn sàng cho đánh giá bảo mật
- ✅ **Hiệu Suất**: < 10ms độ trễ thêm
- ✅ **Chi Phí**: Zero chi phí bảo mật thêm

---

## 🔄 Bảo Trì & Cập Nhật

### Tác Vụ Hàng Tháng
- Review logs bảo mật và cảnh báo
- Cập nhật patches bảo mật và sửa lỗi CVE
- Xoay vòng secrets và chứng chỉ
- Kiểm tra quy trình phản hồi sự cố

### Tác Vụ Hàng Quý
- Đánh giá bảo mật toàn diện
- Review và cập nhật mô hình mối đe dọa
- Kiểm thử xâm phạm
- Chuẩn bị đánh giá tuân thủ

---

**Cập nhật lần cuối:** 2024-11-24
**Ngày review:** 2025-02-24
**Người chịu trách nhiệm:** UIT-Go Security Team

---

*"Bảo mật không phải là sản phẩm, mà là một quy trình."*