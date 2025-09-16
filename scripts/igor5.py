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
        resp.raise_for_status()
        data = resp.json()["result"]
        print(f"✅ Fixed Address created: {data['address']} for {mac_address}")
        return data["address"]
    def query_next_available_ip(self, range_id, count=1):
        """Query next available IP(s) in a given range without allocating."""
        # strip any accidental 'ipam/range/' prefix from id
        clean_id = range_id.split("/")[-1]
        url = f"{self.base_url}/api/ddi/v1/ipam/range/{clean_id}/nextavailableip"
        params = {"count": str(count)}
        print(f"🔍 Querying next {count} available IP(s) in {range_id}")
        resp = self.session.get(url, headers=self._auth_headers(), params=params)
        resp.raise_for_status()
        data = resp.json().get("results", [])
        for ip in data:
            print(f"✨ Next available: {ip['address']}")
        return [ip["address"] for ip in data]
    # --- DNS Zone lookup ---
    def get_zone_id(self, zone_fqdn="infolab.com."):
        url = f"{self.base_url}/api/ddi/v1/dns/auth_zone"
        resp = self.session.get(url, headers=self._auth_headers())
        resp.raise_for_status()
        zones = resp.json().get("results", [])
        for z in zones:
            if z["fqdn"] == zone_fqdn:
                print(f"🌐 Found zone {zone_fqdn} → {z['id']}")
                return z["id"]
        raise RuntimeError(f"❌ Zone {zone_fqdn} not found!")

    # --- IPAM Host ---
    def create_ipam_host(self, space_id, ip_address, fqdn, zone_id):
        url = f"{self.base_url}/api/ddi/v1/ipam/host"
        payload = {
            "name": fqdn,
            "addresses": [
                {
                    "address": ip_address,
                    "space": space_id
                }
            ],
            "host_names": [
                {
                    "name": fqdn,
                    "zone": zone_id,
                    "primary_name": True
                }
            ],
            "auto_generate_records": True,
            "comment": "Created via API demo"
        }
        print(f"➕ Creating IPAM Host {fqdn} → {ip_address} in zone {zone_id}")
        resp = self.session.post(url, headers=self._auth_headers(), json=payload)
        resp.raise_for_status()
        data = resp.json()["result"]
        print(f"✅ IPAM Host created: {data['name']} → {ip_address}")
        return data

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

    mac = "00:1A:2B:3C:4D:BB"
    fqdn = "app50.infolab.com"

    # 1) Discover ranges
    ranges = session.list_ranges()
    if not ranges:
        print("❌ No ranges found.")
        exit(1)
    range_id = ranges[0]["id"]
    space_id = ranges[0]["space"]

    # 2) Query next available IP
    next_ips = session.query_next_available_ip(range_id, count=1)
    print(f"👉 Queried (not reserved yet): {next_ips}")

    # 2) Create Fixed Address
    ip_address = session.create_fixed_address(space_id, range_id, mac)

    # 3) Lookup zone ID
    zone_id = session.get_zone_id("infolab.com.")

    # 4) Create IPAM Host
    session.create_ipam_host(space_id, ip_address, fqdn, zone_id)
