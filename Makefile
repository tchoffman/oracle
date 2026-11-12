.PHONY: help all deps models corpus index venv clean status serve ask

SHELL := /bin/bash
BUILD_DIR := build
VENV := $(BUILD_DIR)/venv
PY := $(VENV)/bin/python

help:
	@echo "Oracle — offline knowledge appliance builder"
	@echo ""
	@echo "Targets:"
	@echo "  make all      — full build: deps + models + corpus + index"
	@echo "  make deps     — install ollama + kiwix-tools via brew (idempotent)"
	@echo "  make venv     — create Python venv and install rag/ requirements"
	@echo "  make models   — pull LLM + embedding model via ollama"
	@echo "  make corpus   — download ZIMs and public-domain PDFs into build/corpus"
	@echo "  make index    — chunk + embed corpus PDFs into Chroma"
	@echo "  make status   — print what's installed / downloaded / indexed"
	@echo "  make serve    — launch kiwix-serve (ZIMs at http://localhost:8080)"
	@echo "  make clean    — wipe build/ (redownload everything)"
	@echo ""
	@echo "Day-to-day CLI (after make all):"
	@echo "  bin/oracle ask \"your question\""
	@echo "  bin/oracle serve"
	@echo "  bin/oracle status"

all: deps venv models corpus index
	@echo ""
	@echo "Oracle build complete. Try:"
	@echo "  bin/oracle ask \"how do I purify water?\""

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

status:
	@bin/oracle status

serve:
	@bin/oracle serve

ask:
	@echo "Usage: bin/oracle ask \"your question\""

clean:
	@echo "Wiping build/ — models and corpus will need to be re-downloaded."
	@rm -rf $(BUILD_DIR)
