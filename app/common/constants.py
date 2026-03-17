"""
Shared constants, enums, and regex patterns used across the application.
"""
from __future__ import annotations

import re

# ---------------------
# Environment & Status
# ---------------------
ENVIRONMENTS = {"sandbox", "dev", "staging", "prod"}
SKILL_STATUSES = {"draft", "published", "archived"}

# ---------------------
# Action enums
# ---------------------
ACTION_CAPABILITIES = {"API", "AI", "RPA", "HUMAN", "RULES", "MESSAGE", "DOCS"}
ACTION_SCOPE = {"global", "client"}
ACTION_DEF_STATUS = {"draft", "published"}
ACTION_VERSION_STATUS = {"draft", "published", "archived"}

# ---------------------
# Validation patterns
# ---------------------
SKILL_KEY_RE = re.compile(r"^[A-Z][A-Z0-9]{1,7}$")        # e.g. D01, A02
ACTION_KEY_RE = re.compile(r"^[a-z0-9][a-z0-9._-]*$")  # e.g. action1, eligibility.verify
