## ADDED Requirements

### Requirement: Automated deployment on push to main
The system SHALL automatically deploy the Azure Functions app to Azure whenever a commit is pushed to the `main` branch.

#### Scenario: Push to main triggers deployment
- **WHEN** a commit is pushed to the `main` branch
- **THEN** the GitHub Actions workflow starts and deploys the app to Azure Functions

#### Scenario: Push to non-main branch does not deploy
- **WHEN** a commit is pushed to any branch other than `main`
- **THEN** no deployment workflow is triggered

### Requirement: Python dependencies installed before deploy
The workflow SHALL install all packages listed in `requirements.txt` into a local directory before packaging the deployment artifact.

#### Scenario: Dependencies packaged with app
- **WHEN** the deployment workflow runs
- **THEN** `pip install -r requirements.txt --target=".python_packages/lib/site-packages"` is executed and the installed packages are included in the deployed zip

### Requirement: Azure credentials stored as GitHub secrets
The workflow SHALL authenticate to Azure using a publish profile stored as a GitHub repository secret and SHALL NOT contain any credentials inline in the workflow file.

#### Scenario: Workflow uses secret for auth
- **WHEN** the deployment step runs
- **THEN** it reads `secrets.AZURE_FUNCTIONAPP_PUBLISH_PROFILE` for authentication and the value is never echoed in logs

#### Scenario: Missing secret causes workflow failure
- **WHEN** the `AZURE_FUNCTIONAPP_PUBLISH_PROFILE` secret is not set
- **THEN** the deployment step fails with a clear authentication error (not a silent no-op)

### Requirement: Python runtime version matches Azure Functions runtime
The workflow SHALL pin the Python version used on the CI runner to 3.13, matching the Azure Functions v4 runtime configuration.

#### Scenario: Runner uses Python 3.13
- **WHEN** the setup-python step runs
- **THEN** Python 3.13 is installed on the runner and used for `pip install`
