# ================================================
# Pod Security Context Template for All Services
# Phase 4: Application Hardening
# ================================================
#
# Security Features Applied:
# - Non-root execution (UID 1000)
# - Read-only root filesystem
# - All capabilities dropped
# - Resource limits (128Mi-512Mi RAM, 100m-500m CPU)
# - Seccomp profile: RuntimeDefault
# - Temporary directory volume for /tmp
#
# Apply to: TripService, DriverService, LocationService, PaymentService
# ================================================

# Add these sections to each service YAML:

Pod-level security context (add under spec:):
---
securityContext:
  runAsNonRoot: true
  runAsUser: 1000
  fsGroup: 1000
  seccompProfile:
    type: RuntimeDefault

Container-level security context (add under containers[].):
---
securityContext:
  allowPrivilegeEscalation: false
  readOnlyRootFilesystem: true
  runAsNonRoot: true
  runAsUser: 1000
  capabilities:
    drop:
    - ALL

Resource limits (add under containers[].):
---
resources:
  requests:
    memory: "128Mi"
    cpu: "100m"
  limits:
    memory: "512Mi"
    cpu: "500m"

Volume mounts (add under containers[].):
---
volumeMounts:
- name: tmp
  mountPath: /tmp

Volumes (add under spec:):
---
volumes:
- name: tmp
  emptyDir: {}
