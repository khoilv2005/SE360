# Threat Model của UIT-Go

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
│           Nền tảng UIT-Go                   │
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
                    │  + Linkerd Mesh  │ ← Service Mesh + mTLS
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
│ + Linkerd    │ ← Service Mesh + mTLS
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

#### Flow 2: Trip Booking

```
┌─────────┐
│ Passenger│
└────┬────┘
     │ POST /api/trips
     │ {pickup, destination}
     ▼
┌──────────────┐
│   Ingress    │ ← Authentication check
│ + Linkerd    │ ← Service Mesh + mTLS
└──────┬───────┘
       │
       ▼
┌──────────────┐
│ TripService  │
│ 1. Validate  │
│ 2. Find driver│
│ 3. Save to DB │
└──────┬───────┘
       │
       ▼
┌──────────────┐
│   CosmosDB   │
│  trips table │
└──────┬───────┘
       │
       │ Return trip ID + status
       ▼
┌──────────────┐
│ TripService  │
│ Notify Driver│
│ Update Redis │
└──────┬───────┘
       │
       │ WebSocket + HTTP
       ▼
┌────────────────────────────┐
│        Driver App          │
│     Notification           │
└────────────────────────────┘
```

**Threats:**
- Unauthorized trip creation
- Fake driver assignment
- Trip data tampering
- Denial of service

#### Flow 3: Payment Processing

```
┌─────────┐
│ Client  │
└────┬────┘
     │ POST /api/payments
     │ {trip_id, amount}
     ▼
┌──────────────┐
│   Ingress    │ ← Input validation
│ + Linkerd    │ ← Service Mesh + mTLS
└──────┬───────┘
       │
       ▼
┌──────────────┐
│PaymentService│
│ 1. Validate  │
│ 2. Call VNPay│
└──────┬───────┘
       │
       │ HTTPS + API Key
       ▼
┌─────────────────────────────┐
│         VNPay Gateway        │
│  Payment processing         │
└─────────────┬───────────────┘
              │
              │ Payment URL
              ▼
┌─────────────────────────────┐
│         Client              │
│  Redirect to VNPay         │
└─────────────────────────────┘
```

**Threats:**
- Payment amount tampering
- Unauthorized refunds
- Payment API abuse
- Transaction replay attacks

---

## 🎯 Phân tích STRIDE

### Component 1: NGINX Ingress Controller + Linkerd Service Mesh

| Threat | Description | Likelihood | Impact | Mitigation | Priority |
|--------|-------------|------------|--------|------------|----------|
| **Spoofing** | Attacker impersonates legitimate client | Medium | High | TLS certificates, JWT validation | HIGH |
| **Tampering** | Modify requests in transit | Low | High | HTTPS/TLS 1.3 + Service Mesh mTLS | MEDIUM |
| **Repudiation** | Deny sending malicious requests | Medium | Low | Access logs, Service Mesh audit logs | LOW |
| **Info Disclosure** | Expose internal service IPs | Low | Medium | Network policies block direct access | MEDIUM |
| **DoS** | Flood with requests | High | High | Rate limiting (NGINX), connection limits | HIGH |
| **Elevation** | Bypass security controls | Medium | High | Network policies + Zero Trust | HIGH |

**Recommended Mitigations:**
- ✅ Enable Linkerd Service Mesh với automatic mTLS
- ✅ Rate limiting: 100 req/min general, 5 login/min
- ✅ Network policies: Default deny all
- ✅ Service-to-service encryption by default
- ✅ Request body size limit: 10MB

---

### Component 2: UserService (Authentication)

| Threat | Description | Likelihood | Impact | Mitigation | Priority |
|--------|-------------|------------|--------|------------|----------|
| **Spoofing** | Fake user credentials | High | High | Strong password hashing, rate limiting | HIGH |
| **Tampering** | Modify user data | Medium | High | Input validation, database constraints | HIGH |
| **Repudiation** | Deny transaction | High | Medium | Comprehensive audit logs | MEDIUM |
| **Info Disclosure** | Leak user PII | Medium | Critical | Data encryption, access controls | CRITICAL |
| **DoS** | Authentication DoS | High | Medium | Rate limiting, account lockout | MEDIUM |
| **Elevation** | Privilege escalation | Low | Critical | RBAC, least privilege | CRITICAL |

**Recommended Mitigations:**
- ✅ Argon2 password hashing
- ✅ JWT với 30-minute expiry
- ✅ Rate limiting: 5 attempts/min
- ✅ Account lockout sau 10 failed attempts
- ✅ PII encryption at rest

---

### Component 3: TripService (Core Business Logic)

| Threat | Description | Likelihood | Impact | Mitigation | Priority |
|--------|-------------|------------|--------|------------|----------|
| **Spoofing** | Fake trip requests | High | High | Authentication + authorization | HIGH |
| **Tampering** | Modify trip data | Medium | High | Input validation, business rules | HIGH |
| **Repudiation** | Deny trip actions | Medium | Medium | Immutable trip logs | MEDIUM |
| **Info Disclosure** | Leak trip info | Medium | Medium | Access controls, data masking | MEDIUM |
| **DoS** | Trip creation flood | Medium | Medium | Rate limiting, quotas | MEDIUM |
| **Elevation** | Admin privilege abuse | Low | High | RBAC, audit trails | HIGH |

**Recommended Mitigations:**
- ✅ Business rule validation
- ✅ Geographic boundary checks
- ✅ Rate limiting per user
- ✅ Immutable trip records
- ✅ Driver rating integration

---

### Component 4: PaymentService (Financial)

| Threat | Description | Likelihood | Impact | Mitigation | Priority |
|--------|-------------|------------|--------|------------|----------|
| **Spoofing** | Fake payment requests | High | Critical | Multi-factor auth, digital signatures | CRITICAL |
| **Tampering** | Modify payment amount | Medium | Critical | Amount validation, digital signatures | CRITICAL |
| **Repudiation** | Deny payment transaction | High | High | Immutable transaction logs | HIGH |
| **Info Disclosure** | Leak payment details | Low | Critical | Encrypt card data, PCI-DSS compliance | CRITICAL |
| **DoS** | Payment API flooding | Medium | High | Rate limiting on payment endpoints | HIGH |
| **Elevation** | Unauthorized refunds | Low | Critical | Multi-factor auth for refunds, role-based access | CRITICAL |

**Recommended Mitigations:**
- ✅ HTTPS only đến VNPay
- ✅ Request/response signature verification
- ✅ Amount format validation in Service Mesh
- ✅ Transaction ID uniqueness check
- ✅ Audit logs cho tất cả payment operations

---

### Component 5: LocationService (Real-time)

| Threat | Description | Likelihood | Impact | Mitigation | Priority |
|--------|-------------|------------|--------|------------|----------|
| **Spoofing** | Fake location data | High | High | GPS validation, anti-spoofing | HIGH |
| **Tampering** | Modify location | Medium | Medium | Location validation, trip correlation | MEDIUM |
| **Repudiation** | Deny location | Low | Low | Location logging | LOW |
| **Info Disclosure** | Leak location data | Medium | High | Location encryption, access controls | HIGH |
| **DoS** | Location update flood | High | Medium | Rate limiting, data throttling | MEDIUM |
| **Elevation** | Access all locations | Low | High | RBAC, data segregation | HIGH |

**Recommended Mitigations:**
- ✅ WebSocket authentication
- ✅ Location validation bounds
- ✅ Rate limiting: 10 updates/min
- ✅ Location data encryption
- ✅ Privacy controls (driver consent)

---

## 🔐 Authentication & Authorization Analysis

### 1. API Endpoints Authentication

| Endpoint | Protocol | Auth Method | Encryption | Priority |
|----------|----------|-------------|------------|----------|
| `/api/users/*` | HTTPS | JWT | None | HIGH |
| `/api/trips/*` | HTTPS | JWT | None | HIGH |
| `/api/drivers/*` | HTTPS | JWT | None | HIGH |
| `/api/locations/*` | HTTPS | JWT | None | MEDIUM |
| `/api/payments/*` | HTTPS | JWT | None | CRITICAL |
| `/ws` | WSS | JWT | None | HIGH |

**After Phase 2 (Service Mesh):**
- Risk Level giảm xuống MEDIUM/LOW
- Service Mesh encryption between services

### 2. Service-to-Service Communication

| Source | Destination | Protocol | Authentication | Encryption |
|--------|-------------|----------|----------------|------------|
| TripService | UserService | HTTP | Linkerd mTLS | mTLS encrypted |
| PaymentService | TripService | HTTP | Linkerd mTLS | mTLS encrypted |
| LocationService | TripService | HTTP | Linkerd mTLS | mTLS encrypted |

**Threats:**
- Service impersonation (MITIGATED ✅)
- Unauthorized cross-service calls (MITIGATED ✅)

**Mitigation (IMPLEMENTED):**
- ✅ Linkerd Service Mesh cho mTLS
- ✅ Zero Trust Network Policies
- ✅ Automatic certificate rotation

### 3. Database Access

| Database | Access Method | Authentication | Encryption |
|----------|----------------|----------------|------------|
| PostgreSQL | VNet | Azure AD + Connection String | TLS 1.3 |
| CosmosDB | Service Endpoint | Azure AD | mTLS |
| Redis | Service Endpoint | Access Key | TLS 1.3 |

---

## 📊 Risk Assessment Matrix

### Risk Levels
- 🔴 **CRITICAL**: Immediate action required
- 🟠 **HIGH**: Address within 1 week
- 🟡 **MEDIUM**: Address within 1 month
- 🟢 **LOW**: Address in next planning cycle

### Identified Risks

| Risk | Component | Mitigation Phase | Status |
|------|-----------|------------------|--------|
| CosmosDB publicly accessible | Databases | Phase 1.2 | 🔴 High Priority |
| Redis publicly accessible | Databases | Phase 1.2 | 🔴 High Priority |
| No Service Mesh protection | Ingress | Phase 2 | ✅ RESOLVED (Linkerd deployed) |
| Payment API vulnerable to tampering | PaymentService | Phase 2 | 🔴 High Priority |
| Weak password hashing | UserService | Phase 3 | 🟡 Medium Priority |
| No API rate limiting | Ingress | Phase 2 | 🟡 Medium Priority |
| Insufficient logging | All services | Phase 5 | 🟡 Medium Priority |

### High Risks

1. **Database Public Exposure** (CRITICAL)
   - CosmosDB & Redis accessible từ internet
   - **Mitigation**: VNet Service Endpoints + NSGs

2. **Payment API Tampering** (HIGH)
   - No validation on payment amounts
   - **Mitigation**: Service mesh + input validation

3. **Insufficient Authentication** (HIGH)
   - No rate limiting on auth endpoints
   - **Mitigation**: NGINX rate limiting + account lockout

---

## 🛡️ Mitigation Strategy

### Phase 1: Network & Data Security (Week 1-2)
- ✅ Database private endpoints (VNet Service Endpoints)
- ✅ Network Security Groups (NSGs)
- ✅ Secrets encryption at rest

### Phase 2: Zero Trust (Week 3)
- ✅ Service mesh implementation (Linkerd)
- ✅ mTLS encryption between services
- ✅ Network policies (default deny)

### Phase 3: Application Security (Week 4-5)
- ✅ Input validation & sanitization
- ✅ Rate limiting & throttling
- ✅ Authentication hardening
- ✅ Error handling improvements

### Phase 4: Monitoring & Response (Week 6)
- ✅ Security monitoring & alerting
- ✅ Log aggregation & analysis
- ✅ Incident response procedures
- ✅ Compliance reporting

---

## 📋 Compliance Requirements

### Data Protection
- **PII Encryption**: User data encrypted at rest and in transit
- **Location Privacy**: Driver location tracking với consent
- **Payment Security**: PCI-DSS compliance for payment processing

### Security Standards
- **OWASP Top 10**: Mitigation cho tất cả 10 categories
- **Zero Trust**: Never trust, always verify
- **Defense in Depth**: Multiple security layers

### Auditing & Monitoring
- **Comprehensive Logging**: All security events logged
- **Real-time Monitoring**: Threat detection and response
- **Regular Assessments**: Quarterly security reviews

---

## 🎯 Success Criteria

### Security Metrics
- ✅ **100%** inter-service traffic encrypted with mTLS
- ✅ **Zero** public database endpoints
- ✅ **< 5 minutes** average incident response time
- ✅ **Zero** critical vulnerabilities in production

### Business Impact
- ✅ **Risk Reduction**: 95% reduction in attack surface
- ✅ **Compliance**: Ready cho security audits
- ✅ **Performance**: < 10ms latency overhead
- ✅ **Cost**: Zero additional security infrastructure cost

---

## 🔄 Maintenance & Updates

### Monthly Tasks
- Review security logs and alerts
- Update security patches and CVE fixes
- Rotate secrets and certificates
- Test incident response procedures

### Quarterly Tasks
- Comprehensive security assessment
- Threat model review and updates
- Penetration testing
- Compliance audit preparation

---

**Last Updated:** 2024-11-24
**Review Date:** 2025-02-24
**Owner:** UIT-Go Security Team

---

*"Security is not a product, but a process."*