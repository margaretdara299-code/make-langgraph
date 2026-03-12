"""
Domain-specific error shortcuts using the standard response envelope.

All functions raise HTTPException producing:
{"status": False, "message": "...", "data": None}
"""
from app.common.response import raise_bad_request, raise_conflict, raise_not_found


# ── Skill ──
def skill_not_found():
    raise_not_found("Skill not found")

def skill_name_exists():
    raise_conflict("Skill name already exists")

def skill_key_exists():
    raise_conflict("Skill key already exists")


# ── Skill Version ──
def skill_version_not_found():
    raise_not_found("Skill version not found")

def skill_version_not_draft():
    raise_conflict("Only draft versions can be modified")

def skill_version_not_compiled():
    raise_bad_request("Skill version must be compiled first")

def skill_graph_validation_failed(errors: list = None):
    raise_bad_request("Graph validation failed")


# ── Action ──
def action_not_found():
    raise_not_found("Action not found")

def action_key_exists():
    raise_conflict("Action key already exists")

# ── Action Version ──
def action_version_not_found():
    raise_not_found("Action version not found")

def action_version_not_draft():
    raise_conflict("Only draft versions can be updated")
