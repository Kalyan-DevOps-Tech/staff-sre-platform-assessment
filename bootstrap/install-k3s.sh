#!/usr/bin/env bash
set -euo pipefail
if [[ ${EUID} -ne 0 ]]; then echo "Run with sudo: sudo $0" >&2; exit 1; fi
command -v curl >/dev/null || { echo "curl is required" >&2; exit 1; }
if command -v k3s >/dev/null; then echo "k3s already installed; refusing to overwrite."; exit 0; fi
curl -sfL https://get.k3s.io | sh -s - --write-kubeconfig-mode 640 --disable traefik
echo "k3s installed. Copy /etc/rancher/k3s/k3s.yaml to your user with restrictive permissions if needed."
echo "Traefik is disabled; expose services only through explicitly configured ingress or port-forwarding."
