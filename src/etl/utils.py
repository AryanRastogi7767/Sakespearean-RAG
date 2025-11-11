from pathlib import Path
import json
import re

def json_write(path, records):
    """
    Write a list of Python objects (dicts) to a JSON or JSONL file.
    Automatically detects format based on file extension.
    """
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)

    # Handle JSONL (one object per line)
    if p.suffix.lower() == ".jsonl":
        with p.open("w", encoding="utf-8") as f:
            for r in records:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
    else:  # Standard JSON (list)
        with p.open("w", encoding="utf-8") as f:
            json.dump(records, f, ensure_ascii=False, indent=2)


def json_read(path):
    """
    Read a JSON or JSONL file and yield each record.
    Automatically detects file format.
    """
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"❌ File not found: {path}")

    if p.suffix.lower() == ".jsonl":
        with p.open("r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    yield json.loads(line)
    else:
        with p.open("r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, list):
                for item in data:
                    yield item
            else:
                yield data


def rx(pattern, flags=re.IGNORECASE):
    """Compile a regex pattern."""
    return re.compile(pattern, flags)


def slug(s: str) -> str:
    """Convert string to lowercase slug (a-z0-9 and hyphens)."""
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")

def jsonl_read(path):
    """
    Read a JSONL (JSON Lines) file line by line and return a list of dicts.
    """
    items = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                items.append(json.loads(line))
            except json.JSONDecodeError as e:
                print(f"⚠️ Skipping malformed line: {e}")
    return items
