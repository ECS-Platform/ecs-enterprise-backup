"""ECS scripts package marker.

Exists so module-style execution works from the repo root on every shell
(including Windows Git Bash):

    PYTHONPATH=. python3 -m scripts.run_enterprise_benchmark --config benchmarks/config/enterprise_workload_config.json

Adding this marker does not change the existing ``python scripts/<name>.py``
invocation style.
"""
