"""BIR Trash Collection API client library."""

from importlib.metadata import PackageNotFoundError, version

from .client import BirTrashAuthError, BirTrashClient, BirTrashConnectionError

try:
    __version__ = version("birtrashclient")
except PackageNotFoundError:
    __version__ = "unknown"

__all__ = [
    "BirTrashClient",
    "BirTrashAuthError",
    "BirTrashConnectionError",
    "__version__",
]
