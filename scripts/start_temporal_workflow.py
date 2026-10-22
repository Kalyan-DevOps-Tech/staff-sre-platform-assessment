#!/usr/bin/env python3
"""Start the assessment incident-analysis workflow against a running Temporal server."""
import argparse, asyncio, os, time, uuid
from temporalio.client import Client
from temporalio.common import WorkflowIDReusePolicy
from temporal_worker import IncidentAnalysisWorkflow

async def main(args):
    client = await Client.connect(args.temporal_address, namespace=args.namespace)
    now = int(time.time())
    payload = {
        "incident_id": args.incident_id or "manual-" + uuid.uuid4().hex[:12],
        "service": args.service,
        "start_unix": args.start_unix or now - args.window_seconds,
        "end_unix": args.end_unix or now,
        "description": args.description,
    }
    handle = await client.start_workflow(
        IncidentAnalysisWorkflow.run,
        payload,
        id=payload["incident_id"],
        task_queue="sre-incident-analysis",
        id_reuse_policy=WorkflowIDReusePolicy.REJECT_DUPLICATE,
    )
    print(f"Started workflow_id={handle.id} run_id={handle.first_execution_run_id}")
    if args.wait:
        result = await handle.result()
        import json
        print(json.dumps(result, indent=2, default=str))

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--temporal-address", default=os.getenv("TEMPORAL_ADDRESS", "127.0.0.1:7233"))
    parser.add_argument("--namespace", default=os.getenv("TEMPORAL_NAMESPACE", "default"))
    parser.add_argument("--service", default="sample-api")
    parser.add_argument("--description", default="Investigate simulated API latency/error increase")
    parser.add_argument("--incident-id")
    parser.add_argument("--window-seconds", type=int, default=900)
    parser.add_argument("--start-unix", type=int)
    parser.add_argument("--end-unix", type=int)
    parser.add_argument("--wait", action="store_true")
    asyncio.run(main(parser.parse_args()))
