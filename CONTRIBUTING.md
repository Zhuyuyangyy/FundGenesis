# Contributing to FundGenesis

Thank you for your interest in contributing to FundGenesis -- a narrative-driven financial reflexivity multi-agent world model.

## Development Setup

### Prerequisites

- Python 3.10+
- Git

### Getting Started

```bash
# Clone the repository
git clone <repo-url>
cd FundGenesis

# Create a virtual environment
python -m venv venv
source venv/bin/activate  # Linux/macOS
# or: venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt

# Run tests to verify setup
pytest tests/ -v
```

### Running the Dashboard

```bash
python dashboard/app.py --port 8765
# API docs at http://localhost:8765/docs
```

### Running Experiments

```bash
# V0.2 classic demos
python experiments/demo_positive_narrative.py
python experiments/demo_regulatory_shock.py
python experiments/demo_narrative_reversal.py

# Full benchmark suite
python experiments/run_bench.py --all --runs 5
```

## Project Architecture

```
core/           Core simulation engine (market, emotion, belief update)
agents/         Multi-agent decision logic (retail, trend, value)
narrative/      Narrative engine (event injection, propagation)
social/         KOL social network (4-tier topology)
trust/          Dynamic trust engine
monitor/        Reflexivity monitor (bubble/panic detection)
risk/           Manipulation risk detection + regulatory intervention
dashboard/      REST API + WebSocket server
experiments/    Demo scripts and benchmarks
tests/          Pytest test suite
```

### Core Causal Chain

The system enforces the Soros reflexivity causal chain:

```
Narrative -> Belief Shift -> Emotion Update -> Behavior Change -> Capital Flow -> Price Change
     ^                                                                          |
     └──────────────────────────────────────────────────────────────────────────┘
```

Narratives never directly modify prices -- they must pass through the full causal chain.

## Code Guidelines

### Style

- Follow PEP 8 conventions
- Use type hints for function signatures
- Use dataclasses for structured data
- Keep docstrings in both Chinese and English where appropriate (this is a bilingual project)

### Testing

- All new features must include tests in `tests/`
- Run the full test suite before submitting: `pytest tests/ -v`
- Tests should be fast and isolated -- use mocks for external dependencies
- Aim for meaningful coverage of decision logic, not just import checks

### Agent Design

When adding new agent types:

1. Subclass `BaseAgent` in `agents/`
2. Implement `decide(market, emotion) -> Action`
3. Implement `update_belief(market, order_imbalance)`
4. Set appropriate `AgentConfig` values (herding_coefficient, emotional_sensitivity, etc.)
5. Add tests in `tests/test_agents.py`

### Narrative Events

When adding new narrative categories:

1. Add the category to `NarrativeCategory` in `narrative/narrative_event.py`
2. Ensure the event follows the reflexivity causal chain
3. Add integration tests

## Submitting Changes

1. Create a feature branch from `main`
2. Make your changes with clear, atomic commits
3. Ensure all tests pass: `pytest tests/ -v`
4. Submit a pull request with a clear description of changes

### Commit Messages

Use conventional commit format:

```
feat(agents): add contrarian investor agent type
fix(belief): correct contradiction signal computation
test(monitor): add bubble risk edge case tests
docs(readme): update version matrix
```

## Reporting Issues

When reporting bugs, please include:

- Python version
- Steps to reproduce
- Expected vs actual behavior
- Relevant log output

## License

By contributing, you agree that your contributions will be licensed under the same license as the project.
