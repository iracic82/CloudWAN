#!/usr/bin/env python3
import os
import requests
import json

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
        resp = self.session.post(f"{self.base_url}/v2/session/users/sign_in",
                                 headers=self.headers, json=payload)
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

    # --- IPAM Range discovery ---
    def list_ranges(self, space_id=None, limit=20):
        url = f"{self.base_url}/api/ddi/v1/ipam/range"
        params = {"_limit": str(limit)}
        if space_id:
            params["_filter"] = f'space=="{space_id}"'
        resp = self.session.get(url, headers=self._auth_headers(), params=params)
        resp.raise_for_status()
        data = resp.json()
        for r in data.get("results", []):
            print(f"📦 Range {r['id']} in {r['space']}: {r['start']} - {r['end']}")
        return data.get("results", [])

    # --- DHCP Fixed Address ---
    def create_fixed_address(self, space_id, range_id, mac_address):
        url = f"{self.base_url}/api/ddi/v1/dhcp/fixed_address"
        payload = {
            "ip_space": space_id,
            "address": f"{range_id}/nextavailableip",
            "match_type": "mac",
            "match_value": mac_address,
            "inheritance_sources": {
                "dhcp_options": {"action": "inherit", "value": []},
                "header_option_server_address": {"action": "inherit"},
                "header_option_server_name": {"action": "inherit"},
                "header_option_filename": {"action": "inherit"}
            },
            "dhcp_options": []
        }
        print(f"➕ Reserving next available IP in {range_id} for MAC {mac_address}")
        resp = self.session.post(url, headers=self._auth_headers(), json=payload)
        if resp.status_code in (200, 201):
            data = resp.json()
            print(f"✅ Fixed Address created: {data['result']['address']}")
            return data
        else:
            print(f"❌ Failed. Status {resp.status_code}")
            print(resp.text)
            resp.raise_for_status()

    # --- DHCP leases ---
    def list_leases(self, limit=20):
        url = f"{self.base_url}/api/ddi/v1/dhcp/lease"
        params = {"_limit": str(limit)}
        resp = self.session.get(url, headers=self._auth_headers(), params=params)
        resp.raise_for_status()
        data = resp.json()
        for lease in data.get("results", []):
            print(f"🔑 Lease {lease.get('address')} → MAC {lease.get('hwaddr')} state={lease.get('state')}")
        return data.get("results", [])

    # --- DHCP services ---
    def list_services(self):
        url = f"{self.base_url}/api/ddi/v1/dhcp/service"
        resp = self.session.get(url, headers=self._auth_headers())
        resp.raise_for_status()
        data = resp.json()
        print(f"🛠️ DHCP Services: {json.dumps(data, indent=2)}")
        return data.get("results", [])

    # --- helpers ---
    def _auth_headers(self):
        return {"Content-Type": "application/json", "Authorization": f"Bearer {self.jwt}"}

    def _read_file(self, filename):
        with open(filename, "r") as f:
            return f.read().strip()


if __name__ == "__main__":
    session = InfobloxSession()
    session.login()
    session.switch_account()

    mac = "00:1A:2B:3C:4D:EE"

    # 1) Discover ranges
    ranges = session.list_ranges()
    if not ranges:
        print("❌ No ranges found.")
        exit(1)
    range_id = ranges[0]["id"]
    space_id = ranges[0]["space"]

    # 2) Create Fixed Address
    session.create_fixed_address(space_id, range_id, mac)

    # 3) Show active leases
    session.list_leases()

    # 4) Show DHCP services
    session.list_services()
