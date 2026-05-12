import asyncio
import logging
import traceback
from typing import Literal

import asyncpg

from jedify_lens.connectors.base import DataClient, _exception_to_query_res
from jedify_lens.connectors.ds_types import QueryFailed, QueryOk, QueryResult
from jedify_lens.connectors.schema_types import (
    ColumnSchema,
    TableConstraints,
    TablePartition,
    TableSchema,
    ForeignKey,
)

logger = logging.getLogger("jedify_lens.postgres")


class PostgresConnector(DataClient):
    def __init__(self, dsn: str, default_retrieval_timeout_sec: float | None = None):
        super().__init__(default_retrieval_timeout_sec)
        self.dsn = dsn
        self._conn: asyncpg.Connection | None = None

    async def _get_conn(self) -> asyncpg.Connection:
        if self._conn is None or self._conn.is_closed():
            self._conn = await asyncpg.connect(self.dsn)
        return self._conn

    async def query(
        self,
        query: str,
        *,
        max_results: int | Literal["NO_LIMIT", "DEFAULT"] = "DEFAULT",
        timeout_sec: float | Literal["NO_TIMEOUT", "DEFAULT"] = "DEFAULT",
    ) -> QueryResult:
        max_results = self._get_max_results(max_results)
        timeout_sec = self._get_timeout(timeout_sec)
        try:
            conn = await self._get_conn()
            records = await asyncio.wait_for(conn.fetch(query), timeout=timeout_sec)
            data = [dict(r) for r in records]
            if max_results:
                data = data[:max_results]
            return QueryOk(data=data)
        except Exception as e:
            logger.warning(f"Postgres query failed: {e}")
            return _exception_to_query_res(e)

    async def get_table_metadata(self, full_table_name: str) -> TableSchema:
        schema_name, table = self._parse_table_name(full_table_name)
        try:
            res = await self.query(
                f"""
                SELECT column_name, data_type, is_nullable, col_description(
                    ('{schema_name}.{table}'::regclass)::oid, ordinal_position
                ) AS comment
                FROM information_schema.columns
                WHERE table_schema = '{schema_name}' AND table_name = '{table}'
                ORDER BY ordinal_position
                """
            )
            if isinstance(res, QueryFailed):
                raise RuntimeError(f"Failed to get columns: {res.message}")

            columns = [
                ColumnSchema(
                    column_name=row["column_name"],
                    type=row["data_type"],
                    is_nullable=row["is_nullable"] == "YES",
                    comment=row.get("comment") or "",
                )
                for row in res.data
            ]

            partitioning_field = ""
            partitioning_type = ""
            for col in columns:
                if "timestamp" in col.type.lower():
                    partitioning_type, partitioning_field = "timestamp", col.column_name
                    break
                elif "date" in col.type.lower():
                    partitioning_type, partitioning_field = "date", col.column_name
                    break

            count_res = await self.query(f'SELECT reltuples::bigint AS row_count FROM pg_class WHERE relname = \'{table}\'')
            row_count = None
            if isinstance(count_res, QueryOk) and count_res.data:
                row_count = count_res.data[0].get("row_count")

            constraints = await self._get_table_constraints(schema_name, table)

            return TableSchema(
                partition=TablePartition(
                    partitioning_type=partitioning_type,
                    partitioning_field=partitioning_field,
                    time_partitioning=partitioning_field,
                ),
                columns_schema=columns,
                constraints=constraints,
                row_count=row_count,
                comment="",
                is_view=False,
            )
        except Exception:
            logger.error(f"Error getting metadata for {full_table_name}: {traceback.format_exc()}")
            raise

    async def _get_table_constraints(self, schema: str, table: str) -> TableConstraints:
        pk_res = await self.query(
            f"""
            SELECT kcu.column_name
            FROM information_schema.table_constraints tc
            JOIN information_schema.key_column_usage kcu
              ON tc.constraint_name = kcu.constraint_name AND tc.table_schema = kcu.table_schema
            WHERE tc.constraint_type = 'PRIMARY KEY'
              AND tc.table_schema = '{schema}' AND tc.table_name = '{table}'
            """
        )
        pk = pk_res.data[0]["column_name"] if isinstance(pk_res, QueryOk) and pk_res.data else ""

        fk_res = await self.query(
            f"""
            SELECT kcu.column_name AS source_column, ccu.column_name AS target_column,
                   ccu.table_schema || '.' || ccu.table_name AS target_table
            FROM information_schema.table_constraints tc
            JOIN information_schema.key_column_usage kcu
              ON tc.constraint_name = kcu.constraint_name AND tc.table_schema = kcu.table_schema
            JOIN information_schema.constraint_column_usage ccu
              ON ccu.constraint_name = tc.constraint_name AND ccu.table_schema = tc.table_schema
            WHERE tc.constraint_type = 'FOREIGN KEY'
              AND tc.table_schema = '{schema}' AND tc.table_name = '{table}'
            """
        )
        fk_list = []
        if isinstance(fk_res, QueryOk):
            fk_list = [ForeignKey(**row) for row in fk_res.data]

        return TableConstraints(primary_key=pk, foreign_keys=fk_list)

    def _parse_table_name(self, full_name: str) -> tuple[str, str]:
        parts = full_name.split(".")
        if len(parts) >= 2:
            return parts[-2], parts[-1]
        return "public", parts[0]

    async def get_potential_tables(self) -> list[str]:
        res = await self.query(
            """
            SELECT table_schema, table_name
            FROM information_schema.tables
            WHERE table_schema NOT IN ('pg_catalog', 'information_schema')
              AND table_type IN ('BASE TABLE', 'VIEW')
            ORDER BY table_schema, table_name
            """
        )
        if isinstance(res, QueryFailed):
            return []
        return [f"{row['table_schema']}.{row['table_name']}" for row in res.data]

    async def close(self) -> None:
        if self._conn and not self._conn.is_closed():
            await self._conn.close()
