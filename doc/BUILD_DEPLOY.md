# Acadia-HQ Build and Deployment

## Scope

Acadia-HQ is the fleet-management development stack: FastAPI API, Python gRPC agent-gateway,
Vue/Vite web client, and Docker Compose services for Postgres, MinIO, Redis, and Keycloak. The
root Makefile is the authoritative local orchestration entry point.

## 1. Prerequisites

- Docker and Docker Compose, Python 3.12+, Node/npm, and `make`; `make doctor` checks Docker,
Python 3, and Node.
- Network access to install Python and npm dependencies.
- The API and gateway `pyproject.toml` files use editable installs and dev extras; the web
package uses the Node engine range declared in `web/package.json`.
- Credentials and identity configuration for production are external; the development Compose
stack supplies development values only.

## 2. Setup

```sh
make doctor
make install
make db-up
make migrate
make seed EMAIL=admin@example.com
```

`install` creates `.venv`, upgrades pip, installs `./api[dev]` and `./agent-gateway[dev]`, and
runs `npm install` in `web`. `db-up` starts the Compose services, waits for
Postgres/MinIO/Keycloak, creates the test database, and creates the `acadiahq` bucket.

## 3. Build and compile

```sh
make build
```

The only root build target is the web production build (`cd web && npm run build`), which runs
Vite type checking and bundle generation. Python services are installed in editable mode; there
is no separate native compile target.

## 4. Test and lint

```sh
make test
make test-api
make test-gateway
make test-web
make lint
make lint-api
make lint-gateway
make lint-web
```

API and gateway tests run pytest with the configured test database and S3 endpoint. Web tests
run `npx vitest run`. Lint runs Ruff for Python and `npm run lint` plus `vue-tsc --noEmit` for
web. Database-backed tests are conditional on `make db-up` and the Compose services being
healthy.

## 5. Packaging and artifacts

The web build emits `web/dist/`; Python packages are local editable installs and no publish
target exists. The development Compose file is `infra/docker-compose.yml` and the service
project name is `acadiahq`. This leaf has no root Docker image build target; production
packaging/deployment must use the existing service/container definitions and deployment
environment.

## 6. Deployment, install, and run

```sh
make run
make logs
make stop
make db-down
```

`run` starts the database dependencies, applies migrations, and launches API on port 8000,
gateway on port 50051, and Vite web on port 5173 in the background, recording PIDs/logs under
`.run/`. It prints LAN-IP URLs and development credentials; use these only in a controlled
development environment. `DATABASE_URL`, `TEST_DATABASE_URL`, and `S3_ENDPOINT_URL` can be
overridden. The OIDC issuer and Keycloak admin values are development settings, not production
secrets.

`stop` stops background API/gateway/web processes but deliberately leaves the Compose database
running; run `make db-down` to stop it. For a deployment, provide real OIDC, database,
object-store, TLS, and network configuration outside the Makefile and perform an authenticated
smoke test.

## 7. Cleanup

```sh
make stop
make db-down
make clean
```

`clean` removes `.venv`, `.run`, `web/node_modules`, `web/dist`, caches, Python `__pycache__`,
egg-info, and test/lint caches. `db-down` stops containers but preserves Docker volumes; remove
volumes only through an explicitly approved environment reset.

## 8. Hardware, cloud, and manual verification caveats

HQ has no direct hardware build. Automated tests and local Compose do not prove production OIDC,
tenant isolation across deployed infrastructure, TLS, object-store durability, device
connectivity, telemetry, or cloud networking. Manual verification must cover login redirects
using the LAN/production origin, API/gateway health, pairing, device telemetry, alarm/run flows,
and dashboard integration. Treat all printed development credentials and Compose defaults as
non-production.
