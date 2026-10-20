#!/usr/bin/env python3
"""
Собирает актуальный каталог лотов (квартир) из psk-info.ru/api/flats/
в файл api/flats.json. Все страницы API, только стандартная библиотека.
Запуск: python3 fetch_flats.py
"""
import json
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).parent
OUT = ROOT / "api" / "flats.json"
START_URL = "https://psk-info.ru/api/flats/?limit=500&offset=0"
KEEP = [
    "id", "number", "type", "status", "rooms", "area", "floor", "max_floor",
    "price", "original_price", "dvizh_min_mortgage", "min_mortgage", "discount",
    "tags", "booking_days", "finishing", "assignment", "leasing", "auction",
    "project", "project_name", "project_slug", "building", "section",
    "completion_year", "completion_quarter", "project_class", "plan", "floor_plan",
]


def fetch_all():
    url, flats, count = START_URL, [], None
    while url:
        with urllib.request.urlopen(url, timeout=60) as r:
            data = json.load(r)
        count = data.get("count", count)
        flats.extend(data.get("results", []))
        url = data.get("next")
        if url and url.startswith("http://"):
            url = "https://" + url[len("http://"):]
    return flats, count


def main():
    raw, count = fetch_all()
    flats = [{k: f.get(k) for k in KEEP} for f in raw]
    if count is not None and len(flats) != count:
        print(f"Внимание: получено {len(flats)} из {count} записей")
    OUT.parent.mkdir(exist_ok=True)
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source": "https://psk-info.ru/api/flats/",
        "count": len(flats),
        "flats": flats,
    }
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    by_project = {}
    for f in flats:
        by_project[f["project_slug"]] = by_project.get(f["project_slug"], 0) + 1
    print(f"Лотов сохранено: {len(flats)} → {OUT}")
    for slug, n in sorted(by_project.items(), key=lambda x: -x[1]):
        print(f"  {slug}: {n}")


if __name__ == "__main__":
    main()
