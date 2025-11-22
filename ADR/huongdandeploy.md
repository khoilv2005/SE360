# Hướng Dẫn Triển Khai Hệ Thống (Deployment Guide)

Tài liệu này hướng dẫn chi tiết các bước để triển khai hệ thống theo mô hình **Modern DevOps (GitOps)**, sử dụng hạ tầng "xịn" của Azure nhưng vẫn đảm bảo kiểm soát chi phí cho tài khoản sinh viên ($100).

---

## ⚠️ QUAN TRỌNG: QUẢN LÝ CHI PHÍ ($100)

Hệ thống này sử dụng các dịch vụ Managed Services (AKS, Postgres Flexible, Redis, CosmosDB) nên chi phí khoảng **$2.5 - $3 / ngày**.

*   **NGUYÊN TẮC SỐNG CÒN:** Chỉ bật hệ thống khi làm việc hoặc demo. Làm xong phải tắt ngay.
*   **Lệnh TẮT (Xóa sạch):**
    ```bash
    cd terraform
    terraform destroy -auto-approve
    ```
*   **Lệnh BẬT (Dựng lại):**
    ```bash
    cd terraform
    terraform apply -auto-approve
    ```
    *(Mất khoảng 10-15 phút để dựng lại toàn bộ)*

---

## GIAI ĐOẠN 1: DỰNG NHÀ RIÊNG (Infrastructure)

**Mục tiêu:** Tạo một bộ tài nguyên riêng biệt trên Azure, không dùng chung tên với người khác để tránh xung đột.

### 1. Sửa file `terraform/variables.tf`
Tìm biến `prefix` và đổi giá trị `default` thành tên riêng của bạn (ví dụ: `huyproject`).

```hcl
variable "prefix" {
  description = "Tiền tố cho tất cả tài nguyên"
  type        = string
  default     = "huyproject" # <--- SỬA Ở ĐÂY
}
```

### 2. Sửa file `terraform/acr.tf`
Tên Azure Container Registry (ACR) phải là **duy nhất trên toàn cầu**.

```hcl
resource "azurerm_container_registry" "acr" {
  name                = "acrhuyproject2025" # <--- SỬA THÀNH TÊN KHÁC (viết thường, không dấu)
  # ...
}
```

### 3. Khởi tạo hạ tầng
Mở terminal tại thư mục `terraform`:
```bash
terraform init
terraform apply -auto-approve
```

---

## GIAI ĐOẠN 2: TỰ ĐỘNG ĐÓNG GÓI (CI - Continuous Integration)

**Mục tiêu:** Khi push code lên GitHub, tự động build Docker Image và đẩy vào ACR.

### 1. Lấy thông tin ACR
Vào Azure Portal -> Tìm ACR vừa tạo -> **Access keys** -> Lấy `Login server`, `Username`, `Password`.

### 2. Cấu hình GitHub Secrets
Vào Repo GitHub -> **Settings** -> **Secrets and variables** -> **Actions** -> **New repository secret**:
*   `ACR_NAME`: Tên ACR (ví dụ: `acrhuyproject2025`)
*   `AZURE_CREDENTIALS`: JSON thông tin đăng nhập Azure (đã có từ trước).

### 3. Sửa file `.github/workflows/deploy.yml`
Chúng ta sẽ chuyển sang GitOps, nên cần **BỎ** phần deploy thủ công trong file này.
*   **Giữ lại:** Job `test` và `build`.
*   **Xóa bỏ:** Job `deploy` và `smoke_test`.

---

## GIAI ĐOẠN 3: TỰ ĐỘNG TRIỂN KHAI (CD - GitOps với ArgoCD)

**Mục tiêu:** ArgoCD (chạy trong AKS) sẽ tự động theo dõi GitHub và đồng bộ code mới về cluster.

### 1. Kết nối vào AKS
```bash
az aks get-credentials --resource-group rg-huyproject-prod --name aks-huyproject-prod
```

### 2. Cài đặt ArgoCD
```bash
kubectl create namespace argocd
kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml
```

### 3. Lấy mật khẩu đăng nhập ArgoCD
```bash
kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath="{.data.password}" | base64 -d
```
*   User: `admin`
*   Pass: (kết quả lệnh trên)

### 4. Port Forward để vào giao diện ArgoCD
```bash
kubectl port-forward svc/argocd-server -n argocd 8080:443
```
Truy cập: `https://localhost:8080`

### 5. Tạo Application trong ArgoCD
Tạo file `argocd-app.yaml`:
```yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: uitgo-app
  namespace: argocd
spec:
  project: default
  source:
    repoURL: 'https://github.com/USERNAME/REPO_NAME.git' # <--- ĐIỀN LINK REPO CỦA BẠN
    targetRevision: HEAD
    path: k8s
  destination:
    server: https://kubernetes.default.svc
    namespace: default
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
```
Apply file này: `kubectl apply -f argocd-app.yaml`

---

## GIAI ĐOẠN 4: GIÁM SÁT (Observability)

**Mục tiêu:** Có dashboard đẹp để báo cáo.

### 1. Cài đặt Prometheus & Grafana (dùng Helm)
```bash
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update
helm install monitoring prometheus-community/kube-prometheus-stack
```

### 2. Truy cập Grafana
```bash
kubectl port-forward svc/monitoring-grafana 3000:80
```
Truy cập: `http://localhost:3000`
*   User: `admin`
*   Pass: `prom-operator`

---

## TỔNG KẾT QUY TRÌNH LÀM VIỆC MỚI

1.  Sửa code trên máy -> Push lên GitHub.
2.  GitHub Actions tự chạy -> Build Docker Image mới -> Push vào ACR.
3.  ArgoCD (trong AKS) tự phát hiện thay đổi (hoặc chờ 3 phút) -> Pull Image mới về -> Update Pod.
4.  Vào Grafana xem biểu đồ thay đổi.
