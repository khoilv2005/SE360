# Architecture Decision Records (ADRs)

This directory contains Architecture Decision Records documenting significant architectural and security decisions made for the UIT-Go platform.

## ADR Index

| ADR | Title | Status | Date |
|-----|-------|--------|------|
| [ADR-001](ADR-001-modsecurity-over-app-gateway.md) | ModSecurity WAF over Azure Application Gateway | Accepted | 2025-11-23 |
| [ADR-002](ADR-002-vnet-service-endpoints.md) | VNet Service Endpoints over Private Endpoints | Accepted | 2025-11-23 |
| [ADR-003](ADR-003-k8s-native-secrets.md) | Kubernetes Native Secrets over Azure Key Vault | Accepted | 2025-11-23 |
| [ADR-004](ADR-004-oss-security-tools.md) | OSS Security Tools over Commercial Solutions | Accepted | 2025-11-23 |
| [ADR-005](ADR-005-fluent-bit-over-fluentd.md) | Fluent Bit over Fluentd for Log Aggregation | Accepted | 2025-11-23 |
| [ADR-006](ADR-006-azure-monitor-free-tier.md) | Azure Monitor FREE Tier for Alerting | Accepted | 2025-11-23 |
| [ADR-007](ADR-007-zero-trust-implementation.md) | Zero Trust Architecture Implementation | Accepted | 2025-11-23 |

## ADR Process

### When to Create an ADR
- Choosing between multiple viable technical approaches
- Making decisions with significant long-term impact
- Deciding on tools, frameworks, or architectural patterns
- Security-related architectural decisions

### ADR Template
See [template.md](template.md) for the standard format.

### ADR Statuses
- **Proposed** - Under consideration
- **Accepted** - Decision made and implemented
- **Deprecated** - No longer recommended
- **Superseded** - Replaced by newer ADR
