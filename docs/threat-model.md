# UIT-Go Threat Model

Threat modeling cho hệ thống UIT-Go ride-sharing platform sử dụng phương pháp STRIDE.

## 📊 Data Flow Diagrams (DFD)

### DFD Level 0: Context Diagram

```
┌──────────────┐
│   Passenger  │
│     App      │
└──────┬───────┘
       │
       │ HTTPS
       ▼
┌─────────────────────────────────────────────┐
│                                             │
│           UIT-Go Platform                   │
│  (5 Microservices trên Azure AKS)           │
│                                             │
└────┬─────────┬──────────┬──────────┬───────┘
     │         │          │          │
     │         │          │          │
┌────▼────┐ ┌──▼──────┐ ┌▼────────┐ ┌▼──────┐
│ Driver  │ │  VNPay  │ │ Mapbox  │ │ Azure │
│   App   │ │ Payment │ │   API   │ │  DBs  │
└─────────┘ └─────────┘ └─────────┘ └───────┘
```

**External Entities:**
1. **Passenger App** - Mobile/Web client cho hành khách
2. **Driver App** - Mobile app cho tài xế
3. **VNPay** - Payment gateway (bên thứ 3)
4. **Mapbox API** - Geolocation service (bên thứ 3)
5. **Azure Databases** - PostgreSQL, CosmosDB, Redis

---

### DFD Level 1: Service Interactions

```
                        Internet (HTTPS)
                              │
                              ▼
                    ┌──────────────────┐
                    │  NGINX Ingress   │
                    │  + ModSecurity   │ ← WAF Layer
                    │    LoadBalancer  │
                    └────────┬─────────┘
                             │
           ┌─────────────────┼──────────────────┐
           │                 │                  │
           ▼                 ▼                  ▼
    ┌─────────────┐   ┌─────────────┐   ┌─────────────┐
    │ UserService │   │ TripService │   │LocationSvc  │
    │   (REST)    │   │   (REST)    │   │(REST+WS)    │
    └──────┬──────┘   └──────┬──────┘   └──────┬──────┘
           │                 │                  │
           ▼                 ▼                  ▼
    ┌───────────┐     ┌───────────┐     ┌───────────┐
    │PostgreSQL │     │ CosmosDB  │     │   Redis   │
    │  (VNet)   │     │(Service EP)     │(Service EP)│
    └───────────┘     └───────────┘     └───────────┘
           
           │                 │                  
           ▼                 ▼                 
    ┌─────────────┐   ┌──────────────┐
    │DriverService│   │PaymentService│
    │   (REST)    │   │   (REST)     │
    └──────┬──────┘   └──────┬───────┘
           │                 │
           ▼                 │
    ┌───────────┐           │
    │ CosmosDB  │           │
    │(Service EP)           │
    └───────────┘           │
                            ▼
                     ┌─────────────┐
                     │ VNPay API   │
                     │  (External) │
                     └─────────────┘
```

**Key Data Flows:**
1. **Authentication**: Passenger/Driver → UserService → PostgreSQL
2. **Trip Booking**: Passenger → TripService → CosmosDB
3. **Location Tracking**: Driver → LocationService → Redis (real-time)
4. **Payment**: Passenger → PaymentService → VNPay → CosmosDB
5. **Driver Management**: Admin → DriverService → CosmosDB

---

### DFD Level 2: Critical Flows

#### Flow 1: User Authentication

```
┌─────────┐
│ Client  │
└────┬────┘
     │ POST /api/users/login
     │ {username, password}
     ▼
┌──────────────┐
│   Ingress    │ ← Rate limiting (5 login/min)
│ ModSecurity  │ ← SQL injection detection
└──────┬───────┘
       │
       ▼
┌──────────────┐
│ UserService  │
│  1. Validate │
│  2. Hash pwd │
│  3. Query DB │
└──────┬───────┘
       │
       ▼
┌──────────────┐
│ PostgreSQL   │
│  users table │
└──────┬───────┘
       │
       │ Return user + hashed password
       ▼
┌──────────────┐
│ UserService  │
│ 1. Verify pwd│
│ 2. Gen JWT   │
└──────┬───────┘
       │
       │ JWT token (30min expiry)
       ▼
┌─────────┐
│ Client  │
└─────────┘
```

**Threats:**
- Brute force attacks
- Credential stuffing
- JWT token stealing
- Man-in-the-middle

#### Flow 2: Payment Processing

```
┌──────────┐
│Passenger │
└────┬─────┘
     │ POST /api/payments
     │ {trip_id, amount}
     ▼
┌──────────────┐
│   Ingress    │ ← Input validation
│ ModSecurity  │ ← Amount format check
└──────┬───────┘
       │
       ▼
┌──────────────┐
│PaymentService│
│ 1. Validate  │
│ 2. Call VNPay│
└──────┬───────┘
       │
       ├────────────────────┐
       │                    │
       ▼                    ▼
┌──────────────┐    ┌──────────────┐
│  VNPay API   │    │  CosmosDB    │
│ (HTTPS only) │    │ Save pending │
└──────┬───────┘    └──────────────┘
       │
       │ Payment result + signature
       ▼
┌──────────────┐
│PaymentService│
│ 1. Verify sig│
│ 2. Update DB │
└──────┬───────┘
       │
       ▼
┌──────────────┐
│  CosmosDB    │
│Update payment│
└──────────────┘
```

**Threats:**
- Payment replay attacks
- Amount tampering
- Signature forgery
- Data repudiation

#### Flow 3: Real-time Location Tracking (WebSocket)

```
┌─────────┐
│ Driver  │
└────┬────┘
     │ WS /ws
     │ {lat, lng, driver_id}
     ▼
┌──────────────┐
│   Ingress    │ ← WS rate limiting
│  (WebSocket) │ ← Connection validation
└──────┬───────┘
       │
       ▼
┌──────────────┐
│LocationSvc   │
│ 1. Auth check│
│ 2. Validate  │
└──────┬───────┘
       │
       ▼
┌──────────────┐
│    Redis     │
│ Store coords │
│  (TTL 60s)   │
└──────┬───────┘
       │
       │ Pub/Sub
       ▼
┌──────────────┐
│ Passengers   │
│(subscribed)  │
└──────────────┘
```

**Threats:**
- Location spoofing
- WebSocket flooding
- Unauthorized tracking
- Privacy leaks

---

## 🎯 STRIDE Analysis

### Component 1: NGINX Ingress Controller + ModSecurity WAF

| Threat | Description | Likelihood | Impact | Mitigation | Priority |
|--------|-------------|------------|--------|------------|----------|
| **Spoofing** | Attacker impersonates legitimate client | Medium | High | TLS certificates, JWT validation | HIGH |
| **Tampering** | Modify requests in transit | Low | High | HTTPS/TLS 1.3 enforced | MEDIUM |
| **Repudiation** | Deny sending malicious requests | Medium | Low | Access logs, ModSecurity audit logs | LOW |
| **Info Disclosure** | Expose internal service IPs | Low | Medium | Block error pages with stack traces | MEDIUM |
| **DoS** | Flood with requests | High | High | Rate limiting (100 req/min), connection limits | HIGH |
| **Elevation** | Bypass WAF rules | Medium | High | OWASP CRS 4.0, regular rule updates | HIGH |

**Recommended Mitigations:**
- ✅ Enable ModSecurity OWASP CRS 4.0
- ✅ Rate limiting: 100 req/min general, 5 login/min
- ✅ Block malicious User-Agents
- ✅ Geo-blocking (optional)
- ✅ Request body size limit: 10MB

---

### Component 2: UserService (Authentication)

| Threat | Description | Likelihood | Impact | Mitigation | Priority |
|--------|-------------|------------|--------|------------|----------|
| **Spoofing** | Fake user credentials | High | High | Bcrypt password hashing, JWT with short expiry (30min) | HIGH |
| **Tampering** | Modify JWT tokens | Medium | High | JWT signature verification, secret rotation | HIGH |
| **Repudiation** | Deny login attempts | Low | Low | Audit logs for failed logins | LOW |
| **Info Disclosure** | Expose user PII | Medium | High | Encrypt secrets at rest, mask sensitive logs | HIGH |
| **DoS** | Brute force login | High | Medium | Login rate limiting (5/min per IP) | HIGH |
| **Elevation** | Gain admin privileges | Low | Critical | RBAC, role claim in JWT | CRITICAL |

**Recommended Mitigations:**
- ✅ Parameterized SQL queries (prevent SQL injection)
- ✅ Input validation with Pydantic
- ✅ Rate limiting on `/api/users/login`
- ✅ JWT with audience claim
- ✅ Password complexity requirements

---

### Component 3: PaymentService

| Threat | Description | Likelihood | Impact | Mitigation | Priority |
|--------|-------------|------------|--------|------------|----------|
| **Spoofing** | Fake payment confirmations | Low | Critical | VNPay signature verification | CRITICAL |
| **Tampering** | Modify payment amounts | Medium | Critical | Request signing, amount validation | CRITICAL |
| **Repudiation** | Deny payment transaction | High | High | Immutable transaction logs, blockchain consideration | HIGH |
| **Info Disclosure** | Leak payment details | Low | Critical | Encrypt card data, PCI-DSS compliance | CRITICAL |
| **DoS** | Payment API flooding | Medium | High | Rate limiting on payment endpoints | HIGH |
| **Elevation** | Unauthorized refunds | Low | Critical | Multi-factor auth for refunds, role-based access | CRITICAL |

**Recommended Mitigations:**
- ✅ HTTPS only to VNPay
- ✅ Request/response signature verification
- ✅ Amount format validation in ModSecurity
- ✅ Transaction ID uniqueness check
- ✅ Audit logs for all payment operations

---

### Component 4: LocationService (WebSocket)

| Threat | Description | Likelihood | Impact | Mitigation | Priority |
|--------|-------------|------------|--------|------------|----------|
| **Spoofing** | Fake driver locations | High | Medium | JWT in WebSocket handshake | HIGH |
| **Tampering** | Modify coordinates | Medium | Medium | Input validation (lat/lng ranges) | MEDIUM |
| **Repudiation** | Deny location history | Low | Low | Location logs with timestamps | LOW |
| **Info Disclosure** | Unauthorized location access | High | High | Subscribe only to own trips | HIGH |
| **DoS** | WebSocket connection exhaustion | High | High | Connection limits, heartbeat timeouts | HIGH |
| **Elevation** | Track any driver | Medium | High | Trip-based subscription authorization | HIGH |

**Recommended Mitigations:**
- ✅ WebSocket auth with JWT
- ✅ Connection rate limiting
- ✅ Redis TTL (60s) to prevent stale data
- ✅ Validate subscriber permissions

---

### Component 5: Databases (PostgreSQL, CosmosDB, Redis)

| Threat | Description | Likelihood | Impact | Mitigation | Priority |
|--------|-------------|------------|--------|------------|----------|
| **Spoofing** | Unauthorized DB access | Low | Critical | VNet isolation, no public endpoints | CRITICAL |
| **Tampering** | Modify database records | Low | Critical | Audit logging, backups | HIGH |
| **Repudiation** | Deny data changes | Low | Medium | Database audit logs | MEDIUM |
| **Info Disclosure** | Data breach from DB | Medium | Critical | Encryption at rest, TLS in transit | CRITICAL |
| **DoS** | Connection exhaustion | Medium | High | Connection pooling, rate limiting | MEDIUM |
| **Elevation** | Admin access escalation | Low | Critical | Principle of least privilege, managed identities | CRITICAL |

**Current Status:**
- ✅ PostgreSQL: Private VNet ✅
- ❌ CosmosDB: Public endpoint ❌ → **Fix in Phase 1**
- ❌ Redis: Public endpoint ❌ → **Fix in Phase 1**

**Recommended Mitigations:**
- ✅ VNet Service Endpoints for CosmosDB/Redis
- ✅ NSGs blocking unauthorized subnets
- ✅ Encryption at rest (already enabled)
- ✅ TLS 1.2+ for connections

---

## 🎭 Attack Surface Analysis

### 1. External-Facing Attack Surface

| Entry Point | Protocol | Authentication | Current Protection | Risk Level |
|-------------|----------|----------------|-------------------|------------|
| `/api/users/*` | HTTPS | JWT | None | HIGH |
| `/api/trips/*` | HTTPS | JWT | None | HIGH |
| `/api/drivers/*` | HTTPS | JWT | None | HIGH |
| `/api/locations/*` | HTTPS | JWT | None | MEDIUM |
| `/api/payments/*` | HTTPS | JWT | None | CRITICAL |
| `/ws` | WSS | JWT | None | HIGH |

**After Phase 2 (ModSecurity):**
- Risk Level giảm xuống MEDIUM/LOW
- OWASP Top 10 protected

---

### 2. Service-to-Service Communication

| Source | Destination | Protocol | Authentication | Encryption |
|--------|-------------|----------|----------------|------------|
| TripService | UserService | HTTP | None | ClusterIP only |
| PaymentService | TripService | HTTP | None | ClusterIP only |
| LocationService | TripService | HTTP | None | ClusterIP only |

**Threats:**
- Service impersonation
- Unauthorized cross-service calls
- No mutual TLS

**Mitigation (Future - Optional):**
- Consider Service Mesh (Istio/Linkerd) for mTLS
- Currently rely on Network Policies

---

### 3. External Dependencies

| Service | Provider | Protocol | Trust Level | Mitigation |
|---------|----------|----------|-------------|------------|
| VNPay API | VNPay | HTTPS | Medium | Signature verification |
| Mapbox API | Mapbox | HTTPS | Medium | API key rotation |
| Azure Services | Microsoft | HTTPS/TLS | High | Managed identities |

**Threats:**
- API key leakage
- Man-in-the-middle (external APIs)
- Service outages

**Mitigation:**
- ✅ Secrets encryption (Phase 1)
- ✅ TLS certificate validation
- ✅ API rate limiting
- ✅ Secrets scan in CI/CD (Phase 3)

---

## 📋 Risk Assessment Summary

### Critical Risks (Must fix immediately)

| Risk | Component | Mitigation Phase | Status |
|------|-----------|------------------|--------|
| CosmosDB publicly accessible | Databases | Phase 1.2 | 🔴 High Priority |
| Redis publicly accessible | Databases | Phase 1.2 | 🔴 High Priority |
| No WAF protection | Ingress | Phase 2 | 🔴 High Priority |
| Payment API vulnerable to tampering | PaymentService | Phase 2 | 🔴 High Priority |

### High Risks

| Risk | Component | Mitigation Phase | Status |
|------|-----------|------------------|--------|
| No rate limiting | All APIs | Phase 2 | 🟠 Medium Priority |
| Secrets not encrypted at rest | K8s | Phase 1.3 | 🟠 Medium Priority |
| No SAST/DAST in CI/CD | Pipeline | Phase 3 | 🟠 Medium Priority |
| Pods running as root | K8s workloads | Phase 4 | 🟠 Medium Priority |

### Medium Risks

| Risk | Component | Mitigation Phase | Status |
|------|-----------|------------------|--------|
| No security monitoring | Infrastructure | Phase 5 | 🟡 Low Priority |
| Missing NSGs | Network | Phase 1.2 | 🟡 Low Priority |

---

## 🗺️ Mitigation Roadmap

```
Week 1-2: Phase 1 (Foundation)
├─ Fix database public endpoints ✅
├─ Add NSGs ✅
└─ Enable K8s secrets encryption ✅

Week 3: Phase 2 (WAF)
├─ Deploy ModSecurity ✅
├─ OWASP CRS 4.0 ✅
└─ Custom rules (rate limiting, payment validation) ✅

Week 4: Phase 3 (CI/CD Security)
├─ SAST (Bandit) ✅
├─ Dependency scan (Safety) ✅
├─ Container scan (Trivy) ✅
├─ Secrets scan (TruffleHog) ✅
├─ IaC scan (Checkov) ✅
└─ DAST (OWASP ZAP) ✅

Week 5: Phase 4 (Hardening)
└─ Pod security contexts ✅

Week 6: Phase 5 (Monitoring)
└─ Azure Monitor alerts ✅

Week 7: Phase 6 (Documentation)
└─ ADRs + security docs ✅
```

---

## ✅ Deliverables Checklist

- [x] DFD Level 0 (Context Diagram)
- [x] DFD Level 1 (Service Interactions)
- [x] DFD Level 2 (Critical Flows: Auth, Payment, Location)
- [x] STRIDE analysis for 5 key components
- [x] Attack surface mapping
- [x] Risk assessment matrix
- [x] Mitigation roadmap with timeline

**Next Steps:**
1. Review threat model with team
2. Prioritize fixes based on risk level
3. Proceed to Phase 1.2: Network Security implementation
