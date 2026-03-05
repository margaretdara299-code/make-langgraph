"""
Centralised error helpers using the standard response envelope.

All errors produce: {"status": False, "message": "...", "data": None}
"""
from app.common.response import bad_request, conflict, internal_error, not_found


# =========================================================================
# Domain-specific error shortcuts
# =========================================================================
def skill_not_found():
    not_found("Skill not found")

def skill_version_not_found():
    not_found("Skill version not found")

def skill_name_exists():
    conflict("Skill name already exists")

def skill_key_exists():
    conflict("Skill key already exists")

def skill_version_not_draft():
    conflict("Only draft versions can be modified")

def skill_version_not_compiled():
    bad_request("Skill version must be compiled first")

def skill_graph_validation_failed(errors: list = None):
    bad_request("Graph validation failed")

def action_not_found():
    not_found("Action not found")

def action_key_exists():
    conflict("Action key already exists")
