"""Abstract provider interface for database schema introspection."""

from abc import ABC, abstractmethod
from typing import Any

from text_to_sql_agent.models import RawIntrospectionResult


class SchemaIntrospectionProvider(ABC):
    """Abstract base class for dialect-specific schema introspection.
    
    Each database vendor (PostgreSQL, MySQL, SQLite, MSSQL, etc.) needs a
    concrete implementation of this interface to read schema metadata from
    the database and return a normalized `RawIntrospectionResult`.
    
    The introspection provider is responsible for:
    - Connecting to the database using the provided config
    - Reading tables, columns, constraints, indexes, etc.
    - Translating vendor-specific metadata into the common raw schema format
    - Handling errors and warnings gracefully
    - Returning a `RawIntrospectionResult` with all discovered schema metadata
    """

    @abstractmethod
    def introspect(
        self,
        database_id: str,
        connection_config: dict[str, Any],
    ) -> RawIntrospectionResult:
        """Introspect a database and return raw schema metadata.
        
        Args:
            database_id: Unique identifier for the target database (e.g., "prod_warehouse").
            connection_config: Connection parameters as a dict.
                Expected keys depend on the dialect; typically include:
                - "host": database server hostname or file path
                - "port": connection port (if applicable)
                - "database" or "dbname": database name
                - "username" or "user": database user
                - "password": database password (if required)
                - "extra_params": any dialect-specific connection options
        
        Returns:
            RawIntrospectionResult containing all discovered tables, columns,
            foreign keys, indexes, and any warnings or errors encountered.
        
        Raises:
            ConnectionError: If the provider cannot connect to the database.
            ValueError: If connection_config is invalid or incomplete.
            Exception: Any dialect-specific errors should be wrapped and raised
                with sufficient context.
        """
        pass
