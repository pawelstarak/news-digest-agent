## Context

The news-digest-agent is a Python Azure Functions app (v4 programming model) with a single timer-triggered function that fires daily at 6 AM UTC. Currently there is no deployment pipeline; publishing requires a developer to run `func azure functionapp publish <app-name>` manually from their machine with the Azure CLI and the right credentials. The goal is to automate this via GitHub Actions so every merge to `main` triggers a deployment.

## Goals / Non-Goals

**Goals:**

- Automatically deploy to Azure Functions on every push to `main`
- Keep credentials out of the repository (use GitHub secrets)
- Use the official Azure Functions GitHub Action for reliability and future-proofing
- Install Python dependencies from `requirements.txt` before packaging

**Non-Goals:**

- Pull request preview environments or staging slots
- Running tests in CI (no test suite exists yet)
- Multi-environment promotion (dev → staging → prod)
- Infrastructure provisioning (Function App must already exist in Azure)

## Decisions

### Use publish profile over service principal

**Decision:** Authenticate with an Azure Function App publish profile stored as `AZURE_FUNCTIONAPP_PUBLISH_PROFILE` secret.

**Rationale:** Publish profiles are scoped to a single Function App — least privilege by default, no Azure AD app registration needed, and the `azure/functions-action` supports them natively. A service principal with `Contributor` on a subscription is broader than necessary for this single-app deployment.

**Alternative considered:** `azure/login` with a service principal + `azure/functions-action`. More flexible for multi-resource pipelines but overkill here; adds an extra secret and Azure AD setup step.

### Remote build disabled — local pip install

**Decision:** Install dependencies locally in the GitHub Actions runner and deploy the full package (not rely on Azure's remote build / Oryx).

**Rationale:** Remote build (SCM build) is enabled by default for Consumption plan apps but can produce inconsistent results for packages with native extensions (e.g., `trafilatura` pulls `lxml`). Local install on `ubuntu-latest` with the matching Python version gives a predictable artifact.

**Alternative considered:** Let Azure do the remote build (`ENABLE_ORYX_BUILD=true`). Simpler workflow but less control over the build environment.

### Python version pinned to 3.13

**Decision:** Pin `python-version: "3.13"` in the workflow to match the Azure Functions runtime (`~4` + Python 3.13).

**Rationale:** Avoids dependency resolution differences that would appear if the runner and the Azure runtime used different Python minor versions. Azure Functions v4 supports Python 3.13.

### Trigger: push to `main` only

**Decision:** Deploy only on `push` to `main`, not on PRs or tags.

**Rationale:** Simple single-environment setup. PRs should not trigger production deploys. Tag-based releases can be added later if needed.

## Risks / Trade-offs

- **Deployment on every merge** → Any broken commit goes straight to production. Mitigation: add a test job as a prerequisite before the deploy step when tests exist.
- **No rollback automation** → If a bad deploy goes out, rollback requires a revert commit or manual re-publish. Mitigation: Azure Functions supports deployment slots; swap-based rollback can be added later.
- **Publish profile expiry** → Publish profiles can be regenerated in the Azure portal, which invalidates the stored secret. Mitigation: document secret rotation in the repo README or `.github/` docs.
- **`ubuntu-latest` runner changes** → GitHub periodically updates `ubuntu-latest`. Native Python package builds (e.g., `lxml`) could break. Mitigation: pin to `ubuntu-22.04` if stability is critical.

## Migration Plan

1. Retrieve the publish profile from the Azure portal (Function App → "Get publish profile").
2. Add it as a GitHub secret named `AZURE_FUNCTIONAPP_PUBLISH_PROFILE`.
3. Add `AZURE_FUNCTIONAPP_NAME` secret (or hardcode the app name in the workflow — secret preferred to avoid leaking infra names).
4. Merge the `.github/workflows/deploy.yml` to `main` — this triggers the first automated deployment.
5. Verify the deployment in the Azure portal (Functions blade → Monitor).

Rollback: revert the workflow commit or manually re-publish the previous zip via `func azure functionapp publish`.
