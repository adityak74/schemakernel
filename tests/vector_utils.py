import json
import os
from typing import Any, Dict


def load_schema_vectors() -> Dict[str, Any]:
    # Find the root directory by looking for 'vectors' folder
    current_dir = os.path.dirname(os.path.abspath(__file__))
    while current_dir != "/":
        vector_path = os.path.join(current_dir, "vectors", "schema_vectors.json")
        if os.path.exists(vector_path):
            with open(vector_path, "r") as f:
                return json.load(f)
        current_dir = os.path.dirname(current_dir)
    raise FileNotFoundError("Could not find vectors/schema_vectors.json")
