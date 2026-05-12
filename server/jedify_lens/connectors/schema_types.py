from datetime import datetime
from pydantic import BaseModel


class ColumnSchema(BaseModel):
    column_name: str
    type: str
    is_nullable: bool
    comment: str = ""


class ForeignKey(BaseModel):
    source_column: str
    target_column: str
    target_table: str


class TableConstraints(BaseModel):
    primary_key: str = ""
    foreign_keys: list[ForeignKey] = []
    unique_keys: list[str] = []
    not_null: list[str] = []


class TablePartition(BaseModel):
    partitioning_type: str = ""
    partitioning_field: str = ""
    time_partitioning: str = ""


class TableSchema(BaseModel):
    partition: TablePartition
    clustering_fields: list[str] = []
    columns_schema: list[ColumnSchema]
    constraints: TableConstraints
    row_count: int | None = None
    comment: str = ""
    is_view: bool | None = None
    last_updated: datetime | None = None
