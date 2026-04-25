from pathlib import Path

import pytest
import yaml

from pydantic import ValidationError

from app.schemas.review_graph import ReviewGraphMapping
from app.services.review_graph.mapping_loader import (
    ReviewGraphMappingInvalid,
    ReviewGraphMappingNotFound,
    load_review_graph_mapping,
)


def test_review_graph_mapping_accepts_minimal_object_and_relation():
    payload = {
        "version": 1,
        "objects": [
            {
                "id": "feature.orders_api",
                "type": "FeatureContainer",
                "label": "OrdersApi",
                "refs": [{"kind": "symbol", "value": "backend.app.api.orders.OrdersApi"}],
            },
            {
                "id": "code.create_order",
                "type": "CodeUnit",
                "label": "create_order",
                "refs": [{"kind": "symbol", "value": "backend.app.services.order_service.create_order"}],
            },
        ],
        "relations": [{"from": "feature.orders_api", "to": "code.create_order", "type": "owns"}],
    }

    model = ReviewGraphMapping.model_validate(payload)

    assert model.version == 1
    assert model.objects[0].type == "FeatureContainer"
    assert model.relations[0].type == "owns"


@pytest.mark.parametrize("version", [0, 2])
def test_review_graph_mapping_rejects_unsupported_versions(version):
    payload = {
        "version": version,
        "objects": [
            {
                "id": "feature.orders_api",
                "type": "FeatureContainer",
                "label": "OrdersApi",
            }
        ],
        "relations": [],
    }

    with pytest.raises(ValidationError, match="Input should be 1"):
        ReviewGraphMapping.model_validate(payload)


def test_review_graph_mapping_rejects_duplicate_object_ids():
    payload = {
        "version": 1,
        "objects": [
            {"id": "feature.orders_api", "type": "FeatureContainer", "label": "OrdersApi"},
            {"id": "feature.orders_api", "type": "CodeUnit", "label": "Duplicate"},
        ],
        "relations": [],
    }

    with pytest.raises(ValidationError, match="duplicate object ids"):
        ReviewGraphMapping.model_validate(payload)


def test_review_graph_mapping_rejects_unknown_relation_object_ids():
    payload = {
        "version": 1,
        "objects": [{"id": "feature.orders_api", "type": "FeatureContainer", "label": "OrdersApi"}],
        "relations": [{"from": "feature.orders_api", "to": "code.create_order", "type": "owns"}],
    }

    with pytest.raises(ValidationError, match="relation.to references unknown object id"):
        ReviewGraphMapping.model_validate(payload)


def test_review_graph_mapping_serializes_relations_with_from_alias():
    payload = {
        "version": 1,
        "objects": [
            {"id": "feature.orders_api", "type": "FeatureContainer", "label": "OrdersApi"},
            {"id": "code.create_order", "type": "CodeUnit", "label": "create_order"},
        ],
        "relations": [{"from": "feature.orders_api", "to": "code.create_order", "type": "owns"}],
    }

    model = ReviewGraphMapping.model_validate(payload)
    dumped = model.model_dump(by_alias=True)

    assert dumped["relations"][0]["from"] == "feature.orders_api"
    assert "from_" not in dumped["relations"][0]


@pytest.mark.parametrize(
    "payload, field_name",
    [
        (
            {
                "version": 1,
                "objects": [{"id": "", "type": "FeatureContainer", "label": "OrdersApi"}],
                "relations": [],
            },
            "objects.0.id",
        ),
        (
            {
                "version": 1,
                "objects": [{"id": "feature.orders_api", "type": "FeatureContainer", "label": ""}],
                "relations": [],
            },
            "objects.0.label",
        ),
        (
            {
                "version": 1,
                "objects": [
                    {
                        "id": "feature.orders_api",
                        "type": "FeatureContainer",
                        "label": "OrdersApi",
                        "refs": [{"kind": "symbol", "value": ""}],
                    }
                ],
                "relations": [],
            },
            "objects.0.refs.0.value",
        ),
        (
            {
                "version": 1,
                "objects": [{"id": "feature.orders_api", "type": "FeatureContainer", "label": "OrdersApi"}],
                "relations": [{"from": "", "to": "feature.orders_api", "type": "owns"}],
            },
            "relations.0.from",
        ),
        (
            {
                "version": 1,
                "objects": [{"id": "feature.orders_api", "type": "FeatureContainer", "label": "OrdersApi"}],
                "relations": [{"from": "feature.orders_api", "to": "", "type": "owns"}],
            },
            "relations.0.to",
        ),
        (
            {
                "version": 1,
                "objects": [
                    {
                        "id": "feature.orders_api",
                        "type": "FeatureContainer",
                        "label": "OrdersApi",
                        "status": "archived",
                    }
                ],
                "relations": [],
            },
            "objects.0.status",
        ),
        (
            {
                "version": 1,
                "objects": [{"id": "feature.orders_api", "type": "FeatureContainer", "label": "OrdersApi"}],
                "relations": [
                    {
                        "from": "feature.orders_api",
                        "to": "feature.orders_api",
                        "type": "owns",
                        "confidence": "certain",
                    }
                ],
            },
            "relations.0.confidence",
        ),
    ],
)
def test_review_graph_mapping_rejects_invalid_strings_and_enums(payload, field_name):
    with pytest.raises(ValidationError, match=field_name):
        ReviewGraphMapping.model_validate(payload)


def test_load_review_graph_mapping_reads_yaml(tmp_path):
    path = tmp_path / "mapping.yaml"
    payload = {
        "version": 1,
        "objects": [
            {
                "id": "feature.orders_api",
                "type": "FeatureContainer",
                "label": "OrdersApi",
            }
        ],
        "relations": [],
    }
    path.write_text(yaml.safe_dump(payload), encoding="utf-8")

    model = load_review_graph_mapping(path)

    assert model.objects[0].id == "feature.orders_api"


def test_load_review_graph_mapping_rejects_duplicate_object_ids(tmp_path):
    path = tmp_path / "mapping.yaml"
    payload = {
        "version": 1,
        "objects": [
            {"id": "feature.orders_api", "type": "FeatureContainer", "label": "OrdersApi"},
            {"id": "feature.orders_api", "type": "CodeUnit", "label": "Duplicate"},
        ],
        "relations": [],
    }
    path.write_text(yaml.safe_dump(payload), encoding="utf-8")

    with pytest.raises(ReviewGraphMappingInvalid, match="invalid review graph mapping"):
        load_review_graph_mapping(path)


def test_repository_review_graph_mapping_is_valid():
    mapping_path = Path(__file__).resolve().parents[2] / "review_graph" / "mapping.yaml"
    model = load_review_graph_mapping(mapping_path)
    object_ids = {obj.id for obj in model.objects}
    relations = {(relation.from_, relation.to, relation.type) for relation in model.relations}

    assert "feature.change_impact" in object_ids
    assert "feature.verification" in object_ids
    assert "code.change_impact_adapter" in object_ids
    assert "code.verification_adapter" in object_ids
    assert "test.change_impact" in object_ids
    assert "test.verification" in object_ids

    assert ("feature.change_impact", "code.change_impact_adapter", "owns") in relations
    assert ("feature.verification", "code.verification_adapter", "owns") in relations
    assert ("test.change_impact", "feature.change_impact", "verifies_primary") in relations
    assert ("test.verification", "feature.verification", "verifies_primary") in relations


def test_load_review_graph_mapping_raises_on_missing_file(tmp_path):
    path = tmp_path / "missing.yaml"

    with pytest.raises(ReviewGraphMappingNotFound):
        load_review_graph_mapping(path)


def test_load_review_graph_mapping_raises_on_invalid_yaml(tmp_path):
    path = tmp_path / "mapping.yaml"
    path.write_text("version: [", encoding="utf-8")

    with pytest.raises(ReviewGraphMappingInvalid, match="invalid yaml"):
        load_review_graph_mapping(path)


def test_load_review_graph_mapping_raises_on_invalid_schema(tmp_path):
    path = tmp_path / "mapping.yaml"
    path.write_text(yaml.safe_dump({"version": 1, "objects": [{"id": "feature.x"}], "relations": []}), encoding="utf-8")

    with pytest.raises(ReviewGraphMappingInvalid, match="invalid review graph mapping"):
        load_review_graph_mapping(path)
