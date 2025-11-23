# ADR-002: VNet Service Endpoints over Private Endpoints

**Status:** Accepted  
**Date:** 2025-11-23  
**Decision Makers:** Infrastructure Team, Security Team

## Context

UIT-Go databases (CosmosDB, Redis, PostgreSQL) need secure, private connectivity from AKS cluster. Azure offers two solutions:

1. **Private Endpoints** ($15/month + data processing)
2. **VNet Service Endpoints** (FREE)

## Decision

We will use **VNet Service Endpoints** for database connectivity.

## Rationale

### Cost Comparison
| Solution | Setup Cost | Monthly Cost | Annual Cost |
|----------|------------|--------------|-------------|
| Private Endpoints (3 DBs) | $0 | $45 | $540 |
| Service Endpoints | $0 | $0 | $0 |

**Savings: $540/year**

### Security Comparison

Both provide equivalent security for our architecture:

**Private Endpoints:**
- ✅ Private IP in VNet
- ✅ Traffic stays on Microsoft backbone
- ✅ Works across VNets/regions
- ✅ Private DNS integration
- ❌ $15/endpoint/month
- ❌ Additional DNS management

**Service Endpoints:**
- ✅ Traffic on Microsoft backbone (same as PE)
- ✅ FREE
- ✅ Simple configuration
- ✅ NSG integration
- ❌ Same VNet/region only (acceptable for our use case)
- ❌ Service-level firewall (vs resource-level)

### Our Use Case

UIT-Go requirements:
- AKS and databases in **same region** ✅
- AKS and databases in **same VNet** ✅
- No cross-region access needed ✅
- Cost optimization priority ✅

Service Endpoints meet all requirements.

## Security Analysis

### Threat Model

**Threat:** Unauthorized access to databases from internet

**With Public Endpoints (current):**
- ❌ Databases accessible from internet
- ❌ Only firewall IP restrictions
- ❌ Risk: IP spoofing, credential theft

**With Service Endpoints:**
- ✅ Public access completely disabled
- ✅ Only accessible from AKS subnet
- ✅ NSG rules enforce network policies
- ✅ Cannot access from internet even with credentials

**With Private Endpoints:**
- ✅ Same security as Service Endpoints (for our architecture)
- ✅ Private IP address
- ❌ Costs $45/month more

**Conclusion:** Service Endpoints provide equivalent security for same-VNet architecture.

## Implementation

### Terraform Changes

**Databases hardened:**
```hcl
# CosmosDB
public_network_access_enabled = false
virtual_network_rule {
  id = azurerm_subnet.aks_subnet.id
}

# Redis  
public_network_access_enabled = false
subnet_id = azurerm_subnet.aks_subnet.id

# PostgreSQL (already private)
public_network_access_enabled = false
delegated_subnet_id = azurerm_subnet.postgres_subnet.id
```

**Service Endpoints enabled:**
```hcl
resource "azurerm_subnet" "aks_subnet" {
  service_endpoints = [
    "Microsoft.AzureCosmosDB",
    "Microsoft.Cache",
    "Microsoft.Sql"
  ]
}
```

## Consequences

### Positive
- **Cost savings:** $45/month = $540/year
- **Simplicity:** Easier configuration than Private Endpoints
- **Performance:** Same latency as Private Endpoints
- **Security:** Zero public database endpoints

### Negative
- **Region limitation:** Cannot access databases from other regions
- **VNet limitation:** Cannot access from peered VNets without additional config

### Neutral
- **Network traffic:** Routes through Microsoft backbone (same as PE)

## Mitigation

For the negative consequences:

1. **Region limitation:** Not applicable - all resources in same region
2. **VNet limitation:** Not applicable - no VNet peering planned
3. **Future expansion:** Can upgrade to Private Endpoints if cross-region needed

## Compliance

- ✅ **Zero Trust:** Explicit deny of public access
- ✅ **Defense-in-Depth:** Network-level isolation + NSGs
- ✅ **Least Privilege:** Only AKS subnet can access
- ✅ **Data Protection:** Encrypted in transit (TLS)

## Verification

```bash
# Verify public access disabled
az cosmosdb show --name cosmos-uitgo-prod --resource-group rg-uitgo-prod --query "publicNetworkAccess"
# Output: "Disabled"

# Verify Service Endpoints
az network vnet subnet show --resource-group rg-uitgo-prod --vnet-name vnet-uitgo-prod --name snet-aks-prod --query "serviceEndpoints[].service"
# Output: ["Microsoft.AzureCosmosDB", "Microsoft.Cache", ...]

# Test access from internet (should fail)
mongosh "$COSMOS_CONNECTION_STRING"
# Error: Connection timeout
```

## Review Date

This decision will be reviewed **annually (November 2026)** or when:
- Cross-region access is required
- VNet peering is implemented
- Azure introduces new cost-effective solutions
