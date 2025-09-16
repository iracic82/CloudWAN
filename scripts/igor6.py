#!/usr/bin/env python3
import os
import requests

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
            "inheritance_sources": {"dhcp_options": {"action": "inherit", "value": []}},
            "dhcp_options": []
        }
        print(f"➕ Reserving next available IP in {range_id} for MAC {mac_address}")
        resp = self.session.post(url, headers=self._auth_headers(), json=payload)
        resp.raise_for_status()
        data = resp.json()["result"]
        ip = data["address"]
        print(f"✅ Fixed Address created: {ip} for {mac_address} (id={data['id']})")
        return data

    # --- Create IPAM Host (placeholder, no DNS) ---
    def create_ipam_host_no_dns(self, space_id, ip_address, fqdn=None):
        url = f"{self.base_url}/api/ddi/v1/ipam/host"
        payload = {
            "name": fqdn if fqdn else ip_address,
            "addresses": [{"address": ip_address, "space": space_id}],
            "host_names": [],
            "auto_generate_records": False,
            "comment": "API demo placeholder host"
        }
        print(f"➕ Creating IPAM Host {payload['name']} → {ip_address} (no DNS)")
        resp = self.session.post(url, headers=self._auth_headers(), json=payload)
        resp.raise_for_status()
        data = resp.json()["result"]
        print(f"✅ IPAM Host created: {data['name']} → {ip_address}")
        return data

    # --- Update IPAM Host ---
    def update_ipam_host(self, host_id, hostname=None, comment=None):
        clean_id = host_id.split("/")[-1] if host_id.startswith("ipam/host/") else host_id
        url = f"{self.base_url}/api/ddi/v1/ipam/host/{clean_id}"
        payload = {}
        if hostname:
            payload["name"] = hostname
        if comment:
            payload["comment"] = comment
        print(f"✏️ Updating IPAM Host {clean_id} → hostname={hostname}, comment={comment}")
        resp = self.session.patch(url, headers=self._auth_headers(), json=payload)
        resp.raise_for_status()
        print(f"✅ IPAM Host updated: hostname={hostname}, comment={comment}")
        return resp.json()

    # --- Update Fixed Address ---
    def update_fixed_address(self, fixed_id, org_name, hostname=None):
        clean_id = fixed_id.split("/")[-1]
        url = f"{self.base_url}/api/ddi/v1/dhcp/fixed_address/{clean_id}"
        payload = {"comment": f"Reserved for {org_name}"}
        if hostname:
            payload["hostname"] = hostname
        print(f"✏️ Updating Fixed Address {clean_id} → {org_name}, hostname={hostname}")
        resp = self.session.patch(url, headers=self._auth_headers(), json=payload)
        resp.raise_for_status()
        print(f"✅ Fixed Address updated: {org_name}, hostname={hostname}")
        return resp.json()

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

    mac = "00:1A:2B:3C:4D:DD"
    org_name = "CustomerXYZ"

    # 1) Discover ranges
    ranges = session.list_ranges()
    range_id = ranges[0]["id"]
    space_id = ranges[0]["space"]

    # 2) Reserve IP via Fixed Address
    fixed_obj = session.create_fixed_address(space_id, range_id, mac)
    ip_address = fixed_obj["address"]
    fixed_id = fixed_obj["id"]

    # 3) Create IPAM Host (placeholder)
    host = session.create_ipam_host_no_dns(space_id, ip_address, fqdn="app70-nodns")

    # 4) Update that *same* IPAM Host
    session.update_ipam_host(
        host["id"],
        hostname="app70-custxyz",
        comment=f"Allocated to {org_name}"
    )

    # 5) Update Fixed Address with same allocation
    session.update_fixed_address(fixed_id, org_name, hostname="app70-custxyz")
