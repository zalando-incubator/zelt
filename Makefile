.PHONY: install
install:
	poetry install

.PHONY: test
test:
	poetry run pytest tests --cov-config .coveragerc --cov-report xml --cov=. .

.PHONY: lint
lint:
	poetry run pylint zelt > pylint-report.txt || true
