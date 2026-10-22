#!/usr/bin/env python3
"""Offline repository validation: YAML syntax and embedded dashboard JSON."""
import json
from pathlib import Path
import sys
try:
    import yaml
except ImportError:
    print("PyYAML missing; install requirements-dev.txt", file=sys.stderr)
    raise SystemExit(2)
root = Path(__file__).resolve().parents[1]
errors = []
for path in sorted([*root.rglob("*.yaml"), *root.rglob("*.yml")]):
    if ".git" in path.parts:
        continue
    try:
        list(yaml.safe_load_all(path.read_text()))
    except Exception as exc:
        errors.append(f"{path.relative_to(root)}: {exc}")
config = root / "gitops/observability/dashboard-configmap.yaml"
try:
    obj = yaml.safe_load(config.read_text())
    json.loads(obj["data"]["sample-api.json"])
except Exception as exc:
    errors.append(f"{config.relative_to(root)} embedded dashboard JSON: {exc}")
if errors:
    print("Repository validation failed:")
    print("\n".join(errors))
    raise SystemExit(1)
print("PASS: YAML documents and embedded Grafana dashboard JSON are syntactically valid")
