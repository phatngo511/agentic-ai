"""Runbook search for the Incident Runbook Agent.

Stores predefined runbooks and retrieves the best match for an alert.
Uses vector similarity (same as DocumentIndex) but over runbook symptoms.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

import chromadb
from chromadb.config import Settings as ChromaSettings


class RunbookStep(BaseModel):
    """A single step in a remediation runbook."""
    order: int
    action: str
    description: str
    risk_level: str = "low"
    requires_approval: bool = False


class Runbook(BaseModel):
    """A complete runbook with symptoms and remediation steps."""
    id: str
    title: str
    symptoms: str
    steps: list[RunbookStep]
    risk_level: str = "medium"
    tags: list[str] = Field(default_factory=list)


class RunbookMatch(BaseModel):
    """A runbook match result with relevance score."""
    runbook: Runbook
    relevance_score: float


class RunbookIndex:
    """Vector index for runbook retrieval."""

    def __init__(self, collection_name: str = "runbooks"):
        self._client = chromadb.Client(ChromaSettings(anonymized_telemetry=False))
        self._collection = self._client.get_or_create_collection(
            name=collection_name, metadata={"hnsw:space": "cosine"}
        )
        self._runbooks: dict[str, Runbook] = {}

    def add_runbooks(self, runbooks: list[Runbook]) -> None:
        for rb in runbooks:
            self._runbooks[rb.id] = rb
        self._collection.add(
            ids=[rb.id for rb in runbooks],
            documents=[rb.symptoms for rb in runbooks],
            metadatas=[{"title": rb.title, "risk_level": rb.risk_level} for rb in runbooks],
        )

    def search(self, alert_text: str, top_k: int = 3) -> list[RunbookMatch]:
        if not self._runbooks:
            return []
        results = self._collection.query(
            query_texts=[alert_text],
            n_results=min(top_k, len(self._runbooks)),
        )
        matches = []
        for i, rb_id in enumerate(results["ids"][0]):
            if rb_id in self._runbooks:
                distance = results["distances"][0][i] if results.get("distances") else 0.0
                matches.append(RunbookMatch(
                    runbook=self._runbooks[rb_id],
                    relevance_score=1.0 - distance,
                ))
        return matches

    def clear(self) -> None:
        self._client.delete_collection(self._collection.name)
        self._collection = self._client.get_or_create_collection(
            name=self._collection.name, metadata={"hnsw:space": "cosine"}
        )
        self._runbooks.clear()


def get_default_runbooks() -> list[Runbook]:
    """Return predefined runbooks for common incidents."""
    return [
        Runbook(id="rb-cpu-high", title="High CPU Usage", symptoms="CPU usage above 90% sustained for more than 5 minutes", risk_level="medium", tags=["cpu", "performance"],
            steps=[
                RunbookStep(order=1, action="identify_process", description="Identify top CPU-consuming processes with top/htop", risk_level="low"),
                RunbookStep(order=2, action="check_logs", description="Check application logs for errors or loops", risk_level="low"),
                RunbookStep(order=3, action="restart_service", description="Restart the affected service if process is stuck", risk_level="medium", requires_approval=True),
                RunbookStep(order=4, action="scale_out", description="Scale out horizontally if load is legitimate", risk_level="medium", requires_approval=True),
            ]),
        Runbook(id="rb-disk-full", title="Disk Space Critical", symptoms="Disk usage above 85% or approaching full", risk_level="high", tags=["disk", "storage"],
            steps=[
                RunbookStep(order=1, action="identify_large_files", description="Find large files and directories with du -sh", risk_level="low"),
                RunbookStep(order=2, action="clear_logs", description="Rotate and compress old log files", risk_level="low"),
                RunbookStep(order=3, action="clear_temp", description="Remove temporary and cache files", risk_level="medium", requires_approval=True),
                RunbookStep(order=4, action="expand_volume", description="Expand disk volume if cleanup is insufficient", risk_level="high", requires_approval=True),
            ]),
        Runbook(id="rb-memory-oom", title="Memory Exhaustion / OOM", symptoms="Memory usage above 95% or OOM killer active", risk_level="critical", tags=["memory", "oom"],
            steps=[
                RunbookStep(order=1, action="identify_leak", description="Check for memory leaks with process memory tracking", risk_level="low"),
                RunbookStep(order=2, action="restart_service", description="Restart the service to free memory", risk_level="high", requires_approval=True),
                RunbookStep(order=3, action="increase_limits", description="Increase memory limits if workload is legitimate", risk_level="medium", requires_approval=True),
            ]),
        Runbook(id="rb-latency-high", title="High Service Latency", symptoms="Service response time p99 above SLA threshold", risk_level="medium", tags=["latency", "performance"],
            steps=[
                RunbookStep(order=1, action="check_dependencies", description="Check downstream service health and latency", risk_level="low"),
                RunbookStep(order=2, action="check_database", description="Check database query performance and connection pool", risk_level="low"),
                RunbookStep(order=3, action="scale_service", description="Scale up the service if load is the cause", risk_level="medium", requires_approval=True),
            ]),
        Runbook(id="rb-error-rate", title="Elevated Error Rate", symptoms="Error rate above threshold for a service", risk_level="medium", tags=["errors", "reliability"],
            steps=[
                RunbookStep(order=1, action="check_logs", description="Review error logs for patterns and root cause", risk_level="low"),
                RunbookStep(order=2, action="check_deployment", description="Check if a recent deployment correlates with error spike", risk_level="low"),
                RunbookStep(order=3, action="rollback", description="Rollback to previous version if deployment is the cause", risk_level="high", requires_approval=True),
            ]),
        Runbook(id="rb-cert-expiry", title="TLS Certificate Expiring", symptoms="TLS certificate expires within 7 days", risk_level="high", tags=["security", "tls", "certificate"],
            steps=[
                RunbookStep(order=1, action="verify_cert", description="Verify certificate details and expiry date", risk_level="low"),
                RunbookStep(order=2, action="renew_cert", description="Trigger certificate renewal via cert-manager or ACME", risk_level="medium", requires_approval=True),
                RunbookStep(order=3, action="verify_renewal", description="Verify new certificate is deployed and valid", risk_level="low"),
            ]),
        Runbook(id="rb-db-connections", title="Database Connection Pool Exhausted", symptoms="Database connection pool at capacity, no available connections", risk_level="high", tags=["database", "connections"],
            steps=[
                RunbookStep(order=1, action="identify_holders", description="Identify which services hold the most connections", risk_level="low"),
                RunbookStep(order=2, action="kill_idle", description="Terminate idle connections older than threshold", risk_level="medium", requires_approval=True),
                RunbookStep(order=3, action="increase_pool", description="Increase max connection pool size if load is legitimate", risk_level="medium", requires_approval=True),
            ]),
        Runbook(id="rb-pod-crashloop", title="Pod CrashLoopBackOff", symptoms="Pod restarting repeatedly in Kubernetes", risk_level="medium", tags=["kubernetes", "pod", "restart"],
            steps=[
                RunbookStep(order=1, action="check_logs", description="Check pod logs for crash reason", risk_level="low"),
                RunbookStep(order=2, action="describe_pod", description="Run kubectl describe pod to check events", risk_level="low"),
                RunbookStep(order=3, action="check_resources", description="Verify resource limits are not too restrictive", risk_level="low"),
                RunbookStep(order=4, action="rollback_deployment", description="Rollback deployment if recent change caused crashes", risk_level="medium", requires_approval=True),
            ]),
        Runbook(id="rb-cache-down", title="Cache Service Down", symptoms="Cache service not responding or heartbeat lost", risk_level="critical", tags=["cache", "redis", "availability"],
            steps=[
                RunbookStep(order=1, action="check_status", description="Check cache service status and logs", risk_level="low"),
                RunbookStep(order=2, action="restart_cache", description="Restart cache service", risk_level="high", requires_approval=True),
                RunbookStep(order=3, action="failover", description="Failover to replica if primary is unrecoverable", risk_level="critical", requires_approval=True),
            ]),
        Runbook(id="rb-traffic-spike", title="Abnormal Traffic Spike", symptoms="Unexpected increase in request volume, possible DDoS or legitimate surge", risk_level="medium", tags=["traffic", "scaling", "security"],
            steps=[
                RunbookStep(order=1, action="analyze_traffic", description="Analyze traffic patterns to distinguish legitimate from malicious", risk_level="low"),
                RunbookStep(order=2, action="enable_rate_limiting", description="Enable or tighten rate limiting", risk_level="medium", requires_approval=True),
                RunbookStep(order=3, action="scale_infra", description="Scale infrastructure if traffic is legitimate", risk_level="medium", requires_approval=True),
            ]),
    ]
