# UIT-Go - Nền tảng Gọi Xe

UIT-Go là nền tảng gọi xe được xây dựng với kiến trúc microservices sử dụng FastAPI, Python, và được triển khai trên Azure Kubernetes Service (AKS).

## 📚 Tài liệu hệ thống

- **[plan.md](docs/plan.md)**: Kế hoạch triển khai & security architecture
- **[ADRs](docs/ADRs/)**: Architecture Decision Records - các quyết định kiến trúc
- **[ENV.sample](docs/ENV.sample)**: Template file môi trường
- **[ARCHITECTURE.md](ARCHITECTURE.md)**: Tổng quan kiến trúc hệ thống
- **[demo.md](docs/demo.md)**: Kế hoạch demo và kịch bản thuyết trình
- **[threat-model.md](docs/threat-model.md)**: Phân tích rủi ro bảo mật

## 🏗️ Triển khai

### Tổng quan Services
- **5 Microservices**: Kiến trúc microservices FastAPI-based
- **3 Databases**: PostgreSQL, Azure CosmosDB, Redis Cache
- **AKS Deployment**: Thiết lập production trên Azure Kubernetes Service

### Công nghệ sử dụng
- **Backend**: Python, FastAPI, SQLAlchemy
- **Database**: PostgreSQL, MongoDB (CosmosDB), Redis
- **Infrastructure**: Azure AKS, Terraform
- **Security**: Linkerd Service Mesh, Zero Trust, mTLS

**Chi tiết architecture**: Xem [ARCHITECTURE.md](ARCHITECTURE.md)

## 🚀 Bắt đầu nhanh

### 1. Cài đặt môi trường

```bash
# Clone repository
git clone <repository-url>
cd se360-uit-go

# Tạo file .env từ template
cp docs/ENV.sample .env

# Chỉnh sửa .env với các credentials của bạn
# - JWT_SECRET_KEY
# - MAPBOX_ACCESS_TOKEN
# - VNP_TMN_CODE, VNP_HASH_SECRET
# - Database credentials
```

### 2. Triển khai trên Azure AKS

```bash
# Triển khai infrastructure
cd terraform
terraform init
terraform apply

# Triển khai ứng dụng
cd ..
kubectl apply -f k8s/

# Kiểm tra trạng thái
kubectl get pods
```

## 🚀 Triển khai trên Local

### Prerequisites
- Python 3.9+
- Docker Desktop
- PostgreSQL, Redis, MongoDB (nếu không dùng Azure)

### 2.1 Chạy với Docker Compose
```bash
# Xây dựng và khởi động các services
docker-compose up --build

# Kiểm tra health
curl http://localhost:8000/userservice/health
curl http://localhost:8002/tripservice/health
```

### 2.2 Chạy local (phát triển)
```bash
# Cài đặt dependencies
pip install -r requirements.txt

# Khởi động các services (mỗi terminal)
cd userservice && python main.py
cd tripservice && python main.py
cd driverservice && python main.py
cd locationservice && python main.py
cd paymentservice && python main.py
```

## 📡 API Documentation

### Authentication
- **POST** `/api/users/login` - Đăng nhập
- **POST** `/api/users/register` - Đăng ký
- **POST** `/api/users/refresh` - Làm mới token

### Trips
- **GET** `/api/trips` - Lấy danh sách chuyến đi
- **POST** `/api/trips` - Tạo chuyến đi mới
- **GET** `/api/trips/{trip_id}` - Chi tiết chuyến đi
- **PUT** `/api/trips/{trip_id}` - Cập nhật trạng thái

### Drivers
- **GET** `/api/drivers/nearby` - Tìm tài xế gần
- **PUT** `/api/drivers/{driver_id}/location` - Cập nhật vị trí
- **GET** `/api/drivers/{driver_id}/wallet` - Xem ví

### Location Tracking
- **WebSocket** `/ws/location/{trip_id}` - Theo dõi vị trí real-time

### Payments
- **POST** `/api/payments/create` - Tạo thanh toán
- **POST** `/api/payments/vnpay` - Thanh toán VNPay

## 🗺️ Kiến trúc hệ thống

### Luồng dữ liệu chính
```
┌──────────────┐    HTTPS    ┌──────────────────┐    mTLS    ┌─────────────────┐
│   Mobile App  │ ────────► │  NGINX Ingress   │ ────────► │ UserService     │
│  (Passenger   │            │ + Linkerd Mesh   │           │ (Authentication)│
│   + Driver)   │            └────────┬─────────┘           └─────────┬───────┘
└──────────────┘                     │                               │
                                      ▼                               ▼
                               ┌─────────────────┐              ┌──────────────┐
                               │  PaymentService │              │ PostgreSQL   │
                               │  (VNPay API)    │              │   (Users)    │
                               └────────┬─────────┘              └──────────────┘
                                        │
                                        ▼
                                ┌─────────────────┐
                                │   TripService   │
                                │ (Orchestration) │
                                └────────┬─────────┘
                                         │
                               mTLS     ▼
                    ┌───────────────────────────────────┐
                    │ CosmosDB (MongoDB) + Redis Cache   │
                    │    (Trips, Locations, Caching)     │
                    └───────────────────────────────────┘
```

### Security Architecture
- **Layer 1**: Network Security (NSGs, VNet)
- **Layer 2**: Ingress Security (NGINX + Rate Limiting)
- **Layer 3**: Service Mesh Security (Linkerd mTLS)
- **Layer 4**: Application Security (JWT, Input Validation)
- **Layer 5**: Data Security (Encryption at Rest)

## 🔒 Các tính năng bảo mật

### Zero Trust Architecture
- **mTLS Encryption**: Mọi traffic giữa services được mã hóa
- **Network Policies**: Default deny, chỉ cho phép traffic cần thiết
- **Identity Verification**: Service-to-service authentication

### Mobile App Security
- **No WAF**: Tối ưu cho mobile app backend
- **API Rate Limiting**: Bảo vệ DoS attacks
- **JWT Authentication**: Secure token-based auth
- **Input Validation**: Ngăn injection attacks

### Database Security
- **VNet Integration**: Private database access
- **Encryption at Rest**: K8s secrets + database encryption
- **Access Control**: Least privilege principle

## 📊 Giám sát & Logging

### Health Checks
- Liveness/Readiness probes cho tất cả services
- Health endpoints: `/health`, `/ready`
- Service mesh health monitoring

### Logs
- Structured JSON logging
- Log aggregation với Fluent Bit
- Application & security event logging

### Metrics
- Application metrics (Prometheus format)
- Service mesh telemetry
- Azure Monitor integration

## 🛠️ Công cụ phát triển

### Local Development
- **Docker Compose**: Full stack local
- **Minikube/kind**: Local Kubernetes
- **SQLite**: Local testing database

### CI/CD
- **GitHub Actions**: Automated testing & deployment
- **Terraform**: Infrastructure as Code
- **Helm**: Kubernetes package management

### Testing
- **Unit Tests**: pytest
- **Integration Tests**: API testing
- **Load Testing**: Performance testing

## 📋 Quy trình phát triển

### 1. Feature Development
```bash
git checkout -b feature/new-feature
# ... development ...
git commit -m "feat: add new feature"
git push origin feature/new-feature
# Create Pull Request
```

### 2. Code Quality
- Code review required
- Automated tests pass
- Security scans pass
- Documentation updated

### 3. Deployment
- Auto-deploy on merge to main
- Staging environment first
- Production with manual approval

## 🚨 Troubleshooting

### Common Issues
- **Service unreachable**: Check network policies
- **Database connection**: Verify VNet endpoints
- **mTLS failures**: Check Linkerd certificates
- **High latency**: Check service mesh metrics

### Debug Commands
```bash
# Service mesh debugging
kubectl get networkpolicies
linkerd check
linkerd tap deploy/userservice

# Application debugging
kubectl logs deployment/userservice
kubectl describe pod <pod-name>
```

## 📞 Hỗ trợ

- **Issues**: [GitHub Issues](https://github.com/[your-org]/se360-uit-go/issues)
- **Documentation**: [Wiki](https://github.com/[your-org]/se360-uit-go/wiki)
- **Team Development**: [Development Guide](docs/development-guide.md)

## 📄 License

© 2024 UIT-Go Team. All rights reserved.

---

**Made with ❤️ by UIT-Go Development Team**

**Version**: 1.0.0
**Last Updated**: 2024-11-24