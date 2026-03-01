"""BIR Trash Collection API client library."""

from .client import BirTrashAuthError, BirTrashClient, BirTrashConnectionError

__version__ = "0.1.2b1"

__all__ = [
    "BirTrashClient",
    "BirTrashAuthError",
    "BirTrashConnectionError",
    "__version__",
]
