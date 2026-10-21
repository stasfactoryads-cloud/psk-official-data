#!/usr/bin/env python3
"""
Собирает единый файл api/projects.json из projects/*.json.

Перед сборкой пересчитывает актуальность условий продаж по сегодняшней дате
на основе дат документов, уже сохранённых в api/conditions.json. Поэтому статус
«устарело» появляется по правилу (до 6 числа) без новых файлов.

Запуск: python3 build.py
Нужен openpyxl (его тянет ingest_conditions.py): pip install openpyxl
"""
import json
import sys
from datetime import date, datetime, timezone
from pathlib import Path

from ingest_conditions import document_status

ROOT = Path(__file__).parent
PROJECTS_DIR = ROOT / "projects"
OUT = ROOT / "api" / "projects.json"
API_DIR = ROOT / "api"
COND_PATH = API_DIR / "conditions.json"
REQUIRED = ["slug", "name", "developer"]


def refresh_conditions(cond, today):
    """Пересчитывает статусы документов, общий статус и просрочку акций. Возвращает True, если что-то изменилось."""
    changed = False
    documents = cond.get("documents", [])
    for doc in documents:
        as_of = date.fromisoformat(doc["as_of"]) if doc.get("as_of") else None
        status = document_status(as_of, today)
        if doc.get("status") != status:
            doc["status"] = status
            changed = True

    statuses = {d["status"] for d in documents}
    if statuses == {"актуально"}:
        overall = "актуально"
    elif "устарело" in statuses:
        overall = "устарело"
    else:
        overall = "требует проверки"
    if cond.get("status") != overall:
        cond["status"] = overall
        changed = True

    for sections in (cond.get("projects") or {}).values():
        for items in sections.values():
            for item in items:
                if item.get("valid_to"):
                    expired = date.fromisoformat(item["valid_to"]) < today
                    if item.get("expired") != expired:
                        item["expired"] = expired
                        changed = True
    return changed


def main():
    today = date.today()

    cond = json.loads(COND_PATH.read_text(encoding="utf-8")) if COND_PATH.exists() else {}
    if cond and refresh_conditions(cond, today):
        COND_PATH.write_text(json.dumps(cond, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"Статусы условий пересчитаны на {today.isoformat()}: {cond.get('status')}")

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

    for it in items:
        it["conditions"] = (cond.get("projects") or {}).get(it["slug"], {})
    OUT.parent.mkdir(exist_ok=True)
    payload = {
        "conditions_status": cond.get("status", "нет данных"),
        "conditions_documents": cond.get("documents", []),
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "count": len(items),
        "projects": items,
    }
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Собрано проектов: {len(items)} → {OUT}")


if __name__ == "__main__":
    main()
