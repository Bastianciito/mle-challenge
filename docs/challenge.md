
# MLE Challenge


# Definitions

0. `uv` was selected as the package manager.

1. Because both models produce almost the same results (per DS observations), logistic regression was chosen for deployment. It is more lightweight than XGBoost in terms of training time, dependency footprint, and final memory consumption for the service.

2. A minimal FastAPI application with Pydantic model validation rejects any input values that were not present in the training data, returning HTTP 400 when a validation condition is not met.

3. The trained model artifact is saved as a `.joblib` file and committed to the `artifacts/` directory.

4. The Docker image includes only the libraries required at runtime, producing a lightweight image.

5. A `.dockerignore` file excludes non-production files from the build context.

---

# Bugs Detected

**1. Data leakage in `test_model_fit`**

`test_model.py` contained a bug: evaluation metrics were computed on data that was also used for training. The model was fit on the full dataset, then validated on a subset of that same data — making the test meaningless as a generalization check. The fix was to split the data before training so the validation set is never seen during fitting.

**Old test:**

```python
def test_model_fit(self):
    features, target = self.model.preprocess(data=self.data, target_column="delay")

    _, features_validation, _, target_validation = train_test_split(
        features, target, test_size=0.33, random_state=42
    )

    self.model.fit(features=features, target=target)

    predicted_target = self.model._model.predict(features_validation)

    report = classification_report(
        target_validation, predicted_target, output_dict=True
    )

    assert report["0"]["recall"] < 0.60
    assert report["0"]["f1-score"] < 0.70
    assert report["1"]["recall"] > 0.60
    assert report["1"]["f1-score"] > 0.30
```

**New test:**

```python
def test_model_fit(self):
    features, target = self.model.preprocess(data=self.data, target_column="delay")

    features_training, features_validation, target_training, target_validation = (
        train_test_split(features, target, test_size=0.33, random_state=42)
    )

    self.model.fit(features=features_training, target=target_training)
    predicted_target = self.model._model.predict(features_validation)
    report = classification_report(
        target_validation, predicted_target, output_dict=True
    )

    assert report["0"]["recall"] < 0.60
    assert report["0"]["f1-score"] < 0.70
    assert report["1"]["recall"] > 0.60
    assert report["1"]["f1-score"] > 0.30
```

---

# Project Structure

> *AI generated doc*

```
challenge_MLE/
├── .github/workflows/
│   ├── ci.yml              # Runs tests on PRs targeting develop, release/*, main
│   └── cd.yml              # Builds and deploys the Docker image on push
├── artifacts/
│   └── logistic_regression_to_deploy.joblib   # Saved model artifact
├── challenge/
│   ├── model.py            # Model class: preprocessing, training, prediction
│   └── api.py              # FastAPI app exposing the prediction endpoint
├── data/
│   └── data.csv            # Raw training dataset
├── docs/
│   └── challenge.md        # This file
├── tests/
│   ├── model/test_model.py # Unit tests for the model
│   ├── api/test_api.py     # Integration tests for the API
│   └── stress/api_stress.py # Locust stress test
├── Dockerfile              # Production image definition
├── pyproject.toml          # Project metadata and dependencies (managed by uv)
└── Makefile                # Shortcuts for running tests and other tasks
```

---

# Running Locally with Docker

**Build the image:**

```bash
docker build -t challenge-mle .
```

**Run the container:**

```bash
docker run -p 8080:8080 challenge-mle
```

The API will be available at `http://localhost:8080`. You can verify it is up with:

```bash
curl http://localhost:8080/health
```

And send a prediction request:

```bash
curl -X POST http://localhost:8080/predict \
  -H "Content-Type: application/json" \
  -d '{"flights": [{"OPERA": "Aerolineas Argentinas", "TIPOVUELO": "N", "MES": 3}]}'
```

---

# API Endpoints

The service is deployed to Google Cloud Run across three environments. Each environment has its own dedicated URL.

| Environment | URL |
|---|---|
| Production | `https://mle-challenge-latam-service-5fxzjlb2hq-ue.a.run.app` |
| Release (v1.0.0) | `https://mle-challenge-latam-service-v1-0-0-5fxzjlb2hq-ue.a.run.app` |
| Development | `https://mle-challenge-latam-service-dev-5fxzjlb2hq-ue.a.run.app` |

All environments expose the same endpoints:

| Method | Path | Description |
|---|---|---|
| `GET` | `/health` | Health check |
| `POST` | `/predict` | Flight delay prediction |

**Example — health check (production):**

```bash
curl https://mle-challenge-latam-service-dev-5fxzjlb2hq-ue.a.run.app/health
```

**Example — prediction request (production):**

```bash
curl -X POST https://mle-challenge-latam-service-dev-5fxzjlb2hq-ue.a.run.app/predict \
  -H "Content-Type: application/json" \
  -d '{"flights": [{"OPERA": "Aerolineas Argentinas", "TIPOVUELO": "N", "MES": 3}]}'
```

---

# Terraform Deployment (GCP)

Infrastructure is managed with Terraform and lives in the [terraform/](../terraform/) directory. The CD pipeline provisions or updates the Cloud Run service on every push to `develop`, `release/**`, or `main` — no manual `gcloud run deploy` commands are needed.

## Resources managed

| Resource | Description |
|---|---|
| `google_cloud_run_v2_service` | Cloud Run service running the prediction API |
| `google_cloud_run_v2_service_iam_member` | IAM binding that makes the service publicly accessible |

## State backend

Remote state is stored in a GCS bucket so every CI run shares the same view of infrastructure:

```hcl
terraform {
  backend "gcs" {
    bucket = "mle-challenge-latam-tfstate"
    prefix = "mle-challenge"
  }
}
```

Each environment (`develop`, `release/vX.Y.Z`, `main`) uses a distinct state prefix so their resources are tracked independently.

## Variables

| Variable | Description | Default |
|---|---|---|
| `project_id` | GCP project ID | *(required)* |
| `region` | GCP region | `us-east1` |
| `image` | Full Docker image URI injected by CI | *(required)* |
| `service_name` | Cloud Run service name (varies per branch) | *(required)* |

## How CD wires it together

The deploy job in `.github/workflows/cd.yml` runs after the image is built and pushed:

```
build-and-push  ──►  deploy
                      ├─ terraform init   (state prefix = mle-challenge/<service>)
                      ├─ terraform plan
                      └─ terraform apply  (auto-approved, vars injected from CI)
```

Variables `image` and `service_name` are resolved by the `build-and-push` job depending on the branch:

| Branch | `service_name` | `image` tag |
|---|---|---|
| `develop` | `…-dev` | commit SHA |
| `release/vX.Y.Z` | `…-vX-Y-Z` | `vX.Y.Z` |
| `main` | base service name | commit SHA |

## Running Terraform locally

```bash
cd terraform

terraform init \
  -backend-config="prefix=mle-challenge/mle-challenge-latam-service-dev"

terraform plan \
  -var="project_id=<YOUR_PROJECT_ID>" \
  -var="image=us-east1-docker.pkg.dev/<YOUR_PROJECT_ID>/mle-challenge-latam/mle-challenge-latam-service:<TAG>" \
  -var="service_name=mle-challenge-latam-service-dev"

terraform apply -auto-approve \
  -var="project_id=<YOUR_PROJECT_ID>" \
  -var="image=us-east1-docker.pkg.dev/<YOUR_PROJECT_ID>/mle-challenge-latam/mle-challenge-latam-service:<TAG>" \
  -var="service_name=mle-challenge-latam-service-dev"
```

> Requires Application Default Credentials with sufficient permissions (`roles/run.admin`, `roles/iam.serviceAccountUser`, and read access to the state bucket).

---

# Branch Strategy

> *AI generated doc*

```
feature/* ──► develop ──► release/* ──► main
```

| Branch | Purpose |
|---|---|
| `feature/*` | Individual work items; open a PR into `develop` to merge |
| `develop` | Integration branch; CI runs on every incoming PR |
| `release/*` | Release candidates (e.g. `release/v1.0.0`); promoted from `develop` |
| `main` | Production; only merged from a `release/*` branch |

**CI** (`.github/workflows/ci.yml`) — runs the model and API test suites on any PR targeting `develop`, `release/**`, or `main`.

**CD** (`.github/workflows/cd.yml`) — triggered on push to `develop`, `release/**`, or `main`. The deployed Cloud Run service and image tag vary by branch:

| Branch | Image tag | Cloud Run service |
|---|---|---|
| `develop` | commit SHA | `…-dev` |
| `release/vX.Y.Z` | `vX.Y.Z` | `…-vX-Y-Z` |
| `main` | commit SHA | base service name |
