#!/usr/bin/env python3

import os
import json
import requests
from datetime import datetime, timezone

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
        resp = self.session.post(f"{self.base_url}/v2/session/users/sign_in", headers=self.headers, json=payload)
        resp.raise_for_status()
        self.jwt = resp.json()["jwt"]
        print("✅ Logged in.")

    def switch_account(self):
        sandbox_id = self._read_file("sandbox_id.txt")
        payload = {"id": f"identity/accounts/{sandbox_id}"}
        resp = self.session.post(f"{self.base_url}/v2/session/account_switch",
                                 headers=self._auth_headers(), json=payload)
        resp.raise_for_status()
        self.jwt = resp.json()["jwt"]
        print(f"✅ Switched account to sandbox ID: {sandbox_id}")

    def get_pools(self):
        url = f"{self.base_url}/api/infra/v1/detail_hosts"
        resp = self.session.get(url, headers=self._auth_headers())
        resp.raise_for_status()
        data = resp.json()

        pools = []
        for idx, host in enumerate(data["results"], start=1):
            pool_id = host["pool"]["pool_id"]
            pools.append(pool_id)
            print(f"📥 Found pool_id: {pool_id} (will map to DNS-{idx})")
        return pools

    def enable_dns_service(self, pool_id, dns_name):
        url = f"{self.base_url}/api/infra/v1/services"
        headers = self._auth_headers()
        now = datetime.now(timezone.utc).isoformat()

        payload = {
            "name": dns_name,
            "service_type": "dns",
            "pool_id": f"infra/pool/{pool_id}",
            "desired_state": "start",
            "created_at": now,
            "updated_at": now,
            "tags": {}
        }

        print(f"🚀 Enabling DNS service '{dns_name}' on pool {pool_id}")
        resp = self.session.post(url, headers=headers, json=payload)
        if resp.status_code == 201:
            print(f"✅ DNS service '{dns_name}' enabled on pool {pool_id}")
        elif resp.status_code == 409:
            print(f"⚠️ DNS service '{dns_name}' already exists on pool {pool_id}")
        else:
            print(f"❌ Failed to enable DNS on {pool_id}. Status: {resp.status_code}")
            print(resp.text)
            resp.raise_for_status()

    def _auth_headers(self):
        return {"Content-Type": "application/json", "Authorization": f"Bearer {self.jwt}"}

    def _read_file(self, filename):
        with open(filename, "r") as f:
            return f.read().strip()

if __name__ == "__main__":
    session = InfobloxSession()
    session.login()
    session.switch_account()
    pools = session.get_pools()

    # Assign names DNS-1, DNS-2, ...
    for idx, pool_id in enumerate(pools, start=1):
        dns_name = f"DNS-{idx}"
        session.enable_dns_service(pool_id=pool_id, dns_name=dns_name)
