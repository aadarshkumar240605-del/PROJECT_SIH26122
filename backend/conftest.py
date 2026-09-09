"""
conftest.py — Project-wide pytest configuration.

Registers the 'slow' marker and adds --runslow flag so that:
  - pytest          → slow tests are SKIPPED automatically
  - pytest --runslow → slow tests run
"""
import pytest


def pytest_addoption(parser):
    parser.addoption(
        "--runslow",
        action="store_true",
        default=False,
        help="Run tests marked @pytest.mark.slow (requires live server on port 8001).",
    )


def pytest_configure(config):
    config.addinivalue_line(
        "markers",
        "slow: marks tests as slow integration tests that call the live server "
        "(skip by default; run with --runslow).",
    )


def pytest_collection_modifyitems(config, items):
    if config.getoption("--runslow"):
        return  # --runslow given: do not skip slow tests
    skip_slow = pytest.mark.skip(reason="slow integration test — run with --runslow")
    for item in items:
        if "slow" in item.keywords:
            item.add_marker(skip_slow)
