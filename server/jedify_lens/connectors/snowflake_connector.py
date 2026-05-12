import asyncio
import logging
import re
import time
import traceback
from contextlib import suppress
from datetime import datetime, timedelta
from typing import Literal

import snowflake.connector
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
from snowflake.connector.errors import ProgrammingError

from jedify_lens.connectors.base import DataClient, _exception_to_query_res
from jedify_lens.connectors.ds_types import QueryFailed, QueryOk, QueryResult
from jedify_lens.connectors.schema_types import (
    ColumnSchema,
    TableConstraints,
    TablePartition,
    TableSchema,
    ForeignKey,
)

logger = logging.getLogger("jedify_lens.snowflake")

_SANITIZE_RE = re.compile(r"[^A-Za-z0-9_-]")
_WRAPPING_QUOTES_RE = re.compile(r"^[`]*|[`]*$")


def _sanitize(s: str) -> str:
    s = s.strip()
    res = _SANITIZE_RE.sub("", s)
    if res != s:
        raise ValueError(f"sanitized value {res} differs from original {s}")
    return res


def _strip_wrapping_quotes(s: str) -> str:
    return _WRAPPING_QUOTES_RE.sub("", s)


class SnowflakeConnector(DataClient):
    DEFAULT_VALIDATION_TIMEOUT_SEC = 120.0

    def __init__(
        self,
        account: str,
        user: str,
        password: str | None = None,
        private_key: str | None = None,
        passphrase: str | None = None,
        database: str | None = None,
        schema: str | None = None,
        warehouse: str | None = None,
        role: str | None = None,
        default_retrieval_timeout_sec: float | None = None,
    ):
        super().__init__(default_retrieval_timeout_sec)

        creds: dict = {"account": account, "user": user}
        if password:
            creds["password"] = password
        if database:
            creds["database"] = database
        if schema:
            creds["schema"] = schema
        if warehouse:
            creds["warehouse"] = warehouse

        if private_key:
            pwd = passphrase.encode("utf-8") if passphrase else None
            p_key = serialization.load_pem_private_key(
                private_key.encode("utf-8"),
                password=pwd,
                backend=default_backend(),
            )
            creds["private_key"] = p_key

        creds["use_arrow_resultset"] = True
        creds["client_session_keep_alive"] = True

        self.connection_args = creds
        self.role = _sanitize(role) if role else None
        self.conn = None
        self.conn_lock = asyncio.Lock()

    async def _ensure_connection(self):
        async with self.conn_lock:
            if self.conn is not None:
                return self.conn

            conn = await asyncio.wait_for(
                asyncio.to_thread(snowflake.connector.connect, **self.connection_args),
                timeout=30,
            )

            if self.role:
                res = await self._query_with_conn(conn, f"USE ROLE {self.role};")
                if not isinstance(res, QueryOk):
                    raise RuntimeError(f"Failed to set role {self.role}: {res}")
                await self._query_with_conn(conn, "USE SECONDARY ROLES NONE;")

            self.conn = conn
            return self.conn

    async def _perform_query(self, conn, cursor, query: str, timeout_sec=None):
        query = _strip_wrapping_quotes(query)
        query_details = await asyncio.to_thread(
            cursor.execute_async, query, timeout=timeout_sec
        )
        query_id = query_details["queryId"]

        start_time = time.time()
        while True:
            status = await asyncio.to_thread(conn.get_query_status, query_id)
            if not conn.is_still_running(status):
                break
            if timeout_sec and (time.time() - start_time) > timeout_sec:
                raise TimeoutError(f"Query timed out (status: {status})")
            await asyncio.sleep(0.25)

        await asyncio.to_thread(cursor.get_results_from_sfqid, query_id)
        return query_id

    async def _query_with_conn(
        self,
        conn,
        query: str,
        *,
        max_results: int | Literal["NO_LIMIT", "DEFAULT"] = "DEFAULT",
        timeout_sec: float | Literal["NO_TIMEOUT", "DEFAULT"] = "DEFAULT",
    ) -> QueryResult:
        max_results = self._get_max_results(max_results)
        timeout_sec = self._get_timeout(timeout_sec)

        try:
            with conn.cursor() as cursor:
                await self._perform_query(conn, cursor, query, timeout_sec)

                records = cursor.fetchmany(max_results) if max_results else cursor.fetchall()
                columns = [desc[0] for desc in cursor.description]
                data = [dict(zip(columns, record)) for record in records]
                if max_results:
                    data = data[:max_results]
            return QueryOk(data=data)

        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.warning(f"Snowflake query failed: {e}\n{traceback.format_exc()}")
            return _exception_to_query_res(e)

    async def query(
        self,
        query: str,
        *,
        max_results: int | Literal["NO_LIMIT", "DEFAULT"] = "DEFAULT",
        timeout_sec: float | Literal["NO_TIMEOUT", "DEFAULT"] = "DEFAULT",
    ) -> QueryResult:
        conn = await self._ensure_connection()
        return await self._query_with_conn(conn, query, max_results=max_results, timeout_sec=timeout_sec)

    async def get_table_metadata(self, full_table_name: str) -> TableSchema:
        database, schema_name, table = self._parse_full_table_name(full_table_name)
        try:
            res = await self.query(f'DESCRIBE TABLE "{database}"."{schema_name}"."{table}"')
            if isinstance(res, QueryFailed):
                raise RuntimeError(f"Failed to describe table: {res.message}")

            table_info = await self.query(
                f"SELECT table_type, comment FROM {database}.INFORMATION_SCHEMA.TABLES "
                f"WHERE table_catalog = '{database}' AND table_schema = '{schema_name}' AND table_name = '{table}'"
            )
            is_view = False
            comment = ""
            if isinstance(table_info, QueryOk) and table_info.data:
                row = table_info.data[0]
                is_view = "VIEW" in (row.get("TABLE_TYPE") or "").upper()
                comment = row.get("comment") or row.get("COMMENT") or ""

            columns = res.data
            partitioning_type = ""
            partitioning_field = ""
            for col in columns:
                col_type = col.get("type", "")
                if "TIMESTAMP" in col_type or "DATETIME" in col_type:
                    partitioning_type, partitioning_field = "timestamp", col.get("name")
                    break
                elif "DATE" in col_type:
                    partitioning_type, partitioning_field = "date", col.get("name")
                    break

            schema = [
                ColumnSchema(
                    column_name=x.get("name"),
                    type=x.get("type"),
                    is_nullable=x.get("null?") == "Y",
                    comment=x.get("comment") or "",
                )
                for x in columns
            ]

            row_count = None
            show_res = await self.query(f"""SHOW OBJECTS LIKE '{table}' IN SCHEMA "{database}"."{schema_name}";""")
            if isinstance(show_res, QueryOk) and show_res.data and show_res.data[0].get("kind") == "TABLE":
                with suppress(Exception):
                    row_count = int(show_res.data[0].get("rows") or 0) or None

            constraints = await self._get_table_constraints(full_table_name)

            return TableSchema(
                partition=TablePartition(
                    partitioning_type=partitioning_type,
                    partitioning_field=partitioning_field or "",
                    time_partitioning=partitioning_field or "",
                ),
                columns_schema=schema,
                constraints=constraints,
                row_count=row_count,
                comment=comment,
                is_view=is_view,
                last_updated=datetime.now(),
            )
        except Exception as e:
            logger.error(f"Error getting metadata for {full_table_name}: {traceback.format_exc()}")
            raise

    async def _get_table_constraints(self, full_table_name: str) -> TableConstraints:
        database, schema, table = self._parse_full_table_name(full_table_name)

        pk_name = ""
        res = await self.query(f'SHOW PRIMARY KEYS IN TABLE "{database}"."{schema}"."{table}"')
        if isinstance(res, QueryOk):
            for row in res.data:
                pk_name = row.get("column_name") or row.get("COLUMN_NAME") or ""

        fk_list = []
        res = await self.query(f'SHOW IMPORTED KEYS IN TABLE "{database}"."{schema}"."{table}"')
        if isinstance(res, QueryOk):
            for r in res.data:
                fk_list.append(ForeignKey(
                    source_column=r["fk_column_name"],
                    target_column=r["pk_column_name"],
                    target_table=f"{r['pk_database_name']}.{r['pk_schema_name']}.{r['pk_table_name']}",
                ))

        unique_keys = []
        res = await self.query(f'SHOW UNIQUE KEYS IN TABLE "{database}"."{schema}"."{table}"')
        if isinstance(res, QueryOk):
            unique_keys = [r.get("column_name") or r.get("COLUMN_NAME") for r in res.data]

        not_null = []
        res = await self.query(
            f"SELECT column_name FROM {database}.INFORMATION_SCHEMA.COLUMNS "
            f"WHERE TABLE_CATALOG = '{database}' AND TABLE_SCHEMA = '{schema}' "
            f"AND TABLE_NAME = '{table}' AND IS_NULLABLE = 'NO';"
        )
        if isinstance(res, QueryOk):
            not_null = [r.get("column_name") or r.get("COLUMN_NAME") for r in res.data]

        return TableConstraints(
            primary_key=pk_name,
            foreign_keys=fk_list,
            unique_keys=unique_keys,
            not_null=not_null,
        )

    def _parse_full_table_name(self, full_name: str) -> tuple[str, str, str]:
        token_pattern = r'"([^"]+)"|([^.]+)'
        parts = [m[0] if m[0] else m[1] for m in re.findall(token_pattern, full_name)]
        if len(parts) >= 3:
            return parts[0], parts[1], ".".join(parts[2:])
        elif len(parts) == 2:
            return "", parts[0], parts[1]
        return "", "", parts[0]

    async def get_potential_tables(self) -> list[str]:
        all_tables = []
        try:
            databases_res = await self.query("SHOW DATABASES;")
            if not isinstance(databases_res, QueryOk):
                return []

            databases = [
                row.get("name") or row.get("NAME")
                for row in databases_res.data
                if (row.get("name") or row.get("NAME")) and "SNOWFLAKE" not in (row.get("name") or row.get("NAME"))
            ]

            for database in databases:
                try:
                    schemas_res = await self.query(f'SHOW SCHEMAS IN DATABASE "{database}";')
                    if not isinstance(schemas_res, QueryOk):
                        continue

                    schemas = [
                        row.get("name") or row.get("NAME")
                        for row in schemas_res.data
                        if (row.get("name") or row.get("NAME", "")).upper() != "INFORMATION_SCHEMA"
                    ]

                    for schema in schemas:
                        try:
                            tables_res = await self.query(f'SHOW TABLES IN SCHEMA "{database}"."{schema}";')
                            views_res = await self.query(f'SHOW VIEWS IN SCHEMA "{database}"."{schema}";')

                            if isinstance(tables_res, QueryOk):
                                for row in tables_res.data:
                                    name = row.get("name") or row.get("NAME")
                                    if name:
                                        all_tables.append(f"{database}.{schema}.{name}")

                            if isinstance(views_res, QueryOk):
                                for row in views_res.data:
                                    name = row.get("name") or row.get("NAME")
                                    if name:
                                        all_tables.append(f"{database}.{schema}.{name}")
                        except Exception:
                            continue
                except Exception:
                    continue

            return all_tables
        except Exception as e:
            logger.error(f"Error in get_potential_tables: {e}")
            return []

    async def close(self) -> None:
        if self.conn is not None:
            self.conn.close()
