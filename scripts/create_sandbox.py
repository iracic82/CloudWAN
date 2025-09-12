import os
import json
from sandbox_api import SandboxAccountAPI

# Configuration
BASE_URL = "https://csp.infoblox.com/v2"
TOKEN = os.environ.get('Infoblox_Token')
TEAM_ID = os.environ.get('INSTRUQT_PARTICIPANT_ID', 'default-team')
SANDBOX_ID_FILE = "sandbox_id.txt"
EXTERNAL_ID_FILE = "external_id.txt"

# Request body for sandbox creation
sandbox_request_body = {
    "name": TEAM_ID,
    "description": "Created via Python script Instruqt Demo",
    "state": "active",
    "tags": {"instruqt": "igor"},
    "admin_user": {
        "email": os.environ.get("INFOBLOX_EMAIL"),
        "name": TEAM_ID
    }
}

# API client initialization
api = SandboxAccountAPI(base_url=BASE_URL, token=TOKEN)
create_response = api.create_sandbox_account(sandbox_request_body)

# Response handling
if create_response["status"] == "success":
    print("✅ Sandbox created successfully.")
    sandbox_data = create_response["data"]
    sandbox_id = None
    external_id = None

    # Extract sandbox_id
    if isinstance(sandbox_data, dict):
        if "result" in sandbox_data and "id" in sandbox_data["result"]:
            sandbox_id = sandbox_data["result"]["id"]
        elif "id" in sandbox_data:
            sandbox_id = sandbox_data["id"]

    # Strip prefix for sandbox_id
    if sandbox_id and sandbox_id.startswith("identity/accounts/"):
        sandbox_id = sandbox_id.split("/")[-1]

    if sandbox_id:
        with open(SANDBOX_ID_FILE, "w") as f:
            f.write(sandbox_id)
        print(f"📁 Sandbox ID saved to {SANDBOX_ID_FILE}: {sandbox_id}")
    else:
        print("⚠️ Sandbox ID not found.")

    # Extract external_id from admin_user.account_id
    admin_user = sandbox_data.get("result", {}).get("admin_user")
    if admin_user and "account_id" in admin_user:
        external_id = admin_user["account_id"].split("/")[-1]

    if external_id:
        with open(EXTERNAL_ID_FILE, "w") as f:
            f.write(external_id)
        print(f"🔐 External ID saved to {EXTERNAL_ID_FILE}: {external_id}")
    else:
        print("⚠️ External ID not found in admin_user.account_id.")
else:
    print(f"❌ Sandbox creation failed: {create_response['error']}")
