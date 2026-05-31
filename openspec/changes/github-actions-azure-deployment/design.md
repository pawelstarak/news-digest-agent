## Context

The news-digest-agent is a Python Azure Functions app (v4 programming model) with a single timer-triggered function that fires daily at 6 AM UTC. Currently there is no deployment pipeline; publishing requires a developer to run `func azure functionapp publish <app-name>` manually from their machine with the Azure CLI and the right credentials. The goal is to automate this via GitHub Actions so every merge to `main` triggers a deployment.

## Goals / Non-Goals

**Goals:**

- Automatically deploy to Azure Functions on every push to `main`
- Keep credentials out of the repository (use GitHub secrets)
- Authenticate with least privilege, no long-lived secrets
- Install Python dependencies via remote build (Oryx) on the Azure side

**Non-Goals:**

- Pull request preview environments or staging slots
- Running tests in CI (no test suite exists yet)
- Multi-environment promotion (dev → staging → prod)
- Infrastructure provisioning (Function App must already exist in Azure)

## Decisions

### OIDC (federated identity) over publish profile

**Decision:** Authenticate via `azure/login@v2` with OIDC using an Entra ID app registration, replacing the publish profile approach.

**Rationale:** `azure/functions-action@v1` with a publish profile always updates `SCM_DO_BUILD_DURING_DEPLOYMENT` and `ENABLE_ORYX_BUILD` as Kudu app settings before every deploy. This triggers a Kudu container restart; with 20 retries at ~15 s each the deployment times out before the container recovers, making every deploy fail. OIDC with `az functionapp deploy` bypasses Kudu app-setting manipulation entirely — it does a direct zip deploy via the ARM API with no restart side-effect. OIDC also has no expiry (unlike publish profiles) and is the approach Microsoft now recommends.

**Alternative considered:** Pre-seeding both app settings as permanent portal values so `azure/functions-action` detects no change and skips the write. Fragile — depends on manual portal state staying in sync with the workflow.

### `az functionapp deploy` over `azure/functions-action`

**Decision:** Use `az functionapp deploy --type zip --build-remote true` instead of the `azure/functions-action` action.

**Rationale:** The action wraps the Kudu API and carries the app-setting manipulation baggage described above. `az functionapp deploy` uses the ARM control-plane zip deploy endpoint, which does not touch app settings and does not cause a Kudu restart. `--build-remote true` instructs Oryx to install `requirements.txt` server-side.

### Remote build via Oryx

**Decision:** Let Oryx install dependencies server-side (`--build-remote true`) rather than pre-installing locally in CI.

**Rationale:** The native-extension concern (`trafilatura`/`lxml`) does not apply because Oryx builds on Linux, matching the Azure Functions Linux runtime. Remote build is the officially supported path for Python Function Apps.

### Trigger: push to `main` only

**Decision:** Deploy only on `push` to `main`, not on PRs or tags.

**Rationale:** Simple single-environment setup. PRs should not trigger production deploys.

## Risks / Trade-offs

- **Deployment on every merge** → Any broken commit goes straight to production. Mitigation: add a test job as a prerequisite when tests exist.
- **No rollback automation** → Rollback requires a revert commit or manual re-publish. Mitigation: Azure Functions deployment slots can be added later.
- **Entra ID app registration** → If the app registration is deleted, deployments break. Mitigation: document the registration name/ID in the repo.
- **`ubuntu-latest` runner changes** → Unlikely to matter since no local build happens.

## Migration Plan

1. Create an Entra ID app registration; note Client ID and Tenant ID.
2. Add a federated credential scoped to this GitHub repo + `main` branch.
3. Assign **Website Contributor** role on the Function App resource to the app registration.
4. Add GitHub secrets: `AZURE_CLIENT_ID`, `AZURE_TENANT_ID`, `AZURE_SUBSCRIPTION_ID`, `AZURE_RESOURCE_GROUP`, `AZURE_FUNCTIONAPP_NAME`.
5. Remove the old `AZURE_FUNCTIONAPP_PUBLISH_PROFILE` secret.
6. Merge `.github/workflows/deploy.yml` to `main`.

Rollback: revert the workflow commit or run `az functionapp deploy` manually.
