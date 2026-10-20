#!/usr/bin/env python3
"""
Собирает единый файл api/projects.json из projects/*.json.
Запуск: python3 build.py
Только стандартная библиотека Python.
"""
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).parent
PROJECTS_DIR = ROOT / "projects"
OUT = ROOT / "api" / "projects.json"
REQUIRED = ["slug", "name", "developer", "landing_url"]


def main():
    items, errors = [], []
    for path in sorted(PROJECTS_DIR.glob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            errors.append(f"{path.name}: некорректный JSON ({e})")
            continue
        missing = [k for k in REQUIRED if not data.get(k)]
        if missing:
            errors.append(f"{path.name}: нет полей {missing}")
            continue
        if data.get("slug") != path.stem:
            errors.append(f"{path.name}: slug «{data.get('slug')}» не совпадает с именем файла")
            continue
        items.append(data)

    if errors:
        print("Ошибки, сборка остановлена:")
        for e in errors:
            print("  -", e)
        sys.exit(1)

    OUT.parent.mkdir(exist_ok=True)
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "count": len(items),
        "projects": items,
    }
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Собрано проектов: {len(items)} → {OUT}")


if __name__ == "__main__":
    main()
