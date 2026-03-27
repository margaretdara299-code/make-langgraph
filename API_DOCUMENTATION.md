# Tensaw Skills Studio — API Documentation

**Base URL:** `http://localhost:8000`  
**Interactive Docs:** [Swagger UI](http://localhost:8000/docs) | [ReDoc](http://localhost:8000/redoc)

---

## Standard Response Envelope

All responses follow this structure:

```json
{ "status": true, "message": "...", "data": { ... } }
```

**Error:**
```json
{ "status": false, "message": "Error details", "data": null }
```

---

## Module 1: Categories

**Base Prefix:** `/api/v1`

| Method | Endpoint | Description |
|:---|:---|:---|
| `GET` | `/categories` | List all categories |
| `POST` | `/categories` | Create a category |
| `GET` | `/categories/{id}` | Get a category |
| `PATCH` | `/categories/{id}` | Update a category |
| `DELETE` | `/categories/{id}` | Delete a category |

### GET /api/v1/categories
```
GET http://localhost:8000/api/v1/categories
```
**Response:**
```json
{
  "status": true,
  "message": "Categories fetched",
  "data": [
    { "category_id": 1, "name": "Eligibility", "description": "Patient eligibility workflows" },
    { "category_id": 2, "name": "Claims", "description": "Claim submission and tracking" }
  ]
}
```

---

## Module 2: Capabilities

**Base Prefix:** `/api/v1`

| Method | Endpoint | Description |
|:---|:---|:---|
| `GET` | `/capabilities` | List all capabilities |
| `POST` | `/capabilities` | Create a capability |
| `GET` | `/capabilities/{id}` | Get a capability |
| `PATCH` | `/capabilities/{id}` | Update a capability |
| `DELETE` | `/capabilities/{id}` | Delete a capability |

### GET /api/v1/capabilities
```
GET http://localhost:8000/api/v1/capabilities
```

---

## Module 3: Connectors

**Base Prefix:** `/api/v1`

| Method | Endpoint | Description |
|:---|:---|:---|
| `GET` | `/connectors` | List all connectors |
| `GET` | `/connectors/grouped` | Connectors grouped by type |
| `POST` | `/connectors` | Create a connector |
| `GET` | `/connectors/{id}` | Get a connector |
| `PATCH` | `/connectors/{id}` | Update a connector |
| `DELETE` | `/connectors/{id}` | Delete a connector |
| `POST` | `/connectors/connectivity/verify` | Test DB connection |

### GET /api/v1/connectors/grouped
```
GET http://localhost:8000/api/v1/connectors/grouped
```
**Response:**
```json
{
  "status": true,
  "message": "Connectors grouped by type fetched successfully",
  "data": {
    "DATABASE": [
      { "connector_id": 1, "name": "Main SQL Engine", "connector_type": "database" }
    ],
    "API": [
      { "connector_id": 2, "name": "Generic API Service", "connector_type": "api" }
    ]
  }
}
```

### POST /api/v1/connectors/connectivity/verify
```
POST http://localhost:8000/api/v1/connectors/connectivity/verify
```
**Request Body:**
```json
{
  "engine": "mysql",
  "host": "127.0.0.1",
  "port": 3306,
  "username": "root",
  "password": "secret",
  "database": "rcm_dev"
}
```

---

## Module 4: Actions

**Base Prefix:** `/api`

| Method | Endpoint | Description |
|:---|:---|:---|
| `GET` | `/actions` | List actions (with filters) |
| `GET` | `/actions/grouped` | Actions grouped by category |
| `POST` | `/actions` | Create an action |
| `GET` | `/actions/{id}` | Get full action definition |
| `PUT` | `/actions/{id}` | Update an action |
| `PUT` | `/actions/{id}/status` | Change action status |
| `DELETE` | `/actions/{id}` | Delete an action |

### GET /api/actions/grouped
```
GET http://localhost:8000/api/actions/grouped
```
**Response:**
```json
{
  "status": true,
  "message": "Grouped actions fetched",
  "data": {
    "Eligibility": [
      { "action_definition_id": "uuid-1", "name": "Verify Eligibility", "action_key": "rcm.eligibility.verify" }
    ]
  }
}
```

---

## Module 5: Skills & Designer

**Base Prefix:** `/api`

| Method | Endpoint | Description |
|:---|:---|:---|
| `GET` | `/skills` | List all skills |
| `POST` | `/skills` | Create a skill |
| `GET` | `/skills/{id}` | Get skill metadata |
| `PATCH` | `/skills/{id}` | Update skill metadata |
| `DELETE` | `/skills/{id}` | Delete skill + all versions |
| `GET` | `/skills/versions/{vid}/graph` | Load graph (nodes + connections + meta) |
| `PUT` | `/skills/versions/{vid}/graph` | Save graph (nodes + connections) |
| `PATCH` | `/skills/versions/{vid}/nodes/{nid}/data` | Update single node config |
| `POST` | `/skills/versions/{vid}/validate` | Validate graph |
| `POST` | `/skills/versions/{vid}/compile` | Compile to runnable JSON |
| `PUT` | `/skills/versions/{vid}/status` | Publish / Draft lifecycle |
| `POST` | `/skills/versions/{vid}/run` | Run / Test the skill |

### GET /api/skills/versions/{vid}/graph
```
GET http://localhost:8000/api/skills/versions/version-uuid-here/graph
```
**Response:**
```json
{
  "status": true,
  "message": "Graph loaded",
  "data": {
    "skill_version_id": "uuid",
    "skill_id": "uuid",
    "name": "My RCM Skill",
    "skill_key": "SK_001",
    "description": "Skill description",
    "nodes": [...],
    "connections": {...}
  }
}
```

### PUT /api/skills/versions/{vid}/graph
```
PUT http://localhost:8000/api/skills/versions/version-uuid-here/graph
```
**Request Body:**
```json
{
  "nodes": [
    { "id": "n1", "type": "trigger", "position": { "x": 100, "y": 100 }, "data": { "label": "Start" } }
  ],
  "connections": {
    "e1": { "id": "e1", "source": "n1", "target": "n2" }
  }
}
```

---

## Module 6: Workflow Engine (Execution)

**Base Prefix:** `/api/engine`

| Method | Endpoint | Description |
|:---|:---|:---|
| `POST` | `/validate` | Structural check for JSON workflows |
| `POST` | `/compile` | Compile and hash a workflow plan |
| `POST` | `/run` | Execute a workflow (direct JSON or plan) |
| `POST` | `/generate-code` | Convert raw JSON to Python code |
| `GET` | `/generate-code/{id}` | Fetch version by ID and convert to Python |
| `GET` | `/actions` | List built-in core actions |

### GET /api/engine/generate-code/{skill_version_id}
Fetches a specific skill version from the database and returns it as a standalone Python script.

**Sample Request:**
`GET http://localhost:8000/api/engine/generate-code/sv_12345`

### POST /api/engine/generate-code
Generates a script from a raw workflow definition (useful for unsaved changes).

**Sample Request (via ID):**
```json
{
  "skill_version_id": "sv_12345"
}
```

**Sample Request (via JSON):**
```json
{
  "workflow_json": {
    "nodes": [...],
    "connections": {...}
  }
}
```

**Sample Response:**
```json
{
  "status": true,
  "message": "Python source generated successfully",
  "data": {
    "code": "from typing import TypedDict...\nbuilder = StateGraph(WorkflowState)...\ngraph = builder.compile()"
  }
}
```

### POST /api/engine/run
Executes a workflow defined as a JSON graph. The engine handles core logic (conditions, state saving) internally and treats any other `actionKey` as a dynamic API call.

**Sample Request (Mixed Core and Dynamic Actions):**
```json
{
  "nodes": [
    {
      "id": "n1",
      "type": "action",
      "data": { 
        "label": "Get Claim Info", 
        "actionKey": "rcm.claims.fetch",
        "configurationsJson": { "claim_id": "CLM-123" }
      }
    },
    {
      "id": "n2",
      "type": "action",
      "data": { 
        "label": "Data Check", 
        "actionKey": "condition_check", 
        "configurationsJson": { "field": "last_result", "op": "exists" } 
      }
    },
    {
      "id": "n3",
      "type": "end.success",
      "data": { 
        "label": "Finalize", 
        "actionKey": "direct_reply",
        "configurationsJson": { "message": "Claim processed successfully" }
      }
    }
  ],
  "connections": {
    "e1": { "source": "n1", "target": "n2" },
    "e2": { "source": "n2", "target": "n3", "condition": { "value": "true" } }
  }
}
```

**Built-in Core Actions:**
| actionKey | Description |
|:---|:---|
| `condition_check` | Logic branching based on state (eq, gt, lt, exists) |
| `save_result` | Copies `last_result` to `saved_data` for later nodes |
| `direct_reply` | Sets the final output message for the workflow |
| `*` (Dynamic) | Any other key dispatches an external API call |

---

## Module 7: Dummy Claims API (External Simulation)
This mock API simulates a real-world Claims processing service. It is used to test external service integration and dynamic API nodes.

**Base Path:** `/api/claims`

| Method | Endpoint | Description |
|:---|:---|:---|
| `GET` | `/?status=Pending` | List claims (query filter) |
| `GET` | `/status/{status}` | List claims (path filter) |
| `GET` | `/{id}` | Fetch a single claim by ID |
| `POST` | `/` | Create a new dummy claim |
| `PUT` | `/{id}` | Update an existing claim |
| `DELETE` | `/{id}` | Delete a claim |

**Sample Claim Object:**
```json
{
  "claim_id": "C001",
  "mrn": "MRN001",
  "patient_name": "John Doe",
  "status": "Pending",
  "total_billed": 1000.0,
  "primary_payer": "Aetna"
}
```

---

## Error Registry

| HTTP | Scenario | Example Message |
|:---|:---|:---|
| `400` | Bad request / in-use conflict | `Action cannot be deleted: currently referenced in skill graphs` |
| `404` | Resource not found | `Skill not found`, `Action not found` |
| `409` | Duplicate key conflict | `Skill with this name already exists` |
| `422` | Validation failed | `Invalid request` |
| `500` | Internal / connectivity error | `Internal error` |
