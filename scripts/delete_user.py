import os
import requests

BASE_URL = "https://csp.infoblox.com/v2"
TOKEN = os.environ.get("Infoblox_Token")
USER_ID_FILE = "user_id.txt"

if not TOKEN:
    print("❌ Missing Infoblox_Token in environment.")
    exit(1)

# Read user ID
try:
    with open(USER_ID_FILE, "r") as f:
        user_id = f.read().strip()
except FileNotFoundError:
    print(f"❌ File {USER_ID_FILE} not found. Run create_user.py first.")
    exit(1)

if not user_id:
    print("⚠️ User ID file is empty.")
    exit(1)

# Construct DELETE call
endpoint = f"{BASE_URL}/users/{user_id}"
headers = {
    "Authorization": f"token {TOKEN}",
    "Accept": "application/json"
}

try:
    print(f"🔗 Sending DELETE to {endpoint}")
    response = requests.delete(endpoint, headers=headers)

    if response.status_code == 204:
        print(f"🗑️ User {user_id} deleted successfully.")
        os.remove(USER_ID_FILE)
    else:
        print(f"❌ Failed to delete user {user_id}. Status: {response.status_code}")
        print(f"Response: {response.text}")

except Exception as e:
    print(f"❌ Error: {e}")
