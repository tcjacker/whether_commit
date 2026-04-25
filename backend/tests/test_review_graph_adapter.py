from __future__ import annotations

from pathlib import Path
import yaml
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.api.endpoints import review_graph as review_graph_endpoint
from app.services.review_graph.adapter import ReviewGraphAdapter
from app.main import app
from app.services.snapshot_store.store import store as snapshot_store


def test_review_graph_adapter_expands_related_nodes_indirectly(tmp_path):
    mapping_path = tmp_path / "mapping.yaml"
    mapping_path.write_text(
        yaml.safe_dump(
            {
                "version": 1,
                "objects": [
                    {
                        "id": "feature.change_impact",
                        "type": "FeatureContainer",
                        "label": "change_impact",
                        "refs": [{"kind": "file", "value": "backend/app/services/change_impact/adapter.py"}],
                    },
                    {
                        "id": "test.change_impact",
                        "type": "TestUnit",
                        "label": "test_change_impact_adapter",
                        "refs": [{"kind": "test_file", "value": "backend/tests/test_change_impact_adapter.py"}],
                    },
                ],
                "relations": [
                    {"from": "test.change_impact", "to": "feature.change_impact", "type": "verifies_primary"}
                ],
            }
        ),
        encoding="utf-8",
    )

    adapter = ReviewGraphAdapter(mapping_path)
    result = adapter.build(
        "repo-1",
        {
            "change_id": "chg-123",
            "change_title": "change impact",
            "changed_files": ["backend/app/services/change_impact/adapter.py"],
            "linked_tests": [],
            "changed_symbols": [],
        },
        {"missing_tests_for_changed_paths": []},
    )

    assert result["summary"]["direct_feature_count"] == 1
    node_ids = {node["id"] for node in result["nodes"]}
    assert {"feature.change_impact", "test.change_impact"} <= node_ids
    assert any(edge["type"] == "verifies_primary" for edge in result["edges"])
    assert all(edge["from"] in node_ids and edge["to"] in node_ids for edge in result["edges"])


def test_review_graph_adapter_marks_direct_vs_expanded_nodes_and_layers(tmp_path):
    mapping_path = tmp_path / "mapping.yaml"
    mapping_path.write_text(
        yaml.safe_dump(
            {
                "version": 1,
                "objects": [
                    {
                        "id": "feature.orders_api",
                        "type": "FeatureContainer",
                        "label": "OrdersApi",
                        "refs": [{"kind": "file", "value": "backend/app/api/orders.py"}],
                    },
                    {
                        "id": "code.create_order",
                        "type": "CodeUnit",
                        "label": "create_order",
                        "refs": [{"kind": "symbol", "value": "backend.app.services.order_service.create_order"}],
                    },
                    {
                        "id": "test.orders_api",
                        "type": "TestUnit",
                        "label": "Orders API tests",
                        "refs": [{"kind": "test_file", "value": "backend/tests/api/test_orders.py"}],
                    },
                    {
                        "id": "feature.merchant_status_api",
                        "type": "FeatureContainer",
                        "label": "MerchantStatusApi",
                        "refs": [{"kind": "file", "value": "backend/app/api/merchant_status.py"}],
                    },
                ],
                "relations": [
                    {"from": "feature.orders_api", "to": "code.create_order", "type": "owns"},
                    {"from": "test.orders_api", "to": "feature.orders_api", "type": "verifies_primary"},
                    {"from": "code.create_order", "to": "feature.merchant_status_api", "type": "impacts"},
                ],
            }
        ),
        encoding="utf-8",
    )

    adapter = ReviewGraphAdapter(mapping_path)
    result = adapter.build(
        "repo-1",
        {
            "change_id": "chg-123",
            "change_title": "orders change",
            "changed_files": ["backend/app/api/orders.py"],
            "linked_tests": [],
            "changed_symbols": ["backend.app.services.order_service.create_order"],
        },
        {"missing_tests_for_changed_paths": []},
    )

    assert result["summary"] == {
        "title": "orders change",
        "direct_feature_count": 1,
        "impacted_feature_count": 1,
        "verification_gap_count": 0,
    }

    nodes_by_id = {node["id"]: node for node in result["nodes"]}
    assert nodes_by_id["feature.orders_api"]["match_status"] == "direct"
    assert set(nodes_by_id["feature.orders_api"]["layers"]) == {"feature", "impact"}
    assert nodes_by_id["code.create_order"]["match_status"] == "direct"
    assert set(nodes_by_id["code.create_order"]["layers"]) == {"feature", "impact"}
    assert nodes_by_id["test.orders_api"]["match_status"] == "expanded"
    assert set(nodes_by_id["test.orders_api"]["layers"]) == {"feature", "impact"}
    assert nodes_by_id["feature.merchant_status_api"]["match_status"] == "expanded"
    assert set(nodes_by_id["feature.merchant_status_api"]["layers"]) == {"impact"}

    edges_by_type = {edge["type"]: edge for edge in result["edges"]}
    assert set(edges_by_type["owns"]["layers"]) == {"feature", "impact"}
    assert set(edges_by_type["verifies_primary"]["layers"]) == {"feature", "impact"}
    assert set(edges_by_type["impacts"]["layers"]) == {"impact"}


def test_review_graph_adapter_returns_unresolved_refs_for_unmapped_inputs(tmp_path):
    mapping_path = tmp_path / "mapping.yaml"
    mapping_path.write_text(
        yaml.safe_dump(
            {
                "version": 1,
                "objects": [
                    {
                        "id": "feature.change_impact",
                        "type": "FeatureContainer",
                        "label": "change_impact",
                        "refs": [{"kind": "file", "value": "backend/app/services/change_impact/adapter.py"}],
                    }
                ],
                "relations": [],
            }
        ),
        encoding="utf-8",
    )

    adapter = ReviewGraphAdapter(mapping_path)
    result = adapter.build(
        "repo-1",
        {
            "changed_files": ["backend/app/services/unknown.py"],
            "linked_tests": [],
            "changed_symbols": [],
        },
        {"missing_tests_for_changed_paths": []},
    )

    assert "backend/app/services/unknown.py" in result["unresolved_refs"]


def test_review_graph_adapter_returns_empty_payload_when_mapping_missing(tmp_path):
    adapter = ReviewGraphAdapter(tmp_path / "missing.yaml")

    result = adapter.build(
        "repo-1",
        {"change_id": "chg-123", "changed_files": [], "linked_tests": [], "changed_symbols": []},
        {"missing_tests_for_changed_paths": ["backend/app/services/unknown.py"]},
    )

    assert result == {
        "version": "v1",
        "change_id": "chg-123",
        "summary": {
            "title": "workspace diff",
            "direct_feature_count": 0,
            "impacted_feature_count": 0,
            "verification_gap_count": 1,
            "mapping_status": "missing",
        },
        "nodes": [],
        "edges": [],
        "unresolved_refs": [],
    }


def test_review_graph_adapter_returns_empty_payload_when_mapping_invalid(tmp_path):
    mapping_path = tmp_path / "mapping.yaml"
    mapping_path.write_text("version: [", encoding="utf-8")

    adapter = ReviewGraphAdapter(mapping_path)
    result = adapter.build(
        "repo-1",
        {"change_id": "chg-123", "changed_files": [], "linked_tests": [], "changed_symbols": []},
        {"missing_tests_for_changed_paths": ["backend/app/services/unknown.py"]},
    )

    assert result == {
        "version": "v1",
        "change_id": "chg-123",
        "summary": {
            "title": "workspace diff",
            "direct_feature_count": 0,
            "impacted_feature_count": 0,
            "verification_gap_count": 1,
            "mapping_status": "invalid",
        },
        "nodes": [],
        "edges": [],
        "unresolved_refs": [],
    }


def test_review_graph_adapter_success_payload_does_not_include_missing_mapping_status(tmp_path):
    mapping_path = tmp_path / "mapping.yaml"
    mapping_path.write_text(
        yaml.safe_dump(
            {
                "version": 1,
                "objects": [
                    {
                        "id": "feature.change_impact",
                        "type": "FeatureContainer",
                        "label": "change_impact",
                        "refs": [{"kind": "file", "value": "backend/app/services/change_impact/adapter.py"}],
                    }
                ],
                "relations": [],
            }
        ),
        encoding="utf-8",
    )

    adapter = ReviewGraphAdapter(mapping_path)
    result = adapter.build(
        "repo-1",
        {
            "change_id": "chg-123",
            "change_title": "change impact",
            "changed_files": ["backend/app/services/change_impact/adapter.py"],
            "linked_tests": [],
            "changed_symbols": [],
        },
        {"missing_tests_for_changed_paths": []},
    )

    assert result["summary"] == {
        "title": "change impact",
        "direct_feature_count": 1,
        "impacted_feature_count": 0,
        "verification_gap_count": 0,
    }


def test_review_graph_latest_endpoint_returns_payload():
    overview_payload = {
        "snapshot": {
            "workspace_snapshot_id": "ws_latest",
        }
    }
    change_payload = {
        "change_id": "chg-123",
        "changed_files": ["backend/app/services/change_impact/adapter.py"],
        "linked_tests": [],
        "changed_symbols": [],
    }
    verification_payload = {"missing_tests_for_changed_paths": []}
    response_payload = {
        "version": "v1",
        "change_id": "chg-123",
        "summary": {
            "title": "workspace diff",
            "direct_feature_count": 1,
            "impacted_feature_count": 0,
            "verification_gap_count": 0,
        },
        "nodes": [],
        "edges": [],
        "unresolved_refs": [],
    }

    with patch.object(snapshot_store, "get_latest_overview", return_value=overview_payload), patch.object(
        snapshot_store, "get_review_graph", return_value=None
    ) as review_graph_mock, patch.object(
        snapshot_store, "get_change_analysis", return_value=change_payload
    ) as change_mock, patch.object(snapshot_store, "get_verification", return_value=verification_payload) as verification_mock, patch(
        "app.api.endpoints.review_graph.ReviewGraphAdapter.build",
        return_value=response_payload,
    ) as build_mock:
        client = TestClient(app)
        response = client.get("/api/changes/review-graph/latest", params={"repo_key": "demo"})

    assert response.status_code == 200
    assert response.json()["version"] == "v1"
    review_graph_mock.assert_called_once_with("demo", "ws_latest", workspace_path=None)
    change_mock.assert_called_once_with("demo", "ws_latest", workspace_path=None)
    verification_mock.assert_called_once_with("demo", "ws_latest", workspace_path=None)
    build_mock.assert_called_once()


def test_review_graph_latest_endpoint_prefers_prebuilt_snapshot_payload():
    overview_payload = {"snapshot": {"workspace_snapshot_id": "ws_latest"}}
    review_graph_payload = {
        "version": "v1",
        "change_id": "chg-123",
        "summary": {
            "title": "workspace diff",
            "direct_feature_count": 1,
            "impacted_feature_count": 0,
            "verification_gap_count": 0,
        },
        "nodes": [],
        "edges": [],
        "unresolved_refs": [],
    }

    with patch.object(snapshot_store, "get_latest_overview", return_value=overview_payload) as latest_mock, patch.object(
        snapshot_store, "get_review_graph", return_value=review_graph_payload
    ) as review_graph_mock, patch.object(
        snapshot_store, "get_change_analysis"
    ) as change_mock, patch.object(snapshot_store, "get_verification") as verification_mock, patch(
        "app.api.endpoints.review_graph.ReviewGraphAdapter.build"
    ) as build_mock:
        client = TestClient(app)
        response = client.get("/api/changes/review-graph/latest", params={"repo_key": "demo", "workspace_path": "/tmp/demo"})

    assert response.status_code == 200
    assert response.json() == review_graph_payload
    latest_mock.assert_called_once_with("demo", workspace_path="/tmp/demo")
    review_graph_mock.assert_called_once_with("demo", "ws_latest", workspace_path="/tmp/demo")
    change_mock.assert_not_called()
    verification_mock.assert_not_called()
    build_mock.assert_not_called()


def test_review_graph_latest_endpoint_uses_repo_root_mapping_path():
    overview_payload = {"snapshot": {"workspace_snapshot_id": "ws_latest"}}
    change_payload = {
        "change_id": "chg-123",
        "changed_files": [],
        "linked_tests": [],
        "changed_symbols": [],
    }
    verification_payload = {"missing_tests_for_changed_paths": []}
    captured_paths: list[Path] = []

    class _FakeAdapter:
        def __init__(self, mapping_file):
            captured_paths.append(mapping_file)

        def build(self, repo_key, change_data, verification_data):
            return {"version": "v1"}

    expected_path = Path(review_graph_endpoint.__file__).resolve().parents[4] / "review_graph" / "mapping.yaml"

    with patch.object(snapshot_store, "get_latest_overview", return_value=overview_payload), patch.object(
        snapshot_store, "get_review_graph", return_value=None
    ), patch.object(
        snapshot_store, "get_change_analysis", return_value=change_payload
    ), patch.object(snapshot_store, "get_verification", return_value=verification_payload), patch(
        "app.api.endpoints.review_graph.ReviewGraphAdapter",
        _FakeAdapter,
    ):
        client = TestClient(app)
        response = client.get("/api/changes/review-graph/latest", params={"repo_key": "demo"})

    assert response.status_code == 200
    assert captured_paths == [expected_path]


def test_review_graph_mapping_covers_divide_prd_to_ui_core_change_chain():
    mapping_path = Path("review_graph/mapping.yaml")
    adapter = ReviewGraphAdapter(mapping_path)

    result = adapter.build(
        "divide_prd_to_ui",
        {
            "change_id": "chg-divide-prd",
            "change_title": "divide_prd_to_ui workspace diff",
            "changed_files": [
                "backend/app/services/editor.py",
                "backend/app/services/orchestrator.py",
                "backend/app/services/pipeline.py",
                "backend/app/services/planner.py",
                "backend/app/services/vfs_supervisor.py",
            ],
            "linked_tests": [
                "tests/test_editor_service_command.py",
                "tests/test_pipeline_orchestrator_integration.py",
                "tests/test_planner_unit.py",
                "tests/test_vfs_supervisor.py",
            ],
            "changed_symbols": [
                "EditorService",
                "Orchestrator",
                "Pipeline",
                "Planner",
                "VfsSupervisor",
            ],
        },
        {"missing_tests_for_changed_paths": []},
    )

    node_ids = {node["id"] for node in result["nodes"]}
    assert "feature.editor_service" in node_ids
    assert "feature.orchestrator" in node_ids
    assert "feature.pipeline" in node_ids
    assert "feature.planner" in node_ids
    assert "feature.vfs_supervisor" in node_ids
    assert "test.editor_service_command" in node_ids
    assert "test.pipeline_orchestrator_integration" in node_ids
    assert result["summary"]["direct_feature_count"] >= 5
