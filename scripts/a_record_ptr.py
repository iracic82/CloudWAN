#!/usr/bin/env python3
import os
import json
import time
import random
import requests
import ipaddress
from datetime import datetime, timezone

class InfobloxSession:
    def __init__(self):
        self.base_url = "https://csp.infoblox.com"
        self.email = os.getenv("INFOBLOX_EMAIL")
        self.password = os.getenv("INFOBLOX_PASSWORD")
        self.jwt = None
        self.session = requests.Session()
        self.headers = {"Content-Type": "application/json"}

    # ---------------- Authentication ----------------
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

    # ---------------- DNS Views ----------------
    def fetch_dns_view_id(self, timeout=240, initial_interval=5, max_interval=20):
        """Poll until a DNS View is visible, then save its ID."""
        url = f"{self.base_url}/api/ddi/v1/dns/view"
        print(f"⏳ Waiting (up to {timeout}s) for DNS View to become accessible...")
        start = time.monotonic()
        interval = initial_interval
        attempts = 0

        while True:
            elapsed = time.monotonic() - start
            if elapsed > timeout:
                raise RuntimeError("❌ Timed out waiting for DNS View to be available")

            try:
                r = self.session.get(url, headers=self._auth_headers())
                if r.status_code == 429:
                    ra = r.headers.get("Retry-After")
                    sleep_s = int(ra) if (ra and ra.isdigit()) else min(max_interval, max(5, interval))
                    print(f"⏸️  429 Too Many Requests. Sleeping {sleep_s}s (Retry-After).")
                    time.sleep(sleep_s)
                    continue

                if r.status_code in (403, 503):
                    print(f"🚦 {r.status_code} transient ({r.reason}); retrying...")
                else:
                    r.raise_for_status()
                    data = r.json()
                    views = data.get("results", []) if isinstance(data, dict) else []
                    if views:
                        dns_view_id = views[0].get("id")
                        self._save_to_file("dns_view_id.txt", dns_view_id)
                        print(f"✅ DNS View ID saved: {dns_view_id}")
                        return dns_view_id

            except requests.RequestException as e:
                print(f"⚠️ Fetch error: {e}; continuing...")

            attempts += 1
            if attempts % 3 == 0:
                try:
                    print("🔄 Refreshing session (login + account switch)...")
                    self.login()
                    self.switch_account()
                except Exception as e:
                    print(f"⚠️ Session refresh failed: {e}")

            sleep_s = min(max_interval, interval) + random.uniform(0, 0.3 * interval)
            print(f"🕐 Still waiting... elapsed={int(elapsed)}s; next check in ~{sleep_s:.1f}s")
            time.sleep(sleep_s)
            interval = min(max_interval, max(initial_interval, interval * 1.7))

    # ---------------- Reverse Zones ----------------
    def cidr_to_reverse_zone(self, cidr: str) -> str:
        """Convert a CIDR (IPv4 only) to the correct reverse DNS zone name."""
        network = ipaddress.ip_network(cidr, strict=False)
        octets = str(network.network_address).split(".")
        prefix = network.prefixlen

        if prefix >= 24:
            rev = ".".join(reversed(octets[:3]))
        elif prefix >= 16:
            rev = ".".join(reversed(octets[:2]))
        elif prefix >= 8:
            rev = octets[0]
        else:
            raise ValueError(f"Unsupported prefix length {prefix} for reverse zone")

        return f"{rev}.in-addr.arpa."

    def _find_zone_id(self, fqdn, dns_view_id):
        """Check if a zone exists by FQDN in a given DNS view."""
        url = f"{self.base_url}/api/ddi/v1/dns/zone_child"
        params = {"_filter": f'name=="{fqdn.strip(".")}" and parent=="{dns_view_id}"'}
        resp = self.session.get(url, headers=self._auth_headers(), params=params)
        if resp.status_code == 200:
            results = resp.json().get("results", [])
            if results:
                return results[0]["id"]
        return None

    def create_reverse_zone(self, dns_view_id, cidr="10.10.10.0/24", wait_time=5, max_retries=3):
        """Ensure a reverse zone exists for a given CIDR (BloxOne API)."""
        fqdn = self.cidr_to_reverse_zone(cidr)
        url = f"{self.base_url}/api/ddi/v1/dns/auth_zone"
        payload = {
            "fqdn": fqdn,
            "view": dns_view_id,
            "primary_type": "cloud",
            "comment": f"Auto-created reverse zone for {cidr}"
        }

        print(f"➕ Creating reverse zone: {fqdn} for {cidr}")
        resp = self.session.post(url, headers=self._auth_headers(), json=payload)

        if resp.status_code in (200, 201):
            zone_id = resp.json()["result"]["id"]
            print(f"✅ Reverse zone created: {fqdn} -> {zone_id}")
        elif resp.status_code == 409:
            print(f"⚠️ Reverse zone {fqdn} already exists.")
            zone_id = self._find_zone_id(fqdn, dns_view_id)
        else:
            print(f"❌ Failed to create reverse zone. Status: {resp.status_code}")
            print(resp.text)
            resp.raise_for_status()

        # Wait for propagation
        for attempt in range(1, max_retries + 1):
            print(f"⏳ Waiting {wait_time}s for reverse zone to propagate (attempt {attempt}/{max_retries})...")
            time.sleep(wait_time)
            if self._find_zone_id(fqdn, dns_view_id):
                print(f"✅ Reverse zone {fqdn} is active.")
                return zone_id
        raise RuntimeError(f"❌ Reverse zone {fqdn} did not propagate after {max_retries * wait_time}s")

    # ---------------- Zones & Records ----------------
    def get_zones(self, dns_view_id, limit=100):
        """Fetch all child zones for a given DNS view."""
        url = f"{self.base_url}/api/ddi/v1/dns/zone_child"
        params = {
            "_filter": f'flat=="false" and parent=="{dns_view_id}"',
            "_order_by": "name asc",
            "_is_total_size_needed": "true",
            "_limit": str(limit),
            "_offset": "0",
            "_fields": ""
        }
        resp = self.session.get(url, headers=self._auth_headers(), params=params)
        resp.raise_for_status()
        data = resp.json()

        zones = {}
        for zone in data.get("results", []):
            zones[zone["name"]] = zone["id"]
            print(f"🌐 Found zone: {zone['name']} -> {zone['id']}")
        return zones

    def create_a_record(self, zone_id, hostname, ip_address, create_ptr=True, reverse_zone_id=None):
        """Create an A record (with optional PTR) in the specified zone."""
        url = f"{self.base_url}/api/ddi/v1/dns/record"
        payload = {
            "name_in_zone": hostname,
            "zone": zone_id,
            "type": "A",
            "rdata": {"address": ip_address},
            "options": {"create_ptr": create_ptr, "check_rmz": True},
            "inheritance_sources": {"ttl": {"action": "inherit"}}
        }

        print(f"➕ Creating A record {hostname} -> {ip_address} (PTR={create_ptr})")
        resp = self.session.post(url, headers=self._auth_headers(), json=payload)
        if resp.status_code in (200, 201):
            print(f"✅ Created A record {hostname} ({ip_address})")
            return resp.json()

        # Fallback: create PTR manually
        if resp.status_code == 400 and reverse_zone_id:
            print("⚠️ Auto PTR creation failed, falling back to manual PTR...")
            fqdn = f"{hostname}.infolab.com."
            self.create_ptr_record(reverse_zone_id, ip_address, fqdn)
            return None

        print(f"❌ Failed to create A record. Status: {resp.status_code}")
        print(resp.text)
        resp.raise_for_status()

    def create_ptr_record(self, reverse_zone_id, ip_address, fqdn):
        """Manually create a PTR record for an IP."""
        url = f"{self.base_url}/api/ddi/v1/dns/record"
        last_octet = ip_address.split(".")[-1]
        payload = {
            "name_in_zone": last_octet,
            "zone": reverse_zone_id,
            "type": "PTR",
            "rdata": {"dname": fqdn}
        }
        print(f"➕ Creating PTR {ip_address} -> {fqdn}")
        resp = self.session.post(url, headers=self._auth_headers(), json=payload)
        if resp.status_code in (200, 201):
            print(f"✅ PTR created for {ip_address} -> {fqdn}")
            return resp.json()
        else:
            print(f"❌ Failed to create PTR. Status: {resp.status_code}")
            print(resp.text)
            resp.raise_for_status()

    # ---------------- Utils ----------------
    def _auth_headers(self):
        return {"Content-Type": "application/json", "Authorization": f"Bearer {self.jwt}"}

    def _read_file(self, filename):
        with open(filename, "r") as f:
            return f.read().strip()

    def _save_to_file(self, filename, content):
        with open(filename, "w") as f:
            f.write(content)

# ---------------- Main ----------------
if __name__ == "__main__":
    session = InfobloxSession()
    session.login()
    session.switch_account()

    dns_view_id = session.fetch_dns_view_id()

    # Auto-create reverse zone for CIDR
    reverse_zone_id = session.create_reverse_zone(dns_view_id, cidr="10.10.10.0/24")

    # Get forward zones
    zones = session.get_zones(dns_view_id)
    forward_zone_id = zones.get("infolab.com")

    # Add A record + PTR
    if forward_zone_id:
        session.create_a_record(zone_id=forward_zone_id,
                                hostname="app10",
                                ip_address="10.10.10.10",
                                create_ptr=True,
                                reverse_zone_id=reverse_zone_id)
