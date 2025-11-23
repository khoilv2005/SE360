# ADR-001: ModSecurity WAF over Azure Application Gateway

**Status:** Accepted  
**Date:** 2025-11-23  
**Decision Makers:** Security Team, DevOps Team

## Context

UIT-Go requires a Web Application Firewall (WAF) to protect against OWASP Top 10 vulnerabilities including SQL injection, XSS, and other web attacks. Two primary options were evaluated:

1. **Azure Application Gateway with WAF tier**
2. **ModSecurity with NGINX Ingress Controller**

## Decision

We will use **ModSecurity WAF** integrated with our existing NGINX Ingress Controller.

## Rationale

### Cost Analysis
| Solution | Monthly Cost | Annual Cost |
|----------|--------------|-------------|
| Azure Application Gateway WAF | $275-455 | $3,300-5,460 |
| ModSecurity (Open Source) | $0 | $0 |

**Savings: $3,300-5,460/year**

### Technical Comparison

**Azure Application Gateway WAF:**
- ✅ Managed service (less maintenance)
- ✅ Azure-native integration
- ✅ Built-in DDoS protection
- ❌ Expensive ($275-455/month)
- ❌ Vendor lock-in
- ❌ Less customization flexibility

**ModSecurity WAF:**
- ✅ FREE and open-source
- ✅ OWASP CRS 4.0 included
- ✅ Highly customizable rules
- ✅ Industry-standard (used by major platforms)
- ✅ No vendor lock-in
- ❌ Requires manual configuration
- ❌ Self-managed (we handle updates)

### Security Capabilities

Both solutions provide equivalent security for our use case:
- OWASP Top 10 protection ✅
- Rate limiting ✅
- Custom rules ✅
- Logging and monitoring ✅

### Implementation Effort

ModSecurity integration required:
- ~4 hours configuration
- Custom rules definition
- Testing and tuning (1-2 weeks)

This one-time effort saves $3,300-5,460 annually.

## Consequences

### Positive
- **Cost savings:** $275-455/month saved
- **Flexibility:** Full control over WAF rules
- **Portability:** Can move to any Kubernetes cluster
- **Community support:** Large ModSecurity community

### Negative
- **Maintenance overhead:** We manage updates and tuning
- **Initial learning curve:** Team needs to learn ModSecurity
- **Tuning required:** 1-2 weeks to eliminate false positives

### Neutral
- **Features:** Equivalent security capabilities to App Gateway WAF
- **Performance:** Minimal latency impact (<5ms per request)

## Mitigation Strategies

To address the negative consequences:

1. **Maintenance:** Documented in `docs/security-runbooks.md`
2. **Learning curve:** Team training on ModSecurity (completed)
3. **Tuning:** DetectionOnly mode first, then blocking mode after 2 weeks
4. **Updates:** Schedule quarterly OWASP CRS updates

## Compliance

- ✅ Meets OWASP Top 10 requirements
- ✅ Supports Zero Trust principle
- ✅ Defense-in-Depth layer satisfied
- ✅ Audit logging enabled

## Implementation

- Configuration: `k8s/nginx-ingress-controller.yaml`
- Custom rules: `k8s/modsecurity-custom-rules.yaml`
- Testing: `scripts/test-modsecurity-waf.sh`

## Review Date

This decision will be reviewed in **6 months (May 2026)** to assess:
- Maintenance burden vs. cost savings
- False positive rate
- Team satisfaction
- Any new Azure WAF pricing tiers
