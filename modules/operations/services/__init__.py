"""Operations service facades."""

from modules.operations.services.predefined_queries_service import (
    PredefinedQueriesService,
    get_predefined_queries_service,
)

__all__ = ["PredefinedQueriesService", "get_predefined_queries_service"]
