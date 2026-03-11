from app.models.data_source_model import DataSourceCreateModel, DataSourceUpdateModel
from app.repositories.data_source_repository import DataSourceRepository


class DataSourceService:
    def __init__(self, repository: DataSourceRepository) -> None:
        self.repository = repository

    def list_paginated(self, page: int, page_size: int) -> tuple[list[dict[str, object]], int]:
        return self.repository.list_paginated(page=page, page_size=page_size)

    def create(self, payload: DataSourceCreateModel) -> dict[str, object]:
        return self.repository.create(payload)

    def get_by_id(self, source_id: str) -> dict[str, object] | None:
        return self.repository.get_by_id(source_id)

    def update(self, source_id: str, payload: DataSourceUpdateModel) -> dict[str, object] | None:
        return self.repository.update(source_id, payload)

    def batch_delete(self, ids: list[str]) -> int:
        return self.repository.batch_soft_delete(ids)
