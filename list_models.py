import urllib.request, json

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
litellm_key = env.get("LITELLM_MASTER_KEY", "***REDACTED-LITELLM-KEY***")
nim_key = env.get("NVIDIA_NIM_API_KEY", "")

# List LiteLLM models
req = urllib.request.Request(
    "http://localhost:4000/v1/models",
    headers={"Authorization": f"Bearer {litellm_key}"}
)
with urllib.request.urlopen(req) as resp:
    data = json.loads(resp.read())
    print("=== LiteLLM Models ===")
    for model in data["data"]:
        print(model["id"])

# List ALL NVIDIA NIM models
print("\n=== NVIDIA NIM Models ===")
req2 = urllib.request.Request(
    "https://integrate.api.nvidia.com/v1/models",
    headers={"Authorization": f"Bearer {nim_key}"}
)
with urllib.request.urlopen(req2) as resp:
    data = json.loads(resp.read())
    for model in sorted(data["data"], key=lambda m: m["id"]):
        print(model["id"])

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