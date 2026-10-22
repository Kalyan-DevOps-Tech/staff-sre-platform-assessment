"""Temporal worker: a durable workflow that calls the read-only AI SRE analyzer."""
import asyncio, os
from datetime import timedelta
from temporalio import activity, workflow

# httpx is used by the activity, not by workflow execution.
with workflow.unsafe.imports_passed_through():
    import httpx
from temporalio.client import Client
from temporalio.common import RetryPolicy
from temporalio.worker import Worker
AGENT_URL=os.getenv("AI_SRE_AGENT_URL","http://ai-sre-agent.apps.svc.cluster.local:8081")
@activity.defn
async def analyze_incident(payload: dict) -> dict:
    async with httpx.AsyncClient(timeout=30) as client:
        response=await client.post(AGENT_URL.rstrip("/")+"/analyze",json=payload); response.raise_for_status(); return response.json()
@workflow.defn
class IncidentAnalysisWorkflow:
    @workflow.run
    async def run(self, payload: dict) -> dict:
        return await workflow.execute_activity(analyze_incident, payload, start_to_close_timeout=timedelta(seconds=45), retry_policy=RetryPolicy(maximum_attempts=3, initial_interval=timedelta(seconds=2)))
async def main():
    address=os.getenv("TEMPORAL_ADDRESS","temporal-frontend.platform.svc.cluster.local:7233")
    client=await Client.connect(address,namespace=os.getenv("TEMPORAL_NAMESPACE","default"))
    worker=Worker(client,task_queue="sre-incident-analysis",workflows=[IncidentAnalysisWorkflow],activities=[analyze_incident])
    await worker.run()
if __name__=="__main__": asyncio.run(main())
