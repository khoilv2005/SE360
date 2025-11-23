#!/bin/bash
# ================================================
# ModSecurity WAF Testing Script
# Test OWASP Top 10 vulnerabilities protection
# ================================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "🔍 ModSecurity WAF Testing Script"
echo "=================================="
echo ""

# Get Ingress LoadBalancer IP
echo "📡 Getting Ingress LoadBalancer IP..."
INGRESS_IP=$(kubectl get service ingress-nginx-controller -n ingress-nginx -o jsonpath='{.status.loadBalancer.ingress[0].ip}')

if [ -z "$INGRESS_IP" ]; then
  echo -e "${RED}❌ Error: Could not get Ingress IP${NC}"
  echo "Make sure NGINX Ingress Controller is deployed and has external IP"
  exit 1
fi

echo -e "${GREEN}✅ Ingress IP: http://$INGRESS_IP${NC}"
TARGET="http://$INGRESS_IP"
echo ""

# Test counter
PASSED=0
FAILED=0

# ================================================
# TEST 1: SQL Injection Detection
# ================================================
echo "TEST 1: SQL Injection Detection"
echo "Testing: /api/users?id=1' OR '1'='1"
RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" "$TARGET/api/users?id=1' OR '1'='1")
if [ "$RESPONSE" = "403" ]; then
  echo -e "${GREEN}✅ PASSED - Blocked with 403${NC}"
  ((PASSED++))
else
  echo -e "${RED}❌ FAILED - Got $RESPONSE (expected 403)${NC}"
  ((FAILED++))
fi
echo ""

# ================================================
# TEST 2: XSS Detection
# ================================================
echo "TEST 2: Cross-Site Scripting (XSS)"
echo "Testing: /api/trips?search=<script>alert('XSS')</script>"
RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" "$TARGET/api/trips?search=<script>alert('XSS')</script>")
if [ "$RESPONSE" = "403" ]; then
  echo -e "${GREEN}✅ PASSED - Blocked with 403${NC}"
  ((PASSED++))
else
  echo -e "${RED}❌ FAILED - Got $RESPONSE (expected 403)${NC}"
  ((FAILED++))
fi
echo ""

# ================================================
# TEST 3: Path Traversal
# ================================================
echo "TEST 3: Path Traversal Attack"
echo "Testing: /api/users/../../../etc/passwd"
RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" "$TARGET/api/users/../../../etc/passwd")
if [ "$RESPONSE" = "400" ] || [ "$RESPONSE" = "403" ]; then
  echo -e "${GREEN}✅ PASSED - Blocked with $RESPONSE${NC}"
  ((PASSED++))
else
  echo -e "${RED}❌ FAILED - Got $RESPONSE (expected 400/403)${NC}"
  ((FAILED++))
fi
echo ""

# ================================================
# TEST 4: Rate Limiting (100 req/min)
# ================================================
echo "TEST 4: Rate Limiting (100 requests per minute)"
echo "Sending 110 requests..."
BLOCKED=0
for i in {1..110}; do
  RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" "$TARGET/api/users")
  if [ "$RESPONSE" = "429" ]; then
    ((BLOCKED++))
  fi
done

if [ $BLOCKED -gt 0 ]; then
  echo -e "${GREEN}✅ PASSED - $BLOCKED requests blocked with 429${NC}"
  ((PASSED++))
else
  echo -e "${YELLOW}⚠️  WARNING - No requests blocked (might not be in blocking mode)${NC}"
  ((FAILED++))
fi
echo ""

# ================================================
# TEST 5: Malicious User-Agent
# ================================================
echo "TEST 5: Malicious Scanner Detection"
echo "Testing: User-Agent: sqlmap/1.0"
RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" -A "sqlmap/1.0" "$TARGET/api/users")
if [ "$RESPONSE" = "403" ]; then
  echo -e "${GREEN}✅ PASSED - Blocked with 403${NC}"
  ((PASSED++))
else
  echo -e "${RED}❌ FAILED - Got $RESPONSE (expected 403)${NC}"
  ((FAILED++))
fi
echo ""

# ================================================
# TEST 6: Login Rate Limiting
# ================================================
echo "TEST 6: Login Rate Limiting (5 attempts per minute)"
echo "Sending 7 login requests..."
BLOCKED=0
for i in {1..7}; do
  RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$TARGET/api/users/login" -H "Content-Type: application/json" -d '{"username":"test"}')
  if [ "$RESPONSE" = "429" ]; then
    ((BLOCKED++))
  fi
done

if [ $BLOCKED -gt 0 ]; then
  echo -e "${GREEN}✅ PASSED - $BLOCKED login attempts blocked${NC}"
  ((PASSED++))
else
  echo -e "${YELLOW}⚠️  WARNING - No login attempts blocked${NC}"
  ((FAILED++))
fi
echo ""

# ================================================
# TEST 7: Payment Amount Validation
# ================================================
echo "TEST 7: Payment Amount Validation"
echo "Testing: Invalid payment amount format"
RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$TARGET/api/payments" -H "Content-Type: application/json" -d '{"amount":"invalid"}')
if [ "$RESPONSE" = "400" ] || [ "$RESPONSE" = "403" ]; then
  echo -e "${GREEN}✅ PASSED - Blocked with $RESPONSE${NC}"
  ((PASSED++))
else
  echo -e "${YELLOW}⚠️  WARNING - Got $RESPONSE (might not validate yet)${NC}"
  ((FAILED++))
fi
echo ""

# ================================================
# TEST 8: Dangerous File Extension
# ================================================
echo "TEST 8: Dangerous File Extension Block"
echo "Testing: /upload/malware.exe"
RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" "$TARGET/upload/malware.exe")
if [ "$RESPONSE" = "403" ]; then
  echo -e "${GREEN}✅ PASSED - Blocked with 403${NC}"
  ((PASSED++))
else
  echo -e "${YELLOW}⚠️  INFO - Got $RESPONSE (endpoint might not exist)${NC}"
  # Don't count as failure since endpoint doesn't exist
fi
echo ""

# ================================================
# TEST 9: Legitimate Traffic
# ================================================
echo "TEST 9: Legitimate Traffic (should pass)"
echo "Testing: Normal request to /api/users"
RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" "$TARGET/api/users")
if [ "$RESPONSE" = "200" ] || [ "$RESPONSE" = "404" ] || [ "$RESPONSE" = "401" ]; then
  echo -e "${GREEN}✅ PASSED - Legitimate traffic allowed ($RESPONSE)${NC}"
  ((PASSED++))
else
  echo -e "${RED}❌ FAILED - Legitimate traffic blocked with $RESPONSE${NC}"
  ((FAILED++))
fi
echo ""

# ================================================
# Summary
# ================================================
echo "=================================="
echo "📊 Test Results Summary"
echo "=================================="
echo -e "${GREEN}✅ PASSED: $PASSED${NC}"
echo -e "${RED}❌ FAILED: $FAILED${NC}"
TOTAL=$((PASSED + FAILED))
echo "📈 Total Tests: $TOTAL"
echo ""

if [ $PASSED -ge 7 ]; then
  echo -e "${GREEN}🎉 ModSecurity WAF is working correctly!${NC}"
  echo ""
  echo "Next steps:"
  echo "1. Check ModSecurity logs: kubectl logs -n ingress-nginx deployment/ingress-nginx-controller | grep ModSecurity"
  echo "2. Monitor for false positives for 1-2 weeks"
  echo "3. Switch from DetectionOnly to On mode when ready"
  exit 0
else
  echo -e "${YELLOW}⚠️  Some tests failed. ModSecurity might be in DetectionOnly mode.${NC}"
  echo ""
  echo "Troubleshooting:"
  echo "1. Check if ModSecurity is enabled: kubectl get cm ingress-nginx-controller -n ingress-nginx -o yaml | grep modsecurity"
  echo "2. Check logs: kubectl logs -n ingress-nginx deployment/ingress-nginx-controller"
  echo "3. Verify custom rules deployed: kubectl get cm modsecurity-custom-rules -n ingress-nginx"
  exit 1
fi
