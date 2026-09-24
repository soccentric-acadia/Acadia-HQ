# Acadia-HQ — top-level entry point.
# Wraps: docker compose (Postgres/MinIO/Redis), the Python venv (api +
# agent-gateway), and the Vue frontend. See IMPLEMENTATION_PLAN.md §0.

.DEFAULT_GOAL := help

SHELL := /bin/bash
CURDIR := $(shell pwd)
VENV := $(CURDIR)/.venv
PY := $(VENV)/bin/python
PIP := $(VENV)/bin/pip
COMPOSE := docker compose -f infra/docker-compose.yml -p acadiahq
RUN_DIR := $(CURDIR)/.run

DATABASE_URL ?= postgresql+asyncpg://acadiahq:acadiahq@localhost:5432/acadiahq
TEST_DATABASE_URL ?= postgresql+asyncpg://acadiahq:acadiahq@localhost:5432/acadiahq_test
S3_ENDPOINT_URL ?= http://localhost:9000

# Host by which other devices reach this machine's services -- the canonical
# origin for the web UI (the session cookie is per-origin, so every device
# should browse the same host) and the default host for the OIDC issuer.
# Tailscale IPv4 first (HQ is commonly reached over the tailnet), falling
# back to the first `hostname -I` address (LAN-only deployments).
REMOTE_HOST = $(shell \
	host=""; \
	if command -v tailscale >/dev/null 2>&1; then \
		host=$$(tailscale ip -4 2>/dev/null | head -n1); \
	fi; \
	if [ -z "$$host" ]; then \
		host=$$(hostname -I 2>/dev/null | awk '{print $$1}'); \
	fi; \
	echo "$$host")

# Full OIDC issuer URL handed to the API by `make run`. A pre-set
# ACADIAHQ_OIDC_ISSUER environment variable overrides it verbatim -- use that
# when Keycloak must be reached at a different address than $(REMOTE_HOST)
# (e.g. LAN-only access: ACADIAHQ_OIDC_ISSUER=http://<lan-ip>:8081/realms/acadiahq).
# The issuer must be reachable from the browser AND from the API process, and
# it must be the same host for everyone: Keycloak (KC_HOSTNAME_STRICT=false)
# echoes the request Host as the token `iss`, which the API validates against
# exactly this issuer (api/app/auth/oidc.py). Baking in the LAN IP broke login
# from Tailscale clients (task 007).
ACADIAHQ_OIDC_ISSUER ?= http://$(REMOTE_HOST):8081/realms/acadiahq

.PHONY: help doctor install db-up db-down migrate seed run stop logs e2e-enroll test test-api test-gateway test-web lint lint-api lint-gateway lint-web build clean



e2e-enroll: ## X5-012: end-to-end device enrollment (Rust agent vs real gateway; needs docker+cargo)
	@bash agent-gateway/tests/e2e_device_enroll.sh

doctor: ## check prerequisites (docker compose v2, python3 3.12+, node 22/24)
	@command -v docker >/dev/null || { echo "docker not found"; exit 1; }
	@docker compose version >/dev/null 2>&1 || { echo "docker compose v2 plugin not found"; exit 1; }
	@command -v python3 >/dev/null || { echo "python3 not found"; exit 1; }
	@python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3, 12) else 1)' || { echo "python3 >= 3.12 required (api/agent-gateway target 3.12)"; exit 1; }
	@command -v node >/dev/null || { echo "node not found"; exit 1; }
	@node -e 'const s=require("./web/package.json").engines.node; const ok=require("semver").satisfies(process.version.slice(1),s).valueOf(); if(!ok){console.error("node "+process.version+" does not satisfy web engines "+s);process.exit(1);}' 2>/dev/null || echo "note: could not check web engines (semver unavailable) — node $$(node --version)"
	@echo "all prerequisites found"

$(VENV)/bin/activate:
	python3 -m venv $(VENV)

install: $(VENV)/bin/activate ## create venv, install api/agent-gateway/web deps
	$(PIP) install --quiet --upgrade pip
	$(PIP) install --quiet -e ./api[dev] -e ./agent-gateway[dev]
	cd web && npm install

db-up: ## start Postgres/MinIO/Redis (docker compose)
	$(COMPOSE) up -d
	@echo "waiting for postgres..."
	@until docker exec $$($(COMPOSE) ps -q postgres) pg_isready -U acadiahq >/dev/null 2>&1; do sleep 1; done
	@docker exec $$($(COMPOSE) ps -q postgres) psql -U acadiahq -d acadiahq -tc \
		"SELECT 1 FROM pg_database WHERE datname='acadiahq_test'" | grep -q 1 || \
		docker exec $$($(COMPOSE) ps -q postgres) createdb -U acadiahq acadiahq_test
	@echo "waiting for minio..."
	@until docker exec $$($(COMPOSE) ps -q minio) mc ready local >/dev/null 2>&1; do sleep 1; done
	@docker run --rm --network acadiahq_default -e MC_HOST_local=http://acadiahq:acadiahq-dev-secret@minio:9000 \
		minio/mc mb -p local/acadiahq >/dev/null 2>&1 || true
	@echo "waiting for keycloak (can take ~30s on first boot)..."
	@until curl -sf http://localhost:8081/realms/acadiahq/.well-known/openid-configuration >/dev/null 2>&1; do sleep 2; done
	@echo "postgres, minio (bucket: acadiahq), redis, keycloak (realm: acadiahq) ready"

db-down: ## stop them (data persists in docker volumes)
	$(COMPOSE) down

migrate: ## alembic upgrade head
	ACADIAHQ_ENV=dev ACADIAHQ_DATABASE_URL=$(DATABASE_URL) $(VENV)/bin/alembic upgrade head

seed:
	@test -n "$(EMAIL)" || { echo "usage: make seed EMAIL=you@example.com"; exit 1; }
	cd api && ACADIAHQ_ENV=dev ACADIAHQ_DATABASE_URL=$(DATABASE_URL) $(PY) -m scripts.seed_dev --email $(EMAIL)

# Each service is launched as `(cd dir && exec env VARS nohup cmd) &` --
# the `exec` makes the subshell replace its own process image with the
# final command instead of forking a child for it, so `$!` (captured right
# after) is the PID of the actual long-running server, not a wrapper shell.
# Without this, `make stop` kills the wrapper and orphans the real process.
run: db-up migrate ## start db + api + agent-gateway + web in the background
	@mkdir -p $(RUN_DIR)
	@busy=""; \
	for p in 8000 5173 50051; do \
		if ss -tlnH 2>/dev/null | awk '{print $$4}' | grep -qE "[:.]$$p$$"; then \
			busy="$$busy $$p"; \
		fi; \
	done; \
	if [ -n "$$busy" ]; then \
		echo "refusing to start: port(s)$$busy already in use."; \
		echo "  run 'make stop' first. If the ports stay busy after that, the"; \
		echo "  listeners are orphans from an earlier run -- locate them with"; \
		echo "  'ss -tlnp | grep -E \":(8000|5173|50051)\"' and kill them, then re-run."; \
		exit 1; \
	fi
	@echo "starting api, agent-gateway, web..."
	@(cd api && exec env ACADIAHQ_ENV=dev ACADIAHQ_DATABASE_URL=$(DATABASE_URL) ACADIAHQ_S3_ENDPOINT_URL=$(S3_ENDPOINT_URL) \
		ACADIAHQ_OIDC_ISSUER=$(ACADIAHQ_OIDC_ISSUER) \
		nohup $(PY) -m uvicorn app.main:app --host 0.0.0.0 --port 8000 > $(RUN_DIR)/api.log 2>&1) & echo $$! > $(RUN_DIR)/api.pid
	@(cd agent-gateway && exec env ACADIAHQ_ENV=dev ACADIAHQ_DATABASE_URL=$(DATABASE_URL) ACADIAHQ_S3_ENDPOINT_URL=$(S3_ENDPOINT_URL) \
		nohup $(PY) -m gateway.server > $(RUN_DIR)/gateway.log 2>&1) & echo $$! > $(RUN_DIR)/gateway.pid
	@WATCH_OK=1; \
		node -e 'try{const w=require("fs").watch(__filename);w.close()}catch(e){process.exit(1)}' 2>/dev/null || WATCH_OK=0; \
		if [ "$$WATCH_OK" = 0 ]; then \
			echo "inotify watcher limit reached -- vite falling back to polling watcher"; \
			VITE_ENV='CHOKIDAR_USEPOLLING=true'; \
		else \
			VITE_ENV=''; \
		fi; \
		(cd web && exec env $$VITE_ENV nohup ./node_modules/.bin/vite --host 0.0.0.0 --port 5173 > $(RUN_DIR)/web.log 2>&1) & echo $$! > $(RUN_DIR)/web.pid
	@sleep 1
	@echo "web:      http://$(REMOTE_HOST):5173   (open THIS origin on every device, including"; \
	echo "                                  this host -- the session cookie is per-origin, so"; \
	echo "                                  mixing hosts splits your login; http://localhost:5173"; \
	echo "                                  works on this machine only)"; \
	echo "api:      http://$(REMOTE_HOST):8000"; \
	echo "keycloak: $(ACADIAHQ_OIDC_ISSUER)"; \
	echo "          admin console: $(subst /realms/acadiahq,,$(ACADIAHQ_OIDC_ISSUER))/admin  (admin/admin)"; \
	echo "gateway:  $(REMOTE_HOST):50051 (gRPC)"; \
	echo ""; \
	echo "login:    admin@example.com / devpassword"; \
	echo "          (first time: make seed EMAIL=admin@example.com to pre-invite it as admin)"; \
	echo ""; \
	echo "logs:     make logs   |   stop:  make stop"

stop: ## stop everything 'make run' started, incl. db (data persists in volumes)
	-@for f in $(RUN_DIR)/*.pid; do [ -f "$$f" ] && kill $$(cat "$$f") 2>/dev/null; rm -f "$$f"; done
	@echo "background services stopped"
	-$(COMPOSE) down
	@echo "db stopped (data persists in docker volumes)"

logs: ## tail logs for the background services
	@tail -n 100 -f $(RUN_DIR)/api.log $(RUN_DIR)/gateway.log $(RUN_DIR)/web.log

test: test-api test-gateway test-web ## run api + agent-gateway + web test suites

test-api:
	cd api && ACADIAHQ_ENV=test ACADIAHQ_TEST_DATABASE_URL=$(TEST_DATABASE_URL) ACADIAHQ_S3_ENDPOINT_URL=$(S3_ENDPOINT_URL) \
		$(VENV)/bin/python -m pytest -q

test-gateway:
	cd agent-gateway && ACADIAHQ_ENV=test ACADIAHQ_TEST_DATABASE_URL=$(TEST_DATABASE_URL) ACADIAHQ_S3_ENDPOINT_URL=$(S3_ENDPOINT_URL) \
		$(VENV)/bin/python -m pytest -q

test-web:
	cd web && npx vitest run

lint: lint-api lint-gateway lint-web ## run ruff (api, agent-gateway) + eslint/oxlint (web)

lint-api:
	$(VENV)/bin/ruff check api

lint-gateway:
	$(VENV)/bin/ruff check agent-gateway

lint-web:
	cd web && npm run lint && npx vue-tsc --noEmit

build: docker-build ## Build web frontend + backend images (Docker — fleet default)

clean: ## remove venv, node_modules, caches, dist, run logs
	rm -rf $(VENV) $(RUN_DIR) web/node_modules web/dist web/.eslintcache
	find . -name __pycache__ -o -name "*.egg-info" -o -name .ruff_cache -o -name .pytest_cache | xargs rm -rf

# ── Docker (fleet-standard build) ────────────────────────────────────────────
# `make build` produces the production container images. See docker/.

.PHONY: docker-build docker-build-backend docker-build-web

IMAGE_HQ := acadiahq

docker-build: docker-build-backend docker-build-web ## Build backend + web Docker images
# Invoke the sub-Makefile with -f (not -C) so its paths
# (docker/Dockerfile, context '.') resolve against the repo root.
docker-build-backend:
	$(MAKE) -f docker/Makefile build IMAGE=$(IMAGE_HQ)
docker-build-web:
	$(MAKE) -f docker/Makefile build-web IMAGE=$(IMAGE_HQ)

# ── Help ──────────────────────────────────────────────────────────────────────
# Targets are self-documenting: text after `## ` on a target line is picked up
# by `make help` automatically, so the listing can never drift from the rules.
.PHONY: help
version: ## Print the project version (CONV-004)
	@grep -m1 '^version' api/pyproject.toml | sed 's/.*"\(.*\)"/\1/'

help: ## Show this help
	@printf '\n  \033[1m%s\033[0m\n' 'Acadia-HQ'
	@printf '  Usage: make <target> [VAR=value ...]\n'
	@printf '\n'
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z0-9_.\/-]+:.*?## / { printf "    \033[36m%-24s\033[0m %s\n", $$1, $$2 }' $(MAKEFILE_LIST)
	@printf '\n'
