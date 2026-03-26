"""Simulated system signals for the Incident Runbook Agent.

In production, these would come from Prometheus, PagerDuty, Datadog, etc.
For learning, we simulate 12 realistic incident scenarios.
"""

from __future__ import annotations

import time
import uuid
from enum import StrEnum

from pydantic import BaseModel, Field


class Severity(StrEnum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class Alert(BaseModel):
    """A simulated system alert."""

    alert_id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    severity: Severity
    source: str
    message: str
    metrics: dict[str, float] = Field(default_factory=dict)
    timestamp: float = Field(default_factory=time.time)
    labels: dict[str, str] = Field(default_factory=dict)


def generate_incidents() -> list[Alert]:
    """Return a set of predefined incident scenarios for testing."""
    return [
        Alert(
            severity=Severity.CRITICAL,
            source="prometheus",
            message="CPU usage above 95% on api-server-01 for 10 minutes",
            metrics={"cpu_percent": 97.2},
            labels={"host": "api-server-01", "service": "api"},
        ),
        Alert(
            severity=Severity.ERROR,
            source="prometheus",
            message="Disk usage above 90% on db-primary-01",
            metrics={"disk_percent": 93.5},
            labels={"host": "db-primary-01", "service": "database"},
        ),
        Alert(
            severity=Severity.CRITICAL,
            source="pagerduty",
            message="Memory usage at 98% on worker-03, OOM killer active",
            metrics={"memory_percent": 98.1},
            labels={"host": "worker-03", "service": "worker"},
        ),
        Alert(
            severity=Severity.ERROR,
            source="datadog",
            message="Service response time p99 above 5s for payment-service",
            metrics={"p99_latency_ms": 5200},
            labels={"service": "payment"},
        ),
        Alert(
            severity=Severity.WARNING,
            source="prometheus",
            message="Error rate above 5% on auth-service",
            metrics={"error_rate_percent": 7.3},
            labels={"service": "auth"},
        ),
        Alert(
            severity=Severity.CRITICAL,
            source="certmanager",
            message="TLS certificate for api.example.com expires in 2 days",
            metrics={"days_until_expiry": 2},
            labels={"domain": "api.example.com"},
        ),
        Alert(
            severity=Severity.ERROR,
            source="postgres",
            message="Connection pool exhausted on db-primary-01, 0 available connections",
            metrics={"available_connections": 0, "max_connections": 100},
            labels={"host": "db-primary-01"},
        ),
        Alert(
            severity=Severity.WARNING,
            source="kubernetes",
            message="Pod restart count above threshold: recommendation-service (12 restarts in 1 hour)",
            metrics={"restart_count": 12},
            labels={"service": "recommendation", "namespace": "production"},
        ),
        Alert(
            severity=Severity.ERROR,
            source="cloudwatch",
            message="Lambda function timeout rate above 10% for data-pipeline-etl",
            metrics={"timeout_rate_percent": 14.2},
            labels={"function": "data-pipeline-etl"},
        ),
        Alert(
            severity=Severity.CRITICAL,
            source="prometheus",
            message="No heartbeat from cache-redis-01 for 120 seconds",
            metrics={"seconds_since_heartbeat": 120},
            labels={"host": "cache-redis-01", "service": "cache"},
        ),
        Alert(
            severity=Severity.WARNING,
            source="grafana",
            message="Anomalous traffic spike detected: 3x normal request volume on api-gateway",
            metrics={"request_multiplier": 3.2},
            labels={"service": "api-gateway"},
        ),
        Alert(
            severity=Severity.INFO,
            source="kubernetes",
            message="Rolling deployment completed for user-service v2.4.1",
            metrics={},
            labels={"service": "user-service", "version": "2.4.1"},
        ),
    ]
