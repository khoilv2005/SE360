# Security Runbooks - UIT-Go

Incident response procedures for common security events.

## 📋 Runbook Index

1. [High CPU Alert](#runbook-1-high-cpu-alert)
2. [Pod Restart Loop](#runbook-2-pod-restart-loop)
3. [Service Mesh mTLS Failure Spike](#runbook-3-service-mesh-mtls-failure-spike)
4. [Database Connection Failures](#runbook-4-database-connection-failures)
5. [Suspicious Login Activity](#runbook-5-suspicious-login-activity)
6. [Container Image Vulnerability](#runbook-6-container-image-vulnerability)

---

## Runbook 1: High CPU Alert

**Trigger:** AKS CPU usage > 80%  
**Severity:** High  
**Alert:** `aks-high-cpu-alert`

### Investigation Steps

```bash
# 1. Check which pods are consuming CPU
kubectl top pods --all-namespaces --sort-by=cpu

# 2. Check node CPU usage
kubectl top nodes

# 3. Describe high-CPU pod
kubectl describe pod <POD_NAME> -n <NAMESPACE>

# 4. Check pod logs
kubectl logs <POD_NAME> -n <NAMESPACE> --tail=100
```

### Common Causes
- **DoS Attack:** Unusual traffic spike → Check ModSecurity logs
- **Memory Leak:** Continuous CPU increase → Check memory usage
- **Inefficient Code:** Specific endpoint causing spike → Review app logs

### Remediation

**If DoS Attack:**
```bash
# Check ModSecurity blocks
kubectl logs -n ingress-nginx deployment/ingress-nginx-controller | grep ModSecurity | grep blocked

# Identify attacking IPs
kubectl logs -n ingress-nginx deployment/ingress-nginx-controller | grep "429\|403"

# Add IP block rule if needed (emergency)
kubectl edit cm  -n ingress-nginx
# Add: SecRule REMOTE_ADDR "@ipMatch 1.2.3.4" "id:900999,phase:1,deny,status:403"
```

**If Application Issue:**
```bash
# Scale up replicas temporarily
kubectl scale deployment/<SERVICE> --replicas=3

# Restart problematic pod
kubectl rollout restart deployment/<SERVICE>

# Rollback if recent deployment
kubectl rollout undo deployment/<SERVICE>
```

### Escalation
If CPU remains >80% for >15 minutes: Contact infrastructure team

---

## Runbook 2: Pod Restart Loop

**Trigger:** Pod status < 80% ready  
**Severity:** Critical  
**Alert:** `aks-pod-restart-alert`

### Investigation Steps

```bash
# 1. Identify failing pods
kubectl get pods --all-namespaces | grep -v Running

# 2. Check restart count
kubectl get pods -o json | jq '.items[] | select(.status.containerStatuses[].restartCount > 3) | .metadata.name'

# 3. Get pod events
kubectl describe pod <POD_NAME>

# 4. Check logs (including previous container)
kubectl logs <POD_NAME> --previous
```

### Common Causes
- **OOM Kill:** Memory limit too low
- **Liveness Probe Failure:** Health check failing
- **Security Context Issue:** Non-root user can't access resources
- **Database Connection:** Can't connect to DB

### Remediation

**For OOM:**
```bash
# Increase memory limit
kubectl edit deployment/<SERVICE>
# Change:
#   limits:
#     memory: "1Gi"  # from 512Mi

kubectl rollout restart deployment/<SERVICE>
```

**For Security Context:**
```bash
# Check filesystem permissions
kubectl exec <POD_NAME> -- ls -la /

# Fix ownership if needed (in Dockerfile next build)
# For now, add writable volume
kubectl edit deployment/<SERVICE>
# Add volumeMount for required path
```

**For Database Connection:**
```bash
# Test database connectivity
kubectl run -it --rm debug --image=busybox --restart=Never -- sh
# Inside: nc -zv <DB_HOST> <DB_PORT>

# Check secrets
kubectl get secret uitgo-secrets -o yaml

# Verify Service Endpoints
az network vnet subnet show --resource-group rg-uitgo-prod --vnet-name vnet-uitgo-prod --name snet-aks-prod --query "serviceEndpoints"
```

### Escalation
If >5 pods in CrashLoopBackOff: Priority 1 incident

---

## Runbook 3: Service Mesh mTLS Failure Spike

**Trigger:** >10 mTLS connection failures in 5 minutes
**Severity:** High
**Alert:** `security-events-alert`

### Investigation Steps

```bash
# 1. Check Linkerd control plane status
linkerd check

# 2. View recent connection failures
kubectl logs -n linkerd deployment/linkerd-controller | grep -i error | tail -50

# 3. Check data plane proxy status
kubectl get pods -n linkerd

# 4. View service mesh edges
linkerd edges deploy --all-namespaces

# 5. Check certificate status
kubectl get certificates -n linkerd

# 6. Check specific service connectivity
kubectl port-forward -n linkerd service/linkerd-controller 8080:8080 &
curl http://localhost:8080/metrics | grep failure
```

### Attack Types

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

### Remediation

**If Legitimate Traffic (False Positive):**
```bash
# Identify rule causing block
# Add exception in ingress.yaml
kubectl edit ingress uitgo-ingress
# Add annotation:
#   nginx.ingress.kubernetes.io/ |
#     SecRuleRemoveById 942100
```

**If Attack:**
```bash
# Already blocked by WAF - no action needed
# Monitor for pattern changes

# If persistent attack from single IP
# Add permanent block
kubectl edit cm  -n ingress-nginx
# Add: SecRule REMOTE_ADDR "@ipMatch <ATTACKER_IP>" "id:900998,phase:1,deny,status:403"
kubectl rollout restart deployment/ingress-nginx-controller -n ingress-nginx
```

### Escalation
If attack continues for >30 minutes: Document and report

---

## Runbook 4: Database Connection Failures

**Trigger:** Application logs show DB errors  
**Severity:** Critical

### Investigation Steps

```bash
# 1. Test PostgreSQL connectivity
kubectl run -it --rm psql-test --image=postgres:15 --restart=Never -- psql -h <POSTGRES_HOST> -U <USER> -d mydb

# 2. Test CosmosDB connectivity
kubectl run -it --rm mongo-test --image=mongo:6 --restart=Never -- mongosh "<CONNECTION_STRING>"

# 3. Test Redis connectivity
kubectl run -it --rm redis-test --image=redis:7 --restart=Never -- redis-cli -h <REDIS_HOST> ping

# 4. Check Service Endpoints
az network vnet subnet show --resource-group rg-uitgo-prod --vnet-name vnet-uitgo-prod --name snet-aks-prod --query "serviceEndpoints[].service"
```

### Common Causes
- **NSG Rules:** Blocking database traffic
- **Service Endpoint Issue:** Not configured properly
- **Secret Rotation:** Old connection string
- **Database Down:** Azure issue

### Remediation

**Check NSG:**
```bash
az network nsg rule list --resource-group rg-uitgo-prod --nsg-name nsg-aks-prod --output table

# Verify database outbound allowed
# Should see: AllowDatabaseOutbound
```

**Check Secrets:**
```bash
# Get current secret
kubectl get secret uitgo-secrets -o jsonpath='{.data.COSMOS_CONNECTION_STRING}' | base64 -d

# Compare with Azure
az cosmosdb keys list --name cosmos-uitgo-prod --resource-group rg-uitgo-prod --type connection-strings
```

**Regenerate Connection String:**
```bash
# Get new connection string
COSMOS_CS=$(az cosmosdb keys list --name cosmos-uitgo-prod --resource-group rg-uitgo-prod --type connection-strings --query "connectionStrings[0].connectionString" -o tsv)

# Update secret
kubectl create secret generic uitgo-secrets --from-literal=COSMOS_CONNECTION_STRING="$COSMOS_CS" --dry-run=client -o yaml | kubectl apply -f -

# Restart affected services
kubectl rollout restart deployment/tripservice
kubectl rollout restart deployment/driverservice
kubectl rollout restart deployment/paymentservice
```

### Escalation
If database unreachable >10 minutes: Azure support ticket

---

## Runbook 5: Suspicious Login Activity

**Trigger:** >5 failed logins from same IP  
**Severity:** Medium  
**Alert:** ModSecurity rule 900106

### Investigation Steps

```bash
# 1. Check failed login attempts
kubectl logs deployment/userservice | grep "401\|failed\|unauthorized"

# 2. Identify IP addresses
kubectl logs -n ingress-nginx deployment/ingress-nginx-controller | grep "/api/users/login" | grep "429\|403"

# 3. Check if IP is known attacker
# Use threat intelligence database or check https://www.abuseipdb.com
```

### Remediation

**If Brute Force Attack:**
```bash
# Already rate-limited by ModSecurity (5 attempts/min)
# Blocked automatically after threshold

# If attack persists, add IP block
kubectl edit cm  -n ingress-nginx
# Add to custom rules
kubectl rollout restart deployment/ingress-nginx-controller -n ingress-nginx
```

**If Credential Stuffing:**
```bash
# Review user accounts for compromised passwords
kubectl exec deployment/userservice -- python -c "
from app import check_compromised_passwords
check_compromised_passwords()
"

# Force password reset for affected users
```

### Escalation
If >100 failed logins/hour: Security team review

---

## Runbook 6: Container Image Vulnerability

**Trigger:** Trivy scan finds HIGH/CRITICAL CVE  
**Severity:** High (varies by CVE)  
**Alert:** GitHub Actions workflow failure

### Investigation Steps

```bash
# 1. Download Trivy report from GitHub Artifacts
gh run download <RUN_ID>
cat trivy-userservice.json | jq '.Results[].Vulnerabilities[] | select(.Severity=="CRITICAL")'

# 2. Check if exploit available
# Review CVE details at https://cve.mitre.org

# 3. Check if fix available
cat trivy-userservice.json | jq '.Results[].Vulnerabilities[] | select(.FixedVersion != "")'
```

### Remediation

**If Fix Available:**
```bash
# Update dependency in requirements.txt
# For userservice example:
echo "flask==2.3.5" >> UserService/requirements.txt  # Fixed version

# Commit and push
git add UserService/requirements.txt
git commit -m "fix: Update Flask to patch CVE-XXXX-YYYY"
git push origin main

# Pipeline will rebuild and rescan
```

**If No Fix Available:**
```bash
# 1. Assess risk
# - Is service exposed?
# - Is vulnerable code path used?
# - What's the CVSS score?

# 2. If low risk, accept temporarily
# Add to Trivy ignore list
echo "CVE-XXXX-YYYY" >> .trivyignore

# 3. Document in ADR
# Create docs/adrs/ADR-011-accepted-cve-XXXX.md

# 4. Set reminder to recheck in 30 days
```

**If Base Image Issue:**
```bash
# Update base image in Dockerfile
# FROM python:3.11-slim  →  FROM python:3.11.8-slim

docker build -t test .
docker run --rm test python --version  # Verify
```

### Escalation
If CRITICAL CVE with known exploit: Immediate hotfix required

---

## Emergency Contacts

| Role | Contact | Purpose |
|------|---------|---------|
| Dev Team Lead | your-email@example.com | Application issues |
| Security Team | security@example.com | Security incidents |
| Azure Support | Azure Portal | Infrastructure issues |
| On-Call Rotation | PagerDuty/Slack | After-hours emergencies |

---

## Monitoring Dashboard Links

- **Azure Monitor:** https://portal.azure.com → Monitor → Alerts
- **Log Analytics:** https://portal.azure.com → Log Analytics workspaces
- **GitHub Actions:** https://github.com/org/repo/actions
- **AKS Cluster:** https://portal.azure.com → Kubernetes services

---

## Post-Incident

After resolving any security incident:

1. ✅ Document incident in incident log
2. ✅ Update runbook if procedures changed
3. ✅ Schedule post-mortem within 48 hours
4. ✅ Implement preventive measures
5. ✅ Update monitoring/alerting as needed
