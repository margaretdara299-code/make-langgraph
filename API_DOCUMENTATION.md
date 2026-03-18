# Tensaw Skills Studio — API Documentation v0.3.0

**Base URL:** `http://localhost:8000`
**Interactive Docs:** [Swagger UI](/docs) | [ReDoc](/redoc)

---

## 🏛️ System Architecture

The Tensaw Skills Studio API follows a modular architecture:
- **Connectors**: External system integrations (Jira, Slack, SQL).
- **Taxonomy**: Organizational hierarchy (Categories & Capabilities).
- **Actions**: Atomic building blocks with defined I/O and execution logic.
- **Skills**: Composed workflows (graphs) built using Actions.

---

## 🛠️ Module 1: Taxonomy (Categories & Capabilities)

Taxonomy uses **integer-based IDs** for efficient relationship mapping.

### Categories
- `GET /api/v1/categories` — List all categories.
- `POST /api/v1/categories` — Create a new category (`{"name": "...", "description": "..."}`).
- `GET /api/v1/categories/{id}` — Get detail.
- `PATCH /api/v1/categories/{id}` — Update metadata.
- `DELETE /api/v1/categories/{id}` — Delete category.

### Capabilities
- `GET /api/v1/capabilities` — List all capabilities.
- `POST /api/v1/capabilities` — Create a new capability.
- `GET /api/v1/capabilities/{id}` — Get detail.
- `PATCH /api/v1/capabilities/{id}` — Update metadata.
- `DELETE /api/v1/capabilities/{id}` — Delete capability.

---

## 🔌 Module 2: Connectors (Integrations)

Connectors store credentials and configuration for external systems.

#### `GET /api/v1/connectors` — List Connectors
- **Query Params**: `active_only` (bool)
- **Response**: Array of connectors.

#### `POST /api/v1/connectors` — Create Connector
- **Request Body**:
```json
{
  "name": "Primrose DB",
  "connector_type": "database",
  "description": "Operations Database",
  "config_json": {
    "host": "54.211.59.215",
    "port": 3306,
    "user": "af_user",
    "password": "...",
    "database": "alloFactorV4"
  }
}
```

#### `PATCH /api/v1/connectors/{id}` — Update Connector
Modify any field including `config_json`.

#### `DELETE /api/v1/connectors/{id}` — Delete
*Note: Cannot delete if currently referenced by actions.*

---

## 🧩 Module 3: Action Catalog

#### `GET /api/actions` — List Actions
- **Query Params**:
  - `status`: `published` or `draft`
  - `category`: Category ID (integer)
  - `capability`: Capability ID (integer)
  - `q`: Search keyword (name or key)

#### `POST /api/actions` — Create Action
```json
{
  "name": "AI Classify",
  "action_key": "ai.classify",
  "category_id": 1,
  "capability_id": 1,
  "inputs_schema_json": { "fields": [...] },
  "execution_json": { "model": "gpt-4o", "temp": 0.1 }
}
```

#### `GET /api/actions/{id}` — Full Detail
Returns metadata + all JSON blobs (Inputs, Outputs, Execution, Policy, UI Form).

---

## 🌪️ Module 4: Skills (Workflows)

### Library Management
#### `GET /api/skills` — List Skills
Returns a paginated list of skills with their latest version status.

#### `POST /api/skills` — Create New Skill
```json
{
  "client_id": "c_demo",
  "name": "Denial Triage",
  "category_id": 1,
  "capability_id": 6,
  "start_from": { "mode": "blank" }
}
```

### Designer & Lifecycle
#### `GET /api/skills/versions/{sv_id}/graph` — Load Nodes & Edges
#### `PUT /api/skills/versions/{sv_id}/graph` — Save Graph (Nodes + Edges)
#### `POST /api/skills/versions/{sv_id}/validate` — Run Sanity Checks
#### `POST /api/skills/versions/{sv_id}/compile` — Freeze Graph for Execution
#### `POST /api/skills/versions/{sv_id}/publish` — Activate for Production
#### `POST /api/skills/versions/{sv_id}/run` — Test Execute with Input Context
- **Example Input**: `{"input_context": {"claim_id": "123"}, "max_steps": 50}`

---

## 🚫 Error Responses

Standard Error Format:
```json
{
  "success": false,
  "error": {
    "code": "SKILL_NAME_EXISTS",
    "message": "Detailed explanation here"
  }
}
```

Common Codes:
- `NOT_FOUND`: Resource missing.
- `CONFLICT`: Duplicate name/key or invalid state transition.
- `VALIDATION_ERROR`: Field constraints failed (e.g. name too short).
- `SKILL_GRAPH_VALIDATION_FAILED`: Graph structure is invalid (missing Start/End).

---

## 🧪 Integrated Examples (Seed Data)

The following connectors are available by default if the database is seeded:
1. **Primrose Database** (`database`): Internal operations DB.
2. **Trillium Database** (`database`): Stage workflow DB.
3. **External API Service** (`api`): Configurable REST connector.
4. **Jira Product** (`api`): Project management.
5. **Slack Operations** (`api`): Team messaging.
