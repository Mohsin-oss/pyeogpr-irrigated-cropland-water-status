from pathlib import Path
import requests
import subprocess


repo = Path(__file__).resolve().parents[1] / "external" / "pyeogpr"

commit = subprocess.check_output(
    ["git", "-C", str(repo), "rev-parse", "HEAD"],
    text=True,
).strip()


model_url = (
    "https://raw.githubusercontent.com/"
    f"emmadcle/pyeogpr/{commit}/models/"
    "SENTINEL2_L1C_laiCw_GEE.py"
)


print("Commit:", commit)
print("Testing:", model_url)


response = requests.get(model_url, timeout=30)

print("HTTP status:", response.status_code)
print("File size:", len(response.text), "characters")

response.raise_for_status()

assert "404: Not Found" not in response.text
assert len(response.text) > 1000

print("✅ Sentinel-2 L1C laiCw model accessible.")