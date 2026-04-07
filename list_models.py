import json
import sys
import urllib.request


def load_env(path=".env"):
    env = {}
    try:
        with open(path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    env[k.strip()] = v.strip().strip('"').strip("'")
    except FileNotFoundError:
        print(f"Warning: {path} not found, falling back to empty env")
    return env


env = load_env()
litellm_url = env.get("LITELLM_BASE_URL", "").strip()
litellm_key = env.get("LITELLM_MASTER_KEY", "").strip()
nim_key = env.get("NVIDIA_NIM_API_KEY", "").strip()

# List LiteLLM models
if not litellm_url or not litellm_key:
    print("=== LiteLLM Models ===")
    print("(skipped: set LITELLM_BASE_URL and LITELLM_MASTER_KEY in .env)")
else:
    req = urllib.request.Request(
        f"{litellm_url.rstrip('/')}/v1/models",
        headers={"Authorization": f"Bearer {litellm_key}"},
    )
    try:
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read())
            print("=== LiteLLM Models ===")
            for model in data["data"]:
                print(model["id"])
    except Exception as e:
        print(f"=== LiteLLM Models ===\n(error: {e})", file=sys.stderr)

# List ALL NVIDIA NIM models
print("\n=== NVIDIA NIM Models ===")
if not nim_key:
    print("(skipped: set NVIDIA_NIM_API_KEY in .env)")
else:
    req2 = urllib.request.Request(
        "https://integrate.api.nvidia.com/v1/models",
        headers={"Authorization": f"Bearer {nim_key}"},
    )
    try:
        with urllib.request.urlopen(req2) as resp:
            data = json.loads(resp.read())
            for model in sorted(data["data"], key=lambda m: m["id"]):
                print(model["id"])
    except Exception as e:
        print(f"(error: {e})", file=sys.stderr)

# List OpenCode.ai models
print("\n=== OpenCode.ai Models ===")
req3 = urllib.request.Request(
    "https://opencode.ai/zen/v1/models",
    headers={
        "Authorization": "Bearer public",
        "x-opencode-session": "litellm-bridge",
        "User-Agent": "Mozilla/5.0",
    }
)
with urllib.request.urlopen(req3) as resp:
    data = json.loads(resp.read())
    for model in sorted(data["data"], key=lambda m: m["id"]):
        print(model["id"])