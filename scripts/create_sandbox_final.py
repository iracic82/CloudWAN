import os
import sys
import time
import random
from sandbox_api import SandboxAccountAPI

# Configuration
BASE_URL = "https://csp.infoblox.com/v2"
TOKEN = os.environ.get("Infoblox_Token")
TEAM_ID = os.environ.get("INSTRUQT_PARTICIPANT_ID", "default-team")
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
        "name": TEAM_ID,
    },
}

# API client initialization
api = SandboxAccountAPI(base_url=BASE_URL, token=TOKEN)

# Retry on transient errors (e.g. 504 Gateway Timeout)
max_retries = 5
for attempt in range(max_retries):
    create_response = api.create_sandbox_account(sandbox_request_body)
    if create_response.get("status") == "success":
        break
    print(
        f"⚠️ Attempt {attempt+1} failed: {create_response.get('error')}",
        flush=True,
    )
    time.sleep((2**attempt) + random.random())
else:
    print("❌ Sandbox creation failed after retries", flush=True)
    sys.exit(1)

print("✅ Sandbox created successfully.", flush=True)
sandbox_data = create_response["data"]

# Extract sandbox_id
sandbox_id = None
if isinstance(sandbox_data, dict):
    if "result" in sandbox_data and "id" in sandbox_data["result"]:
        sandbox_id = sandbox_data["result"]["id"]
    elif "id" in sandbox_data:
        sandbox_id = sandbox_data["id"]

if sandbox_id and sandbox_id.startswith("identity/accounts/"):
    sandbox_id = sandbox_id.split("/")[-1]

if not sandbox_id:
    print("❌ Sandbox ID not found. Aborting.", flush=True)
    sys.exit(1)

with open(SANDBOX_ID_FILE, "w") as f:
    f.write(sandbox_id)
print(f"✅ Sandbox ID saved to {SANDBOX_ID_FILE}: {sandbox_id}", flush=True)

# Extract external_id
admin_user = sandbox_data.get("result", {}).get("admin_user")
external_id = None
if admin_user and "account_id" in admin_user:
    external_id = admin_user["account_id"].split("/")[-1]

if not external_id:
    print("❌ External ID not found in admin_user.account_id. Aborting.", flush=True)
    sys.exit(1)

with open(EXTERNAL_ID_FILE, "w") as f:
    f.write(external_id)
print(f"✅ External ID saved to {EXTERNAL_ID_FILE}: {external_id}", flush=True)
