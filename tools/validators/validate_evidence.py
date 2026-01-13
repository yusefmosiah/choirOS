import json
import jsonschema
import sys
from pathlib import Path

def load_schema(schema_path: str):
    with open(schema_path, 'r') as f:
        return json.load(f)

def validate_evidence(manifest_path: str, schema_path: str):
    with open(manifest_path, 'r') as f:
        manifest = json.load(f)

    schema = load_schema(schema_path)

    try:
        jsonschema.validate(instance=manifest, schema=schema)
        print(f"PASS: {manifest_path} is valid.")
        return True
    except jsonschema.ValidationError as e:
        print(f"FAIL: {manifest_path} is invalid.")
        print(e)
        return False

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python validate_evidence.py <manifest_path> <schema_path>")
        sys.exit(1)

    success = validate_evidence(sys.argv[1], sys.argv[2])
    sys.exit(0 if success else 1)
