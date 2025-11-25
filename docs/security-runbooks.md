# Runbooks Bảo Mật - UIT-Go

Quy trình phản hồi sự cố cho các sự kiện bảo mật phổ biến.

## 📋 Mục Lục Runbook

1. [Cảnh báo CPU cao](#runbook-1-cảnh-báo-cpu-cao)
2. [Pod khởi động lại lặp lại](#runbook-2-pod-khởi-động-lại-lặp-lại)
3. [Spike thất bại mTLS Service Mesh](#runbook-3-spike-thất-bại-mtls-service-mesh)
4. [Thất bại kết nối Database](#runbook-4-thất-bại-kết-nối-database)
5. [Hoạt động đăng nhập đáng ngờ](#runbook-5-hoạt-động-đăng-nhập-đáng-ngờ)
6. [Lỗ hổng container image](#runbook-6-lỗ-hổng-container-image)

---

## Runbook 1: Cảnh Báo CPU Cao

**Kích hoạt:** CPU AKS > 80%
**Mức độ nghiêm trọng:** Cao
**Cảnh báo:** `aks-high-cpu-alert`

### Các bước điều tra

```bash
# 1. Kiểm tra pod nào đang sử dụng CPU nhiều nhất
kubectl top pods --all-namespaces --sort-by=cpu

# 2. Kiểm tra mức sử dụng CPU node
kubectl top nodes

# 3. Mô tả pod CPU cao
kubectl describe pod <POD_NAME> -n <NAMESPACE>

# 4. Kiểm tra logs pod
kubectl logs <POD_NAME> -n <NAMESPACE> --tail=100
```

### Nguyên nhân phổ biến
- **Tấn công DoS:** Spike traffic bất thường → Kiểm tra logs Service Mesh
- **Rò rỉ bộ nhớ:** Tăng CPU liên tục → Kiểm tra mức sử dụng bộ nhớ
- **Code không hiệu quả:** Endpoint cụ thể gây spike → Review logs ứng dụng

### Khắc phục

**Nếu tấn công DoS:**
```bash
# Kiểm tra block Service Mesh
kubectl logs -n ingress-nginx deployment/ingress-nginx-controller | grep Service Mesh | grep blocked

# Xác định IP tấn công
kubectl logs -n ingress-nginx deployment/ingress-nginx-controller | grep "429\|403"

# Thêm quy tắc block IP (khẩn cấp)
kubectl edit cm -n ingress-nginx
# Thêm: SecRule REMOTE_ADDR "@ipMatch 1.2.3.4" "id:900999,phase:1,deny,status:403"
```

**Nếu sự cố ứng dụng:**
```bash
# Tạm thời tăng số lượng replica
kubectl scale deployment/<SERVICE> --replicas=3

# Khởi động lại pod có vấn đề
kubectl rollout restart deployment/<SERVICE>

# Hoàn về phiên bản trước nếu triển khai gần đây
kubectl rollout undo deployment/<SERVICE>
```

### Mức độ ưu tiên
Nếu CPU >80% >15 phút: Liên hệ team cơ sở hạ tầng

---

## Runbook 2: Pod Khởi Động Lại Lặp Lại

**Kích hoạt:** Trạng thái pod < 80% sẵn sàng
**Mức độ nghiêm trọng:** Nghiêm trọng
**Cảnh báo:** `aks-pod-restart-alert`

### Các bước điều tra

```bash
# 1. Xác định pod đang thất bại
kubectl get pods --all-namespaces | grep -v Running

# 2. Kiểm tra số lần khởi động lại
kubectl get pods -o json | jq '.items[] | select(.status.containerStatuses[].restartCount > 3) | .metadata.name'

# 3. Lấy sự kiện pod
kubectl describe pod <POD_NAME>

# 4. Kiểm tra logs (bao gồm container trước đó)
kubectl logs <POD_NAME> --previous
```

### Nguyên nhân phổ biến
- **OOM Kill:** Giới hạn bộ nhớ quá thấp
- **Thất bại Liveness Probe:** Kiểm tra sức khỏe thất bại
- **Vấn đề Security Context:** Người dùng không root không thể truy cập tài nguyên
- **Kết nối Database:** Không thể kết nối DB

### Khắc phục

**Đối với OOM:**
```bash
# Tăng giới hạn bộ nhớ
kubectl edit deployment/<SERVICE>
# Thay đổi:
#   limits:
#     memory: "1Gi"  # từ 512Mi

kubectl rollout restart deployment/<SERVICE>
```

**Đối với Security Context:**
```bash
# Kiểm tra quyền hệ thống file
kubectl exec <POD_NAME> -- ls -la /

# Sửa quyền sở hữu nếu cần (trong Dockerfile build tiếp theo)
# Hiện tại, thêm volume ghi được
kubectl edit deployment/<SERVICE>
# Thêm volumeMount cho path cần thiết
```

**Đối với kết nối Database:**
```bash
# Kiểm tra kết nối database
kubectl run -it --rm debug --image=busybox --restart=Never -- sh
# Bên trong: nc -zv <DB_HOST> <DB_PORT>

# Kiểm tra secrets
kubectl get secret uitgo-secrets -o yaml

# Xác minh Service Endpoints
az network vnet subnet show --resource-group rg-uitgo-prod --vnet-name vnet-uitgo-prod --name snet-aks-prod --query "serviceEndpoints"
```

### Mức độ ưu tiên
Nếu >5 pods trong CrashLoopBackOff: Sự cố ưu tiên 1

---

## Runbook 3: Spike Thất Bại mTLS Service Mesh

**Kích hoạt:** >10 thất bại kết nối mTLS trong 5 phút
**Mức độ nghiêm trọng:** Cao
**Cảnh báo:** `security-events-alert`

### Các bước điều tra

```bash
# 1. Kiểm tra trạng thái control plane Linkerd
linkerd check

# 2. Xem các thất bại kết nối gần đây
kubectl logs -n linkerd deployment/linkerd-controller | grep -i error | tail -50

# 3. Kiểm tra trạng thái proxy data plane
kubectl get pods -n linkerd

# 4. Xem edges service mesh
linkerd edges deploy --all-namespaces

# 5. Kiểm tra trạng thái chứng chỉ
kubectl get certificates -n linkerd

# 6. Kiểm tra kết nối service cụ thể
kubectl port-forward -n linkerd service/linkerd-controller 8080:8080 &
curl http://localhost:8080/metrics | grep failure
```

### Các loại tấn công

**SQL Injection:**
```bash
# Rule ID: 942xxx (OWASP CRS)
kubectl logs -n ingress-nginx deployment/ingress-nginx-controller | grep "id:942"
```

**XSS:**
```bash
# Rule ID: 941xxx
kubectl logs -n ingress-nginx deployment/ingress-nginx-controller | grep "id:941"
```

**Scanner:**
```bash
# Custom rule ID: 900115
kubectl logs -n ingress-nginx deployment/ingress-nginx-controller | grep "id:900115"
```

### Khắc phục

**Nếu traffic hợp lệ (Sai dương):**
```bash
# Xác định quy tắc gây block
# Thêm exception trong ingress.yaml
kubectl edit ingress uitgo-ingress
# Thêm annotation:
#   nginx.ingress.kubernetes.io/ |
#     SecRuleRemoveById 942100
```

**Nếu tấn công:**
```bash
# Đã được Service Mesh chặn - không cần hành động
# Theo dõi thay đổi pattern

# Nếu tấn công liên tục từ IP đơn lẻ
# Thêm block vĩnh viễn
kubectl edit cm -n ingress-nginx
# Thêm: SecRule REMOTE_ADDR "@ipMatch <ATTACKER_IP>" "id:900998,phase:1,deny,status:403"
kubectl rollout restart deployment/ingress-nginx-controller -n ingress-nginx
```

### Mức độ ưu tiên
Nếu tấn công tiếp tục >30 phút: Ghi lại và báo cáo

---

## Runbook 4: Thất Bại Kết Nối Database

**Kích hoạt:** Logs ứng dụng hiển thị lỗi DB
**Mức độ nghiêm trọng:** Nghiêm trọng

### Các bước điều tra

```bash
# 1. Kiểm tra kết nối PostgreSQL
kubectl run -it --rm psql-test --image=postgres:15 --restart=Never -- psql -h <POSTGRES_HOST> -U <USER> -d mydb

# 2. Kiểm tra kết nối CosmosDB
kubectl run -it --rm mongo-test --image=mongo:6 --restart=Never -- mongosh "<CONNECTION_STRING>"

# 3. Kiểm tra kết nối Redis
kubectl run -it --rm redis-test --image=redis:7 --restart=Never -- redis-cli -h <REDIS_HOST> ping

# 4. Kiểm tra Service Endpoints
az network vnet subnet show --resource-group rg-uitgo-prod --vnet-name vnet-uitgo-prod --name snet-aks-prod --query "serviceEndpoints[].service"
```

### Nguyên nhân phổ biến
- **Quy tắc NSG:** Chặn traffic database
- **Vấn đề Service Endpoint:** Không được cấu hình đúng
- **Xoay vòng Secret:** Chuỗi kết nối cũ
- **Database hỏng:** Vấn đề Azure

### Khắc phục

**Kiểm tra NSG:**
```bash
az network nsg rule list --resource-group rg-uitgo-prod --nsg-name nsg-aks-prod --output table

# Xác minh outbound database được cho phép
# Nên thấy: AllowDatabaseOutbound
```

**Kiểm tra Secrets:**
```bash
# Lấy secret hiện tại
kubectl get secret uitgo-secrets -o jsonpath='{.data.COSMOS_CONNECTION_STRING}' | base64 -d

# So sánh với Azure
az cosmosdb keys list --name cosmos-uitgo-prod --resource-group rg-uitgo-prod --type connection-strings
```

**Tạo lại Chuỗi Kết Nối:**
```bash
# Lấy chuỗi kết nối mới
COSMOS_CS=$(az cosmosdb keys list --name cosmos-uitgo-prod --resource-group rg-uitgo-prod --type connection-strings --query "connectionStrings[0].connectionString" -o tsv)

# Cập nhật secret
kubectl create secret generic uitgo-secrets --from-literal=COSMOS_CONNECTION_STRING="$COSMOS_CS" --dry-run=client -o yaml | kubectl apply -f -

# Khởi động lại các dịch vụ bị ảnh hưởng
kubectl rollout restart deployment/tripservice
kubectl rollout restart deployment/driverservice
kubectl rollout restart deployment/paymentservice
```

### Mức độ ưu tiên
Nếu database không thể kết nối >10 phút: Vé hỗ trợ Azure

---

## Runbook 5: Hoạt Động Đăng Nhập Đáng Ngờ

**Kích hoạt:** >5 lần đăng nhập thất bại từ cùng IP
**Mức độ nghiêm trọng:** Trung bình
**Cảnh báo:** Quy tắc Service Mesh 900106

### Các bước điều tra

```bash
# 1. Kiểm tra các lần đăng nhập thất bại
kubectl logs deployment/userservice | grep "401\|failed\|unauthorized"

# 2. Xác định địa chỉ IP
kubectl logs -n ingress-nginx deployment/ingress-nginx-controller | grep "/api/users/login" | grep "429\|403"

# 3. Kiểm tra IP có phải là kẻ tấn công đã biết không
# Sử dụng cơ sở dữ liệu threat intelligence hoặc kiểm tra https://www.abuseipdb.com
```

### Khắc phục

**Nếu tấn công brute force:**
```bash
# Đã được giới hạn tốc độ bởi Service Mesh (5 lần/phút)
# Tự động bị chặn sau khi vượt ngưỡng

# Nếu tấn công tiếp tục, thêm block IP
kubectl edit cm -n ingress-nginx
# Thêm vào quy tắc tùy chỉnh
kubectl rollout restart deployment/ingress-nginx-controller -n ingress-nginx
```

**Nếu Credential Stuffing:**
```bash
# Review các tài khoản người dùng cho password bị xâm phạm
kubectl exec deployment/userservice -- python -c "
from app import check_compromised_passwords
check_compromised_passwords()
"

# Yêu cầu đặt lại password cho người dùng bị ảnh hưởng
```

### Mức độ ưu tiên
Nếu >100 lần đăng nhập thất bại/giờ: Review team bảo mật

---

## Runbook 6: Lỗ Hổng Container Image

**Kích hoạt:** Quét Trivy phát hiện CVE CAO/NGHIÊM TRỌNG
**Mức độ nghiêm trọng:** Cao (thay đổi theo CVE)
**Cảnh báo:** Workflow GitHub Actions thất bại

### Các bước điều tra

```bash
# 1. Tải báo cáo Trivy từ GitHub Artifacts
gh run download <RUN_ID>
cat trivy-userservice.json | jq '.Results[].Vulnerabilities[] | select(.Severity=="CRITICAL")'

# 2. Kiểm tra nếu có exploit có sẵn
# Review chi tiết CVE tại https://cve.mitre.org

# 3. Kiểm tra nếu có bản sửa lỗi
cat trivy-userservice.json | jq '.Results[].Vulnerabilities[] | select(.FixedVersion != "")'
```

### Khắc phục

**Nếu có bản sửa lỗi:**
```bash
# Cập nhật dependency trong requirements.txt
# Ví dụ cho userservice:
echo "flask==2.3.5" >> UserService/requirements.txt  # Phiên bản đã sửa

# Commit và push
git add UserService/requirements.txt
git commit -m "fix: Update Flask to patch CVE-XXXX-YYYY"
git push origin main

# Pipeline sẽ build lại và quét lại
```

**Nếu không có bản sửa lỗi:**
```bash
# 1. Đánh giá rủi ro
# - Service có được phơi bày không?
# - Code path dễ bị tổn thương có được sử dụng không?
# - Điểm CVSS là bao nhiêu?

# 2. Nếu rủi ro thấp, chấp nhận tạm thời
# Thêm vào danh sách bỏ qua Trivy
echo "CVE-XXXX-YYYY" >> .trivyignore

# 3. Ghi lại trong ADR
# Tạo docs/adrs/ADR-011-accepted-cve-XXXX.md

# 4. Đặt nhắc nhở kiểm tra lại sau 30 ngày
```

**Nếu vấn đề base image:**
```bash
# Cập nhật base image trong Dockerfile
# FROM python:3.11-slim  →  FROM python:3.11.8-slim

docker build -t test .
docker run --rm test python --version  # Xác minh
```

### Mức độ ưu tiên
Nếu CVE NGHIÊM TRỌNG với exploit đã biết: Cần hotfix ngay lập tức

---

## Liên Hệ Khẩn Cấp

| Vai trò | Liên hệ | Mục đích |
|------|---------|---------|
| Trưởng nhóm Dev | your-email@example.com | Vấn đề ứng dụng |
| Team Bảo Mật | security@example.com | Sự cố bảo mật |
| Azure Support | Azure Portal | Vấn đề cơ sở hạ tầng |
| Người trực | PagerDuty/Slack | Khẩn cấp ngoài giờ |

---

## Liên kết Dashboard Giám Sát

- **Azure Monitor:** https://portal.azure.com → Monitor → Alerts
- **Log Analytics:** https://portal.azure.com → Log Analytics workspaces
- **GitHub Actions:** https://github.com/org/repo/actions
- **AKS Cluster:** https://portal.azure.com → Kubernetes services

---

## Sau Sự Cố

Sau khi giải quyết bất kỳ sự cố bảo mật nào:

1. ✅ Ghi lại sự cố trong nhật ký sự cố
2. ✅ Cập nhật runbook nếu quy trình thay đổi
3. ✅ Lên lịch post-mortem trong vòng 48 giờ
4. ✅ Triển khai các biện pháp phòng ngừa
5. ✅ Cập nhật giám sát/cảnh báo nếu cần