import os
import sys
import time
import random
import requests
from sandbox_api import SandboxAccountAPI

BASE_URL = "https://csp.infoblox.com/v2"
TOKEN = os.environ.get("Infoblox_Token")
SANDBOX_ID_FILE = "sandbox_id.txt"

# --- Read sandbox ID ---
try:
    with open(SANDBOX_ID_FILE, "r") as f:
        sandbox_id = f.read().strip()
except FileNotFoundError:
    print(f"❌ {SANDBOX_ID_FILE} not found. Run create_sandbox.py first.", flush=True)
    sys.exit(1)

if not sandbox_id:
    print("❌ Empty sandbox ID. Aborting.", flush=True)
    sys.exit(1)

api = SandboxAccountAPI(base_url=BASE_URL, token=TOKEN)
endpoint = f"{api.base_url}/sandbox/accounts/{sandbox_id}"

# --- Retry loop for deletion ---
max_retries = 5
for attempt in range(max_retries):
    try:
        print(f"🔗 DELETE {endpoint} (attempt {attempt+1})", flush=True)
        resp = requests.delete(endpoint, headers=api._headers())
        if resp.status_code in [200, 204]:
            print(f"✅ Sandbox {sandbox_id} deleted.", flush=True)
            try:
                os.remove(SANDBOX_ID_FILE)
                print(f"📁 Removed {SANDBOX_ID_FILE}", flush=True)
            except OSError as e:
                print(f"⚠️ Could not remove {SANDBOX_ID_FILE}: {e}", flush=True)
            sys.exit(0)
        else:
            print(f"⚠️ Status {resp.status_code}: {resp.text}", flush=True)
    except Exception as e:
        print(f"⚠️ Error: {e}", flush=True)
    time.sleep((2**attempt) + random.random())

print("❌ Sandbox deletion failed after retries. Manual cleanup required.", flush=True)
sys.exit(1)
