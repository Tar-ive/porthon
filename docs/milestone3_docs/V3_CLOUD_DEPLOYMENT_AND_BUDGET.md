# V3 Cloud Deployment and Budget (Cloud Run)

Last updated: 2026-03-05

This runbook deploys the backend to Google Cloud Run with a public HTTPS endpoint for event intake, persistent runtime state, and an explicit monthly cost/runway model.

## 1) Target architecture

- Runtime: Cloud Run service (`gen2`), `min=1`, `max-instances=1`, `--no-cpu-throttling` (always-on agent loop).
- Public URL: default Cloud Run `https://<service>-<hash>-<region>.run.app`.
- Secrets: Secret Manager, injected into Cloud Run env at deploy time.
- State persistence: Cloud Storage bucket mounted into the container (`type=cloud-storage`) and used for `runtime_state.json`.
- Event ingress: public `POST /v1/figma/webhooks` with passcode verification.
- Control plane: bearer-auth API routes for mutations/reads outside webhook and health paths.

Why single instance now:
- Runtime state is JSON-file backed, so single-writer avoids cross-instance write races.

## 2) One-time Google Cloud setup

Set variables:

```bash
export PROJECT_ID="your-gcp-project"
export REGION="us-central1"
export SERVICE="porthon-backend"
export SA_NAME="porthon-runner"
export SA_EMAIL="${SA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"
export STATE_BUCKET="${PROJECT_ID}-porthon-state"
```

Enable required APIs:

```bash
gcloud config set project "$PROJECT_ID"
gcloud services enable \
  run.googleapis.com \
  cloudbuild.googleapis.com \
  artifactregistry.googleapis.com \
  secretmanager.googleapis.com \
  storage.googleapis.com
```

Create service account:

```bash
gcloud iam service-accounts create "$SA_NAME" \
  --display-name="Porthon Cloud Run Runtime"
```

Create state bucket:

```bash
gcloud storage buckets create "gs://${STATE_BUCKET}" --location="$REGION"
```

Grant runtime permissions:

```bash
gcloud projects add-iam-policy-binding "$PROJECT_ID" \
  --member="serviceAccount:${SA_EMAIL}" \
  --role="roles/secretmanager.secretAccessor"

gcloud storage buckets add-iam-policy-binding "gs://${STATE_BUCKET}" \
  --member="serviceAccount:${SA_EMAIL}" \
  --role="roles/storage.objectAdmin"
```

## 3) Secret Manager setup

Create secrets once:

```bash
for s in FIGMA_API_KEY FIGMA_WEBHOOK_PASSCODE NOTION_INTEGRATION_SECRET NOTION_WEBHOOK_VERIFICATION_TOKEN PORTTHON_API_KEYS OPENAI_API_KEY; do
  gcloud secrets create "$s" --replication-policy="automatic" || true
done
```

Add secret values (repeat as needed for rotation):

```bash
printf '%s' "$FIGMA_API_KEY" | gcloud secrets versions add FIGMA_API_KEY --data-file=-
printf '%s' "$FIGMA_WEBHOOK_PASSCODE" | gcloud secrets versions add FIGMA_WEBHOOK_PASSCODE --data-file=-
printf '%s' "$NOTION_INTEGRATION_SECRET" | gcloud secrets versions add NOTION_INTEGRATION_SECRET --data-file=-
printf '%s' "$NOTION_WEBHOOK_VERIFICATION_TOKEN" | gcloud secrets versions add NOTION_WEBHOOK_VERIFICATION_TOKEN --data-file=-
printf '%s' "$PORTTHON_API_KEYS" | gcloud secrets versions add PORTTHON_API_KEYS --data-file=-
printf '%s' "$OPENAI_API_KEY" | gcloud secrets versions add OPENAI_API_KEY --data-file=-
```

`PORTTHON_API_KEYS` format:
- comma-separated keys, e.g. `sk_live_ops_abc,sk_live_ci_xyz`

## 4) Deploy command (source deploy)

From repo root:

```bash
gcloud run deploy "$SERVICE" \
  --source=src/backend \
  --region="$REGION" \
  --service-account="$SA_EMAIL" \
  --allow-unauthenticated \
  --execution-environment=gen2 \
  --min=1 \
  --max-instances=1 \
  --no-cpu-throttling \
  --set-env-vars=PORTTHON_OFFLINE_MODE=0,AGENT_TICK_SECONDS=900,RUNTIME_STATE_PATH=/app/state/runtime_state.json,PORTTHON_REQUIRE_AUTH=true \
  --set-secrets=FIGMA_API_KEY=FIGMA_API_KEY:latest,FIGMA_WEBHOOK_PASSCODE=FIGMA_WEBHOOK_PASSCODE:latest,NOTION_INTEGRATION_SECRET=NOTION_INTEGRATION_SECRET:latest,NOTION_WEBHOOK_VERIFICATION_TOKEN=NOTION_WEBHOOK_VERIFICATION_TOKEN:latest,PORTTHON_API_KEYS=PORTTHON_API_KEYS:latest,OPENAI_API_KEY=OPENAI_API_KEY:latest \
  --add-volume=name=runtime-state,type=cloud-storage,bucket="$STATE_BUCKET" \
  --add-volume-mount=volume=runtime-state,mount-path=/app/state
```

Get service URL:

```bash
gcloud run services describe "$SERVICE" --region="$REGION" --format='value(status.url)'
```

Use the returned `run.app` URL for Figma webhook endpoint:
- `https://<service-url>/v1/figma/webhooks`

## 5) API exposure policy (required for production)

Because Figma must call your endpoint without Google IAM tokens, the service is deployed with unauthenticated ingress. Protect API surface as follows:

- Keep these public:
  - `GET /v1/health`
  - `POST /v1/figma/webhooks`
  - `POST /v1/notion/webhooks` (plus compatibility aliases `/notion/webhooks` and `/`)
  - `/docs`, `/openapi.json` (optional)
- Require bearer API key for all other `/v1/*` routes.

If this policy is not enforced in app code yet, treat rollout as incomplete for production data.

## 6) Post-deploy verification

Assume:

```bash
export BASE_URL="https://<service-url>"
export API_KEY="sk_live_ops_xxx"
```

Health:

```bash
curl -s "${BASE_URL}/v1/health"
```

Non-webhook endpoint should reject missing auth:

```bash
curl -i "${BASE_URL}/v1/runtime"
```

Authenticated call should succeed:

```bash
curl -s "${BASE_URL}/v1/runtime" \
  -H "Authorization: Bearer ${API_KEY}"
```

Webhook passcode rejection check:

```bash
curl -i -X POST "${BASE_URL}/v1/figma/webhooks" \
  -H "Content-Type: application/json" \
  -d '{"event_type":"FILE_COMMENT","passcode":"wrong"}'
```

Webhook wiring smoke test:
- Create watcher (`POST /v1/figma/watchers`) with auth.
- Post a valid comment event.
- Confirm queue via `GET /v1/figma/comments/pending` with auth.

Persistence smoke test:
- Create watcher.
- Deploy new revision.
- Verify watcher still exists after restart.

## 7) Monthly budget forecast (as of 2026-03-05)

### Baseline assumptions

- Region: `us-central1` (Tier 1).
- Billing mode: instance-based (`--no-cpu-throttling`).
- Instance shape: default `1 vCPU`, `512 MiB` memory.
- 30-day month (`2,592,000` seconds).
- Excludes upstream vendor spend (OpenAI/Notion/Figma).

### Cloud Run compute estimate

Using Cloud Run services instance-based pricing and free tier:
- CPU rate: `$0.000018` per vCPU-second.
- Memory rate: `$0.000002` per GiB-second.
- Free tier: `240,000` vCPU-seconds, `450,000` GiB-seconds.

Computation:
- CPU billable: `2,592,000 - 240,000 = 2,352,000`
- CPU cost: `2,352,000 * 0.000018 = $42.34`
- Memory billable: `(2,592,000 * 0.5) - 450,000 = 846,000`
- Memory cost: `846,000 * 0.000002 = $1.69`
- Cloud Run subtotal: `$44.03 / month`

### Other monthly components (typical)

- Secret Manager: usually near `$0` when staying within free 6 active versions and 10k accesses.
- Cloud Build: often `$0` within 2,500 free build-minutes/month.
- Artifact Registry: first `0.5 GB` free; above that `$0.10/GB-month`.
- Cloud Logging: first `50 GiB/project/month` free; then `$0.50/GiB`.
- Cloud Storage state bucket: typically low single-digit dollars or less for this footprint.

### Practical monthly range

- Lean: `$44–$47`
- Expected: `$45–$55`
- Heavy logging/build churn: `$60–$90`

## 8) Runway with $280 remaining credits

Credit-only runway (ignoring expiry date):

- At `$45/month`: `280 / 45 = 6.22 months`
- At `$55/month`: `280 / 55 = 5.09 months`

Practical answer:
- About `5 to 6 months` on this always-on configuration.

Important cap:
- If these are Free Trial credits, they expire after `90 days` from signup, even if balance remains.

## 9) Cost controls to apply immediately

- Billing budget alerts at `$20`, `$35`, `$45`, `$55`, and `$75`.
- Keep `max-instances=1` until you move state out of JSON storage.
- Add log exclusions for noisy success-path logs.
- Configure Artifact Registry cleanup policy (keep last N images).
- Rotate secrets without accumulating excessive active versions.
- Review monthly:
  - Cloud Run vCPU-seconds and GiB-seconds.
  - Logging ingestion volume.
  - Build minute usage.
  - Remaining credits and expiry date.

## 10) References

- Cloud Run pricing: https://cloud.google.com/run/pricing
- Cloud Run billing settings (`--no-cpu-throttling`): https://cloud.google.com/run/docs/configuring/cpu-allocation
- Cloud Run auth overview: https://cloud.google.com/run/docs/authenticating/overview
- Cloud Run secrets: https://cloud.google.com/run/docs/configuring/services/secrets
- Cloud Run Cloud Storage mounts: https://cloud.google.com/run/docs/configuring/services/cloud-storage-volume-mounts
- Secret Manager pricing: https://cloud.google.com/secret-manager/pricing
- Cloud Build pricing: https://cloud.google.com/build/pricing
- Artifact Registry pricing: https://cloud.google.com/artifact-registry/pricing
- Cloud Logging pricing: https://cloud.google.com/stackdriver/pricing
- Google Cloud Free Program / trial duration: https://docs.cloud.google.com/free/docs/free-cloud-features
