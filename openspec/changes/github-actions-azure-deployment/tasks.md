## 1. One-time Azure Setup

- [x] 1.1 Download the Function App publish profile from the Azure portal (Function App → Overview → "Get publish profile")
- [x] 1.2 Add the publish profile XML as a GitHub secret named `AZURE_FUNCTIONAPP_PUBLISH_PROFILE`
- [x] 1.3 Add the Function App name as a GitHub secret named `AZURE_FUNCTIONAPP_NAME`

## 2. GitHub Actions Workflow

- [x] 2.1 Create `.github/workflows/` directory
- [x] 2.2 Create `.github/workflows/deploy.yml` with trigger on push to `main`
- [x] 2.3 Add `setup-python` step pinned to Python 3.13
- [x] 2.4 Add `pip install -r requirements.txt --target=".python_packages/lib/site-packages"` step
- [x] 2.5 Add `azure/functions-action` step using `AZURE_FUNCTIONAPP_PUBLISH_PROFILE` and `AZURE_FUNCTIONAPP_NAME` secrets

## 3. Validation

- [ ] 3.1 Push workflow file to `main` and confirm the Actions run appears in the GitHub Actions tab
- [ ] 3.2 Verify the deployment succeeded in the Azure portal (Function App → Functions — the `news_digest_timer` function should be listed)
- [ ] 3.3 Confirm the timer trigger fires correctly on next scheduled run (or trigger manually via Azure portal to test)
