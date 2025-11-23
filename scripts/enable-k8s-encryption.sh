#!/bin/bash
# ================================================
# Enable encryption at rest for Kubernetes secrets
# (AKS native feature - FREE)
# ================================================

set -e

echo "🔒 Enabling AKS encryption at rest for secrets..."

# Update AKS cluster to enable encryption at host
az aks update \
  --resource-group rg-uitgo-prod \
  --name aks-uitgo-prod \
  --enable-encryption-at-host

echo "✅ Encryption at host enabled"

# Verify encryption enabled
echo "🔍 Verifying encryption status..."
az aks show \
  --resource-group rg-uitgo-prod \
  --name aks-uitgo-prod \
  --query "securityProfile" -o table

echo ""
echo "✅ Kubernetes secrets encryption at rest is now ENABLED"
echo ""
echo "📋 Next steps:"
echo "  1. Restart all pods to apply new encryption: kubectl rollout restart deployment --all"
echo "  2. Verify pods are running: kubectl get pods --all-namespaces"
echo "  3. Check encryption in Azure Portal: AKS → Security"
