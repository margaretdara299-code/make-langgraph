# Tensaw Skills Studio API — Agent Skill Definition Guide

> **Version:** 4.0  
> **Scope:** `.agent/tensaw-skills-studio-api/`  
> **Purpose:** Define how the AI assistant reads, interprets, and applies skill files when contributing to this codebase.

---

## Overview

Skill files are **binding architectural contracts** for the AI agent. Every `.md` file in `.agent/tensaw-skills-studio-api/` teaches the agent a specific pattern, rule set, or standard it must follow without deviation when generating or reviewing code in this project.

The agent must treat these files as **source of truth** — above its own general training knowledge — for any decision within their defined scope.

---

## App Error Architecture (Read First)

Before writing any controller, service, or router code, the agent must understand how errors flow through this application end-to-end.

### 1. Standardized Response Envelope

Every response — success or error — returns this exact JSON structure. Never deviate.

```json
// Success
{ "status": true,  "message": "Item fetched", "data": { ... } }

// Error
{ "status": false, "message": "Item not found", "data": null }
```

FastAPI's default error format (`{"detail": ...}`) is **never** acceptable.

---

### 2. HTTP Helper Functions (`app/common/response.py`)

These are the **only** way to raise HTTP errors or return success responses. Direct `HTTPException` construction is forbidden.

| Function | HTTP Status | When to Use |
|---|---|---|
| `build_success_response(msg, data)` | 200 | All successful responses |
| `raise_bad_request(msg)` | 400 | Invalid input / business rule violation |
| `raise_not_found(msg)` | 404 | Resource does not exist |
| `raise_conflict(msg)` | 409 | Duplicate / unique constraint violation |
| `raise_internal_server_error()` | 500 | Unexpected crash in `except Exception` |

Internally, `raise_*` helpers construct and throw an `HTTPException`. This is why `except HTTPException: raise` must always come first — to let them bubble up untouched.

---

### 3. Global Exception Handlers (`main.py`)

Three `@application.exception_handler` decorators catch anything that escapes controllers:

| Handler | Catches | Returns |
|---|---|---|
| `HTTPException` | All intentional HTTP errors | Formatted envelope |
| `RequestValidationError` | FastAPI/Pydantic schema errors | 422 envelope |
| `Exception` | Any unhandled crash | 500 envelope |

All three inject the raw exception into `request.state.error = exc` for the middleware to consume.

---

### 4. Request Logger Middleware (`app/common/middleware.py`)

`RequestLoggerMiddleware` runs after every response and:

1. Checks if `request.state.error` was populated
2. Extracts the deepest traceback line → `filename:line_number`
3. Prints one concise diagnostic line:

```
-> GET /api/v1/skills/99 | Status: 404 | Time: 12.30ms | FAIL: HTTPException: 404: Not found (controller.py:85)
```

Log level rules:
- **4xx** client errors → `INFO`
- **5xx** server errors → `ERROR`

The agent must never replicate this logging manually — it is handled automatically by the middleware.

---

## Improvement Patterns (Apply These Always)

These are enhancements beyond the baseline pattern. Every new controller, service, and utility the agent writes must incorporate all of the following.

---

### I1: Context-Rich Exception Logging

**Problem with baseline:**
```python
# ❌ No context — useless in production logs
logger.exception("Unexpected error fetching item")
```

**Improved pattern — always include the identifier and operation:**
```python
# ✅ Actionable: tells you exactly what failed and on what input
logger.exception(f"Failed to fetch item | item_id={item_id}")
```

**Format rule:** `logger.exception(f"Failed to <verb> <resource> | <key>=<value>[, <key>=<value>]")`

Examples:
```python
logger.exception(f"Failed to create skill | name={payload.name!r}")
logger.exception(f"Failed to update user | user_id={user_id}, role={payload.role!r}")
logger.exception(f"Failed to delete session | session_id={session_id}")
```

> Use `!r` on string values so `None` and empty strings are visually distinct in logs.

---

### I2: Guard Clauses Over Nested Logic

**Problem with baseline:**
```python
# ❌ Logic buried inside nested if — hard to read at scale
try:
    result = service.get_item(db, item_id)
    if result:
        if result.is_active:
            return build_success_response("Item fetched", result)
        else:
            raise_bad_request("Item is inactive")
    else:
        raise_not_found("Item not found")
```

**Improved — fail fast, keep the happy path at the bottom:**
```python
# ✅ Early exits, happy path at the end — reads top to bottom
try:
    result = service.get_item(db, item_id)
    if not result:
        raise_not_found("Item not found")
    if not result.is_active:
        raise_bad_request("Item is inactive")
    return build_success_response("Item fetched", result)
```

**Rule:** Business validation errors must be checked and raised *before* the success return — never inside nested `if/else` chains.

---

### I3: Service Layer Error Contract

The service layer must never return `None` silently for error states. It must either:
- Return the object (success)
- Raise a domain-specific exception (failure)

**Problem:**
```python
# ❌ Service returns None — controller guesses what went wrong
def get_item(db, item_id):
    return db.query(Item).filter(Item.id == item_id).first()
```

**Improved — service raises typed domain exceptions:**
```python
# app/exceptions.py  ← create this file if it doesn't exist

class ItemNotFoundError(Exception):
    pass

class ItemInactiveError(Exception):
    pass

class DuplicateSkillError(Exception):
    pass
```

```python
# app/services/item_service.py
from app.exceptions import ItemNotFoundError, ItemInactiveError

def get_item(db: Session, item_id: int) -> Item:
    item = db.query(Item).filter(Item.id == item_id).first()
    if not item:
        raise ItemNotFoundError(f"Item {item_id} not found")
    if not item.is_active:
        raise ItemInactiveError(f"Item {item_id} is inactive")
    return item
```

```python
# app/routers/items.py  ← controller maps domain exceptions to HTTP errors
from app.exceptions import ItemNotFoundError, ItemInactiveError

@router.get("/{item_id}")
def get_item(item_id: int, db: Session = Depends(get_db_session)):
    logger.debug(f"Fetching item | item_id={item_id}")
    try:
        result = item_service.get_item(db, item_id)
        return build_success_response("Item fetched", result)
    except ItemNotFoundError:
        raise_not_found("Item not found")
    except ItemInactiveError:
        raise_bad_request("Item is inactive")
    except HTTPException:
        raise
    except Exception:
        logger.exception(f"Failed to fetch item | item_id={item_id}")
        raise_internal_server_error()
```

**Why:** The controller is responsible for HTTP mapping. The service is responsible for domain logic. This separation means services are testable without HTTP context.

---

### I4: Domain Exception Catch Order

When using typed domain exceptions (I3), the `except` block order is:

```python
except <DomainSpecificError>:       # 1. Most specific domain errors first
    raise_<appropriate_http_error>()
except HTTPException:                # 2. Re-raise intentional HTTP errors
    raise
except Exception:                    # 3. Generic crash handler — always last
    logger.exception(f"Failed to ...")
    raise_internal_server_error()
```

**Never** place `except Exception` above any specific exception handler.

---

### I5: Pydantic Response Schemas

Never return raw SQLAlchemy model objects from a route. Always serialize through a Pydantic response schema.

**Problem:**
```python
# ❌ Returns ORM object — SQLAlchemy lazy-load issues, exposes internal fields
return build_success_response("Item fetched", result)
```

**Improved:**
```python
# app/schemas/item_schema.py
from pydantic import BaseModel

class ItemResponse(BaseModel):
    id: int
    name: str
    is_active: bool

    model_config = {"from_attributes": True}
```

```python
# In the route
result = item_service.get_item(db, item_id)
return build_success_response("Item fetched", ItemResponse.model_validate(result))
```

**Rule:** Every route that returns a model must have a corresponding `*Response` schema in `app/schemas/`.

---

### I6: Route-Level Docstrings for OpenAPI

Every route must have a docstring. FastAPI uses it for the OpenAPI `/docs` description.

```python
@router.get("/{item_id}")
def get_item(item_id: int, db: Session = Depends(get_db_session)):
    """
    Fetch a single item by ID.

    Returns 404 if the item does not exist.
    Returns 400 if the item is inactive.
    """
    ...
```

**Rule:** Docstring must list every non-200 status code the route can return.

---

### I7: Consistent Log Entry Format

All `logger.debug` entry logs must follow this exact format:

```python
logger.debug(f"<VERB> <resource> | <key>=<value>")
```

| Verb | When |
|---|---|
| `Fetching` | GET by ID |
| `Listing` | GET collection |
| `Creating` | POST |
| `Updating` | PUT / PATCH |
| `Deleting` | DELETE |

Examples:
```python
logger.debug(f"Fetching item | item_id={item_id}")
logger.debug(f"Listing skills | user_id={user_id}")
logger.debug(f"Creating skill | name={payload.name!r}")
logger.debug(f"Updating skill | skill_id={skill_id}")
logger.debug(f"Deleting skill | skill_id={skill_id}")
```

---

### I8: Variable Naming Conventions

All variables must be immediately readable — no guessing what they hold.

**Rules:**

| Context | Convention | Example |
|---|---|---|
| ORM query result (single) | `<resource>` | `item`, `user`, `skill` |
| ORM query result (list) | `<resource>s` | `items`, `users`, `skills` |
| Service return value | `result` | `result = item_service.get_item(...)` |
| Pydantic serialized output | `<resource>_data` | `item_data = ItemResponse.model_validate(result)` |
| Request payload / body | `payload` | `payload: ItemCreateSchema` |
| DB session | `db` | `db: Session = Depends(get_db_session)` |
| Boolean flags | `is_` / `has_` / `can_` prefix | `is_active`, `has_permission`, `can_edit` |
| Count results | `<resource>_count` | `skill_count` |
| ID parameters | `<resource>_id` | `item_id`, `user_id`, `skill_id` |
| Temp/intermediate values | descriptive noun | `raw_data`, `parsed_config`, `token_payload` |

**Anti-patterns:**

```python
# ❌ Single-letter, cryptic, or generic names
x = service.get_item(db, i)
res = service.get_item(db, item_id)
d = ItemResponse.model_validate(res)
flag = result.is_active

# ✅ Self-documenting names
result = item_service.get_item(db, item_id)
item_data = ItemResponse.model_validate(result)
is_active = result.is_active
```

**Loop variables** — always name after the item, not a letter:

```python
# ❌
for x in items:
    ...

# ✅
for item in items:
    ...
```

---

### I9: Function Naming Conventions

Every function name must state exactly what it does — verb + noun.

#### Controller (Router) Functions

Format: `<http_verb>_<resource>[_<qualifier>]`

| Route | Function Name |
|---|---|
| `GET /{id}` | `get_item` |
| `GET /` | `list_items` |
| `POST /` | `create_item` |
| `PUT /{id}` | `update_item` |
| `PATCH /{id}` | `patch_item` |
| `DELETE /{id}` | `delete_item` |
| `GET /{id}/skills` | `list_item_skills` |
| `POST /{id}/activate` | `activate_item` |

```python
# ❌ Ambiguous
@router.get("/{item_id}")
def item(item_id: int, ...):          # noun only — is this get, create, update?

@router.post("/")
def handle_item(payload, ...):        # "handle" says nothing

# ✅ Verb + noun — instantly clear
@router.get("/{item_id}")
def get_item(item_id: int, ...):

@router.post("/")
def create_item(payload: ItemCreateSchema, ...):
```

#### Service Layer Functions

Format: `<verb>_<resource>[_by_<field>]`

| Action | Function Name |
|---|---|
| Fetch by ID | `get_item(db, item_id)` |
| Fetch by field | `get_item_by_name(db, name)` |
| Fetch all | `list_items(db)` |
| Fetch filtered | `list_items_by_user(db, user_id)` |
| Create | `create_item(db, payload)` |
| Update | `update_item(db, item_id, payload)` |
| Delete | `delete_item(db, item_id)` |
| Soft delete | `deactivate_item(db, item_id)` |
| Existence check | `item_exists(db, item_id) -> bool` |

```python
# ❌
def fetch(db, id): ...
def process_item(db, payload): ...
def do_delete(db, id): ...

# ✅
def get_item(db: Session, item_id: int) -> Item: ...
def create_item(db: Session, payload: ItemCreateSchema) -> Item: ...
def delete_item(db: Session, item_id: int) -> None: ...
```

#### Helper / Utility Functions

Format: `<verb>_<what>` — pure action verbs, no `handle_`, `process_`, `do_`

```python
# ❌ Vague verbs
def handle_response(data): ...
def process_token(token): ...
def do_validation(payload): ...

# ✅ Precise verbs
def build_success_response(message, data): ...
def decode_access_token(token: str) -> dict: ...
def validate_email_format(email: str) -> bool: ...
```

#### Boolean-returning Functions

Must start with `is_`, `has_`, `can_`, or `exists`:

```python
# ❌
def active(item): ...
def permission(user, resource): ...

# ✅
def is_active(item: Item) -> bool: ...
def has_permission(user: User, resource: str) -> bool: ...
def can_edit(user: User, item: Item) -> bool: ...
def skill_exists(db: Session, skill_id: int) -> bool: ...
```

#### Domain Exception Classes

Format: `<Resource><Reason>Error`

```python
# ❌
class NotFound(Exception): ...
class Error1(Exception): ...
class ItemError(Exception): ...   # too vague — which error?

# ✅
class ItemNotFoundError(Exception): ...
class ItemInactiveError(Exception): ...
class DuplicateSkillError(Exception): ...
class UserPermissionError(Exception): ...
```

#### Pydantic Schema Classes

Format: `<Resource><Purpose>`

| Purpose | Name |
|---|---|
| Request body (POST) | `ItemCreateSchema` |
| Request body (PUT) | `ItemUpdateSchema` |
| Request body (PATCH) | `ItemPatchSchema` |
| Response serialization | `ItemResponse` |
| Nested/embedded schema | `ItemSummary` |

---

### I10: Service Function Return Type Annotations

Every service function must declare its return type. Never omit it.

```python
# ❌ No return type — unreadable contract
def get_item(db: Session, item_id: int): ...
def list_items(db: Session): ...

# ✅ Explicit — unambiguous
def get_item(db: Session, item_id: int) -> Item: ...
def list_items(db: Session, skip: int, limit: int) -> list[Item]: ...
def create_item(db: Session, payload: ItemCreateSchema) -> Item: ...
def update_item(db: Session, item_id: int, payload: ItemUpdateSchema) -> Item: ...
def delete_item(db: Session, item_id: int) -> None: ...
def item_exists(db: Session, item_id: int) -> bool: ...
```

**Rule:** Return type must be the exact model class, `list[Model]`, `bool`, or `None`. Never `Any`, never omitted.

---

### I11: DB Transaction Discipline in Service Layer

Every write function must follow the `add → commit → refresh → return` pattern. `db.commit()` and `db.refresh()` must never appear in a controller.

```python
# ❌ No commit, no refresh — caller gets stale/detached object
def create_item(db: Session, payload: ItemCreateSchema) -> Item:
    item = Item(**payload.model_dump())
    db.add(item)
    return item

# ✅ Full write lifecycle owned by the service
def create_item(db: Session, payload: ItemCreateSchema) -> Item:
    item = Item(**payload.model_dump())
    db.add(item)
    db.commit()       # persist to DB
    db.refresh(item)  # reload server-generated fields (id, created_at, etc.)
    return item

# ✅ Update pattern
def update_item(db: Session, item_id: int, payload: ItemUpdateSchema) -> Item:
    item = get_item(db, item_id)   # raises ItemNotFoundError if missing
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(item, field, value)
    db.commit()
    db.refresh(item)
    return item

# ✅ Delete pattern
def delete_item(db: Session, item_id: int) -> None:
    item = get_item(db, item_id)
    db.delete(item)
    db.commit()
```

---

### I12: Pagination for All List Endpoints

Every `list_*` route must support `skip` + `limit` pagination. Unbounded list returns are forbidden.

```python
# Service
def list_items(db: Session, skip: int = 0, limit: int = 20) -> list[Item]:
    return db.query(Item).offset(skip).limit(limit).all()

# Router
@router.get("/")
def list_items(
    skip: int = 0,
    limit: int = 20,
    db: Session = Depends(get_db_session),
):
    """
    List all items with pagination.

    - **skip**: Records to skip (default 0)
    - **limit**: Max records to return (default 20, max 100)
    """
    logger.debug(f"Listing items | skip={skip}, limit={limit}")
    try:
        if limit > PaginationLimits.MAX_LIMIT:
            raise_bad_request(f"Limit cannot exceed {PaginationLimits.MAX_LIMIT}")
        items = item_service.list_items(db, skip=skip, limit=limit)
        return build_success_response(
            ItemMessages.LIST,
            [ItemResponse.model_validate(item) for item in items]
        )
    except HTTPException:
        raise
    except Exception:
        logger.exception(f"Failed to list items | skip={skip}, limit={limit}")
        raise_internal_server_error()
```

**Rules:** Default limit = 20. Max limit = 100 (enforced in route). Never return all records without a limit.

---

### I13: Constants Over Magic Values

All user-facing strings, error messages, and numeric business rules must live in `app/common/constants.py`. Never inline them.

```python
# ❌ Magic strings and numbers scattered everywhere
return build_success_response("Item fetched", ...)
raise_not_found("Item not found")
if limit > 100:

# ✅ Defined once, referenced everywhere
# app/common/constants.py

class ItemMessages:
    FETCHED   = "Item fetched"
    CREATED   = "Item created"
    UPDATED   = "Item updated"
    DELETED   = "Item deleted"
    LIST      = "Items fetched"
    NOT_FOUND = "Item not found"
    INACTIVE  = "Item is inactive"
    DUPLICATE = "Item with this name already exists"

class PaginationLimits:
    DEFAULT_SKIP  = 0
    DEFAULT_LIMIT = 20
    MAX_LIMIT     = 100
```

```python
# Usage in router
from app.common.constants import ItemMessages, PaginationLimits

return build_success_response(ItemMessages.FETCHED, item_data)
raise_not_found(ItemMessages.NOT_FOUND)
```

**Rule:** Any string a user reads, or any number encoding a business rule, must be a constant.

---

### I14: PATCH Uses `exclude_unset=True`

PATCH endpoints must only update fields explicitly sent by the client. Full `.model_dump()` overwrites unset fields with `None`.

```python
# ❌ Overwrites unset fields with None
for field, value in payload.model_dump().items():
    setattr(item, field, value)

# ✅ Only touches fields the client sent
for field, value in payload.model_dump(exclude_unset=True).items():
    setattr(item, field, value)
```

**PATCH schema — all fields optional:**
```python
class ItemPatchSchema(BaseModel):
    name: str | None = None
    description: str | None = None
    is_active: bool | None = None
```

**Rule:** PUT uses `.model_dump()` (full replace). PATCH always uses `.model_dump(exclude_unset=True)` (partial update).

---

### I15: Reusable Dependencies for Shared Route Logic

Any logic repeated across more than one route must become a FastAPI `Depends()`. Never copy-paste auth checks, pagination parsing, or permission gates.

```python
# ❌ Auth check duplicated in every route
@router.get("/{item_id}")
def get_item(item_id: int, token: str = Header(...), db: Session = Depends(get_db_session)):
    user = decode_access_token(token)
    if not user:
        raise_bad_request("Invalid token")
    ...

# ✅ Extracted into one reusable dependency
# app/dependencies.py

def get_current_user(authorization: str = Header(...)) -> dict:
    user = decode_access_token(authorization)
    if not user:
        raise_unauthorized("Invalid or expired token")
    return user

def get_pagination(skip: int = 0, limit: int = PaginationLimits.DEFAULT_LIMIT) -> dict:
    if limit > PaginationLimits.MAX_LIMIT:
        raise_bad_request(f"Limit cannot exceed {PaginationLimits.MAX_LIMIT}")
    return {"skip": skip, "limit": limit}
```

```python
# Clean router — zero repeated logic
from app.dependencies import get_current_user, get_pagination

@router.get("/")
def list_items(
    db: Session = Depends(get_db_session),
    pagination: dict = Depends(get_pagination),
    current_user: dict = Depends(get_current_user),
):
    ...
```

**Rule:** If logic appears in 2+ routes, it must be a dependency — not copied code.

---

Every skill file must follow this exact structure. Missing sections are not acceptable.

---

### 1. `# <Skill Name>`

**Format:** `# <Domain>: <Specific Rule Area>`

The title must be specific enough to be unambiguous.

| ❌ Vague | ✅ Precise |
|---|---|
| `# API Rules` | `# FastAPI: Controller Layer Standards` |
| `# Database` | `# SQLAlchemy: Session & Transaction Management` |
| `# Errors` | `# Error Handling: HTTP Exception Propagation` |

---

### 2. `## Metadata`

```markdown
## Metadata
- **Applies To:** `app/routers/`, `app/services/`, `app/models/` *(list exact dirs/files)*
- **Language/Framework:** Python 3.11+, FastAPI 0.110+, SQLAlchemy 2.x
- **Related Skills:** `sqlalchemy_orm_patterns.md`, `error_handling_rules.md`
- **Last Updated:** YYYY-MM-DD
- **Enforced By:** Code review + agent validation
```

This section tells the agent **exactly where** a rule applies and what other skills to cross-reference.

---

### 3. `## Objective`

One to three sentences. Must answer:
- **What** pattern does this skill establish?
- **Why** does it exist (what problem does it prevent)?

**Template:**
```
To establish [pattern] for [scope], ensuring [outcome].
This prevents [anti-pattern or failure mode].
```

**Example:**
```
To establish a uniform controller pattern for all FastAPI route handlers, ensuring
consistent error propagation, response formatting, and observability.
This prevents naked dict returns, swallowed exceptions, and inconsistent HTTP status codes.
```

---

### 4. `## Canonical Imports`

List every import the agent must use for this domain. No alternatives are permitted unless explicitly listed as acceptable.

```python
## Canonical Imports

# ✅ Always use these — exact paths, no substitutions
from app.logger.logging import logger          # project logger — never import `logging` directly
from app.db.session import get_db_session      # DB session dependency
from app.common.response import (              # ← app/common/response.py (NOT app/utils/)
    build_success_response,
    raise_bad_request,
    raise_not_found,
    raise_conflict,
    raise_internal_server_error,
)
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
```

> ⚠️ The response helpers live in `app/common/response.py` — **not** `app/utils/`. Always verify the import path before generating code.

> If a required utility does not exist yet, the agent must create it following the established utility pattern before using it — never inline the logic.

---

### 5. `## Rules & Guidelines`

Numbered, declarative, and unambiguous. Each rule must be independently testable.

**Format for each rule:**

```
**R<N>: <Short Rule Name>**
<One-sentence imperative statement of the rule.>
Rationale: <Why this rule exists.>
```

**Example rules for a controller skill:**

```
**R1: Always Use `build_success_response()` for Success**
All route handlers must return `build_success_response(message, data)` — never a raw dict.
Rationale: Guarantees the uniform envelope `{ status: true, message, data }` across all endpoints.

**R2: Always Use Centralized Error Raisers from `app/common/response.py`**
Never construct `HTTPException` directly. Always use:
`raise_bad_request()`, `raise_not_found()`, `raise_conflict()`, `raise_internal_server_error()`.
Rationale: These helpers build the correct error envelope. Direct HTTPException bypasses envelope formatting.

**R3: `except HTTPException: raise` Must Always Come Before `except Exception`**
The re-raise block for HTTPException is mandatory and must precede the generic catch.
Rationale: `raise_not_found()` internally raises an HTTPException. Without this block,
the generic `except Exception` would catch it and overwrite it as a 500 Internal Error.

**R4: Always Log Entry Points with `logger.debug`**
Every route handler must open with `logger.debug(f"<Action>: <identifier>")`.
Rationale: Provides a consistent audit trail. The middleware logs outcomes; the controller logs intent.

**R5: Use `logger.exception()` in `except Exception` — Never `logger.error()`**
Inside the generic catch, always use `logger.exception(f"Unexpected error <context>")`.
Rationale: `logger.exception` captures the full stack trace automatically. `logger.error` does not.
The client still receives a clean 500 envelope — the trace stays server-side only.

**R6: Service Layer Owns All Business Logic**
Controllers must not contain DB queries, computations, or transformations.
All logic belongs in `app/services/`.
Rationale: Keeps controllers thin, readable, and independently testable.

**R7: Type-Annotate All Route Parameters**
Every route parameter, request body, and dependency must carry a Python type annotation.
Rationale: Powers FastAPI's automatic validation and OpenAPI schema generation.
A missing annotation means FastAPI cannot validate or document the parameter.

**R8: Never Catch `RequestValidationError` in Controllers**
Pydantic schema validation errors are handled globally by `main.py`. Do not intercept them.
Rationale: The global handler formats them as a 422 envelope. Catching locally would bypass this.

**R9: Never Log Inside `except HTTPException: raise`**
The re-raise block must be silent — no logging, no wrapping.
Rationale: The global exception handler and middleware already log HTTP errors with full context.
Double-logging creates noise and inaccurate traceback attribution.
```

---

### 6. `## Anti-Patterns (Strictly Forbidden)`

A checklist of what the agent must **never** generate. Written as detectable code smells.

```markdown
## Anti-Patterns (Strictly Forbidden)

- ❌ Returning raw `dict` from a route — always use `build_success_response()`
- ❌ Raising `HTTPException(status_code=404, detail="...")` directly — use `raise_not_found("...")`
- ❌ Importing from `app/utils/response.py` — correct path is `app/common/response.py`
- ❌ Placing `except Exception` before `except HTTPException` — swallows intentional HTTP errors as 500
- ❌ Adding logging inside `except HTTPException: raise` — middleware handles it
- ❌ Using `logger.error(...)` in `except Exception` — use `logger.exception(...)` to capture stack trace
- ❌ Bare `logger.exception("Unexpected error")` with no context — always include resource + identifier (I1)
- ❌ Nested `if/else` for business validation — use guard clauses, fail fast (I2)
- ❌ Service returning `None` for missing resources — service must raise typed domain exceptions (I3)
- ❌ Returning raw SQLAlchemy model objects — always serialize through a Pydantic `*Response` schema (I5)
- ❌ Routes without docstrings — every route must document its non-200 status codes (I6)
- ❌ `logger.debug(f"Fetching item: {id}")` — use pipe format `f"Fetching item | item_id={id}"` (I7)
- ❌ Using `print()` for any output — always use the project logger
- ❌ Importing `logging` directly — always import from `app.logger.logging`
- ❌ Writing DB queries inside a controller — belongs in `app/services/`
- ❌ Catching `RequestValidationError` in controllers — handled globally by `main.py`
- ❌ Returning `None` implicitly from a route — always return a response object
- ❌ Untyped route parameters — e.g., `def get_item(item_id)` instead of `def get_item(item_id: int)`
- ❌ Using `Optional` from `typing` — use `X | None` syntax (Python 3.10+)
- ❌ Single-letter or cryptic variable names like `x`, `res`, `d`, `i` — always use descriptive names (I8)
- ❌ Generic variable names like `result` for serialized data — use `<resource>_data` (I8)
- ❌ Function names with vague verbs: `handle_`, `process_`, `do_` — use precise verb+noun (I9)
- ❌ Route functions named as nouns only: `def item(...)` — must be `def get_item(...)` (I9)
- ❌ Boolean functions without `is_`/`has_`/`can_` prefix — e.g. `def active()` → `def is_active()` (I9)
- ❌ Domain exception classes named vaguely: `NotFound`, `ItemError` — use `ItemNotFoundError` pattern (I9)
- ❌ Schema classes named without purpose suffix: `Item` — use `ItemResponse`, `ItemCreateSchema` (I9)
- ❌ Service functions without return type annotations (I10)
- ❌ `db.commit()` or `db.refresh()` inside a controller — belongs in service layer (I11)
- ❌ List routes without `skip` + `limit` pagination params (I12)
- ❌ `limit` enforced without a max cap — unbounded queries are forbidden (I12)
- ❌ Inline magic strings like `"Item not found"` scattered across routes — use constants (I13)
- ❌ Inline magic numbers like `100` for max limit — use `PaginationLimits.MAX_LIMIT` (I13)
- ❌ PATCH using `.model_dump()` instead of `.model_dump(exclude_unset=True)` (I14)
- ❌ Auth, pagination, or permission logic copy-pasted across routes — must be a `Depends()` (I15)
```

---

### 7. `## Golden Path Examples`

At minimum: one full correct example and one corrected anti-pattern example.

#### 7a. Complete Correct Example — GET with typed domain exceptions (all improvements applied)

```python
# app/routers/items.py

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.logger.logging import logger
from app.db.session import get_db_session
from app.common.response import (
    build_success_response,
    raise_bad_request,
    raise_not_found,
    raise_internal_server_error,
)
from app.exceptions import ItemNotFoundError, ItemInactiveError  # I3
from app.schemas.item_schema import ItemResponse                 # I5
from app.services import item_service

router = APIRouter(prefix="/items", tags=["Items"])


@router.get("/{item_id}")
def get_item(item_id: int, db: Session = Depends(get_db_session)):
    """
    Fetch a single item by ID.

    Returns 404 if the item does not exist.
    Returns 400 if the item is inactive.
    """                                                           # I6
    logger.debug(f"Fetching item | item_id={item_id}")           # I7
    try:
        result = item_service.get_item(db, item_id)
        return build_success_response(
            "Item fetched",
            ItemResponse.model_validate(result)                   # I5
        )
    except ItemNotFoundError:                                     # I3, I4
        raise_not_found("Item not found")
    except ItemInactiveError:                                     # I3, I4
        raise_bad_request("Item is inactive")
    except HTTPException:
        raise
    except Exception:
        logger.exception(f"Failed to fetch item | item_id={item_id}")  # I1
        raise_internal_server_error()
```

#### 7b. Complete Correct Example — POST with creation

```python
@router.post("/")
def create_item(payload: ItemCreateSchema, db: Session = Depends(get_db_session)):
    """
    Create a new item.

    Returns 409 if an item with the same name already exists.
    """                                                           # I6
    logger.debug(f"Creating item | name={payload.name!r}")       # I7
    try:
        result = item_service.create_item(db, payload)
        return build_success_response(
            "Item created",
            ItemResponse.model_validate(result)                   # I5
        )
    except DuplicateItemError:                                    # I3, I4
        raise_conflict("Item with this name already exists")
    except HTTPException:
        raise
    except Exception:
        logger.exception(f"Failed to create item | name={payload.name!r}")  # I1
        raise_internal_server_error()
```

#### 7c. Anti-Pattern → Corrected Comparison

```python
# ❌ WRONG — 7 violations
@router.get("/{item_id}")
def get_item(item_id, db=Depends(get_db_session)):          # untyped param
    item = db.query(Item).filter(Item.id == item_id).first() # DB logic in controller
    if item:
        if item.is_active:                                   # nested logic, not guard clause
            return {"status": "ok", "data": item}            # raw dict, no response schema
        else:
            raise HTTPException(status_code=400)             # direct raise, no message
    else:
        raise HTTPException(status_code=404)                 # direct raise

# ✅ CORRECT — all 7 improvements applied
@router.get("/{item_id}")
def get_item(item_id: int, db: Session = Depends(get_db_session)):
    """
    Fetch a single item by ID.

    Returns 404 if the item does not exist.
    Returns 400 if the item is inactive.
    """
    logger.debug(f"Fetching item | item_id={item_id}")
    try:
        result = item_service.get_item(db, item_id)         # service raises typed exceptions
        return build_success_response(
            "Item fetched",
            ItemResponse.model_validate(result)
        )
    except ItemNotFoundError:
        raise_not_found("Item not found")
    except ItemInactiveError:
        raise_bad_request("Item is inactive")
    except HTTPException:
        raise
    except Exception:
        logger.exception(f"Failed to fetch item | item_id={item_id}")
        raise_internal_server_error()
```

---

### 8. `## Edge Cases & Decision Rules`

Explicit guidance for ambiguous situations the agent will encounter.

```markdown
## Edge Cases & Decision Rules

| Situation | Decision |
|---|---|
| Route returns a list (possibly empty) | Return `build_success_response("Items fetched", [])` — never 404 for empty list |
| Route deletes a resource | Return `build_success_response("Item deleted", {"id": item_id})` |
| Validation error from Pydantic | FastAPI handles automatically; do not catch `ValidationError` in controllers |
| Duplicate resource (unique constraint) | Service layer raises `raise_conflict()`; controller re-raises via `except HTTPException` |
| Partial update (PATCH) | Service receives only provided fields; use `.model_dump(exclude_unset=True)` on schema |
| Auth/permission failure | Handled by dependency; controller never checks auth inline |
```

---

### 9. `## Testing Expectations`

Defines what test coverage the agent must produce alongside any code it generates.

```markdown
## Testing Expectations

For every controller route generated, the agent must also generate:

- ✅ Happy path test (200 response, correct structure)
- ✅ Not-found test (404 response via `raise_not_found`)
- ✅ Server error test (500 via mocked service exception)
- ✅ Type validation test (422 for wrong param type, handled by FastAPI)

Test file location: `tests/routers/test_<resource>.py`
Use `pytest` + `httpx.AsyncClient` + `unittest.mock.patch` for service mocking.
```

---

## File Naming Convention

| Skill Domain | File Name |
|---|---|
| FastAPI controller patterns | `fastapi_controller_standards.md` |
| SQLAlchemy ORM & sessions | `sqlalchemy_orm_patterns.md` |
| Error handling & propagation | `error_handling_rules.md` |
| Response formatting | `response_formatting_standards.md` |
| Pydantic schema design | `pydantic_schema_patterns.md` |
| Authentication & authorization | `auth_patterns.md` |
| Background tasks & workers | `background_task_standards.md` |
| Logging & observability | `logging_observability_rules.md` |
| Database migrations (Alembic) | `alembic_migration_standards.md` |
| Dependency injection patterns | `dependency_injection_patterns.md` |

---

## Agent Compliance Checklist

Before submitting any generated code, the agent must self-verify:

**Baseline:**
- [ ] All imports use `app/common/response.py` — not `app/utils/`
- [ ] Every route has `logger.debug(...)` at entry in pipe format (I7)
- [ ] `except` order: domain exceptions → `except HTTPException: raise` → `except Exception`
- [ ] `except HTTPException: raise` block is silent — no logging inside it
- [ ] `except Exception` uses `logger.exception(...)` — not `logger.error()`
- [ ] No business logic or DB queries inside the controller
- [ ] All responses use `build_success_response()`
- [ ] All errors use designated raiser functions — no direct `HTTPException` construction
- [ ] All parameters are type-annotated
- [ ] `RequestValidationError` is not caught in the controller

**Improvements (I1–I7):**
- [ ] `logger.exception` includes resource name and identifier (I1)
- [ ] Business errors use guard clauses — no nested `if/else` (I2)
- [ ] Service raises typed domain exceptions — no `None` returns for errors (I3)
- [ ] Domain exceptions are caught before `HTTPException` in the `except` chain (I4)
- [ ] Route returns `Model.model_validate(result)` — not a raw ORM object (I5)
- [ ] Route has a docstring listing all non-200 responses (I6)
- [ ] `logger.debug` uses `| key=value` pipe format (I7)
- [ ] `app/exceptions.py` has domain exception classes for this resource
- [ ] `app/schemas/<resource>_schema.py` has a `*Response` Pydantic model
- [ ] Corresponding test stubs generated
- [ ] Variable names follow `<resource>`, `<resource>s`, `payload`, `result`, `<resource>_data` conventions (I8)
- [ ] No single-letter or cryptic variable names anywhere (I8)
- [ ] Route functions named `<http_verb>_<resource>` — e.g. `get_item`, `list_items`, `create_item` (I9)
- [ ] Service functions named `<verb>_<resource>[_by_<field>]` (I9)
- [ ] Boolean functions prefixed with `is_`, `has_`, `can_` (I9)
- [ ] Domain exceptions named `<Resource><Reason>Error` (I9)
- [ ] Schema classes named `<Resource>Response`, `<Resource>CreateSchema`, `<Resource>UpdateSchema` (I9)
- [ ] All service functions have explicit return type annotations (I10)
- [ ] Write functions follow `add → commit → refresh → return` — no commits in controllers (I11)
- [ ] All list routes have `skip` + `limit` params with a max cap enforced (I12)
- [ ] All user-facing strings and business-rule numbers are constants in `app/common/constants.py` (I13)
- [ ] PATCH routes use `.model_dump(exclude_unset=True)` — PUT uses `.model_dump()` (I14)
- [ ] Any logic used in 2+ routes is a `Depends()` in `app/dependencies.py` (I15)

> If any check fails, the agent must self-correct before outputting the code.

---

## Skill Precedence Rule

When multiple skills conflict, apply in this order:

1. **Security skills** (`auth_patterns.md`) — highest priority
2. **Error handling skills** (`error_handling_rules.md`)
3. **Domain-specific skills** (e.g., `fastapi_controller_standards.md`)
4. **General formatting skills** (e.g., `response_formatting_standards.md`)
5. **Agent's general knowledge** — lowest priority, used only when no skill applies
