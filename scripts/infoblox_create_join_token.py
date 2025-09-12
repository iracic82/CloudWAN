#!/usr/bin/env python3

import os
import json
import requests
import time
import subprocess
from pathlib import Path

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

    def create_join_token_and_export(self, token_name="demo-token2"):
        url = f"{self.base_url}/atlas-host-activation/v1/jointoken"
        headers = self._auth_headers()
        payload = {"name": token_name}

        print(f"📤 Creating join token: {token_name}")
        response = self.session.post(url, headers=headers, json=payload)
        response.raise_for_status()

        join_token = response.json().get("join_token")
        if not join_token:
            raise RuntimeError("❌ Failed to extract join token from response.")

        print(f"✅ Join token created: {join_token}")

        # Save to file
        self._save_to_file("join_token.txt", join_token)

        # Export to env for current shell
        os.environ["INFOBLOX_JOIN_TOKEN"] = join_token
        os.environ["TF_VAR_infoblox_join_token"] = join_token
        print("🌍 Exported to current session")

        # Append to ~/.bashrc for persistence
        bashrc_path = Path.home() / ".bashrc"
        export_lines = [
            f'export INFOBLOX_JOIN_TOKEN="{join_token}"\n',
            f'export TF_VAR_infoblox_join_token="{join_token}"\n'
        ]

        with open(bashrc_path, "r") as f:
            lines = f.readlines()

        with open(bashrc_path, "a") as f:
            f.write(f"\n# Exported by InfobloxSession on {time.ctime()}\n")
            for line in export_lines:
                if line not in lines:
                    f.write(line)
        print(f"💾 Appended to {bashrc_path}")

        # Reload the file (non-blocking)
        subprocess.run(["bash", "-c", f"source {bashrc_path}"], check=False)
        print("🔁 Reloaded .bashrc to persist token")

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
    session.create_join_token_and_export()
