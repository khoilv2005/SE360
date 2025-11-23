# ADR-004: Open Source Security Tools over Commercial Solutions

**Status:** Accepted  
**Date:** 2025-11-23  
**Decision Makers:** DevOps Team, Security Team

## Context

UIT-Go requires comprehensive security scanning in CI/CD pipeline covering:
- Static Application Security Testing (SAST)
- Dependency vulnerability scanning
- Secrets detection
- Infrastructure as Code (IaC) scanning
- Container image scanning
- Dynamic Application Security Testing (DAST)

Two approaches evaluated:
1. **Commercial security platforms** (Snyk, SonarQube, etc.)
2. **Open Source Security (OSS) tools**

## Decision

We will use **Open Source Security tools** for all CI/CD security scanning.

## Tool Selection

| Category | Commercial Option | Monthly Cost | OSS Tool | Cost |
|----------|-------------------|--------------|----------|------|
| SAST | SonarQube/Veracode | $50-200 | **Bandit** | $0 |
| Dependency | Snyk/WhiteSource | $30-100 | **Safety** | $0 |
| Secrets | GitGuardian | $20-50 | **TruffleHog** | $0 |
| IaC | Prisma Cloud | $30-100 | **Checkov** | $0 |
| Container | Aqua/Twistlock | $50-200 | **Trivy** | $0 |
| DAST | Burp Suite Pro | $50-150 | **OWASP ZAP** | $0 |
| **TOTAL** | - | **$230-800** | - | **$0** |

**Annual Savings: $2,760 - $9,600**

## Rationale

### OSS Tool Capabilities

All selected OSS tools are:
- ✅ **Production-ready:** Used by major organizations
- ✅ **Actively maintained:** Regular updates and CVE database refreshes
- ✅ **Well-documented:** Extensive community documentation
- ✅ **GitHub Actions native:** Easy CI/CD integration
- ✅ **No API tokens required:** Fully free, no rate limits

### Tool-Specific Justification

**Bandit (SAST):**
- Python-specific security linter
- Maintained by PyCQA organization
- 100+ security checks
- Used by: OpenStack, NASA, Mozilla

**Safety (Dependency):**
- PyUp.io vulnerability database (50,000+ CVEs)
- Updated daily
- Free for open source
- Used by: Django, Flask projects

**TruffleHog (Secrets):**
- Scans entire git history
- 700+ credential types detected
- High accuracy, low false positives
- Used by: GitHub, Microsoft, AWS

**Checkov (IaC):**
- Bridgecrew (acquired by Palo Alto Networks)
- 1000+ built-in policies
- Terraform + Kubernetes support
- CIS Benchmark compliance

**Trivy (Container):**
- Aqua Security (company offers commercial version)
- FREE scanner with same engine
- OS + app dependency scanning
- Updated CVE database

**OWASP ZAP (DAST):**
- OWASP flagship project
- Industry standard for DAST
- Active + passive scanning
- Used by: Mozilla, eBay, Vodafone

## Commercial vs OSS Comparison

### Commercial Advantages
- ✅ Unified dashboard
- ✅ Customer support
- ✅ Prioritized findings
- ✅ Compliance reporting

### OSS Advantages  
- ✅ **Zero cost**
- ✅ No vendor lock-in
- ✅ Full control and customization
- ✅ No data sent to third parties
- ✅ Can run offline
- ✅ No licensing restrictions

### Why OSS is Sufficient for UIT-Go

1. **Small team:** 5-10 developers don't need unified dashboard
2. **Budget constraints:** Educational/startup project
3. **Technical capability:** Team can integrate multiple tools
4. **GitHub Actions:** Built-in artifact storage for reports
5. **No compliance requirements:** No SOC2/ISO needed yet

## Implementation

### CI/CD Integration

All tools run in GitHub Actions workflow (`.github/workflows/deploy.yml`):

```yaml
# Parallel execution after unit tests
jobs:
  sast:           # Bandit
  dependency:     # Safety  
  secrets:        # TruffleHog
  iac:            # Checkov
  build:
    needs: [sast, dependency, secrets, iac]  # Gates
  container:      # Trivy (after build)
  dast:           # OWASP ZAP (after deploy)
```

### Quality Gates

Build fails if:
- ✅ HIGH/CRITICAL code vulnerabilities (Bandit)
- ✅ Known CVEs in dependencies (Safety)
- ✅ Secrets detected in history (TruffleHog)
- ✅ IaC policy violations (Checkov)
- ✅ HIGH/CRITICAL container CVEs (Trivy)
- ⚠️ DAST findings (report only)

## Consequences

### Positive
- **Cost savings:** $230-800/month
- **Flexibility:** Can swap tools easily
- **Privacy:** No data sent to vendors
- **Learning:** Team gains security tool expertise

### Negative
- **No unified dashboard:** Need to check multiple reports
- **Manual correlation:** Can't link findings across tools
- **Self-support:** No vendor support channel
- **Tool updates:** Team responsible for staying current

### Neutral
- **Security coverage:** Equivalent to commercial solutions
- **False positives:** Similar rates to commercial tools

## Mitigation Strategies

For negative consequences:

1. **No dashboard:** 
   - GitHub Actions artifacts central location
   - Consider Grafana for metrics (future)

2. **Manual correlation:**
   - Document common patterns
   - Create scripts for report parsing

3. **Self-support:**
   - Use community forums (Stack Overflow, GitHub Issues)
   - Maintain runbook for each tool

4. **Tool updates:**
   - Quarterly review of tool versions
   - Subscribe to security mailing lists

## Success Criteria

OSS approach is successful if:
- ✅ Zero HIGH/CRITICAL vulnerabilities in production
- ✅ <5% false positive rate
- ✅ <10min added to pipeline time
- ✅ Team comfortable with all tools (achieved)

## Migration Path to Commercial

If we outgrow OSS tools, upgrade when:
- Team size >20 developers
- Compliance requirements (SOC2, ISO)
- Need for unified reporting
- Security team established

Candidate commercial platforms:
- Snyk (developer-friendly)
- Sonar Cloud (SAST focus)
- GitHub Advanced Security (native integration)

## Review Date

This decision will be reviewed **quarterly** or when:
- Team size doubles
- Compliance requirements emerge
- False positive rate >10%
- Tool maintenance burden becomes significant
