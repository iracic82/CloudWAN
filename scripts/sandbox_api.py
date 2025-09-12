import json
import requests
import logging
from logging.handlers import RotatingFileHandler

# Setup logging
logger = logging.getLogger('SandboxAccountLogger')
logger.setLevel(logging.DEBUG)
handler = RotatingFileHandler('SandboxAccount.log', maxBytes=5_000_000, backupCount=2)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)


class SandboxAccountAPI:
    """
    Interacts with the /sandbox/accounts endpoint to manage sandbox accounts.
    """

    def __init__(self, base_url: str, token: str):
        self.base_url = base_url.rstrip("/")
        self.token = token

    def _headers(self):
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        if self.token:
            headers["Authorization"] = f"token {self.token}"
        return headers

    def create_sandbox_account(self, sandbox_account_request: dict) -> dict:
        endpoint = f"{self.base_url}/sandbox/accounts"
        try:
            logger.debug(f"Creating sandbox at {endpoint} with payload: {sandbox_account_request}")
            response = requests.post(url=endpoint, headers=self._headers(), data=json.dumps(sandbox_account_request))
            response.raise_for_status()
            result = response.json()
            logger.info(f"Sandbox created: {json.dumps(result, indent=2)}")
            return {"status": "success", "data": result}
        except Exception as e:
            logger.error(f"Failed to create sandbox: {e}")
            return {"status": "failure", "error": str(e)}

    def get_sandbox_account_id_by_name(self, name: str) -> str:
        endpoint = f"{self.base_url}/sandbox/accounts"
        params = {"_filter": f'name=="{name}"'}
        try:
            logger.debug(f"Querying sandbox ID with filter: {params}")
            response = requests.get(endpoint, headers=self._headers(), params=params)
            response.raise_for_status()
            result = response.json()
            if result.get("results"):
                sandbox_id = result["results"][0]["id"]
                logger.info(f"Found sandbox ID: {sandbox_id} for name: {name}")
                return sandbox_id
            else:
                logger.warning(f"No sandbox found with name: {name}")
                return None
        except Exception as e:
            logger.error(f"Error fetching sandbox ID: {e}")
            return None

    def delete_sandbox_account(self, sandbox_id: str) -> bool:
        endpoint = f"{self.base_url}/sandbox/accounts/{sandbox_id}"
        try:
            logger.debug(f"Deleting sandbox ID: {sandbox_id} at {endpoint}")
            response = requests.delete(endpoint, headers=self._headers())
            if response.status_code == 204:
                logger.info(f"Sandbox ID {sandbox_id} deleted successfully.")
                return True
            else:
                logger.error(f"Failed to delete sandbox. Status code: {response.status_code}, Response: {response.text}")
                return False
        except Exception as e:
            logger.error(f"Error deleting sandbox: {e}")
            return False
