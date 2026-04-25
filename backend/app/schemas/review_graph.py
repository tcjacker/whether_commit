from __future__ import annotations

from typing import Any, Dict, List, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

ObjectType = Literal["FeatureContainer", "CodeUnit", "TestUnit", "EvidenceGroup"]
RelationType = Literal["owns", "verifies_primary", "verifies_secondary", "supports", "impacts", "contains"]
RefKind = Literal[
    "file",
    "symbol",
    "module",
    "route",
    "job",
    "consumer",
    "scheduler",
    "test_file",
    "test_suite",
    "test_case",
]


class MappingRef(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: RefKind
    value: str = Field(min_length=1)


class MappingObject(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1)
    type: ObjectType
    label: str = Field(min_length=1)
    description: str = ""
    status: Literal["active", "deprecated", "draft"] = "active"
    tags: List[str] = Field(default_factory=list)
    refs: List[MappingRef] = Field(default_factory=list)
    attributes: Dict[str, Any] = Field(default_factory=dict)


class MappingRelation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    from_: str = Field(alias="from", min_length=1)
    to: str = Field(min_length=1)
    type: RelationType
    status: Literal["active", "deprecated", "draft"] = "active"
    confidence: Literal["high", "medium", "low"] = "high"
    rationale: str = ""


class ReviewGraphMapping(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    version: Literal[1]
    metadata: Dict[str, Any] = Field(default_factory=dict)
    objects: List[MappingObject] = Field(default_factory=list)
    relations: List[MappingRelation] = Field(default_factory=list)

    @model_validator(mode="after")
    def _validate_graph_integrity(self) -> "ReviewGraphMapping":
        object_ids = [obj.id for obj in self.objects]
        if len(object_ids) != len(set(object_ids)):
            raise ValueError("duplicate object ids are not allowed")

        known_ids = set(object_ids)
        for relation in self.relations:
            if relation.from_ not in known_ids:
                raise ValueError(f"relation.from references unknown object id: {relation.from_}")
            if relation.to not in known_ids:
                raise ValueError(f"relation.to references unknown object id: {relation.to}")

        return self
