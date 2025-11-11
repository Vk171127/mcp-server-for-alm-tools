"""
Database Manager for PostgreSQL/CloudSQL Connections
Handles async database operations for the ALM traceability system
"""

import asyncio
import logging
import os
from typing import Optional, Dict, Any, List
import asyncpg
from contextlib import asynccontextmanager
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class DatabaseConfig:
    """Database connection configuration"""
    host: str
    port: int
    database: str
    user: str
    password: str
    ssl_mode: str = "require"
    min_connections: int = 5
    max_connections: int = 20
    command_timeout: int = 60

class DatabaseManager:
    """Async PostgreSQL database manager with connection pooling"""

    def __init__(self, config: DatabaseConfig = None):
        self.config = config or self._load_config_from_env()
        self.pool: Optional[asyncpg.Pool] = None
        self._is_initialized = False

    def _load_config_from_env(self) -> DatabaseConfig:
        """Load database configuration from environment variables"""
        return DatabaseConfig(
            host=os.getenv("DB_HOST", "localhost"),
            port=int(os.getenv("DB_PORT", "5432")),
            database=os.getenv("DB_NAME", "alm_traceability"),
            user=os.getenv("DB_USER", "postgres"),
            password=os.getenv("DB_PASSWORD", ""),
            ssl_mode=os.getenv("DB_SSL_MODE", "require"),
            min_connections=int(os.getenv("DB_MIN_CONNECTIONS", "5")),
            max_connections=int(os.getenv("DB_MAX_CONNECTIONS", "20")),
            command_timeout=int(os.getenv("DB_COMMAND_TIMEOUT", "60"))
        )

    async def initialize(self) -> Dict[str, Any]:
        """Initialize database connection pool"""
        try:
            if self._is_initialized:
                return {"success": True, "message": "Already initialized"}

            # Build connection string
            dsn = f"postgresql://{self.config.user}:{self.config.password}@{self.config.host}:{self.config.port}/{self.config.database}"

            # Create connection pool
            self.pool = await asyncpg.create_pool(
                dsn,
                min_size=self.config.min_connections,
                max_size=self.config.max_connections,
                command_timeout=self.config.command_timeout,
                ssl=self.config.ssl_mode if self.config.ssl_mode != "disable" else None
            )

            # Test connection
            async with self.pool.acquire() as connection:
                result = await connection.fetchval("SELECT version()")
                logger.info(f"Connected to PostgreSQL: {result}")

            self._is_initialized = True

            return {
                "success": True,
                "message": "Database initialized successfully",
                "host": self.config.host,
                "database": self.config.database,
                "pool_size": f"{self.config.min_connections}-{self.config.max_connections}"
            }

        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    async def close(self):
        """Close database connection pool"""
        if self.pool:
            await self.pool.close()
            self.pool = None
            self._is_initialized = False
            logger.info("Database connection pool closed")

    @asynccontextmanager
    async def get_connection(self):
        """Get a database connection from the pool"""
        if not self._is_initialized:
            raise RuntimeError("Database not initialized. Call initialize() first.")

        async with self.pool.acquire() as connection:
            yield connection

    async def execute_schema(self, schema_file_path: str) -> Dict[str, Any]:
        """Execute schema SQL file to set up database"""
        try:
            async with open(schema_file_path, 'r') as f:
                schema_sql = f.read()

            async with self.get_connection() as conn:
                async with conn.transaction():
                    await conn.execute(schema_sql)

            logger.info(f"Schema executed successfully from {schema_file_path}")
            return {
                "success": True,
                "message": "Schema executed successfully",
                "schema_file": schema_file_path
            }

        except Exception as e:
            logger.error(f"Failed to execute schema: {e}")
            return {
                "success": False,
                "error": str(e),
                "schema_file": schema_file_path
            }

    async def fetch_one(self, query: str, *args) -> Optional[Dict[str, Any]]:
        """Execute query and fetch one row"""
        try:
            async with self.get_connection() as conn:
                row = await conn.fetchrow(query, *args)
                return dict(row) if row else None
        except Exception as e:
            logger.error(f"Failed to fetch one: {e}")
            raise

    async def fetch_all(self, query: str, *args) -> List[Dict[str, Any]]:
        """Execute query and fetch all rows"""
        try:
            async with self.get_connection() as conn:
                rows = await conn.fetch(query, *args)
                return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Failed to fetch all: {e}")
            raise

    async def execute(self, query: str, *args) -> str:
        """Execute query and return status"""
        try:
            async with self.get_connection() as conn:
                result = await conn.execute(query, *args)
                return result
        except Exception as e:
            logger.error(f"Failed to execute query: {e}")
            raise

    async def execute_transaction(self, queries: List[tuple]) -> Dict[str, Any]:
        """Execute multiple queries in a transaction"""
        try:
            async with self.get_connection() as conn:
                async with conn.transaction():
                    results = []
                    for query, args in queries:
                        result = await conn.execute(query, *args)
                        results.append(result)

                    return {
                        "success": True,
                        "results": results,
                        "queries_executed": len(queries)
                    }

        except Exception as e:
            logger.error(f"Transaction failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    async def test_connection(self) -> Dict[str, Any]:
        """Test database connection and return status"""
        try:
            if not self._is_initialized:
                await self.initialize()

            async with self.get_connection() as conn:
                # Test basic query
                version = await conn.fetchval("SELECT version()")

                # Test our enum exists
                enum_check = await conn.fetchval("""
                    SELECT EXISTS (
                        SELECT 1 FROM pg_type
                        WHERE typname = 'alm_platform_type'
                    )
                """)

                # Test traceability_links table exists
                table_check = await conn.fetchval("""
                    SELECT EXISTS (
                        SELECT 1 FROM information_schema.tables
                        WHERE table_name = 'traceability_links'
                    )
                """)

                return {
                    "success": True,
                    "connection_status": "active",
                    "postgresql_version": version,
                    "alm_platform_type_enum_exists": bool(enum_check),
                    "traceability_links_table_exists": bool(table_check),
                    "pool_size": self.pool.get_size() if self.pool else 0
                }

        except Exception as e:
            logger.error(f"Connection test failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "connection_status": "failed"
            }

    async def get_table_info(self, table_name: str) -> Dict[str, Any]:
        """Get information about a specific table"""
        try:
            async with self.get_connection() as conn:
                # Get column information
                columns = await conn.fetch("""
                    SELECT column_name, data_type, is_nullable, column_default
                    FROM information_schema.columns
                    WHERE table_name = $1
                    ORDER BY ordinal_position
                """, table_name)

                # Get row count
                count_query = f"SELECT COUNT(*) FROM {table_name}"
                row_count = await conn.fetchval(count_query)

                return {
                    "success": True,
                    "table_name": table_name,
                    "columns": [dict(col) for col in columns],
                    "row_count": row_count,
                    "exists": len(columns) > 0
                }

        except Exception as e:
            logger.error(f"Failed to get table info for {table_name}: {e}")
            return {
                "success": False,
                "error": str(e),
                "table_name": table_name
            }

# Global database manager instance
db_manager = DatabaseManager()

# Convenience functions for global access
async def initialize_database() -> Dict[str, Any]:
    """Initialize the global database manager"""
    return await db_manager.initialize()

async def get_db_connection():
    """Get database connection from global manager"""
    return db_manager.get_connection()

async def close_database():
    """Close the global database manager"""
    await db_manager.close()