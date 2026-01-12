.PHONY: install dev test lint format docker-build docker-up docker-down k8s-deploy clean

# Install dependencies
install:
	pip install -r requirements.txt

# Development setup
dev: install
	docker-compose up -d postgres redis
	alembic upgrade head
	uvicorn hornet.main:app --reload

# Run tests
test:
	pytest -v

# Run tests with coverage
test-cov:
	pytest --cov=hornet --cov-report=html

# Lint code
lint:
	ruff check hornet tests
	mypy hornet

# Format code
format:
	black hornet tests
	ruff check --fix hornet tests

# Build Docker image
docker-build:
	docker build -t hornet:latest .

# Start all services with Docker Compose
docker-up:
	docker-compose up -d

# Stop all services
docker-down:
	docker-compose down

# View logs
docker-logs:
	docker-compose logs -f

# Deploy to Kubernetes
k8s-deploy:
	kubectl apply -f k8s/namespace.yaml
	kubectl apply -f k8s/configmap.yaml
	kubectl apply -f k8s/secrets.yaml
	kubectl apply -f k8s/serviceaccount.yaml
	kubectl apply -f k8s/networkpolicy.yaml
	kubectl apply -f k8s/postgres.yaml
	kubectl apply -f k8s/redis.yaml
	kubectl apply -f k8s/deployment.yaml
	kubectl apply -f k8s/service.yaml
	kubectl apply -f k8s/ingress.yaml
	kubectl apply -f k8s/hpa.yaml

# Run database migrations
migrate:
	alembic upgrade head

# Generate new migration
migration:
	alembic revision --autogenerate -m "$(msg)"

# Run synthetic events
synth:
	python scripts/synth.py --scenario $(scenario) -v

# Run all scenarios
synth-all:
	python scripts/synth.py -s brute_force
	python scripts/synth.py -s ransomware
	python scripts/synth.py -s phishing
	python scripts/synth.py -s exfil
	python scripts/synth.py -s c2_beacon

# Clean up
clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	rm -rf .pytest_cache .coverage htmlcov

# Show help
help:
	@echo "HORNET Makefile Commands:"
	@echo "  make install      - Install dependencies"
	@echo "  make dev          - Start development environment"
	@echo "  make test         - Run tests"
	@echo "  make test-cov     - Run tests with coverage"
	@echo "  make lint         - Lint code"
	@echo "  make format       - Format code"
	@echo "  make docker-build - Build Docker image"
	@echo "  make docker-up    - Start Docker Compose"
	@echo "  make docker-down  - Stop Docker Compose"
	@echo "  make k8s-deploy   - Deploy to Kubernetes"
	@echo "  make migrate      - Run database migrations"
	@echo "  make synth scenario=brute_force - Run synthetic scenario"
	@echo "  make clean        - Clean up"
