import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Literal

from jedify_lens.connectors.ds_types import QueryResult, QueryTimeout, QueryFailed


@dataclass
class EstimatedQueryCost:
    runtime_seconds: float
    cost_usd: float


def _exception_to_err_msg(e: Exception) -> str:
    err_msg = e.message if hasattr(e, "message") else str(e)
    return err_msg if err_msg else "Unknown error"


def _exception_to_query_res(e: Exception, permission_error: bool = False) -> QueryResult:
    if (
        isinstance(e, asyncio.TimeoutError)
        or isinstance(e, TimeoutError)
        or "timeout" in str(e).lower()
        or "job timed out" in str(e).lower()
        or "timeout" in type(e).__name__.lower()
    ):
        return QueryTimeout()

    return QueryFailed(
        message=_exception_to_err_msg(e),
        permission_error=permission_error,
    )


class DataClient(ABC):
    DEFAULT_VALIDATION_TIMEOUT_SEC = 30.0
    DEFAULT_RETRIEVAL_TIMEOUT_SEC = 300.0
    DEFAULT_MAX_RESULTS = 10_000

    def __init__(
        self,
        default_retrieval_timeout_sec: float | None = None,
        default_max_results: int | None = None,
    ):
        self.default_retrieval_timeout_sec = (
            default_retrieval_timeout_sec or self.DEFAULT_RETRIEVAL_TIMEOUT_SEC
        )
        self.default_max_results = default_max_results or self.DEFAULT_MAX_RESULTS

    def _get_timeout(self, timeout_sec: float | Literal["NO_TIMEOUT", "DEFAULT"]) -> float | None:
        if timeout_sec == "NO_TIMEOUT":
            return None
        elif timeout_sec == "DEFAULT":
            return self.default_retrieval_timeout_sec
        return timeout_sec

    def _get_max_results(self, max_results: int | Literal["NO_LIMIT", "DEFAULT"]) -> int | None:
        if max_results == "NO_LIMIT":
            return None
        elif max_results == "DEFAULT":
            return self.default_max_results
        return max_results

    def _get_validation_timeout(self, timeout_sec: float | Literal["NO_TIMEOUT", "DEFAULT"]) -> float | None:
        if timeout_sec == "NO_TIMEOUT":
            return None
        elif timeout_sec == "DEFAULT":
            return self.DEFAULT_VALIDATION_TIMEOUT_SEC
        return timeout_sec

    @abstractmethod
    async def query(
        self,
        query: str,
        *,
        max_results: int | Literal["NO_LIMIT", "DEFAULT"] = "DEFAULT",
        timeout_sec: float | Literal["NO_TIMEOUT", "DEFAULT"] = "DEFAULT",
    ) -> QueryResult:
        pass

    @abstractmethod
    async def get_table_metadata(self, table_name: str):
        pass

    @abstractmethod
    async def get_potential_tables(self) -> list[str]:
        pass

    async def close(self) -> None:
        pass
