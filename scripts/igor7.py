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

    # --- Auth ---
    def login(self):
        payload = {"email": self.email, "password": self.password}
        resp = self.session.post(
            f"{self.base_url}/v2/session/users/sign_in",
            headers={"Content-Type": "application/json"},
            json=payload
        )
        resp.raise_for_status()
        self.jwt = resp.json()["jwt"]
        print("✅ Logged in.")

    def switch_account(self):
        sandbox_id = self._read_file("sandbox_id.txt")
        payload = {"id": f"identity/accounts/{sandbox_id}"}
        resp = self.session.post(
            f"{self.base_url}/v2/session/account_switch",
            headers=self._auth_headers(),
            json=payload
        )
        resp.raise_for_status()
        self.jwt = resp.json()["jwt"]
        print(f"✅ Switched account to sandbox ID: {sandbox_id}")

    # --- List Address Blocks ---
    def list_blocks(self, limit=20):
        url = f"{self.base_url}/api/ddi/v1/ipam/address_block"
        resp = self.session.get(url, headers=self._auth_headers(), params={"_limit": str(limit)})
        resp.raise_for_status()
        data = resp.json()
        for b in data.get("results", []):
            print(f"📦 Block {b['address']}/{b['cidr']} (id={b['id']})")
        return data.get("results", [])

    # --- Find specific block ---
    def find_block(self, cidr_block):
        blocks = self.list_blocks(limit=50)
        for b in blocks:
            prefix = f"{b['address']}/{b['cidr']}"
            if prefix == cidr_block:
                print(f"✅ Found block {prefix} → {b['id']}")
                return b["id"]
        raise RuntimeError(f"❌ Block {cidr_block} not found")

    # --- Allocate next available subnet ---
        # --- Allocate next available subnet ---
        # --- Allocate next available subnet ---
        # --- Allocate next available subnet ---
    def allocate_next_subnet(self, block_id, cidr, comment=None, count=1):
        clean_id = block_id.split("/")[-1] if block_id.startswith("ipam/address_block/") else block_id
        url = f"{self.base_url}/api/ddi/v1/ipam/address_block/{clean_id}/nextavailablesubnet"

        # Important: use query params, not JSON payload
        params = {
            "cidr": cidr,
            "count": count
        }

        print(f"➕ Allocating {count} next available /{cidr} subnet(s) in block {clean_id}")
        resp = self.session.post(url, headers=self._auth_headers(), params=params)
        resp.raise_for_status()

        results = resp.json().get("results", [])
        for r in results:
            print(f"✅ Subnet allocated: {r['address']}/{r['cidr']} (id={r['id']}) → {r.get('comment','')}")
        return results

    # --- List all subnets inside a block ---
    def list_subnets(self, block_id, limit=20):
        clean_id = block_id.split("/")[-1] if block_id.startswith("ipam/address_block/") else block_id
        url = f"{self.base_url}/api/ddi/v1/ipam/subnet"
        params = {"_limit": str(limit), "_filter": f'parent=="ipam/address_block/{clean_id}"'}
        print(f"📥 Fetching subnets under block {clean_id}...")
        resp = self.session.get(url, headers=self._auth_headers(), params=params)
        resp.raise_for_status()
        data = resp.json()
        for s in data.get("results", []):
            print(f"🌐 Subnet {s['address']}/{s['cidr']} (id={s['id']}) → {s.get('comment','')}")
        return data.get("results", [])

    # --- Helpers ---
    def _auth_headers(self):
        return {"Content-Type": "application/json", "Authorization": f"Bearer {self.jwt}"}

    def _read_file(self, filename):
        with open(filename, "r") as f:
            return f.read().strip()


if __name__ == "__main__":
    session = InfobloxSession()
    session.login()
    session.switch_account()

    # 1. Find your 10.20.0.0/16 block
    block_id = session.find_block("10.20.0.0/16")

    # 2. Allocate next available /24 subnet
    session.allocate_next_subnet(block_id, 24, comment="Demo subnet for CustomerXYZ")

    # 3. Show all subnets under the block
    session.list_subnets(block_id)
