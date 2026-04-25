from app.schemas.review_graph import ReviewGraphMapping
from app.services.review_graph.resolver import ReviewGraphResolver


def test_resolver_matches_changed_file_to_feature_and_test_units():
    mapping = ReviewGraphMapping.model_validate(
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
            "relations": [],
        }
    )

    resolver = ReviewGraphResolver(mapping)
    result = resolver.resolve_refs(
        changed_files={"backend/app/services/change_impact/adapter.py"},
        linked_tests={"backend/tests/test_change_impact_adapter.py"},
        changed_symbols=set(),
    )

    assert result.matched_object_ids == {"feature.change_impact", "test.change_impact"}
    assert result.unresolved_refs == set()


def test_resolver_can_expand_related_objects_from_primary_match():
    mapping = ReviewGraphMapping.model_validate(
        {
            "version": 1,
            "objects": [
                {
                    "id": "feature.change_impact",
                    "type": "FeatureContainer",
                    "label": "change_impact",
                },
                {
                    "id": "code.change_impact_adapter",
                    "type": "CodeUnit",
                    "label": "ChangeImpactAdapter",
                },
            ],
            "relations": [
                {"from": "feature.change_impact", "to": "code.change_impact_adapter", "type": "owns"}
            ],
        }
    )

    resolver = ReviewGraphResolver(mapping)

    assert resolver.expand_related({"feature.change_impact"}, {"owns"}) == {
        "feature.change_impact",
        "code.change_impact_adapter",
    }


def test_resolver_can_expand_related_objects_through_reverse_verification_edge():
    mapping = ReviewGraphMapping.model_validate(
        {
            "version": 1,
            "objects": [
                {
                    "id": "feature.change_impact",
                    "type": "FeatureContainer",
                    "label": "change_impact",
                },
                {
                    "id": "test.change_impact",
                    "type": "TestUnit",
                    "label": "test_change_impact_adapter",
                },
            ],
            "relations": [
                {
                    "from": "test.change_impact",
                    "to": "feature.change_impact",
                    "type": "verifies_primary",
                }
            ],
        }
    )

    resolver = ReviewGraphResolver(mapping)

    assert resolver.expand_related({"feature.change_impact"}, {"verifies_primary"}) == {
        "feature.change_impact",
        "test.change_impact",
    }


def test_resolver_can_expand_related_objects_across_multiple_hops():
    mapping = ReviewGraphMapping.model_validate(
        {
            "version": 1,
            "objects": [
                {
                    "id": "feature.change_impact",
                    "type": "FeatureContainer",
                    "label": "change_impact",
                },
                {
                    "id": "code.change_impact_adapter",
                    "type": "CodeUnit",
                    "label": "ChangeImpactAdapter",
                },
                {
                    "id": "test.change_impact",
                    "type": "TestUnit",
                    "label": "test_change_impact_adapter",
                },
            ],
            "relations": [
                {"from": "feature.change_impact", "to": "code.change_impact_adapter", "type": "owns"},
                {"from": "test.change_impact", "to": "feature.change_impact", "type": "verifies_primary"},
            ],
        }
    )

    resolver = ReviewGraphResolver(mapping)

    assert resolver.expand_related({"code.change_impact_adapter"}, {"owns", "verifies_primary"}) == {
        "code.change_impact_adapter",
        "feature.change_impact",
        "test.change_impact",
    }
