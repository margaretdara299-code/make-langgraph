"""
Pydantic request and response schemas for the Skill feature.
"""
from __future__ import annotations

from typing import Any, Dict, List, Literal

from pydantic import BaseModel, Field, field_validator

from app.common.constants import ENVIRONMENTS, SKILL_KEY_RE


# =========================================================================
# Create Skill — request / response
# =========================================================================
class CloneSourceDetails(BaseModel):
    """Details of the skill to clone from."""
    source_skill_id: str
    source_skill_version_id: str
    include_test_cases: bool = True


class SkillStartFrom(BaseModel):
    """How to initialise the new skill graph."""
    mode: Literal["blank", "template", "clone"] = "blank"
    template_id: str | None = None
    clone: CloneSourceDetails | None = None


class CreateSkillRequest(BaseModel):
    """Payload to create a new Skill in the Skills Library."""
    client_id: str
    environment: str = "dev"
    name: str
    skill_key: str | None = None
    description: str | None = Field(default=None, max_length=240)
    category: str | None = None
    tags: List[str] = Field(default_factory=list)

    start_from: SkillStartFrom = Field(default_factory=SkillStartFrom)


class UpdateSkillRequest(BaseModel):
    """Payload to update an existing skill's metadata."""
    name: str | None = None
    description: str | None = Field(default=None, max_length=240)
    category: str | None = None
    is_active: bool | None = None
    tags: List[str] | None = None


class CreateSkillResponse(BaseModel):
    """Response after successfully creating a Skill."""
    skill: Dict[str, Any]
    skill_version: Dict[str, Any]
    designer_url: str


# =========================================================================
# Graph node DTO (stored as JSON inside skill_version.nodes)
# =========================================================================
class SkillGraphNode(BaseModel):
    """A single node on the visual canvas — stored inside skill_version.nodes JSON."""
    id: str = Field(description="Unique node identifier (used as key everywhere)")
    type: str = Field(description="Node type (e.g. trigger.queue, action.llm, end.success)")
    position: Dict[str, float] = Field(default_factory=lambda: {"x": 0, "y": 0})
    data: Dict[str, Any] = Field(default_factory=dict)

    model_config = {"populate_by_name": True}


# =========================================================================
# Connection DTO (stored in skill_route table, returned as dict keyed by id)
# =========================================================================
class SkillGraphConnection(BaseModel):
    """A single edge between two nodes — persisted in skill_route."""
    id: str
    source: str
    target: str
    sourceHandle: str | None = None
    targetHandle: str | None = None
    condition: Dict[str, Any] = Field(default_factory=dict)
    is_default: bool = False


# =========================================================================
# Graph response / request
# =========================================================================
class SkillGraphResponse(BaseModel):
    """Full graph payload returned when loading a skill version."""
    skill_version_id: str
    skill_id: str
    environment: str
    version: str = "1.0.1"
    status: str = "published"
    nodes: List[SkillGraphNode]
    connections: Dict[str, SkillGraphConnection] = Field(default_factory=dict)


class SaveSkillGraphRequest(BaseModel):
    """Payload to bulk-save the graph for a skill version."""
    nodes: List[SkillGraphNode]
    connections: Dict[str, SkillGraphConnection] = Field(default_factory=dict)


class UpdateNodeConfigRequest(BaseModel):
    """Payload to update a single node's data (right panel)."""
    data: Dict[str, Any]


# =========================================================================
# Workflow operations — request / response
# =========================================================================
class ValidationResult(BaseModel):
    """Result of validating a skill graph before compilation."""
    valid: bool
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)


class CompilationResult(BaseModel):
    """Result of compiling a validated skill graph into LangGraph JSON."""
    compile_hash: str
    compiled_skill_json: Dict[str, Any]


class PublishSkillRequest(BaseModel):
    """Payload to publish a draft skill version."""
    notes: str | None = None


class RunSkillRequest(BaseModel):
    """Payload to execute a compiled skill (dry run / test)."""
    input_context: Dict[str, Any] = Field(default_factory=dict)
    max_steps: int = 200


class RunSkillResponse(BaseModel):
    """Result of running a compiled skill."""
    status: str
    visited: List[str]
    context: Dict[str, Any]
    last_outputs: Dict[str, Any] = Field(default_factory=dict)
