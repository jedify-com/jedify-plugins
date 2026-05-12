from dataclasses import dataclass


@dataclass
class QueryOk:
    data: list[dict]


@dataclass
class QueryFailed:
    message: str
    permission_error: bool = False


@dataclass
class QueryTimeout:
    pass


QueryResult = QueryOk | QueryFailed | QueryTimeout


class QueryValidationError(Exception):
    def __init__(self, message: str):
        self.message = message
        super().__init__(message)
