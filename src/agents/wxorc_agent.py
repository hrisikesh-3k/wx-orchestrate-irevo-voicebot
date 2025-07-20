"""
step 1:
pip install -r requirements.txt:
requests>=2.31.0
python-dotenv>=1.0.0
colorama>=0.4.6
pyyaml>=6.0

step 2:
orchestrate env add -n my-orc-env -u https://api.au-syd.watson-orchestrate.cloud.ibm.com/instances/5b80a5df-041c-4fa9-af19-67a6256731e7

step 3:
python rag_agent.py
"""
#!/usr/bin/env python3
"""
Standalone IBM watsonx Orchestrate client with auto‑refreshing token,
fast polling, and a simple ask(question) → answer API.
"""

import os
import subprocess, yaml, base64, json, time, requests
from datetime import datetime, timezone
from typing import Dict
from dotenv import load_dotenv

load_dotenv()

IBM_CLOUD_API_KEY       = os.getenv("IBM_CLOUD_API_KEY")
ORCHESTRATE_ENV_NAME    = os.getenv("ORCHESTRATE_ENV_NAME")
ORCHESTRATE_URL         = os.getenv("ORCHESTRATE_URL")
ORCHESTRATE_INSTANCE_ID = os.getenv("ORCHESTRATE_INSTANCE_ID")
AGENT_ID     = os.getenv("ORCHESTRATE_AGENT_ID")

# ============ CONFIGURE THESE FIVE VALUES =============
# IBM_CLOUD_API_KEY       = "zcLmFY4A2IVjSpbFunAfmTHDrQo3Fv3j7WfW4CuO76Sc"
# ORCHESTRATE_ENV_NAME    = "my-orc-env"
# ORCHESTRATE_URL         = "https://api.au-syd.watson-orchestrate.cloud.ibm.com"
# ORCHESTRATE_INSTANCE_ID = "5b80a5df-041c-4fa9-af19-67a6256731e7"
# AGENT_ID                = "42bbee0d-4b58-41bc-9ec9-9efdb15eeee0"
# ======================================================

class OrchestrateClient:
    def __init__(self):
        # Validate required config
        for val,name in [
            (IBM_CLOUD_API_KEY,       "IBM_CLOUD_API_KEY"),
            (ORCHESTRATE_ENV_NAME,    "ORCHESTRATE_ENV_NAME"),
            (ORCHESTRATE_URL,         "ORCHESTRATE_URL"),
            (ORCHESTRATE_INSTANCE_ID, "ORCHESTRATE_INSTANCE_ID"),
            (AGENT_ID,                "AGENT_ID"),
        ]:
            if not val:
                raise ValueError(f"Missing required config: {name}")

        self.ibm_api_key = IBM_CLOUD_API_KEY
        self.env_name    = ORCHESTRATE_ENV_NAME
        self.base_url    = ORCHESTRATE_URL.rstrip("/")
        self.instance_id = ORCHESTRATE_INSTANCE_ID
        self.agent_id    = AGENT_ID

        self._session   = requests.Session()
        self._thread_id = None
        self._token     = None
        self._expiry    = 0
        self._runs_url  = f"{self.base_url}/instances/{self.instance_id}/v1/orchestrate/runs"

        # Fetch first token
        self._ensure_token()

    def _activate_env(self):
        """Refresh the WXO_MCSP_TOKEN via CLI."""
        proc = subprocess.run([
            "orchestrate","env","activate", self.env_name,
            "--api-key", self.ibm_api_key
        ], capture_output=True, text=True)
        if proc.returncode != 0:
            raise RuntimeError(f"Env activate failed:\n{proc.stderr.strip()}")

    def _read_token_cache(self):
        """Read token & expiry from ~/.cache/orchestrate/credentials.yaml."""
        path = subprocess.os.path.expanduser("~/.cache/orchestrate/credentials.yaml")
        data = yaml.safe_load(open(path))
        blk  = data.get("auth", {}).get(self.env_name, {})
        tok  = blk.get("wxo_mcsp_token")
        exp  = blk.get("wxo_mcsp_token_expiry", 0)
        if not tok or not exp:
            raise RuntimeError("Token cache missing fields")
        return tok, exp

    def _is_expired(self, tok: str) -> bool:
        """Return True if JWT exp is past (30s slack)."""
        try:
            seg    = tok.split(".")[1]
            padded = seg + "=" * (-len(seg) % 4)
            pl     = json.loads(base64.b64decode(padded))
            exp_ts = int(pl.get("exp", 0))
            return datetime.now(timezone.utc).timestamp() >= exp_ts - 30
        except:
            return True

    def _ensure_token(self):
        """Refresh in‑memory token if missing or expired."""
        if not self._token or self._is_expired(self._token):
            self._activate_env()
            tok, exp = self._read_token_cache()
            self._token, self._expiry = tok, exp

    def _headers(self) -> Dict[str,str]:
        """Build auth headers (reuse thread if set)."""
        self._ensure_token()
        h = {
            "Authorization": f"Bearer {self._token}",
            "Content-Type":  "application/json",
            "Accept":        "application/json",
        }
        if self._thread_id:
            h["X-IBM-THREAD-ID"] = self._thread_id
        return h

    def ask(self, question: str, timeout: int = 120) -> str:
        """
        Ask your agent a question and return its text reply.
        """
        # 1) POST /runs
        payload = {
            "agent_id": self.agent_id,
            "message": {
                "role": "user",
                "content": [{"response_type":"text","text":question}]
            }
        }
        if self._thread_id:
            payload["thread_id"] = self._thread_id

        res = self._session.post(self._runs_url,
                                  json=payload,
                                  headers=self._headers(),
                                  timeout=timeout)
        res.raise_for_status()
        info           = res.json()
        run_id         = info["run_id"]
        self._thread_id = info.get("thread_id")

        # 2) Fast‑poll /events
        ev_url    = f"{self._runs_url}/{run_id}/events"
        start, dl = time.time(), 0.1
        while time.time() - start < timeout:
            evs = self._session.get(ev_url, headers=self._headers()).json()
            # look for the assistant message
            for e in reversed(evs):
                if e.get("event") == "message.created":
                    cnt = e["data"]["message"].get("content", [])
                    if isinstance(cnt, list):
                        return " ".join(p.get("text","") for p in cnt).strip()
                    if isinstance(cnt, str):
                        return cnt
            time.sleep(dl)
            dl = min(dl * 1.2, 0.5)

        raise TimeoutError(f"No reply after {timeout}s")

# === USAGE EXAMPLE ===
# from orchestrate_client import OrchestrateClient
# client = OrchestrateClient()
# answer = client.ask("Your question here")
# print(answer)

