# Tensaw Skills Studio API Documentation
This document is auto-generated from the OpenAPI schema.

## Health
### `[GET] /health` - Health Check
**Response (Success):**
- Returns JSON object

---

## Skills
### `[GET] /api/v1/skills` - List All Skills
**Parameters:**
- `client_id` [query] : string
- `status` [query] : string
- `search` [query] : string
**Response (Success):**
- Returns JSON object

---

### `[POST] /api/v1/skills` - Create Skill
**Request Body:**
- Schema: `CreateSkillRequest`
  - `client_id` (integer)
  - `environment` (string)
  - `name` (string)
  - `skill_key` (any)
  - `description` (any)
  - `category_id` (any)
  - `capability_id` (any)
  - `tags` (List[string])
  - `start_from` (SkillStartFrom)
**Response (Success):**
- Returns JSON object

---

### `[GET] /api/v1/skills/{skill_id}` - Get Skill
Fetch a single skill's full metadata.
**Parameters:**
- `skill_id` [path] (required) : integer
**Response (Success):**
- Returns JSON object

---

### `[PATCH] /api/v1/skills/{skill_id}` - Update Skill
Update skill metadata.
**Parameters:**
- `skill_id` [path] (required) : integer
**Request Body:**
- Schema: `UpdateSkillRequest`
  - `name` (any)
  - `skill_key` (any)
  - `description` (any)
  - `category_id` (any)
  - `capability_id` (any)
  - `is_active` (any)
  - `tags` (any)
**Response (Success):**
- Returns JSON object

---

### `[DELETE] /api/v1/skills/{skill_id}` - Delete Skill
Delete a skill and all its versions.
**Parameters:**
- `skill_id` [path] (required) : integer
**Response (Success):**
- Returns JSON object

---

## Skill Versions
### `[GET] /api/v1/skill-versions/{skill_version_id}/graph` - Load Skill Graph
Load the current workflow graph (nodes + connections) for a skill version.
**Parameters:**
- `skill_version_id` [path] (required) : integer
**Response (Success):**
- Returns JSON object

---

### `[PUT] /api/v1/skill-versions/{skill_version_id}/graph` - Save Skill Graph
Bulk-save nodes and connections for a skill version.
**Parameters:**
- `skill_version_id` [path] (required) : integer
**Request Body:**
- Schema: `SaveSkillGraphRequest`
  - `nodes` (List[SkillGraphNode])
  - `connections` (object)
**Response (Success):**
- Returns JSON object

---

### `[GET] /api/v1/skill-versions/{skill_version_id}` - Get Skill Version Detail
Alias to load graph and version metadata.
**Parameters:**
- `skill_version_id` [path] (required) : integer
**Response (Success):**
- Returns JSON object

---

### `[PATCH] /api/v1/skill-versions/{skill_version_id}/nodes/{node_id}/data` - Update Node Data
Update a single node's configuration data.
**Parameters:**
- `skill_version_id` [path] (required) : integer
- `node_id` [path] (required) : string
**Request Body:**
- Schema: `UpdateNodeConfigRequest`
  - `data` (object)
**Response (Success):**
- Returns JSON object

---

### `[PUT] /api/v1/skill-versions/{skill_version_id}/status` - Update Skill Version Status
Unified endpoint to publish or unpublish a skill version.
**Parameters:**
- `skill_version_id` [path] (required) : integer
**Request Body:**
- Schema: `UpdateSkillVersionStatusRequest`
  - `status` (string)
  - `notes` (any)
**Response (Success):**
- Returns JSON object

---

### `[POST] /api/v1/skill-versions/{skill_version_id}/validate` - Validate Skill Version
Run engine validation on a saved skill version.
**Parameters:**
- `skill_version_id` [path] (required) : integer
**Response (Success):**
- Returns JSON object

---

### `[POST] /api/v1/skill-versions/{skill_version_id}/compile` - Compile Skill Version
Compile a skill version into an execution plan.
**Parameters:**
- `skill_version_id` [path] (required) : integer
**Response (Success):**
- Returns JSON object

---

### `[POST] /api/v1/skill-versions/{skill_version_id}/run` - Run Skill Version
Execute a skill version (dry-run).
**Parameters:**
- `skill_version_id` [path] (required) : integer
**Request Body:**
- Schema: `RunSkillRequest`
  - `input_context` (object)
  - `max_steps` (integer)
**Response (Success):**
- Returns JSON object

---

## Actions
### `[POST] /api/v1/actions` - Create Action
Create a new action. Default: status=published, is_active=true.
**Request Body:**
- Schema: `CreateActionDefinitionRequest`
  - `name` (string)
  - `action_key` (string)
  - `description` (any)
  - `category_id` (any)
  - `capability_id` (any)
  - `icon` (any)
  - `default_node_title` (any)
  - `scope` (any)
  - `client_id` (any)
  - `status` (any)
  - `is_active` (boolean)
  - `configurations_json` (any)
**Response (Success):**
- Returns JSON object

---

### `[GET] /api/v1/actions` - List Actions
List all actions. Optional filters: status, capability, category, q (search).
**Parameters:**
- `status` [query] : string
- `capability` [query] : string
- `category` [query] : string
- `q` [query] : string
**Response (Success):**
- Returns JSON object

---

### `[PUT] /api/v1/actions/{action_definition_id}/status` - Update Action Status
Update only the status (draft/published) and/or is_active flag.
**Parameters:**
- `action_definition_id` [path] (required) : integer
**Request Body:**
- Schema: `UpdateActionStatusRequest`
  - `status` (any)
  - `is_active` (any)
**Response (Success):**
- Returns JSON object

---

### `[GET] /api/v1/actions/{action_definition_id}` - Get Action
Get a single action with all its JSON blobs.
**Parameters:**
- `action_definition_id` [path] (required) : integer
**Response (Success):**
- Returns JSON object

---

### `[PUT] /api/v1/actions/{action_definition_id}` - Update Action
Update action metadata and/or JSON blobs. Also supports status and is_active.
**Parameters:**
- `action_definition_id` [path] (required) : integer
**Request Body:**
- Schema: `UpdateActionDefinitionRequest`
  - `name` (any)
  - `action_key` (any)
  - `description` (any)
  - `category_id` (any)
  - `capability_id` (any)
  - `icon` (any)
  - `default_node_title` (any)
  - `scope` (any)
  - `status` (any)
  - `is_active` (any)
  - `configurations_json` (any)
**Response (Success):**
- Returns JSON object

---

### `[DELETE] /api/v1/actions/{action_definition_id}` - Delete Action
Delete an action (only if not in use by any skill graphs).
**Parameters:**
- `action_definition_id` [path] (required) : integer
**Response (Success):**
- Returns JSON object

---

## Connectors
### `[POST] /api/v1/connectors/connectivity/verify` - Verify Connectivity Endpoint
Enterprise Connectivity Validation.
Verifies database credentials and returns rich metadata (latency, version).
**Request Body:**
- Schema: `ConnectivityValidationRequest`
  - `engine` (string)
  - `host` (string)
  - `port` (integer)
  - `username` (string)
  - `password` (string)
  - `database` (string)
**Response (Success):**
- Returns JSON object

---

### `[POST] /api/v1/connectors` - Create Connector
Create a new connector with configuration.
**Request Body:**
- Schema: `CreateConnectorRequest`
  - `name` (string)
  - `connector_type` (string)
  - `description` (any)
  - `config_json` (object)
  - `is_active` (boolean)
**Response (Success):**
- Returns JSON object

---

### `[GET] /api/v1/connectors` - List Connectors
List all connectors.
**Parameters:**
- `active_only` [query] : string
**Response (Success):**
- Returns JSON object

---

### `[GET] /api/v1/connectors/grouped` - List Connectors Grouped
List all connectors grouped by their connector type (e.g., DATABASE, API).
**Response (Success):**
- Returns JSON object

---

### `[GET] /api/v1/connectors/{connector_id}` - Get Connector
Get a single connector by ID.
**Parameters:**
- `connector_id` [path] (required) : integer
**Response (Success):**
- Returns JSON object

---

### `[PATCH] /api/v1/connectors/{connector_id}` - Update Connector
Update an existing connector's configuration.
**Parameters:**
- `connector_id` [path] (required) : integer
**Request Body:**
- Schema: `UpdateConnectorRequest`
  - `name` (any)
  - `connector_type` (any)
  - `description` (any)
  - `config_json` (any)
  - `status` (any)
  - `is_active` (any)
**Response (Success):**
- Returns JSON object

---

### `[DELETE] /api/v1/connectors/{connector_id}` - Delete Connector
Delete a connector (only if not in use by any actions).
**Parameters:**
- `connector_id` [path] (required) : integer
**Response (Success):**
- Returns JSON object

---

## Category
### `[GET] /api/v1/categories` - List Categories
**Response (Success):**
- Returns JSON object

---

### `[POST] /api/v1/categories` - Create Category
**Request Body:**
- Schema: `CreateCategoryRequest`
  - `name` (string)
  - `description` (any)
**Response (Success):**
- Returns JSON object

---

### `[GET] /api/v1/categories/{category_id}` - Get Category
**Parameters:**
- `category_id` [path] (required) : integer
**Response (Success):**
- Returns JSON object

---

### `[PATCH] /api/v1/categories/{category_id}` - Update Category
**Parameters:**
- `category_id` [path] (required) : integer
**Request Body:**
- Schema: `UpdateCategoryRequest`
  - `name` (any)
  - `description` (any)
**Response (Success):**
- Returns JSON object

---

### `[DELETE] /api/v1/categories/{category_id}` - Delete Category
**Parameters:**
- `category_id` [path] (required) : integer
**Response (Success):**
- Returns JSON object

---

## Capability
### `[GET] /api/v1/capabilities` - List Capabilities
**Response (Success):**
- Returns JSON object

---

### `[POST] /api/v1/capabilities` - Create Capability
**Request Body:**
- Schema: `CreateCapabilityRequest`
  - `name` (string)
  - `description` (any)
**Response (Success):**
- Returns JSON object

---

### `[GET] /api/v1/capabilities/{capability_id}` - Get Capability
**Parameters:**
- `capability_id` [path] (required) : integer
**Response (Success):**
- Returns JSON object

---

### `[PATCH] /api/v1/capabilities/{capability_id}` - Update Capability
**Parameters:**
- `capability_id` [path] (required) : integer
**Request Body:**
- Schema: `UpdateCapabilityRequest`
  - `name` (any)
  - `description` (any)
**Response (Success):**
- Returns JSON object

---

### `[DELETE] /api/v1/capabilities/{capability_id}` - Delete Capability
**Parameters:**
- `capability_id` [path] (required) : integer
**Response (Success):**
- Returns JSON object

---

## Workflow Engine
### `[POST] /api/v1/engine/validate` - Validate Engine Workflow
Run structural checks on a workflow JSON definition without building it.
**Request Body:**
**Response (Success):**
- Returns JSON object

---

### `[POST] /api/v1/engine/compile` - Compile Engine Workflow
Validate and hash the workflow definition into a cacheable execution plan.
**Request Body:**
**Response (Success):**
- Returns JSON object

---

### `[POST] /api/v1/engine/run` - Execute Workflow
Execute a workflow JSON or compiled plan.
Supply an optional ?thread_id=... query parameter to resume/share memory state.
**Parameters:**
- `thread_id` [query] : string
**Request Body:**
**Response (Success):**
- Returns JSON object

---

### `[POST] /api/v1/engine/generate-code` - Generate Workflow Code
Convert a workflow JSON definition into executable LangGraph Python script.
**Request Body:**
- Schema: `WorkflowPayload`
  - `nodes` (any)
  - `edges` (any)
  - `compile_hash` (any)
  - `workflow_json` (any)
  - `skill_version_id` (any)
**Response (Success):**
- Returns JSON object

---

### `[GET] /api/v1/engine/generate-code/{skill_version_id}` - Generate Workflow Code By Id
Fetch a workflow from DB and convert it into executable LangGraph Python script.
**Parameters:**
- `skill_version_id` [path] (required) : string
**Response (Success):**
- Returns JSON object

---

### `[GET] /api/v1/engine/actions` - List Engine Actions
Return a list of all built-in action_keys the engine supports.
**Response (Success):**
- Returns JSON object

---

## Dummy Claims API
### `[GET] /api/v1/claims` - Get Claims
Return all dummy claims, optionally filtered by status.
**Parameters:**
- `status` [query] : string
**Response (Success):**
- Returns JSON object

---

### `[POST] /api/v1/claims` - Create Claim
Simulate creating a new claim.
**Request Body:**
**Response (Success):**
- Returns JSON object

---

### `[GET] /api/v1/claims/status/{status}` - Get Claims By Status
Fetch all claims that match a specific status (path-based).
**Parameters:**
- `status` [path] (required) : string
**Response (Success):**
- Returns JSON object

---

### `[GET] /api/v1/claims/{claim_id}` - Get Claim
Fetch a single claim by its ID.
**Parameters:**
- `claim_id` [path] (required) : string
**Response (Success):**
- Returns JSON object

---

### `[PUT] /api/v1/claims/{claim_id}` - Update Claim
Simulate updating an existing claim.
**Parameters:**
- `claim_id` [path] (required) : string
**Request Body:**
**Response (Success):**
- Returns JSON object

---

### `[DELETE] /api/v1/claims/{claim_id}` - Delete Claim
Simulate deleting a claim.
**Parameters:**
- `claim_id` [path] (required) : string
**Response (Success):**
- Returns JSON object

---

## Designer
### `[GET] /api/v1/designer/actions` - List Actions Grouped
List actions grouped by their category name.
**Response (Success):**
- Returns JSON object

---

## Data Models
### CloneSourceDetails
- `source_skill_id` : integer
- `source_skill_version_id` : integer
- `include_test_cases` : boolean

### ConnectivityValidationRequest
- `engine` : string
- `host` : string
- `port` : integer
- `username` : string
- `password` : string
- `database` : string

### CreateActionDefinitionRequest
- `name` : string
- `action_key` : string
- `description` : any
- `category_id` : any
- `capability_id` : any
- `icon` : any
- `default_node_title` : any
- `scope` : any
- `client_id` : any
- `status` : any
- `is_active` : boolean
- `configurations_json` : any

### CreateCapabilityRequest
- `name` : string
- `description` : any

### CreateCategoryRequest
- `name` : string
- `description` : any

### CreateConnectorRequest
- `name` : string
- `connector_type` : string
- `description` : any
- `config_json` : object
- `is_active` : boolean

### CreateSkillRequest
- `client_id` : integer
- `environment` : string
- `name` : string
- `skill_key` : any
- `description` : any
- `category_id` : any
- `capability_id` : any
- `tags` : List[string]
- `start_from` : SkillStartFrom

### RunSkillRequest
- `input_context` : object
- `max_steps` : integer

### SaveSkillGraphRequest
- `nodes` : List[SkillGraphNode]
- `connections` : object

### SkillGraphConnection
- `id` : string
- `source` : string
- `target` : string
- `sourceHandle` : any
- `targetHandle` : any
- `condition` : object
- `is_default` : boolean
- `data` : object
- `label` : any
- `labelShowBg` : any

### SkillGraphNode
- `id` : string
- `type` : string
- `position` : object
- `data` : object

### SkillStartFrom
- `mode` : string
- `template_id` : any
- `clone` : any

### UpdateActionDefinitionRequest
- `name` : any
- `action_key` : any
- `description` : any
- `category_id` : any
- `capability_id` : any
- `icon` : any
- `default_node_title` : any
- `scope` : any
- `status` : any
- `is_active` : any
- `configurations_json` : any

### UpdateActionStatusRequest
- `status` : any
- `is_active` : any

### UpdateCapabilityRequest
- `name` : any
- `description` : any

### UpdateCategoryRequest
- `name` : any
- `description` : any

### UpdateConnectorRequest
- `name` : any
- `connector_type` : any
- `description` : any
- `config_json` : any
- `status` : any
- `is_active` : any

### UpdateNodeConfigRequest
- `data` : object

### UpdateSkillRequest
- `name` : any
- `skill_key` : any
- `description` : any
- `category_id` : any
- `capability_id` : any
- `is_active` : any
- `tags` : any

### UpdateSkillVersionStatusRequest
- `status` : string
- `notes` : any

### WorkflowPayload
- `nodes` : any
- `edges` : any
- `compile_hash` : any
- `workflow_json` : any
- `skill_version_id` : any
