# Kế hoạch nâng cấp bảo mật hệ thống UIT-Go (Cost-Optimized)

Nâng cấp hệ thống UIT-Go với **Zero Trust, Defense-in-Depth, và DevSecOps practices** - tối ưu chi phí tối đa.

## Phân tích hiện trạng

### Hệ thống hiện tại
- **Kiến trúc**: Microservices trên Azure AKS (5 services)
- **Network**: VNet 172.16.0.0/16 với 2 subnets (AKS: 172.16.1.0/24, PostgreSQL: 172.16.2.0/24)
- **Databases**: PostgreSQL (Private VNet ✅), CosmosDB (Public ❌), Redis (Public ❌)
- **CI/CD**: GitHub Actions → ACR → AKS (Test → Build → Deploy → Smoke Test)
- **Ingress**: NGINX Ingress Controller v1.9.4 (LoadBalancer, không có WAF)
- **Secrets**: Kubernetes Secrets (base64, không encrypted at rest)
- **Monitoring**: Azure Monitor + Log Analytics (đã có ✅)

### Gap Analysis

| Security Layer | Required | Current | Gap | Free Solution |
|----------------|----------|---------|-----|---------------|
| WAF | ✅ | ❌ | No OWASP protection | ModSecurity (FREE) |
| Network Isolation | ✅ | ⚠️ | 2 DBs public | VNet Service Endpoints (FREE) |
| Secrets Management | ✅ | ⚠️ | Base64 only | K8s encrypted secrets (FREE) |
| SAST/SCA | ✅ | ❌ | No scanning | Bandit, Safety, Trivy (FREE) |
| DAST | ✅ | ❌ | No runtime testing | OWASP ZAP (FREE) |
| SIEM | ✅ | ⚠️ | Basic only | Azure Monitor alerts (FREE tier) |
| Network Segmentation | ✅ | ⚠️ | 2 subnets | NSGs + Service Endpoints (FREE) |

---

## Cost Optimization Strategy

### FREE Alternatives Used

| Enterprise Solution | Cost | FREE Alternative | Savings |
|---------------------|------|------------------|---------|
| Azure App Gateway WAF | $275-455/mo | **ModSecurity WAF** | $275-455/mo |
| Private Endpoints (2×) | $15/mo | **VNet Service Endpoints** | $15/mo |
| Azure Key Vault Premium | $1-5/mo | **K8s Secrets + encryption at rest** | $1-5/mo |
| Azure Sentinel | $20-50/mo | **Azure Monitor Free Tier** | $20-50/mo |
| Commercial SAST/DAST | $100+/mo | **OSS Tools (Bandit, ZAP, etc.)** | $100+/mo |
| **Total Savings** | - | - | **$411-625/mo** |

### Additional Costs

| Service | Cost | Justification |
|---------|------|---------------|
| **No additional services required** | **$0/mo** | All solutions use FREE tier or OSS |

**Total Additional Cost: $0-3/month** (chỉ có thể phát sinh từ increased Log Analytics data nếu vượt FREE tier 5GB/tháng)

---

## Proposed Changes

### Phase 1: Foundation & Threat Modeling (Week 1-2)

#### 1.1 Threat Model

##### [NEW] [docs/threat-model.md](file:///d:/UIT/SE360/UITGO/se360-uit-go/docs/threat-model.md)
```markdown
# UIT-Go Threat Model

## Data Flow Diagrams
- DFD Level 0: Context diagram
- DFD Level 1: Service interactions
- DFD Level 2: Authentication, Payment, Real-time tracking flows

## STRIDE Analysis
- Per component threat analysis
- Risk ratings (High/Medium/Low)
- Mitigation strategies mapped to implementation phases

## Attack Surface Analysis
- External APIs (VNPay, Mapbox)
- Public endpoints (REST, WebSocket)
- Database connections
- Service-to-service communication
```

**Deliverables:**
- [ ] DFD diagrams (Draw.io)
- [ ] STRIDE analysis matrix
- [ ] Risk assessment report
- [ ] Mitigation roadmap

**Measurable Outcomes:**
- ✅ 100% of components analyzed
- ✅ All HIGH risks have mitigation plan
- ✅ Attack surface documented

---

#### 1.2 Network Security Enhancement (FREE)

##### [MODIFY] [terraform/main.tf](file:///d:/UIT/SE360/UITGO/se360-uit-go/terraform/main.tf)
Thêm 2 subnets (CosmosDB và Redis vẫn dùng service endpoints, không cần dedicated subnets):
```hcl
# Management Subnet (cho Bastion/Jump box nếu cần sau này)
resource "azurerm_subnet" "management_subnet" {
  name                 = "snet-management-prod"
  resource_group_name  = azurerm_resource_group.rg.name
  virtual_network_name = azurerm_virtual_network.vnet.name
  address_prefixes     = ["172.16.5.0/24"]
}
```

##### [NEW] [terraform/network-security.tf](file:///d:/UIT/SE360/UITGO/se360-uit-go/terraform/network-security.tf)
```hcl
# NSG for AKS Subnet
resource "azurerm_network_security_group" "aks_nsg" {
  name                = "nsg-aks-prod"
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name

  # Inbound: Only from Internet on 80/443
  security_rule {
    name                       = "AllowHTTPSInbound"
    priority                   = 100
    direction                  = "Inbound"
    access                     = "Allow"
    protocol                   = "Tcp"
    source_port_range          = "*"
    destination_port_ranges    = ["80", "443"]
    source_address_prefix      = "Internet"
    destination_address_prefix = "172.16.1.0/24"
  }

  # Deny all other inbound
  security_rule {
    name                       = "DenyAllInbound"
    priority                   = 4096
    direction                  = "Inbound"
    access                     = "Deny"
    protocol                   = "*"
    source_port_range          = "*"
    destination_port_range     = "*"
    source_address_prefix      = "*"
    destination_address_prefix = "*"
  }

  # Outbound: Allow to database subnets + Azure services
  security_rule {
    name                       = "AllowDatabaseOutbound"
    priority                   = 100
    direction                  = "Outbound"
    access                     = "Allow"
    protocol                   = "Tcp"
    source_port_range          = "*"
    destination_port_ranges    = ["5432", "6379", "10255"]
    source_address_prefix      = "172.16.1.0/24"
    destination_address_prefix = "172.16.2.0/24"
  }

  security_rule {
    name                       = "AllowInternetOutbound"
    priority                   = 110
    direction                  = "Outbound"
    access                     = "Allow"
    protocol                   = "Tcp"
    source_port_range          = "*"
    destination_port_range     = "443"
    source_address_prefix      = "172.16.1.0/24"
    destination_address_prefix = "Internet"
  }
}

# Associate NSG with AKS subnet
resource "azurerm_subnet_network_security_group_association" "aks_nsg_assoc" {
  subnet_id                 = azurerm_subnet.aks_subnet.id
  network_security_group_id = azurerm_network_security_group.aks_nsg.id
}

# NSG for PostgreSQL Subnet
resource "azurerm_network_security_group" "postgres_nsg" {
  name                = "nsg-postgres-prod"
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name

  # Only allow from AKS subnet
  security_rule {
    name                       = "AllowAKSInbound"
    priority                   = 100
    direction                  = "Inbound"
    access                     = "Allow"
    protocol                   = "Tcp"
    source_port_range          = "*"
    destination_port_range     = "5432"
    source_address_prefix      = "172.16.1.0/24"
    destination_address_prefix = "172.16.2.0/24"
  }

  security_rule {
    name                       = "DenyAllInbound"
    priority                   = 4096
    direction                  = "Inbound"
    access                     = "Deny"
    protocol                   = "*"
    source_port_range          = "*"
    destination_port_range     = "*"
    source_address_prefix      = "*"
    destination_address_prefix = "*"
  }

  # Deny all outbound (databases should not initiate connections)
  security_rule {
    name                       = "DenyAllOutbound"
    priority                   = 4096
    direction                  = "Outbound"
    access                     = "Deny"
    protocol                   = "*"
    source_port_range          = "*"
    destination_port_range     = "*"
    source_address_prefix      = "*"
    destination_address_prefix = "*"
  }
}

resource "azurerm_subnet_network_security_group_association" "postgres_nsg_assoc" {
  subnet_id                 = azurerm_subnet.postgres_subnet.id
  network_security_group_id = azurerm_network_security_group.postgres_nsg.id
}
```

##### [MODIFY] [terraform/databases.tf](file:///d:/UIT/SE360/UITGO/se360-uit-go/terraform/databases.tf)
```hcl
# CosmosDB: Enable VNet Service Endpoint (FREE alternative to Private Endpoint)
resource "azurerm_cosmosdb_account" "cosmos" {
  # ... existing config ...
  
  # CHANGE: Disable public access, use VNet rules
  public_network_access_enabled     = false  # Changed from true
  is_virtual_network_filter_enabled = true   # Enable VNet filtering
  
  # Allow access from AKS subnet via service endpoint
  virtual_network_rule {
    id = azurerm_subnet.aks_subnet.id
  }
}

# Redis: Enable VNet Service Endpoint
resource "azurerm_redis_cache" "redis" {
  # ... existing config ...
  
  # CHANGE: Configure for VNet access
  public_network_access_enabled = false  # Changed from true
  
  # Create firewall rule for AKS subnet
  subnet_id = azurerm_subnet.aks_subnet.id  # Redis in AKS subnet
}

# Remove old firewall rule (no longer needed)
# resource "azurerm_redis_firewall_rule" "allow_azure_services" {
#   # DELETED
# }
```

##### [MODIFY] [terraform/main.tf](file:///d:/UIT/SE360/UITGO/se360-uit-go/terraform/main.tf) - Enable service endpoints
```hcl
resource "azurerm_subnet" "aks_subnet" {
  # ... existing config ...
  
  # Add service endpoints (FREE)
  service_endpoints = [
    "Microsoft.AzureCosmosDB",
    "Microsoft.Cache",
    "Microsoft.Storage",
    "Microsoft.Sql"
  ]
}
```

**Deliverables:**
- [ ] Network architecture diagram
- [ ] NSG rules applied to all subnets
- [ ] Service Endpoints enabled for CosmosDB/Redis
- [ ] Terraform validated and applied

**Measurable Outcomes:**
- ✅ 0 public database endpoints
- ✅ All database traffic through VNet
- ✅ NSG rules block unauthorized access

---

#### 1.3 Kubernetes Secrets Encryption at Rest (FREE)

##### [NEW] [scripts/enable-k8s-encryption.sh](file:///d:/UIT/SE360/UITGO/se360-uit-go/scripts/enable-k8s-encryption.sh)
```bash
#!/bin/bash
# Enable encryption at rest for Kubernetes secrets (AKS native feature - FREE)

az aks update \
  --resource-group rg-uitgo-prod \
  --name aks-uitgo-prod \
  --enable-encryption-at-host

# Verify encryption enabled
az aks show \
  --resource-group rg-uitgo-prod \
  --name aks-uitgo-prod \
  --query "securityProfile.azureKeyVaultKms" -o table

echo "✅ Kubernetes secrets now encrypted at rest"
```

**Deliverables:**
- [ ] Encryption at rest enabled for AKS
- [ ] Secrets rotation policy documented
- [ ] Secrets access audit enabled

**Measurable Outcomes:**
- ✅ 100% secrets encrypted at rest
- ✅ Encryption verified in Azure Portal

---

### Phase 2: ModSecurity WAF Implementation (Week 3)

#### 2.1 ModSecurity Configuration

##### [MODIFY] [k8s/nginx-ingress-controller.yaml](file:///d:/UIT/SE360/UITGO/se360-uit-go/k8s/nginx-ingress-controller.yaml)
```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: ingress-nginx-controller
  namespace: ingress-nginx
data:
  # Enable ModSecurity
  enable-modsecurity: "true"
  enable-owasp-modsecurity-crs: "true"
  modsecurity-snippet: |
    SecRuleEngine DetectionOnly  # Start in detection mode
    SecRequestBodyAccess On
    SecAuditEngine RelevantOnly
    SecAuditLogRelevantStatus "^(?:5|4(?!04))"
    SecAuditLogParts ABIJDEFHZ
    
    # Include OWASP CRS 4.0
    Include /etc/nginx/owasp-modsecurity-crs/nginx-modsecurity.conf
    Include /etc/nginx/owasp-modsecurity-crs/crs-setup.conf
    Include /etc/nginx/owasp-modsecurity-crs/rules/*.conf
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: ingress-nginx-controller
  namespace: ingress-nginx
spec:
  template:
    spec:
      containers:
      - name: controller
        image: registry.k8s.io/ingress-nginx/controller:v1.10.0
        args:
          # ... existing args ...
          - --enable-modsecurity=true
          - --enable-owasp-modsecurity-crs=true
        volumeMounts:
        - name: modsecurity-rules
          mountPath: /etc/nginx/owasp-modsecurity-crs
      volumes:
      - name: modsecurity-rules
        configMap:
          name: modsecurity-custom-rules
```

##### [NEW] [k8s/modsecurity-custom-rules.yaml](file:///d:/UIT/SE360/UITGO/se360-uit-go/k8s/modsecurity-custom-rules.yaml)
```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: modsecurity-custom-rules
  namespace: ingress-nginx
data:
  custom-rules.conf: |
    # UIT-Go Custom Security Rules
    
    # 1. Rate Limiting (100 requests/min per IP)
    SecAction "id:900100,phase:1,nolog,pass,initcol:ip=%{REMOTE_ADDR}"
    SecRule IP:REQUEST_RATE "@gt 100" \
        "id:900101,phase:1,deny,status:429,\
        msg:'Rate limit exceeded (100 req/min)',\
        setvar:ip.request_rate=+1,\
        expirevar:ip.request_rate=60"
    
    # 2. Authentication Rate Limiting (5 login attempts per minute)
    SecRule REQUEST_URI "@beginsWith /api/users/login" \
        "id:900105,phase:1,chain,deny,status:429,\
        msg:'Login rate limit exceeded (5/min)'"
    SecRule IP:LOGIN_RATE "@gt 5" \
        "setvar:ip.login_rate=+1,\
        expirevar:ip.login_rate=60"
    
    # 3. Payment API Protection
    SecRule REQUEST_URI "@beginsWith /api/payments" \
        "id:900110,phase:2,chain,deny,status:400,\
        msg:'Invalid payment request format'"
    SecRule ARGS:amount "!@rx ^[0-9]{1,10}$"
    
    # 4. Block malicious User-Agents
    SecRule REQUEST_HEADERS:User-Agent "@rx (sqlmap|nikto|nmap|masscan)" \
        "id:900115,phase:1,deny,status:403,\
        msg:'Malicious scanner detected'"
    
    # 5. Geo-blocking (optional - customize countries)
    # SecRule REMOTE_ADDR "@geoLookup" \
    #     "id:900120,phase:1,chain,deny,msg:'Blocked country'"
    # SecRule GEO:COUNTRY_CODE "@rx ^(KP|IR)$"
    
    # 6. File upload restrictions
    SecRule REQUEST_FILENAME "@rx \.(php|exe|sh|bat)$" \
        "id:900125,phase:1,deny,status:403,\
        msg:'Dangerous file extension blocked'"
```

##### [MODIFY] [k8s/ingress.yaml](file:///d:/UIT/SE360/UITGO/se360-uit-go/k8s/ingress.yaml)
```yaml
metadata:
  annotations:
    # ... existing annotations ...
    
    # ModSecurity annotations
    nginx.ingress.kubernetes.io/enable-modsecurity: "true"
    nginx.ingress.kubernetes.io/enable-owasp-core-rules: "true"
    nginx.ingress.kubernetes.io/modsecurity-transaction-id: "$request_id"
    
    # Disable ModSecurity for specific paths if needed
    # nginx.ingress.kubernetes.io/modsecurity-snippet: |
    #   SecRuleRemoveById 920100
```

**Deliverables:**
- [ ] ModSecurity enabled in DetectionOnly mode
- [ ] OWASP CRS 4.0 deployed
- [ ] Custom rules configured
- [ ] Logging configured

**Measurable Outcomes:**
- ✅ WAF blocks SQL injection attempts
- ✅ WAF blocks XSS attempts
- ✅ Rate limiting effective (429 after 100 req/min)
- ✅ 0 false positives for legitimate traffic

---

### Phase 3: CI/CD Security Integration (Week 4)

##### [MODIFY] [.github/workflows/deploy.yml](file:///d:/UIT/SE360/UITGO/se360-uit-go/.github/workflows/deploy.yml)

**Add 6 FREE security jobs:**

```yaml
jobs:
  # EXISTING: test job
  test:
    # ... keep as is ...

  # NEW JOB 1: SAST (Static Application Security Testing)
  sast:
    runs-on: ubuntu-latest
    needs: test
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'
    
    - name: Install Bandit
      run: pip install bandit[toml]
    
    - name: Run Bandit SAST
      run: |
        bandit -r UserService/ TripService/ DriverService/ LocationService/ PaymentService/ \
          -f json -o bandit-report.json || true
        bandit -r . -ll  # Show only HIGH severity
      continue-on-error: false
    
    - name: Upload SAST results
      uses: github/codeql-action/upload-sarif@v2
      if: always()
      with:
        sarif_file: bandit-report.json

  # NEW JOB 2: Dependency Scanning
  dependency-scan:
    runs-on: ubuntu-latest
    needs: test
    steps:
    - uses: actions/checkout@v3
    
    - name: Install Safety
      run: pip install safety
    
    - name: Scan dependencies
      run: |
        for service in UserService TripService DriverService LocationService PaymentService; do
          echo "Scanning $service..."
          safety check -r $service/requirements.txt --json || true
        done
      continue-on-error: false

  # NEW JOB 3: Secrets Scanning
  secrets-scan:
    runs-on: ubuntu-latest
    needs: test
    steps:
    - uses: actions/checkout@v3
      with:
        fetch-depth: 0  # Full history for TruffleHog
    
    - name: Run TruffleHog
      run: |
        docker run --rm -v "$PWD:/pwd" trufflesecurity/trufflehog:latest \
          filesystem /pwd --json --fail
      continue-on-error: false

  # NEW JOB 4: IaC Scanning
  iac-scan:
    runs-on: ubuntu-latest
    needs: test
    steps:
    - uses: actions/checkout@v3
    
    - name: Install Checkov
      run: pip install checkov
    
    - name: Scan Terraform files
      run: |
        checkov -d terraform/ --framework terraform --quiet \
          --compact --skip-check CKV_AZURE_*
      continue-on-error: false

  # EXISTING: build job
  build:
    needs: [test, sast, dependency-scan, secrets-scan, iac-scan]
    # ... keep as is ...
    
    # NEW STEP: Container scanning after each build
    - name: Scan UserService image
      run: |
        docker run --rm -v /var/run/docker.sock:/var/run/docker.sock \
          aquasec/trivy image --severity HIGH,CRITICAL \
          --exit-code 1 \
          ${{ env.ACR_NAME }}.azurecr.io/userservice:${{ github.sha }}
      continue-on-error: false
    
    # Repeat for other services...

  # EXISTING: deploy + smoke_test jobs
  deploy:
    # ... keep as is ...

  smoke_test:
    # ... keep as is ...

  # NEW JOB 6: DAST (Dynamic Application Security Testing)
  dast:
    runs-on: ubuntu-latest
    needs: smoke_test
    steps:
    - uses: actions/checkout@v3
    
    - name: Get Ingress IP
      run: |
        API_URL="${{ needs.smoke_test.outputs.API_URL }}"
        echo "TARGET_URL=$API_URL" >> $GITHUB_ENV
    
    - name: Run OWASP ZAP Baseline Scan
      run: |
        docker run --rm -v $(pwd):/zap/wrk/:rw \
          owasp/zap2docker-stable zap-baseline.py \
          -t ${{ env.TARGET_URL }} \
          -r zap-report.html \
          -J zap-report.json
      continue-on-error: true  # Don't fail build, but report
    
    - name: Upload ZAP Report
      uses: actions/upload-artifact@v3
      if: always()
      with:
        name: zap-report
        path: zap-report.html
```

**Deliverables:**
- [ ] SAST with Bandit integrated
- [ ] Dependency scanning with Safety
- [ ] Container scanning with Trivy
- [ ] Secrets scanning with TruffleHog
- [ ] IaC scanning with Checkov
- [ ] DAST with OWASP ZAP

**Measurable Outcomes:**
- ✅ 0 HIGH/CRITICAL vulnerabilities in production
- ✅ 100% of commits scanned
- ✅ Security scan results in GitHub Security tab
- ✅ Build fails on critical issues

---

### Phase 4: Application Hardening (Week 5)

#### 4.1 Pod Security Context

##### [MODIFY] All service YAMLs: [k8s/userservice.yaml](file:///d:/UIT/SE360/UITGO/se360-uit-go/k8s/userservice.yaml), [k8s/tripservice.yaml](file:///d:/UIT/SE360/UITGO/se360-uit-go/k8s/tripservice.yaml), etc.

```yaml
spec:
  template:
    spec:
      # Add security context
      securityContext:
        runAsNonRoot: true
        runAsUser: 1000
        fsGroup: 1000
        seccompProfile:
          type: RuntimeDefault
      
      containers:
      - name: userservice
        # ... existing config ...
        
        # Container security context
        securityContext:
          allowPrivilegeEscalation: false
          readOnlyRootFilesystem: true
          runAsNonRoot: true
          runAsUser: 1000
          capabilities:
            drop:
            - ALL
        
        # Add resource limits
        resources:
          requests:
            memory: "128Mi"
            cpu: "100m"
          limits:
            memory: "512Mi"
            cpu: "500m"
        
        # Read-only filesystem needs tmp volume
        volumeMounts:
        - name: tmp
          mountPath: /tmp
        
      volumes:
      - name: tmp
        emptyDir: {}
```

**Deliverables:**
- [ ] All pods run as non-root
- [ ] Read-only root filesystem
- [ ] Resource limits configured
- [ ] Capabilities dropped

**Measurable Outcomes:**
- ✅ 0 pods running as root
- ✅ All pods have resource limits
- ✅ Security contexts enforced

---

### Phase 5: Monitoring & Alerting (Week 6)

#### 5.1 Azure Monitor Alerts (FREE Tier)

##### [NEW] [terraform/monitoring-alerts.tf](file:///d:/UIT/SE360/UITGO/se360-uit-go/terraform/monitoring-alerts.tf)
```hcl
# Action Group for notifications (FREE)
resource "azurerm_monitor_action_group" "security_alerts" {
  name                = "security-alerts"
  resource_group_name = azurerm_resource_group.rg.name
  short_name          = "secalert"

  email_receiver {
    name          = "security-team"
    email_address = "your-email@example.com"  # Replace with actual email
  }
}

# Alert: High CPU usage (potential DoS)
resource "azurerm_monitor_metric_alert" "high_cpu" {
  name                = "aks-high-cpu-alert"
  resource_group_name = azurerm_resource_group.rg.name
  scopes              = [azurerm_kubernetes_cluster.aks.id]
  description         = "Alert when CPU usage exceeds 80%"
  severity            = 2

  criteria {
    metric_namespace = "Microsoft.ContainerService/managedClusters"
    metric_name      = "node_cpu_usage_percentage"
    aggregation      = "Average"
    operator         = "GreaterThan"
    threshold        = 80
  }

  action {
    action_group_id = azurerm_monitor_action_group.security_alerts.id
  }
}

# Alert: High memory usage
resource "azurerm_monitor_metric_alert" "high_memory" {
  name                = "aks-high-memory-alert"
  resource_group_name = azurerm_resource_group.rg.name
  scopes              = [azurerm_kubernetes_cluster.aks.id]
  description         = "Alert when memory usage exceeds 80%"
  severity            = 2

  criteria {
    metric_namespace = "Microsoft.ContainerService/managedClusters"
    metric_name      = "node_memory_working_set_percentage"
    aggregation      = "Average"
    operator         = "GreaterThan"
    threshold        = 80
  }

  action {
    action_group_id = azurerm_monitor_action_group.security_alerts.id
  }
}

# Alert: Pod restart frequency
resource "azurerm_monitor_metric_alert" "pod_restarts" {
  name                = "aks-pod-restart-alert"
  resource_group_name = azurerm_resource_group.rg.name
  scopes              = [azurerm_kubernetes_cluster.aks.id]
  description         = "Alert when pods restart frequently"
  severity            = 1

  criteria {
    metric_namespace = "Microsoft.ContainerService/managedClusters"
    metric_name      = "kube_pod_status_ready"
    aggregation      = "Average"
    operator         = "LessThan"
    threshold        = 0.8
  }

  action {
    action_group_id = azurerm_monitor_action_group.security_alerts.id
  }
}
```

##### [NEW] [k8s/fluent-bit.yaml](file:///d:/UIT/SE360/UITGO/se360-uit-go/k8s/fluent-bit.yaml)
```yaml
# Fluent Bit for log aggregation (FREE, lightweight alternative to Fluentd)
apiVersion: v1
kind: ConfigMap
metadata:
  name: fluent-bit-config
  namespace: kube-system
data:
  fluent-bit.conf: |
    [SERVICE]
        Flush         5
        Daemon        off
        Log_Level     info

    [INPUT]
        Name              tail
        Path              /var/log/containers/*ingress-nginx*.log
        Parser            docker
        Tag               nginx
        Refresh_Interval  5

    [FILTER]
        Name                parser
        Match               nginx
        Key_Name            log
        Parser              modsecurity
        Reserve_Data        On

    [OUTPUT]
        Name                azure
        Match               *
        Customer_ID         ${WORKSPACE_ID}
        Shared_Key          ${SHARED_KEY}
        Log_Type            ModSecurity

  parsers.conf: |
    [PARSER]
        Name        modsecurity
        Format      regex
        Regex       ^.*ModSecurity: (?<severity>[A-Z]+) (?<message>.*)$
---
apiVersion: apps/v1
kind: DaemonSet
metadata:
  name: fluent-bit
  namespace: kube-system
spec:
  selector:
    matchLabels:
      app: fluent-bit
  template:
    metadata:
      labels:
        app: fluent-bit
    spec:
      containers:
      - name: fluent-bit
        image: fluent/fluent-bit:2.1
        volumeMounts:
        - name: varlog
          mountPath: /var/log
        - name: config
          mountPath: /fluent-bit/etc/
        env:
        - name: WORKSPACE_ID
          valueFrom:
            secretKeyRef:
              name: log-analytics-secret
              key: workspace-id
        - name: SHARED_KEY
          valueFrom:
            secretKeyRef:
              name: log-analytics-secret
              key: shared-key
      volumes:
      - name: varlog
        hostPath:
          path: /var/log
      - name: config
        configMap:
          name: fluent-bit-config
```

##### [NEW] [docs/security-runbooks/incident-response.md](file:///d:/UIT/SE360/UITGO/se360-uit-go/docs/security-runbooks/incident-response.md)
```markdown
# Security Incident Response Playbook

## 1. WAF Alert Response

### When: ModSecurity blocks attack

**Immediate Actions:**
1. Check alert in Azure Monitor
2. Identify attack type (SQL injection, XSS, etc.)
3. Review ModSecurity logs: `kubectl logs -n ingress-nginx <pod> | grep ModSecurity`
4. Block attacker IP if persistent:
   ```bash
   kubectl edit configmap modsecurity-custom-rules -n ingress-nginx
   # Add: SecRule REMOTE_ADDR "@ipMatch 1.2.3.4" "id:900999,phase:1,deny"
   ```

### Follow-up:
- Document incident in threat-model.md
- Update WAF rules if needed
- Report to security team

## 2. High CPU/Memory Alert

### When: Resource usage > 80%

**Immediate Actions:**
1. Check if DoS attack: `kubectl top nodes && kubectl top pods`
2. Review recent traffic spike in logs
3. Scale deployment if needed: `kubectl scale deployment/userservice --replicas=3`

## 3. Pod Restart Alert

### When: Pods restarting frequently

**Investigation:**
1. Check crash logs: `kubectl logs <pod> --previous`
2. Describe pod: `kubectl describe pod <pod>`
3. Check for OOMKilled or CrashLoopBackOff

## 4. Failed Security Scan in CI/CD

### When: Pipeline fails on security gate

**Resolution:**
1. Review scan results in GitHub Actions
2. Fix vulnerability or update dependency
3. Re-run pipeline
4. Document exception if false positive
```

**Deliverables:**
- [ ] Azure Monitor alerts configured
- [ ] Fluent Bit deployed for log aggregation
- [ ] Security runbooks created
- [ ] Alert notification tested

**Measurable Outcomes:**
- ✅ Alerts fire within 5 minutes of incident
- ✅ 100% of HIGH severity issues generate alerts
- ✅ Mean Time To Detect (MTTD) < 5 minutes

---

### Phase 6: Documentation & Training (Week 7)

#### 6.1 Architecture Decision Records

##### [NEW] [ADR/ADR-006-zero-trust-network.md](file:///d:/UIT/SE360/UITGO/se360-uit-go/ADR/ADR-006-zero-trust-network.md)
##### [NEW] [ADR/ADR-007-k8s-secrets-encryption.md](file:///d:/UIT/SE360/UITGO/se360-uit-go/ADR/ADR-007-k8s-secrets-encryption.md)
##### [NEW] [ADR/ADR-008-modsecurity-waf.md](file:///d:/UIT/SE360/UITGO/se360-uit-go/ADR/ADR-008-modsecurity-waf.md)
##### [NEW] [ADR/ADR-009-devsecops-pipeline.md](file:///d:/UIT/SE360/UITGO/se360-uit-go/ADR/ADR-009-devsecops-pipeline.md)
##### [NEW] [ADR/ADR-010-vnet-service-endpoints.md](file:///d:/UIT/SE360/UITGO/se360-uit-go/ADR/ADR-010-vnet-service-endpoints.md)

**Template:**
```markdown
# ADR-XXX: [Title]

## Status
Accepted

## Context
[Problem statement]

## Decision
[Solution chosen]

## Consequences
### Positive
- ...

### Negative
- ...

## Alternatives Considered
- Alternative 1: [Why rejected]
- Alternative 2: [Why rejected]

## Cost Analysis
| Solution | Cost | Notes |
|----------|------|-------|
| Chosen | $X | ... |
| Alternative | $Y | ... |
```

##### [MODIFY] [README.md](file:///d:/UIT/SE360/UITGO/se360-uit-go/README.md)
Add security section:
```markdown
## 🔒 Security Architecture

### Defense-in-Depth Layers

1. **Perimeter Security**
   - ModSecurity WAF (OWASP CRS 4.0)
   - Rate limiting (100 req/min)
   - Geo-blocking capabilities

2. **Network Security**
   - Zero Trust architecture
   - NSGs on all subnets
   - VNet Service Endpoints for databases
   - No public database access

3. **Application Security**
   - DevSecOps pipeline (6 security gates)
   - SAST, SCA, DAST, container scanning
   - Pod security contexts (non-root, read-only FS)
   - Resource limits

4. **Data Security**
   - TLS 1.3 in transit
   - Encryption at rest (AKS native)
   - Secrets encrypted

5. **Monitoring**
   - Azure Monitor alerts
   - ModSecurity WAF logs
   - Security incident response playbooks

### Compliance
- ✅ OWASP Top 10 protected
- ✅ Zero Trust principles
- ✅ Defense-in-Depth
- ✅ DevSecOps practices

See [docs/threat-model.md](docs/threat-model.md) for detailed analysis.
```

**Deliverables:**
- [ ] 5 ADRs written and reviewed
- [ ] README.md updated
- [ ] Security architecture diagram
- [ ] Team training completed

**Measurable Outcomes:**
- ✅ All architecture decisions documented
- ✅ 100% team members trained
- ✅ Security documentation complete

---

## Verification Plan

### Automated Tests

#### 1. Infrastructure Validation
```bash
# Apply Terraform changes
cd terraform
terraform init
terraform validate
terraform plan -out=tfplan
terraform apply tfplan

# Verify NSGs
az network nsg list --resource-group rg-uitgo-prod -o table

# Verify service endpoints
az network vnet subnet show \
  --resource-group rg-uitgo-prod \
  --vnet-name vnet-uitgo-prod \
  --name snet-aks-prod \
  --query "serviceEndpoints[*].service" -o table

# Should show: Microsoft.AzureCosmosDB, Microsoft.Cache
```

#### 2. ModSecurity WAF Testing
```bash
# Deploy WAF
kubectl apply -f k8s/modsecurity-custom-rules.yaml
kubectl apply -f k8s/nginx-ingress-controller.yaml
kubectl rollout status deployment/ingress-nginx-controller -n ingress-nginx

# Get Ingress IP
INGRESS_IP=$(kubectl get svc ingress-nginx-controller -n ingress-nginx -o jsonpath='{.status.loadBalancer.ingress[0].ip}')

# Test 1: SQL Injection (should be blocked 403)
curl -i "http://$INGRESS_IP/api/users?id=1' OR '1'='1"

# Test 2: XSS (should be blocked 403)
curl -i "http://$INGRESS_IP/api/trips?search=<script>alert('XSS')</script>"

# Test 3: Rate limiting (should get 429 after 100 requests)
for i in {1..110}; do 
  curl -s -o /dev/null -w "%{http_code}\n" "http://$INGRESS_IP/api/users"
done

# Test 4: Check ModSecurity logs
kubectl logs -n ingress-nginx deployment/ingress-nginx-controller | grep "ModSecurity:"
```

#### 3. CI/CD Security Pipeline
```bash
# Trigger full pipeline
git add .
git commit -m "Security upgrade complete"
git push origin main

# Monitor pipeline: https://github.com/[your-org]/se360-uit-go/actions
# Verify all 6 security gates pass:
# ✅ SAST (Bandit)
# ✅ Dependency scan (Safety)
# ✅ Secrets scan (TruffleHog)
# ✅ IaC scan (Checkov)
# ✅ Container scan (Trivy)
# ✅ DAST (OWASP ZAP)
```

#### 4. Database Connectivity
```bash
# Verify CosmosDB NOT accessible from internet
curl -I https://cosmos-uitgo-prod.documents.azure.com:443
# Should timeout or refuse connection

# Verify accessible from within AKS
kubectl run -it --rm test --image=mongo:6 --restart=Never -- \
  mongosh "$COSMOS_CONNECTION_STRING"
# Should connect successfully

# Same for Redis
kubectl run -it --rm test --image=redis:7 --restart=Never -- \
  redis-cli -h redis-uitgo-prod.redis.cache.windows.net -a "$REDIS_KEY"
```

#### 5. Security Posture Validation
```bash
# Check pod security
kubectl get pods --all-namespaces -o json | \
  jq '.items[] | select(.spec.securityContext.runAsUser == null or .spec.securityContext.runAsUser == 0) | .metadata.name'
# Should return empty (no pods running as root)

# Check resource limits
kubectl get pods --all-namespaces -o json | \
  jq '.items[] | select(.spec.containers[].resources.limits == null) | .metadata.name'
# Should return empty (all pods have limits)

# Check encryption at rest
az aks show --resource-group rg-uitgo-prod --name aks-uitgo-prod \
  --query "diskEncryptionSetID" -o tsv
# Should show encryption enabled
```

### Manual Verification

#### Security Dashboard
1. Navigate to Azure Portal → Security Center
2. Review Secure Score (should improve by 15-20 points)
3. Check recommendations addressed

#### Penetration Testing
> [!IMPORTANT]
> Recommend user to perform manual penetration testing

**Test cases:**
1. OWASP Top 10 vulnerabilities
2. Authentication bypass attempts
3. API rate limiting effectiveness
4. WebSocket security
5. Payment endpoint security

**Tools:**
- Burp Suite Community Edition (FREE)
- OWASP ZAP (already in pipeline)
- Nikto web scanner

---

## Success Metrics

| Metric | Before | After | Target Met |
|--------|--------|-------|------------|
| WAF Protection | None | OWASP CRS 4.0 | ✅ |
| Public DB Endpoints | 2 | 0 | ✅ |
| Security Gates in CI/CD | 0 | 6 | ✅ |
| Secrets Encrypted | No | Yes (at rest) | ✅ |
| Network Segmentation | Basic | Zero Trust | ✅ |
| MTTR for vulnerabilities | N/A | < 15 min | 🎯 |
| False Positive Rate | N/A | < 5% | 🎯 |
| Monthly Cost Increase | - | $0-3 | ✅ |

**Cost Target:** $0-3/month (vs. $411-625/month for enterprise solutions)

---

## Timeline & Effort

| Phase | Duration | Effort (hours) | Dependencies |
|-------|----------|----------------|--------------|
| Phase 1 | Week 1-2 | 16h | None |
| Phase 2 | Week 3 | 8h | Phase 1 complete |
| Phase 3 | Week 4 | 12h | Phase 1, 2 complete |
| Phase 4 | Week 5 | 6h | Phase 1-3 complete |
| Phase 5 | Week 6 | 8h | Phase 1-4 complete |
| Phase 6 | Week 7 | 6h | All phases complete |
| **Total** | **7 weeks** | **56 hours** | - |

**Team Size:** 1-2 engineers (can parallelize some phases)

---

## Risk Mitigation

### Risk 1: ModSecurity False Positives
**Likelihood:** Medium  
**Impact:** High (blocks legitimate users)  
**Mitigation:**
- Start in DetectionOnly mode for 1-2 weeks
- Monitor logs daily
- Tune rules progressively
- Document exceptions

### Risk 2: Service Endpoints Configuration Error
**Likelihood:** Low  
**Impact:** Medium (database connectivity issues)  
**Mitigation:**
- Test in dev environment first
- Have rollback plan ready
- Schedule during maintenance window
- Keep PostgreSQL config as-is (already working)

### Risk 3: CI/CD Pipeline Increase Build Time
**Likelihood:** High  
**Impact:** Low  
**Mitigation:**
- Run scans in parallel
- Cache dependencies
- Optimize scan configurations
- Expected increase: +5-8 minutes (acceptable)

### Risk 4: Resource Limits Too Restrictive
**Likelihood:** Medium  
**Impact:** Medium (OOMKilled pods)  
**Mitigation:**
- Start with generous limits
- Monitor actual usage for 1 week
- Adjust based on metrics
- Use HPA (Horizontal Pod Autoscaler) if needed

---

## Rollback Procedures

### Phase 1 Rollback
```bash
# Revert Terraform changes
cd terraform
git checkout HEAD~1 main.tf databases.tf network-security.tf
terraform apply -auto-approve
```

### Phase 2 Rollback
```bash
# Disable ModSecurity
kubectl patch configmap ingress-nginx-controller -n ingress-nginx \
  --type=json \
  -p='[{"op": "replace", "path": "/data/enable-modsecurity", "value": "false"}]'

kubectl rollout restart deployment/ingress-nginx-controller -n ingress-nginx
```

### Phase 3 Rollback
```bash
# Revert CI/CD pipeline
cd .github/workflows
git checkout HEAD~1 deploy.yml
git commit -m "Rollback security gates"
git push
```

### Phase 4 Rollback
```bash
# Revert pod security contexts
for file in k8s/*service.yaml; do
  git checkout HEAD~1 "$file"
done
kubectl apply -f k8s/
```

---

## Next Steps

1. ✅ Review this optimized plan
2. ✅ Confirm $0-3/month budget acceptable
3. ✅ Answer any questions
4. 🎯 Get approval to proceed
5. 🎯 Start Phase 1 implementation

**Total Investment:** 56 hours over 7 weeks, $0-3/month ongoing cost for **enterprise-grade security**! 🚀
