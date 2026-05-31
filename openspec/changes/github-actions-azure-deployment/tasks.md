## 1. One-time Azure & GitHub Setup

- [ ] 1.1 Create an Entra ID app registration (Azure portal → Microsoft Entra ID → App registrations → New registration); note the **Client ID** and **Tenant ID**
- [ ] 1.2 Add a federated credential to the app registration: Certificates & secrets → Federated credentials → Add → GitHub Actions, enter repo and branch `main`
- [ ] 1.3 Assign **Website Contributor** role to the app registration on the Function App resource (Function App → Access control (IAM) → Add role assignment)
- [ ] 1.4 Add GitHub secrets: `AZURE_CLIENT_ID`, `AZURE_TENANT_ID`, `AZURE_SUBSCRIPTION_ID`, `AZURE_RESOURCE_GROUP`, `AZURE_FUNCTIONAPP_NAME`
- [ ] 1.5 Remove the old `AZURE_FUNCTIONAPP_PUBLISH_PROFILE` secret from GitHub

## 2. GitHub Actions Workflow

- [x] 2.1 Create `.github/workflows/` directory
- [x] 2.2 Create `.github/workflows/deploy.yml` with trigger on push to `main`
- [x] 2.3 Add `azure/login@v2` step using OIDC secrets
- [x] 2.4 Add deploy step using `az functionapp deploy --type zip --build-remote true`

## 3. Validation

- [ ] 3.1 Push workflow file to `main` and confirm the Actions run appears in the GitHub Actions tab
- [ ] 3.2 Verify the deployment succeeded in the Azure portal (Function App → Functions — the `news_digest_timer` function should be listed)
- [ ] 3.3 Confirm the timer trigger fires correctly on next scheduled run (or trigger manually via Azure portal to test)
