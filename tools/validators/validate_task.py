import json
import jsonschema
import sys
import yaml
from pathlib import Path

def load_schema(schema_path: str):
    with open(schema_path, 'r') as f:
        return json.load(f)

def load_task(task_path: str):
    with open(task_path, 'r') as f:
        if task_path.endswith('.yaml') or task_path.endswith('.yml'):
            return yaml.safe_load(f)
        return json.load(f)

def validate_task(task_path: str, schema_path: str):
    task = load_task(task_path)
    schema = load_schema(schema_path)

    try:
        jsonschema.validate(instance=task, schema=schema)
        print(f"PASS: {task_path} is valid.")
        return True
    except jsonschema.ValidationError as e:
        print(f"FAIL: {task_path} is invalid.")
        print(e)
        return False

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python validate_task.py <task_path> <schema_path>")
        sys.exit(1)

    success = validate_task(sys.argv[1], sys.argv[2])
    sys.exit(0 if success else 1)
