import json
from app.engine.executor.runner import run_workflow

workflow_json = {
    "nodes": [
        {"id":"node-1775045629870-7096","type":"start","data":{"label": "Start"}},
        {"id":"node-1775047710197-3137","type":"action","data":{"label": "Initialize", "action_key":"initialize", "configurations_json":{"url":"http://localhost:8005/api/v1/denial/initialize","method":"GET","output_key":"initialize_response"}}},
        {"id":"node-1775047719990-456","type":"action","data":{"label": "Fetch Record", "action_key":"fetch_record", "configurations_json":{"url":"http://localhost:8005/api/v1/denial/fetch-record","method":"GET","output_key":"fetch_response"}}},
        {"id":"node-1775047728917-9455","type":"action","data":{"label": "Verify Claim", "action_key":"verify_claim", "configurations_json":{"url":"http://localhost:8005/api/v1/denial/verify-claim","method":"GET","output_key":"verify_response"}}},
        {"id":"node-1775047738005-5598","type":"action","data":{"label": "Triage Type", "action_key":"triage_type", "configurations_json":{"url":"http://localhost:8005/api/v1/denial/triage-type","method":"GET","output_key":"triage_response"}}},
        {"id":"node-1775047747109-6217","type":"action","data":{"label": "Parse Reasons", "action_key":"parse_reasons", "configurations_json":{"url":"http://localhost:8005/api/v1/denial/parse-reasons","method":"GET","output_key":"parse_response"}}},
        {"id":"node-1775047755261-754","type":"action","data":{"label": "Draft Appeal", "action_key":"draft_appeal", "configurations_json":{"url":"http://localhost:8005/api/v1/denial/draft-appeal","method":"GET","output_key":"draft_response"}}},
        {"id":"node-1775047766054-7962","type":"action","data":{"label": "Close Case", "action_key":"close_case", "configurations_json":{"url":"http://localhost:8005/api/v1/denial/close-case","method":"GET","output_key":"close_response"}}},
        {"id":"end-node","type":"end.success","data":{"label": "End"}}
    ],
    "connections": {
        "e1": {"source":"node-1775045629870-7096","target":"node-1775047710197-3137"},
        "e2": {"source":"node-1775047710197-3137","target":"node-1775047719990-456"},
        "e3": {"source":"node-1775047719990-456","target":"node-1775047728917-9455"},
        "e4": {"source":"node-1775047728917-9455","target":"node-1775047738005-5598"},
        "e5": {"source":"node-1775047738005-5598","target":"node-1775047747109-6217"},
        "e6": {"source":"node-1775047747109-6217","target":"node-1775047755261-754"},
        "e7": {"source":"node-1775047755261-754","target":"node-1775047766054-7962"},
        "e8": {"source":"node-1775047766054-7962","target":"end-node"}
    }
}

if __name__ == "__main__":
    print("Testing 7-node flow execution via real HTTP requests (Port 8005)...")
    try:
        final_state = run_workflow(workflow_json, thread_id="test_run_7_node")
        print(json.dumps({k: v for k, v in final_state.items() if k != "logs"}, indent=2))
        print("✅ Workflow execution completed successfully.")
    except Exception as e:
        print(f"Error during execution: {e}")
