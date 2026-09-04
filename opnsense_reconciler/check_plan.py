import argparse
import json
from pathlib import Path


def baked_uri(plan: dict) -> str:
    variables = plan.get("variables")
    if not isinstance(variables, dict):
        raise ValueError("plan JSON must contain a variables object")
    entry = variables.get("opnsense_uri")
    if not isinstance(entry, dict) or not isinstance(entry.get("value"), str):
        raise ValueError("plan JSON must contain variables.opnsense_uri.value")
    return entry["value"]


def check_plan_file(plan_path: Path, expected_uri: str) -> str:
    actual = baked_uri(json.loads(plan_path.read_text()))
    if actual != expected_uri:
        raise ValueError(f"plan targets {actual}, expected {expected_uri}")
    return actual


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description="Assert a saved tofu plan targets the expected OPNsense URI"
    )
    parser.add_argument("--plan", required=True, type=Path)
    parser.add_argument("--expect-uri", required=True)
    arguments = parser.parse_args(argv)
    uri = check_plan_file(arguments.plan, arguments.expect_uri)
    print(json.dumps({"opnsense_uri": uri}, sort_keys=True))


if __name__ == "__main__":
    main()
