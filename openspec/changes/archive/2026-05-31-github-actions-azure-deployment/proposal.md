## Why

The project runs as an Azure Functions app but has no CI/CD pipeline — deployments require manual `func azure functionapp publish` runs from a developer machine. A GitHub Actions workflow automates this, ensuring every push to `main` deploys a consistent, dependency-locked build without relying on local tooling or credentials stored on individual machines.

## What Changes

- Add a GitHub Actions workflow file (`.github/workflows/deploy.yml`) that deploys to Azure Functions on push to `main`
- Workflow installs Python dependencies, zips the app, and publishes via the Azure Functions Action
- Azure credentials stored as GitHub repository secrets (not committed)
- No changes to application code, `host.json`, or `requirements.txt`

## Capabilities

### New Capabilities

- `ci-cd-pipeline`: GitHub Actions workflow that builds and deploys the Azure Functions app to Azure on push to `main`, using publish profile or service principal credentials stored as GitHub secrets

### Modified Capabilities

<!-- None — no existing spec-level behavior changes -->

## Impact

- New file: `.github/workflows/deploy.yml`
- Requires one-time setup: Azure Function App publish profile (or service principal) added as a GitHub secret (`AZURE_FUNCTIONAPP_PUBLISH_PROFILE`)
- No runtime code changes; existing `function_app.py`, `host.json`, `requirements.txt` untouched
