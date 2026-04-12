"""
Skill service — business logic for the Skills Library and Visual Skill Designer.
"""
from typing import Any, Dict, List, Tuple
from sqlalchemy import text
from sqlalchemy.orm import Session
from app.common.errors import (skill_name_exists, skill_key_exists,
                               skill_version_not_found, skill_version_not_draft,
                               skill_version_not_compiled, skill_graph_validation_failed)
from app.common.utils import (generate_unique_id, compute_sha256_hash,
                              deserialize_json, serialize_to_json)
from app.skill import repository as skill_repository
from app.skill.models import (RunSkillResponse, SaveSkillGraphRequest,
                               SkillGraphConnection, SkillGraphResponse, UpdateSkillVersionStatusRequest)
from app.logger.logging import logger
from app.engine.compiler.validator import validate_workflow
from app.engine.compiler.builder import compile_workflow_plan
from app.engine.executor.runner import run_workflow


# =========================================================================
# Skill Metadata CRUD
# =========================================================================

def list_all_skills(
    db: Session,
    client_id: str | None = None,
    status: str | None = None,
    search_query: str | None = None,
) -> Dict:
    items = skill_repository.fetch_all_skills(db, client_id=client_id, status=status, search_query=search_query)
    return {"items": items, "total": len(items)}


def create_skill(db: Session, request, user_id: int = 1) -> Dict:
    """Create a new Skill with an initial draft version and starter graph."""
    if skill_repository.does_skill_name_exist(db, request.client_id, request.name):
        skill_name_exists()

    skill_key = request.skill_key or generate_unique_id("SK")[:8].upper()
    if skill_repository.does_skill_key_exist(db, request.client_id, skill_key):
        skill_key_exists()

    # IDs are now auto-incremented by the database
    skill_id = skill_repository.insert_skill(
        db, client_id=request.client_id,
        name=request.name, skill_key=skill_key, description=request.description,
        category_id=request.category_id, capability_id=request.capability_id, created_by=user_id,
    )
    skill_version_id = skill_repository.insert_skill_version(
        db, skill_id=skill_id,
        environment=request.environment, created_by=user_id,
    )

    if request.start_from.mode == "blank":
        skill_repository.create_blank_graph(db, skill_version_id)
    elif request.start_from.mode == "clone" and request.start_from.clone:
        skill_repository.clone_graph(db, new_skill_version_id=skill_version_id,
                                     source_skill_version_id=request.start_from.clone.source_skill_version_id)

    if request.tags:
        tag_ids = skill_repository.upsert_tags(db, request.tags)
        skill_repository.attach_tags_to_skill(db, skill_id, tag_ids)

    logger.debug(f"Created skill '{request.name}' (key={skill_key}, id={skill_id})")

    return {
        "skill_id": skill_id,
        "skill_version_id": skill_version_id,
    }


def get_skill(db: Session, skill_id: int) -> dict | None:
    """Fetch a single skill's full metadata."""
    return skill_repository.fetch_skill_by_id(db, skill_id)


def update_skill(db: Session, skill_id: str, request) -> bool:
    """Update skill metadata and optionally tags."""
    update_data = request.model_dump(exclude_unset=True)
    if not update_data:
        return False
        
    if "skill_key" in update_data or "name" in update_data:
        existing_skill = skill_repository.fetch_skill_by_id(db, skill_id)
        if not existing_skill:
            return False
            
        client_id = existing_skill["client_id"]
        
        if "skill_key" in update_data and update_data["skill_key"] != existing_skill["skill_key"]:
            if skill_repository.does_skill_key_exist(db, client_id, update_data["skill_key"]):
                skill_key_exists()
                
        if "name" in update_data and update_data["name"] != existing_skill["name"]:
            if skill_repository.does_skill_name_exist(db, client_id, update_data["name"]):
                skill_name_exists()

    success = skill_repository.update_skill(db, skill_id, update_data)

    if "tags" in update_data:
        skill_repository.remove_all_tags_from_skill(db, skill_id)
        if update_data["tags"]:
            tag_ids = skill_repository.upsert_tags(db, update_data["tags"])
            skill_repository.attach_tags_to_skill(db, skill_id, tag_ids)

    if success:
        logger.debug(f"Updated skill '{skill_id}'")
    return success


def delete_skill(db: Session, skill_id: int) -> bool:
    """Delete a skill and all its versions."""
    success = skill_repository.delete_skill(db, skill_id)
    if success:
        logger.debug(f"Deleted skill '{skill_id}'")
    return success


# =========================================================================
# Skill Graph / Designer
# =========================================================================

def get_skill_graph(db: Session, skill_version_id: int) -> SkillGraphResponse:
    """Load the graph (nodes + connections) for a skill version."""
    return skill_repository.fetch_skill_graph(db, skill_version_id)


def save_graph(db: Session, skill_version_id: int, request: SaveSkillGraphRequest) -> SkillGraphResponse:
    """Bulk-save the entire graph (nodes + connections) for a skill version."""
    skill_repository.save_skill_graph(db, skill_version_id, request.nodes, request.connections, request.viewport_json)
    logger.debug(f"Saved graph for skill version {skill_version_id} "
                f"({len(request.nodes)} nodes, {len(request.connections)} connections)")
    return skill_repository.fetch_skill_graph(db, skill_version_id)


def update_node(db: Session, skill_version_id: int, node_id: str, data: dict) -> dict:
    """Update a single node's configuration data."""
    skill_repository.update_node_data(db, skill_version_id, node_id, data)
    return {"ok": True}






# =========================================================================
# Publish
# =========================================================================

def update_skill_version_status(db: Session, skill_version_id: int, request: UpdateSkillVersionStatusRequest) -> dict:
    """Unified status management for skill versions (publish/unpublish)."""
    version_row = skill_repository.fetch_skill_version_by_id(db, skill_version_id)
    if not version_row:
        skill_version_not_found()

    if request.status == "published":
        if version_row["status"] == "published":
            return {"status": "published", "message": "Already published"}
        # if not version_row["compiled_skill_json"]:
        #    skill_version_not_compiled()
        published_at = skill_repository.publish_skill_version(
            db, skill_version_id, version_row["skill_id"], version_row["environment"], request.notes)
        return {"status": "published", "published_at": published_at}
    
    elif request.status == "unpublished":
        if version_row["status"] == "unpublished":
            return {"status": "unpublished", "message": "Already unpublished"}
        skill_repository.unpublish_skill_version(db, skill_version_id)
        return {"status": "unpublished"}

    elif request.status == "draft":
        if version_row["status"] == "draft":
            return {"status": "draft", "message": "Already in draft status"}
        # Manual revert to draft from published or unpublished
        db.execute(
            text("UPDATE skill_version SET status='draft', published_at=NULL WHERE skill_version_id=:sv_id"),
            {"sv_id": skill_version_id}
        )
        return {"status": "draft"}
    
    return {"status": version_row["status"]}


def validate_skill_version(db: Session, skill_version_id: int) -> dict:
    """Load graph and run engine validation logic."""
    skill_graph = skill_repository.fetch_skill_graph(db, skill_version_id)
    if not skill_graph:
        skill_version_not_found()
    
    workflow_data = {
        "nodes": [n.model_dump() for n in skill_graph.nodes],
        "connections": {k: v.model_dump() for k, v in skill_graph.connections.items()}
    }
    return validate_workflow(workflow_data)


def compile_skill_version(db: Session, skill_version_id: int) -> dict:
    """Load, validate and compile graph into a plan."""
    skill_graph = skill_repository.fetch_skill_graph(db, skill_version_id)
    if not skill_graph:
        skill_version_not_found()
        
    workflow_data = {
        "nodes": [n.model_dump() for n in skill_graph.nodes],
        "connections": {k: v.model_dump() for k, v in skill_graph.connections.items()}
    }
    
    plan = compile_workflow_plan(workflow_data)
    
    # Save the compiled JSON back to the version
    import json
    skill_repository.update_compiled_graph(db, skill_version_id, json.dumps(plan["workflow_json"]), plan["compile_hash"])
    
    return plan


def run_skill_version(db: Session, skill_version_id: int, input_context: dict) -> dict:
    """Execute the skill version's graph with provided input."""
    # First, fetch the compiled graph
    version = skill_repository.fetch_skill_version_by_id(db, skill_version_id)
    if not version:
        skill_version_not_found()
        
    if not version.get("compiled_skill_json") or not version.get("compile_hash"):
        # Auto-compile if missing? For tests, let's just complain or auto-compile
        # For now, let's require compilation as per spec
        skill_version_not_compiled()
    
    # Run the engine
    from app.common.utils import deserialize_json
    import json # Ensure json is available
    workflow_data = deserialize_json(version["compiled_skill_json"], {})
    
    # We should probably pass the input_context to the runner if it supported it.
    # For now, let's see if it even starts.
    try:
        final_state = run_workflow(workflow_data)
        
        return {
            "status": final_state.get("status", "succeeded"),
            "logs": final_state.get("logs", []), # trace
            "context": {k:v for k,v in final_state.items() if k != "logs"},
            "last_outputs": final_state.get("last_result", {})
        }
    except Exception as e:
        logger.exception(f"Engine execution failed for version {skill_version_id}")
        raise e


