.PHONY: help all deps models corpus index venv clean status serve ask setup plan smoke-test test check-urls

SHELL := /bin/bash
BUILD_DIR := build
VENV := $(BUILD_DIR)/venv
PY := $(VENV)/bin/python

help:
	@echo "Pergamon — offline knowledge appliance builder"
	@echo ""
	@echo "Targets:"
	@echo "  make setup    — interactively pick what to install (writes install.local.yaml)"
	@echo "  make plan     — show the planned downloads without fetching"
	@echo "  make all      — full build: deps + models + corpus + index"
	@echo "  make deps     — install ollama + kiwix-tools via brew (idempotent)"
	@echo "  make venv     — create Python venv and install rag/ requirements"
	@echo "  make models   — pull LLM + embedding model via ollama"
	@echo "  make corpus   — download whatever is enabled in config/install*.yaml"
	@echo "  make index    — chunk + embed corpus PDFs into Chroma"
	@echo "  make zim-index    — ingest ZIM articles into Chroma (use ZIM_LIMIT=N to cap)"
	@echo "  make status     — print what's installed / downloaded / indexed"
	@echo "  make serve      — launch kiwix-serve (ZIMs at http://localhost:8080)"
	@echo "  make web        — launch the web UI (http://localhost:8090)"
	@echo "  make test       — run unit tests (config logic, no network)"
	@echo "  make check-urls — HEAD-request every URL in the plan (catches dead links)"
	@echo "  make smoke-test — run end-to-end validation"
	@echo "  make clean      — wipe build/ (redownload everything)"
	@echo ""
	@echo "Day-to-day CLI (after make all):"
	@echo "  bin/pergamon ask \"your question\""
	@echo "  bin/pergamon serve"
	@echo "  bin/pergamon status"

all: deps venv models corpus index
	@echo ""
	@echo "Pergamon build complete. Try:"
	@echo "  bin/pergamon ask \"how do I purify water?\""

deps:
	@scripts/install-deps.sh

venv: $(VENV)/.ready

$(VENV)/.ready: rag/requirements.txt
	@scripts/setup-venv.sh
	@touch $(VENV)/.ready

models:
	@scripts/pull-models.sh

corpus:
	@scripts/fetch-corpus.sh

index: venv corpus
	@scripts/build-index.sh

zim-index: venv
	@scripts/build-zim-index.sh

status:
	@bin/pergamon status

setup: venv
	@bin/pergamon setup

plan: venv
	@DRY_RUN=1 scripts/fetch-corpus.sh

test: venv
	@$(PY) -m pytest tests/ -v

check-urls: venv
	@scripts/check-urls.sh

smoke-test:
	@scripts/smoke-test.sh

serve:
	@bin/pergamon serve

web: venv
	@bin/pergamon web

ask:
	@echo "Usage: bin/pergamon ask \"your question\""

clean:
	@echo "Wiping build/ — models and corpus will need to be re-downloaded."
	@rm -rf $(BUILD_DIR)
