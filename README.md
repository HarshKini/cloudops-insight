# CloudOps Insight — AI‑Powered Observability on AWS (Ephemeral / Low‑Cost Demo)

Real-time Kubernetes metrics (Prometheus + Grafana) with a FastAPI service that turns raw data into plain‑English **rightsizing hints**. Built to be spun up briefly for demos, capture screenshots, and **torn down to avoid cost**. Automated with **Terraform, Docker, Helm, Chef, and GitHub Actions**.

---

## Highlights
- **End‑to‑end DevOps**: Terraform (infra) → Chef (bootstrap) → Helm (observability) → FastAPI (app) → **GitHub Actions** (CI/CD).
- **Actionable insights**: `/insights/now` returns CPU/Mem/Disk plus practical rightsizing guidance.
- **Ephemeral**: Bring up for ~30–60 minutes, take screenshots, then destroy to minimize spend.
- **Reproducible**: One command bootstrap on a fresh EC2 host; CI deploys per-commit with safe rollouts.

---

## Architecture (single EC2 demo)

```
GitHub → Actions → Docker Hub
                 │
             (image tag)
                 │
AWS EC2 (k3s) ── Prometheus + Grafana (Helm)
     │                        │
  AI Insights (FastAPI) ←── Prometheus HTTP API
     │
  NodePort 32123 → /healthz, /insights/now
Grafana NodePort 32000 → dashboards
```

> For long‑running or production use, replace NodePorts with **Ingress + TLS** and lock down Security Groups.

---

## Repo Structure

```
infra/terraform/                       # EC2, SG, IAM, (optional S3)
app/ai-insights/                       # FastAPI service + Dockerfile
k8s/manifests/                         # K8s manifests (if applying without Chef)
chef/cookbooks/cloudops_setup/         # Chef cookbook (bootstrap everything)
.github/workflows/ci-cd.yml            # CI/CD: build & deploy
README.md
```

---

## Prerequisites
- AWS account + key pair
- Ubuntu 22.04 EC2 instance with outbound internet
- Docker Hub account (example: `hunter1994`)
- GitHub repository with Actions enabled
- Local machine: WSL/Ubuntu/macOS/Linux

---

## One‑Time Setup

### 1) Docker Hub
Create an **access token** for CI (Account → Security → New Access Token).

### 2) GitHub Secrets (Repo → Settings → Secrets and variables → Actions)
```
DOCKERHUB_USERNAME = <your-dockerhub-username>
DOCKERHUB_TOKEN    = <dockerhub-access-token>
EC2_HOST           = <ec2-public-ip>
EC2_USER           = ubuntu
EC2_SSH_KEY        = <contents-of-your-ssh-private-key>
```

### 3) CI/CD Workflow
`/.github/workflows/ci-cd.yml` builds and pushes images (`latest` + commit SHA), then SSHes to EC2 and runs:
```
export KUBECONFIG=/etc/rancher/k3s/k3s.yaml
kubectl -n cloudops set image deployment/ai-insights ai-insights=${DOCKERHUB_USERNAME}/cloudops-ai-insights:${GITHUB_SHA}
kubectl -n cloudops rollout status deployment/ai-insights
```

> The application Deployment includes readiness & liveness probes so NodePort isn’t served until the container is ready.

---

## Spin‑Up (Ephemeral Demo Flow)

> Goal: run for 30–60 minutes, capture screenshots, then tear down.

### 0) Optional: Provision EC2 via Terraform
```bash
cd infra/terraform
terraform init
terraform apply
# copy the EC2 public IP from outputs
```

### 1) SSH to EC2 and Bootstrap with Chef
```bash
# On EC2 instance
sudo CHEF_LICENSE=accept-silent chef-client -z -c /etc/chef/client.rb -o 'recipe[cloudops_setup::default]'
# Installs docker, helm, k3s, kube-prometheus-stack, and applies the app
```

### 2) Make kubectl Persistent (EC2)
```bash
mkdir -p ~/.kube && sudo cp /etc/rancher/k3s/k3s.yaml ~/.kube/config && chmod 600 ~/.kube/config
```

### 3) Verify
```bash
kubectl -n cloudops get deploy,po,svc
curl -sS "http://<EC2_PUBLIC_IP>:32123/healthz"
curl -sS "http://<EC2_PUBLIC_IP>:32123/insights/now" | jq
# Grafana: http://<EC2_PUBLIC_IP>:32000  (admin / <your-password>)
```

### 4) CI/CD (optional, recommended)
Commit a tiny change in `app/ai-insights/main.py` to trigger the pipeline. The Deploy step sets the image to the **commit SHA** and waits for rollout.

---

## What to Screenshot (for Portfolio/LinkedIn)
1. **GitHub Actions run** (build & deploy → success).
2. **Docker Hub**: repository with `latest` and SHA tags.
3. **kubectl**: `kubectl -n cloudops get deploy,po,svc` (mask IPs if desired).
4. **Insights API JSON** from `/insights/now` (showing rightsizing hint).
5. **Grafana**: home screen + a dashboard (e.g., *Node Exporter Full* #1860).

> Tip: blur/black out public IPs before posting publicly.

---

## Tear‑Down (Avoid Ongoing Costs)
- If created by Terraform:
  ```bash
  cd infra/terraform
  terraform destroy
  ```
- If created manually: terminate the EC2 instance in AWS console.
- Optional pre-cleanup on EC2:
  ```bash
  /usr/local/bin/k3s-uninstall.sh || true
  ```

---

## Day‑2 Operations (when environment is up)

```bash
# Namespace status
kubectl -n cloudops get deploy,po,svc

# Logs & debug
kubectl -n cloudops logs deploy/ai-insights --tail=100
kubectl -n cloudops get endpoints ai-insights

# Manual image change (if needed)
kubectl -n cloudops set image deploy/ai-insights ai-insights=<user>/cloudops-ai-insights:<tag>
kubectl -n cloudops rollout status deploy/ai-insights
```

### Probes (already configured)
```yaml
readinessProbe: { httpGet: { path: /healthz, port: 8000 }, initialDelaySeconds: 3, periodSeconds: 5 }
livenessProbe:  { httpGet: { path: /healthz, port: 8000 }, initialDelaySeconds: 5, periodSeconds: 10 }
```

---

## Security / Hardening
- Restrict Security Group to your `/32` for SSH and web.
- Rotate Grafana admin password via Chef attributes and re‑converge.
- Replace NodePorts with **Ingress + cert-manager** for HTTPS if running longer than a demo.
- Store sensitive values in GitHub Secrets; avoid committing credentials.

---

## Troubleshooting
- **kubectl uses localhost:8080** → `export KUBECONFIG=~/.kube/config` on EC2.
- **Helm cannot reach cluster** → ensure `export KUBECONFIG=/etc/rancher/k3s/k3s.yaml` inside automation.
- **ImagePullBackOff** → verify the image exists and is public (`docker pull <image>`).
- **Connection refused during rollout** → probes avoid this; wait for `rollout status` to complete.

---

## Roadmap / Extensions
- Ingress + TLS + auth
- HPA (CPU) + demo load
- Alerts (PrometheusRule) + Alertmanager
- AWS Cost Explorer integration

---

### Credits
Built by **Harsh Kini** (GitHub: `HarshKini`). Docker Hub user used in this project: `hunter1994`.
