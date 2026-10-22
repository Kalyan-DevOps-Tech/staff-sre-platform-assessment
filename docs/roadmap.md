# Roadmap

1. Verify clean-room bootstrap on a supported Linux host.
2. Pin all chart versions and image digests; add SBOM, image scan, and signature verification.
3. Add alert routing to a local test receiver and test alert resolution.
4. Add enforced network policies and positive/negative connectivity tests.
5. Add persistent storage sizing, backup, restore, and retention tests for Loki, Tempo, Prometheus, and Temporal.
6. Add load tests, resource profiling, and SLO burn-rate alerts.
7. Add multi-node k3s failure drills.
8. Port to EKS with IRSA, multi-AZ node groups, managed secrets, encrypted storage, and tested DR.
