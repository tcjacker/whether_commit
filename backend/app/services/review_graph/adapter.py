from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

from app.services.review_graph.mapping_loader import (
    ReviewGraphMappingInvalid,
    ReviewGraphMappingNotFound,
    load_review_graph_mapping,
)
from app.services.review_graph.resolver import ReviewGraphResolver


class ReviewGraphAdapter:
    def __init__(self, mapping_file: Path):
        self.mapping_file = mapping_file

    def build(self, repo_key: str, change_data: Dict[str, Any], verification_data: Dict[str, Any]) -> Dict[str, Any]:
        try:
            mapping = load_review_graph_mapping(self.mapping_file)
        except ReviewGraphMappingNotFound:
            return {
                "version": "v1",
                "change_id": change_data.get("change_id", "chg_unknown"),
                "summary": {
                    "title": change_data.get("change_title", "workspace diff"),
                    "direct_feature_count": 0,
                    "impacted_feature_count": 0,
                    "verification_gap_count": len(verification_data.get("missing_tests_for_changed_paths", [])),
                    "mapping_status": "missing",
                },
                "nodes": [],
                "edges": [],
                "unresolved_refs": [],
            }
        except ReviewGraphMappingInvalid:
            return {
                "version": "v1",
                "change_id": change_data.get("change_id", "chg_unknown"),
                "summary": {
                    "title": change_data.get("change_title", "workspace diff"),
                    "direct_feature_count": 0,
                    "impacted_feature_count": 0,
                    "verification_gap_count": len(verification_data.get("missing_tests_for_changed_paths", [])),
                    "mapping_status": "invalid",
                },
                "nodes": [],
                "edges": [],
                "unresolved_refs": [],
            }

        resolver = ReviewGraphResolver(mapping)
        resolved = resolver.resolve_refs(
            changed_files=set(change_data.get("changed_files", [])),
            linked_tests=set(change_data.get("linked_tests", [])),
            changed_symbols=set(change_data.get("changed_symbols", [])),
        )

        direct_ids = set(resolved.matched_object_ids)
        feature_relation_types = {relation.type for relation in mapping.relations if relation.type != "impacts"}
        all_relation_types = {relation.type for relation in mapping.relations}

        feature_layer_ids = resolver.expand_related(direct_ids, feature_relation_types)
        expanded_ids = resolver.expand_related(direct_ids, all_relation_types)
        expanded_objects = [obj for obj in mapping.objects if obj.id in expanded_ids]
        edges = []
        for rel in mapping.relations:
            if rel.from_ not in expanded_ids or rel.to not in expanded_ids:
                continue

            layers = ["impact"]
            if rel.type != "impacts" and rel.from_ in feature_layer_ids and rel.to in feature_layer_ids:
                layers = ["feature", "impact"]

            edges.append(
                {
                    "from": rel.from_,
                    "to": rel.to,
                    "type": rel.type,
                    "layers": layers,
                }
            )

        return {
            "version": "v1",
            "change_id": change_data.get("change_id", "chg_unknown"),
            "summary": {
                "title": change_data.get("change_title", "workspace diff"),
                "direct_feature_count": sum(
                    1 for obj in mapping.objects if obj.id in direct_ids and obj.type == "FeatureContainer"
                ),
                "impacted_feature_count": sum(
                    1 for obj in mapping.objects if obj.id in expanded_ids - feature_layer_ids and obj.type == "FeatureContainer"
                ),
                "verification_gap_count": len(verification_data.get("missing_tests_for_changed_paths", [])),
            },
            "nodes": [
                {
                    "id": obj.id,
                    "type": obj.type,
                    "label": obj.label,
                    "match_status": "direct" if obj.id in direct_ids else "expanded",
                    "layers": ["feature", "impact"] if obj.id in feature_layer_ids else ["impact"],
                    "refs": [{"kind": ref.kind, "value": ref.value} for ref in obj.refs],
                }
                for obj in expanded_objects
            ],
            "edges": edges,
            "unresolved_refs": sorted(resolved.unresolved_refs),
        }
