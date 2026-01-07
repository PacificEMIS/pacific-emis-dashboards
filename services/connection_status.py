"""
Connection status tracking for API and SQL data sources.

This module provides a centralized way to track the health of data connections
and report any issues to the user interface.
"""

import threading
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class ConnectionStatus:
    """Represents the status of a single data connection."""

    name: str
    source_type: str  # "api" or "sql"
    is_connected: bool = False
    last_success: Optional[datetime] = None
    last_error: Optional[datetime] = None
    error_message: Optional[str] = None

    def set_success(self):
        """Mark this connection as successful."""
        self.is_connected = True
        self.last_success = datetime.now()
        self.error_message = None

    def set_error(self, message: str):
        """Mark this connection as failed with an error message."""
        self.is_connected = False
        self.last_error = datetime.now()
        self.error_message = message


class ConnectionStatusRegistry:
    """Thread-safe registry for tracking all data connection statuses."""

    def __init__(self):
        self._statuses: dict[str, ConnectionStatus] = {}
        self._lock = threading.Lock()

    def register(self, name: str, source_type: str) -> ConnectionStatus:
        """Register a new connection to track."""
        with self._lock:
            if name not in self._statuses:
                self._statuses[name] = ConnectionStatus(
                    name=name, source_type=source_type
                )
            return self._statuses[name]

    def get(self, name: str) -> Optional[ConnectionStatus]:
        """Get the status of a specific connection."""
        with self._lock:
            return self._statuses.get(name)

    def set_success(self, name: str):
        """Mark a connection as successful."""
        with self._lock:
            if name in self._statuses:
                self._statuses[name].set_success()

    def set_error(self, name: str, message: str):
        """Mark a connection as failed."""
        with self._lock:
            if name in self._statuses:
                self._statuses[name].set_error(message)

    def get_all_errors(self) -> list[ConnectionStatus]:
        """Get all connections that currently have errors."""
        with self._lock:
            return [s for s in self._statuses.values() if not s.is_connected]

    def get_all_statuses(self) -> list[ConnectionStatus]:
        """Get all connection statuses."""
        with self._lock:
            return list(self._statuses.values())

    def has_errors(self) -> bool:
        """Check if any connection has an error."""
        with self._lock:
            return any(not s.is_connected for s in self._statuses.values())


# Global registry instance
connection_registry = ConnectionStatusRegistry()

# Pre-register known connections
connection_registry.register("SQL Server", "sql")
connection_registry.register("API Authentication", "api")
connection_registry.register("API Data", "api")
