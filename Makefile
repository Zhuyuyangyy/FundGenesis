.PHONY: test regression demo bench-mini bench-mini-seeds analyze-mini compare-regulation lint clean

test:
	pytest -q

regression:
	pytest tests/regression -q

demo:
	python main.py

bench-mini:
	python benchmarks/runner.py --suite mini --seeds 42 --output outputs/bench/mini

bench-mini-seeds:
	python benchmarks/runner.py --suite mini --seeds 0 1 2 3 4 5 6 7 8 9 --output outputs/bench/mini_10seed

analyze-mini:
	python -m reflexmarket.analysis.bootstrap --input outputs/bench/mini_10seed/summary.csv --output outputs/bench/mini_10seed/bootstrap_ci.json
	python -m reflexmarket.analysis.compare_conditions --input outputs/bench/mini_10seed/summary.csv --output outputs/bench/mini_10seed/regulation_comparison.json

compare-regulation:
	python -m reflexmarket.analysis.compare_conditions --input outputs/bench/mini_10seed/summary.csv --output outputs/bench/mini_10seed/regulation_comparison.json

lint:
	python -m py_compile core/market_environment.py
	python -m py_compile core/emotion_field.py
	python -m py_compile social/kol_network.py
	python -m py_compile risk/regulator_agent.py
	python -m py_compile risk/manipulation_risk_agent.py

clean:
	rm -rf .pytest_cache __pycache__ */__pycache__ outputs/tmp
	find . -name "*.pyc" -delete
	find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
