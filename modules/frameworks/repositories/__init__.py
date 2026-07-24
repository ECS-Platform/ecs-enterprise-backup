"""Framework data repositories — swappable storage backends."""

from modules.frameworks.repositories.framework_control_repository import (
    FileFrameworkControlRepository,
    FrameworkControlRepository,
    clear_framework_control_repository_cache,
    get_framework_control_repository,
)

__all__ = [
    "FileFrameworkControlRepository",
    "FrameworkControlRepository",
    "clear_framework_control_repository_cache",
    "get_framework_control_repository",
]
