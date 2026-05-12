import os

from jedify_lens.connectors.base import DataClient


def connector_from_env() -> DataClient:
    """Create a DataClient from environment variables."""
    warehouse_type = os.environ.get("WAREHOUSE_TYPE", "").lower()

    if warehouse_type == "snowflake":
        from jedify_lens.connectors.snowflake_connector import SnowflakeConnector
        return SnowflakeConnector(
            account=_require("SNOWFLAKE_ACCOUNT"),
            user=_require("SNOWFLAKE_USER"),
            password=os.environ.get("SNOWFLAKE_PASSWORD"),
            private_key=os.environ.get("SNOWFLAKE_PRIVATE_KEY"),
            passphrase=os.environ.get("SNOWFLAKE_PASSPHRASE"),
            database=os.environ.get("SNOWFLAKE_DATABASE"),
            schema=os.environ.get("SNOWFLAKE_SCHEMA"),
            warehouse=os.environ.get("SNOWFLAKE_WAREHOUSE"),
            role=os.environ.get("SNOWFLAKE_ROLE"),
        )

    if warehouse_type in ("postgres", "postgresql"):
        from jedify_lens.connectors.postgres_connector import PostgresConnector
        return PostgresConnector(dsn=_require("POSTGRES_DSN"))

    if warehouse_type == "redshift":
        from jedify_lens.connectors.postgres_connector import PostgresConnector
        return PostgresConnector(dsn=_require("REDSHIFT_DSN"))

    raise ValueError(
        f"Unsupported or missing WAREHOUSE_TYPE: '{warehouse_type}'. "
        "Supported values: snowflake, postgres, redshift."
    )


def _require(env_var: str) -> str:
    value = os.environ.get(env_var)
    if not value:
        raise ValueError(f"Required environment variable {env_var} is not set.")
    return value
