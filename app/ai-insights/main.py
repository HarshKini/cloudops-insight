import os
import requests
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any

PROM_URL = os.getenv("PROM_URL", "http://localhost:9090")

app = FastAPI(title="CloudOps AI Insights", version="0.1.0")

class Insight(BaseModel):
    title: str
    severity: str  # info|warning|critical
    description: str
    recommendations: List[str]

class InsightResponse(BaseModel):
    status: str
    insights: List[Insight]
    raw: Dict[str, Any]

def q(query: str) -> float:
    """Run a Prometheus instant query and return the first scalar/vector value as float."""
    try:
        r = requests.get(f"{PROM_URL}/api/v1/query", params={"query": query}, timeout=8)
        r.raise_for_status()
        data = r.json()
        if data.get("status") != "success":
            return float("nan")
        result = data["data"]["result"]
        if not result:
            return float("nan")
        # take the first sample’s value
        val = result[0].get("value") or result[0].get("values", [None])[-1]
        return float(val[1])
    except Exception:
        return float("nan")

def safe(v, default=float("nan")):
    return v if isinstance(v, (int, float)) else default

@app.get("/healthz")
def healthz():
    return {"ok": True, "prom": PROM_URL}

@app.get("/insights/now", response_model=InsightResponse)
def insights_now():
    # Node-wide (%). Requires node-exporter (installed by kube-prometheus-stack).
    cpu_query = '100 - (avg by (instance) (rate(node_cpu_seconds_total{mode="idle"}[5m])) * 100)'
    mem_query = '100 * (1 - (avg by (instance) (node_memory_MemAvailable_bytes) / avg by (instance) (node_memory_MemTotal_bytes)))'
    disk_query = '100 - (avg by (instance) (node_filesystem_avail_bytes{fstype!~"tmpfs|overlay",mountpoint="/"} / node_filesystem_size_bytes{fstype!~"tmpfs|overlay",mountpoint="/"} * 100))'

    cpu = safe(q(cpu_query))
    mem = safe(q(mem_query))
    disk = safe(q(disk_query))

    insights: List[Insight] = []

    # Simple “AI-like” rules (transparent and recruiter-friendly)
    # You’ll extend these later; for now, they’re crisp and useful.
    if cpu != cpu:  # NaN check
        insights.append(Insight(
            title="No CPU metrics",
            severity="warning",
            description="Prometheus query returned no CPU data. Node exporter or scrape config may be missing.",
            recommendations=[
                "Verify kube-prometheus-stack is installed and node-exporter is running.",
                "Check Prometheus targets page for scrape errors."
            ],
        ))
    else:
        if cpu > 85:
            insights.append(Insight(
                title=f"High CPU usage ({cpu:.1f}%)",
                severity="critical",
                description="Sustained CPU > 85% can cause throttling and latency.",
                recommendations=[
                    "Scale up EC2 instance (t3.medium → t3.large) or add a node.",
                    "Enable HPA for busy workloads (target 60–70% CPU)."
                ],
            ))
        elif cpu < 20:
            insights.append(Insight(
                title=f"Low CPU headroom ({cpu:.1f}%)",
                severity="info",
                description="CPU usage is consistently low—over-provisioning likely.",
                recommendations=[
                    "Consider downsizing to t3.small or t3.micro to save cost.",
                    "Consolidate low-traffic workloads."
                ],
            ))

    if mem != mem:
        insights.append(Insight(
            title="No Memory metrics",
            severity="warning",
            description="Prometheus query returned no Memory data.",
            recommendations=["Confirm node-exporter and proper scrape configs."],
        ))
    else:
        if mem > 85:
            insights.append(Insight(
                title=f"High Memory usage ({mem:.1f}%)",
                severity="critical",
                description="Memory pressure increases OOM risk.",
                recommendations=[
                    "Increase instance memory (t3.medium→t3.large).",
                    "Tune pod requests/limits; enable VPA if appropriate."
                ],
            ))
        elif mem < 30:
            insights.append(Insight(
                title=f"Low Memory usage ({mem:.1f}%)",
                severity="info",
                description="Plenty of unused memory—potential cost optimization.",
                recommendations=[
                    "Downsize instance or pack more workloads.",
                    "Reduce pod memory limits if set too high."
                ],
            ))

    if disk != disk:
        insights.append(Insight(
            title="No Disk metrics",
            severity="warning",
            description="Prometheus query returned no Disk data for '/'.",
            recommendations=["Verify node-exporter mount points and filesystem metrics."],
        ))
    else:
        if disk > 80:
            insights.append(Insight(
                title=f"Disk usage high ({disk:.1f}%)",
                severity="critical",
                description="Running low on disk can crash pods and databases.",
                recommendations=[
                    "Expand root volume (gp3) from 30GB to 50GB+, then grow FS.",
                    "Prune images and old logs; add retention policies."
                ],
            ))
        elif disk < 50:
            insights.append(Insight(
                title=f"Disk usage healthy ({disk:.1f}%)",
                severity="info",
                description="No immediate storage pressure.",
                recommendations=["Keep image pruning and log rotation in place."],
            ))

    # Tiny cost heuristic (static—for demo; you’ll tie Cost Explorer later)
    # t3.medium ~ $0.0416/hr; t3.small ~ $0.0208/hr (Mumbai rough ballpark)
    cost_hint = Insight(
        title="Cost heuristic",
        severity="info",
        description="Approximate instance rightsizing suggestion based on CPU/Memory.",
        recommendations=[
            "If CPU<20% and Mem<30% for 24h: consider t3.small (~50% cheaper).",
            "If CPU>85% or Mem>85% often: consider t3.large or add a node."
        ],
    )
    insights.append(cost_hint)

    return InsightResponse(
        status="ok",
        insights=insights,
        raw={"cpu_pct": cpu, "mem_pct": mem, "disk_pct": disk}
    )
