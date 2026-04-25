from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import ValidationError

from app.schemas.review_graph import ReviewGraphMapping


class ReviewGraphMappingError(Exception):
    pass


class ReviewGraphMappingNotFound(FileNotFoundError):
    pass


class ReviewGraphMappingInvalid(ReviewGraphMappingError):
    pass


def load_review_graph_mapping(path: Path) -> ReviewGraphMapping:
    if not path.exists():
        raise ReviewGraphMappingNotFound(str(path))

    try:
        with path.open("r", encoding="utf-8") as handle:
            payload = yaml.safe_load(handle)
    except yaml.YAMLError as exc:
        raise ReviewGraphMappingInvalid(f"invalid yaml in {path}") from exc

    try:
        return ReviewGraphMapping.model_validate(payload)
    except ValidationError as exc:
        raise ReviewGraphMappingInvalid(f"invalid review graph mapping in {path}") from exc
