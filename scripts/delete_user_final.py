import os, sys, time, random, requests

BASE_URL = "https://csp.infoblox.com"
EMAIL = os.getenv("INFOBLOX_EMAIL")
PASSWORD = os.getenv("INFOBLOX_PASSWORD")
SANDBOX_ID_FILE = "sandbox_id.txt"
USER_ID_FILE = "user_id.txt"

# --- Read IDs ---
try:
    sandbox_id = open(SANDBOX_ID_FILE).read().strip()
    user_id = open(USER_ID_FILE).read().strip()
except FileNotFoundError:
    sys.exit("❌ sandbox_id.txt or user_id.txt not found. Run create scripts first.")

if not sandbox_id or not user_id:
    sys.exit("❌ Missing sandbox_id or user_id in file(s).")

# --- Step 1: Login ---
auth_url = f"{BASE_URL}/v2/session/users/sign_in"
auth_resp = requests.post(auth_url, json={"email": EMAIL, "password": PASSWORD})
auth_resp.raise_for_status()
jwt = auth_resp.json()["jwt"]
headers = {"Authorization": f"Bearer {jwt}", "Content-Type": "application/json"}
print("✅ Authenticated.", flush=True)

# --- Step 2: Switch account ---
switch_url = f"{BASE_URL}/v2/session/account_switch"
switch_resp = requests.post(switch_url, headers=headers, json={"id": f"identity/accounts/{sandbox_id}"})
switch_resp.raise_for_status()
jwt = switch_resp.json()["jwt"]
headers["Authorization"] = f"Bearer {jwt}"
print(f"🔁 Switched to sandbox account {sandbox_id}", flush=True)

# --- Step 3: Delete user with retries ---
endpoint = f"{BASE_URL}/v2/users/{user_id}"
max_retries = 5

for attempt in range(max_retries):
    try:
        print(f"🔗 DELETE {endpoint} (attempt {attempt+1})", flush=True)
        resp = requests.delete(endpoint, headers=headers)

        if resp.status_code == 204:
            print(f"✅ User {user_id} deleted.", flush=True)
            os.remove(USER_ID_FILE)
            print(f"📁 Removed {USER_ID_FILE}", flush=True)
            sys.exit(0)
        else:
            print(f"⚠️ Status {resp.status_code}: {resp.text}", flush=True)
    except Exception as e:
        print(f"⚠️ Error: {e}", flush=True)
    time.sleep((2**attempt) + random.random())

sys.exit("❌ User deletion failed after retries")
