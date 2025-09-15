import os
import json
import requests
import time

class InfobloxSession:
    def __init__(self):
        self.base_url = "https://csp.infoblox.com"
        self.email = os.getenv("INFOBLOX_EMAIL")
        self.password = os.getenv("INFOBLOX_PASSWORD")
        self.jwt = None
        self.session = requests.Session()
        self.headers = {"Content-Type": "application/json"}

    def login(self):
        payload = {"email": self.email, "password": self.password}
        response = self.session.post(f"{self.base_url}/v2/session/users/sign_in", 
                                     headers=self.headers, json=payload)
        response.raise_for_status()
        self.jwt = response.json().get("jwt")
        print("✅ Logged in and JWT acquired")

    def switch_account(self):
        sandbox_id = self._read_file("sandbox_id.txt")
        payload = {"id": f"identity/accounts/{sandbox_id}"}
        headers = self._auth_headers()
        response = self.session.post(f"{self.base_url}/v2/session/account_switch", 
                                     headers=headers, json=payload)
        response.raise_for_status()
        self.jwt = response.json().get("jwt")
        self._save_to_file("jwt.txt", self.jwt)
        print(f"✅ Switched to sandbox {sandbox_id} and updated JWT")

    def create_api_key_and_export_env(self, key_name="Instruqt", expiration="2025-12-10T18:44:50.121Z"):
        url = f"{self.base_url}/v2/current_api_keys"
        headers = self._auth_headers()
        payload = {
            "name": key_name,
            "expires_at": expiration
        }

        print(f"📤 Requesting API key '{key_name}' with expiration {expiration}")
        response = self.session.post(url, headers=headers, json=payload)
        response.raise_for_status()

        result = response.json().get("result", {})
        api_key = result.get("key")

        if not api_key:
            raise RuntimeError("❌ Failed to extract API key from response.")

        # Save API key to ~/.bashrc
        bashrc_path = os.path.expanduser("~/.bashrc")
        export_line = f'export TF_VAR_ddi_api_key="{api_key}"\n'

        with open(bashrc_path, "r") as f:
            lines = f.readlines()

        if export_line not in lines:
            with open(bashrc_path, "a") as f:
                f.write(f"\n# Exported by InfobloxSession on {time.ctime()}\n")
                f.write(export_line)

        os.system(f"source {bashrc_path}")
        print("🔐 API Key stored as TF_VAR_ddi_api_key and .bashrc reloaded.")

    def _auth_headers(self):
        return {"Content-Type": "application/json", "Authorization": f"Bearer {self.jwt}"}
    def _save_to_file(self, filename, content):
        with open(filename, "w") as f:
            f.write(content.strip())

    def _read_file(self, filename):
        with open(filename, "r") as f:
            return f.read().strip()
    

if __name__ == "__main__":
    session = InfobloxSession()
    session.login()
    session.switch_account()
    session.create_api_key_and_export_env()
