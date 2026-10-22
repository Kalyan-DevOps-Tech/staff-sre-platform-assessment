# Security Controls and Gaps

## Controls in this repository
- Separate namespaces for apps, observability, and platform services.
- Application service accounts with token automount disabled where Kubernetes API access is unnecessary.
- Non-root containers, read-only root filesystems where compatible, dropped Linux capabilities, and resource bounds.
- Readiness/liveness probes and bounded telemetry query windows.
- No committed secret values; environment variables reference Kubernetes Secret keys.
- AI SRE agent has no Kubernetes API credentials and performs read-only telemetry queries.
- Fault injection is opt-in and token protected.

## Verify before relying on controls
- Confirm network policies are enforced by the CNI in the k3s installation.
- Run negative tests to prove unauthorized access is denied.
- Pin and scan images; generate SBOMs and verify signatures in a hardened release pipeline.
- Replace local Kubernetes Secret examples with an approved external secret manager for production.
- Restrict ingress and use TLS for non-local access.
- Define backup encryption, retention, access, and restoration tests.
- Review upstream Helm chart RBAC and security contexts after rendering.

## Explicit limitations
This local assessment is not a compliance certification. A single-node k3s cluster does not prove high availability, tenant isolation at production scale, data residency, or disaster recovery.
