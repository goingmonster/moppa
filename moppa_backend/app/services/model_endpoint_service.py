from app.models.model_endpoint_model import ModelEndpointCreateModel, ModelEndpointUpdateModel
from app.repositories.model_endpoint_repository import ModelEndpointRepository


class ModelEndpointService:
    def __init__(self, repository: ModelEndpointRepository) -> None:
        self.repository = repository

    def list_paginated(self, page: int, page_size: int) -> tuple[list[dict[str, object]], int]:
        return self.repository.list_paginated(page=page, page_size=page_size)

    def create(self, payload: ModelEndpointCreateModel) -> dict[str, object]:
        return self.repository.create(payload)

    def get_by_id(self, endpoint_id: str) -> dict[str, object] | None:
        return self.repository.get_by_id(endpoint_id)

    def update(self, endpoint_id: str, payload: ModelEndpointUpdateModel) -> dict[str, object] | None:
        return self.repository.update(endpoint_id, payload)

    def batch_delete(self, ids: list[str]) -> int:
        return self.repository.batch_soft_delete(ids)
