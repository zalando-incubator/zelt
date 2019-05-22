.PHONY: install
install:
	poetry install -E docs

.PHONY: test
test:
	poetry run pytest tests --cov-config .coveragerc --cov-report xml --cov=. .

.PHONY: lint
lint:
	poetry run pylint zelt > pylint-report.txt || true
	poetry run python -m readme_renderer README.rst -o /dev/null

.PHONY: docs
docs:
	poetry run $(MAKE) -C docs html
