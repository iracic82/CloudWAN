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

    # ---------------- Auth ----------------
    def login(self):
        payload = {"email": self.email, "password": self.password}
        resp = self.session.post(f"{self.base_url}/v2/session/users/sign_in",
                                 headers={"Content-Type": "application/json"}, json=payload)
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

    # ---------------- IPAM Range ----------------
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
        ip = data["address"]
        print(f"✅ Fixed Address created: {ip} for {mac_address}")
        return ip

    # ---------------- DNS Zones ----------------
    def get_zone_id(self, fqdn):
        url = f"{self.base_url}/api/ddi/v1/dns/auth_zone"
        resp = self.session.get(url, headers=self._auth_headers())
        resp.raise_for_status()
        for z in resp.json().get("results", []):
            if z["fqdn"].rstrip(".") == fqdn.rstrip("."):
                print(f"🌐 Found zone {z['fqdn']} → {z['id']}")
                return z["id"]
        raise RuntimeError(f"❌ Zone {fqdn} not found!")

    # ---------------- IPAM Hosts ----------------
    def create_ipam_host_with_dns(self, space_id, ip_address, fqdn, zone_id, tags=None):
        url = f"{self.base_url}/api/ddi/v1/ipam/host"
        payload = {
            "name": fqdn,
            "addresses": [{"address": ip_address, "space": space_id}],
            "host_names": [{"name": fqdn, "zone": zone_id, "primary_name": True}],
            "auto_generate_records": True,
            "comment": "API demo with DNS"
        }
        if tags:
            payload["tags"] = tags
        print(f"➕ Creating IPAM Host {fqdn} → {ip_address} (with DNS, tags={tags})")
        resp = self.session.post(url, headers=self._auth_headers(), json=payload)
        resp.raise_for_status()
        data = resp.json()["result"]
        print(f"✅ IPAM Host created: {data['name']} → {ip_address}")
        return data

    def create_ipam_host_no_dns(self, space_id, ip_address, fqdn=None, tags=None):
        url = f"{self.base_url}/api/ddi/v1/ipam/host"
        payload = {
            "name": fqdn if fqdn else ip_address,
            "addresses": [{"address": ip_address, "space": space_id}],
            "host_names": [],
            "auto_generate_records": False,
            "comment": "API demo without DNS"
        }
        if tags:
            payload["tags"] = tags
        print(f"➕ Creating IPAM Host {payload['name']} → {ip_address} (no DNS, tags={tags})")
        resp = self.session.post(url, headers=self._auth_headers(), json=payload)
        resp.raise_for_status()
        data = resp.json()["result"]
        print(f"✅ IPAM Host created: {data['name']} → {ip_address}")
        return data

    def list_ipam_hosts(self, limit=20):
        url = f"{self.base_url}/api/ddi/v1/ipam/host"
        params = {"_limit": str(limit)}
        print("📥 Fetching IPAM Host objects...")
        resp = self.session.get(url, headers=self._auth_headers(), params=params)
        resp.raise_for_status()
        data = resp.json()
        for h in data.get("results", []):
            addrs = [a["address"] for a in h.get("addresses", [])]
            print(f"🖥️ Host {h['name']} → {', '.join(addrs)} | tags={h.get('tags',{})}")
        return data.get("results", [])

    def search_hosts_by_tag(self, key, value, limit=20):
        url = f"{self.base_url}/api/ddi/v1/ipam/host"
        params = {"_filter": f'tags.{key}=="{value}"', "_limit": str(limit)}
        print(f"🔎 Searching hosts with tag {key}={value}...")
        resp = self.session.get(url, headers=self._auth_headers(), params=params)
        resp.raise_for_status()
        results = resp.json().get("results", [])
        for h in results:
            addrs = [a["address"] for a in h.get("addresses", [])]
            print(f"🖥️ Host {h['name']} → {', '.join(addrs)} | tags={h.get('tags',{})}")
        return results

    # ---------------- Helpers ----------------
    def _auth_headers(self):
        return {"Content-Type": "application/json", "Authorization": f"Bearer {self.jwt}"}

    def _read_file(self, filename):
        with open(filename, "r") as f:
            return f.read().strip()


if __name__ == "__main__":
    session = InfobloxSession()
    session.login()
    session.switch_account()

    # Step 1: Discover ranges
    ranges = session.list_ranges()
    range_id = ranges[0]["id"]
    space_id = ranges[0]["space"]

    # Step 2: Reserve IPs
    ip1 = session.create_fixed_address(space_id, range_id, "00:1A:2B:3C:4D:01")
    ip2 = session.create_fixed_address(space_id, range_id, "00:1A:2B:3C:4D:02")
    ip3 = session.create_fixed_address(space_id, range_id, "00:1A:2B:3C:4D:03")

    # Step 3: Zone lookup
    zone_id = session.get_zone_id("infolab.com")

    # Step 4: Create hosts
    session.create_ipam_host_with_dns(space_id, ip1, "prod-app1.infolab.com", zone_id,
                                      tags={"Environment": "Production", "Owner": "Igor"})
    session.create_ipam_host_with_dns(space_id, ip2, "dev-app1.infolab.com", zone_id,
                                      tags={"Environment": "Development", "Owner": "TeamA"})
    session.create_ipam_host_no_dns(space_id, ip3, fqdn="lab-app1",
                                    tags={"Environment": "Lab", "Owner": "TeamB"})

    # Step 5: List all hosts
    session.list_ipam_hosts()

    # Step 6: Show only Production-tagged hosts
    session.search_hosts_by_tag("Environment", "Production")
