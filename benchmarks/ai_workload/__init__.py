"""ECS AI workload benchmark package.

Holds the existing lightweight runner plus the enterprise extension modules:
``workload_profiles``, ``bench_statistics``, ``capacity_planning``,
``reporting`` and ``enterprise_runner``. All of them REUSE the existing ECS RAG
pipeline (``ecs_platform.rag.answer``) and its built-in instrumentation; none of
them modify ECS or the instrumentation.
"""
