# ──────────────────────────────────────────────────────────────────────
# PROJ-05: Vedic Astrology — Makefile
# ──────────────────────────────────────────────────────────────────────
.PHONY: all test lint build run up down clean logs shell ephe-download

SHELL := /bin/bash

IMAGE_NAME  := vedic-astrology
IMAGE_TAG   := latest
COMPOSE     := docker compose
PROD_COMPOSE := docker compose -f docker-compose.yml -f docker-compose.prod.yml

# ── Default ───────────────────────────────────────────────────────
all: test build

# ── Testing ───────────────────────────────────────────────────────
test:
	@echo "── unit tests (mock_swe, no real Swiss Ephemeris) ──"
	python3 -m pytest test_main.py -v --tb=short

test-coverage:
	@echo "── tests with coverage ──"
	python3 -m pytest test_main.py -v --cov=main --cov-report=term-missing

# ── Linting ──────────────────────────────────────────────────────
lint:
	@echo "── flake8 ──"
	python3 -m flake8 main.py app.py mock_swe.py --max-line-length=120 --ignore=E501,W503 || true
	@echo "── mypy ──"
	python3 -m mypy main.py app.py --ignore-missing-imports || true

# ── Docker build ─────────────────────────────────────────────────
build:
	@echo "── building Docker image $(IMAGE_NAME):$(IMAGE_TAG) ──"
	$(COMPOSE) build --no-cache api

# ── Docker run / compose ─────────────────────────────────────────
up:
	$(COMPOSE) up -d

down:
	$(COMPOSE) down --remove-orphans

restart: down up

logs:
	$(COMPOSE) logs -f api

shell:
	$(COMPOSE) run --rm api bash

# ── Ephemeris data ───────────────────────────────────────────────
ephe-download:
	@echo "── downloading Swiss Ephemeris data files ──"
	@mkdir -p ephe
	@echo "Downloading sepl1050.txt..."
	wget -q -O ephe/sepl1050.txt "http://www.astro.com/swissexp/sweph/sepl1050.txt" || \
	 wget -q -O ephe/sepl1050.txt "https://www.astrodatabank.com/download/sepl1050.txt" || \
	 echo "WARNING: Could not download ephemeris data"
	@ls -lh ephe/sepl1050.txt 2>/dev/null || true

# ── Production deploy ────────────────────────────────────────────
prod-up: build
	$(PROD_COMPOSE) up -d --build

prod-down:
	$(PROD_COMPOSE) down --remove-orphans

# ── Clean ────────────────────────────────────────────────────────
clean:
	rm -rf __pycache__ .pytest_cache *.egg-info build/ dist/
	find . -name '*.pyc' -delete
	find . -name '__pycache__' -type d -exec rm -rf {} + 2>/dev/null || true
