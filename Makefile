# RAHBAR development and evidence commands. Run from a Bash environment.

SHELL := /bin/bash
NS ?= rahbar
TAG ?= dev
PY ?= python3
VENV ?= .venv
BIN := $(abspath $(VENV))/bin
# The Ingress address. On Linux this is the minikube IP. On macOS or Windows with the
# docker driver, run `minikube tunnel` in another terminal and use INGRESS_IP=127.0.0.1.
INGRESS_IP ?= $(shell minikube ip 2>/dev/null)
HOST ?= rahbar.local

.DEFAULT_GOAL := help
.PHONY: help install test lint dev cluster images apply secret index ask fetch eval eval-fixtures check deploy-real audit-live calibrate-cache evidence rollout-demo

help: ## list the targets
	@grep -E '^[a-z-]+:.*## ' $(MAKEFILE_LIST) | awk -F':.*## ' '{printf "  make %-14s %s\n", $$1, $$2}'

install: ## create .venv and install the api, indexer and tool dependencies
	$(PY) -m venv $(VENV)
	"$(BIN)/pip" install -q --upgrade pip
	"$(BIN)/pip" install -q -r api/requirements-dev.txt -r indexer/requirements-dev.txt

test: ## run API, indexer and evaluation tests without external services
	cd api && "$(BIN)/pytest" -q
	cd indexer && "$(BIN)/pytest" -q
	"$(BIN)/python" -m pytest -q -c eval/pyproject.toml eval/tests

lint: ## ruff and mypy over everything in Python
	"$(BIN)/ruff" check api indexer eval corpus scripts
	cd api && "$(BIN)/mypy" app
	cd indexer && "$(BIN)/mypy" pipeline

dev: ## run the API with stubs on http://localhost:8000, serving the chat UI too
	cd api && SERVE_UI_DIR=../ui RETRIEVER=stub LLM_PROVIDER=stub "$(BIN)/uvicorn" app.main:app --reload --port 8000

cluster: ## start minikube with Calico, then enable metrics-server and ingress
	minikube start --driver=docker --cni=calico --memory=6144 --cpus=4
	minikube addons enable metrics-server
	minikube addons enable ingress

images: ## build corpus-free images and load them into minikube
	docker build --build-arg VCS_REF=$$(git rev-parse HEAD) -t rahbar-api:$(TAG) api
	docker build --build-arg VCS_REF=$$(git rev-parse HEAD) -t rahbar-indexer:$(TAG) indexer
	docker build --build-arg VCS_REF=$$(git rev-parse HEAD) -t rahbar-ui:$(TAG) ui
	minikube image load rahbar-api:$(TAG)
	minikube image load rahbar-indexer:$(TAG)
	minikube image load rahbar-ui:$(TAG)

apply: ## apply the explicitly stubbed dev overlay
	kubectl apply -k k8s/overlays/dev

secret: ## create the LLM key Secret from the LLM_API_KEY variable; never from a file
	@test -n "$$LLM_API_KEY" || { echo "export LLM_API_KEY=... first"; exit 1; }
	kubectl create secret generic rahbar-secret -n $(NS) \
	  --from-literal=LLM_API_KEY="$$LLM_API_KEY" --dry-run=client -o yaml | kubectl apply -f -

index: ## run the indexer once from the reindex CronJob template
	kubectl create job --from=cronjob/reindex reindex-$$(date +%s) -n $(NS)
	@echo "watch it with: kubectl get jobs -n $(NS) -w"

ask: ## ask through the Ingress: make ask Q="What CGPA puts a student on academic warning?"
	@curl -s -X POST "http://$(INGRESS_IP)/api/ask" -H "Host: $(HOST)" \
	  -H 'Content-Type: application/json' -d "$$(Q="$(Q)" $(PY) -c 'import json,os; print(json.dumps({"question": os.environ["Q"]}))')" \
	  | $(PY) -m json.tool

fetch: ## download the documents listed in corpus/sources.yaml
	"$(BIN)/python" corpus/fetch.py

eval: ## score eval/golden.yaml through the Ingress and apply the CI gate
	"$(BIN)/python" eval/run_eval.py --api "http://$(INGRESS_IP)" --host $(HOST)

eval-fixtures: ## score the local fixtures through the API with offline service doubles
	"$(BIN)/python" -m pytest -q -c eval/pyproject.toml eval/tests/test_fixture_stack.py

check: ## run the submission checker
	$(PY) scripts/check_submission.py

deploy-real: ## fetch pinned PDFs, resolve host egress, build corpus image, and deploy prod
	PYTHON="$(BIN)/python" TAG="$(TAG)" bash scripts/deploy_real.sh

audit-live: ## measure three chunk settings and cache thresholds against real local services
	"$(BIN)/python" -m eval.live_audit --out eval/runs/current

calibrate-cache: ## measure labelled cache false hits using the configured real embedding model
	"$(BIN)/python" -m eval.calibrate_cache

evidence: ## capture real cluster/resource evidence (run while the index Job is active)
	bash scripts/capture_evidence.sh

rollout-demo: ## perform a visible UI update and rollback, then restore the original image
	INGRESS_IP="$(INGRESS_IP)" HOST="$(HOST)" bash scripts/rollout_demo.sh
