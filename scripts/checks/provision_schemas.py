from __future__ import annotations

import json
import subprocess
from pathlib import Path


def main() -> None:
    root = Path(__file__).resolve().parents[2]
    destination = root / ".agent-cache" / "schemas"
    result = subprocess.run(
        ["kubectl", "get", "customresourcedefinitions", "-o", "json"],
        check=True,
        capture_output=True,
        text=True,
        timeout=30,
    )
    document = json.loads(result.stdout)
    written = 0
    for crd in document["items"]:
        group = crd["spec"]["group"]
        kind = crd["spec"]["names"]["kind"]
        directory = destination / group
        directory.mkdir(parents=True, exist_ok=True)
        for version in crd["spec"]["versions"]:
            schema = version.get("schema", {}).get("openAPIV3Schema")
            if not version.get("served") or not schema:
                continue
            encoded_group = group.split(".", 1)[0]
            path = (
                destination / f"{kind.lower()}-{encoded_group}-{version['name']}.json"
            )
            path.write_text(json.dumps(schema, sort_keys=True) + "\n", encoding="utf-8")
            written += 1
    if not written:
        raise RuntimeError("cluster returned no served CRD schemas")
    print(f"provisioned {written} CRD schemas in {destination}")


if __name__ == "__main__":
    main()
