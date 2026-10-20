#!/usr/bin/env python3
"""
Собирает актуальный каталог лотов (квартир) из psk-info.ru/api/flats/
в api/flats.json и считает срез наличия в api/availability.json.
Все страницы API, только стандартная библиотека.
Запуск: python3 fetch_flats.py
"""
import json
import urllib.request
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).parent
API_DIR = ROOT / "api"
START_URL = "https://psk-info.ru/api/flats/?limit=500&offset=0"
KEEP = [
    "id", "number", "type", "status", "rooms", "area", "floor", "max_floor",
    "price", "original_price", "dvizh_min_mortgage", "min_mortgage", "discount",
    "tags", "booking_days", "finishing", "assignment", "leasing", "auction",
    "project", "project_name", "project_slug", "building", "section",
    "completion_year", "completion_quarter", "project_class", "plan", "floor_plan",
]
FREE, RESERVED = "Свободно", "Бронь"


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


def availability(flats, generated_at):
    by_project = defaultdict(lambda: {"total": 0, "free": 0, "reserved": 0, "other": 0,
                                      "free_min_price": None, "free_rooms": Counter()})
    for f in flats:
        p = by_project[f["project_slug"]]
        p["project_name"] = f["project_name"]
        p["total"] += 1
        st = f.get("status")
        if st == FREE:
            p["free"] += 1
            price = f.get("price")
            if price and (p["free_min_price"] is None or price < p["free_min_price"]):
                p["free_min_price"] = price
            p["free_rooms"][str(f.get("rooms"))] += 1
        elif st == RESERVED:
            p["reserved"] += 1
        else:
            p["other"] += 1

    projects = {}
    for slug, p in sorted(by_project.items(), key=lambda x: -x[1]["total"]):
        projects[slug] = {
            "project_name": p["project_name"],
            "total": p["total"],
            "free": p["free"],
            "reserved": p["reserved"],
            "other": p["other"],
            "free_share_pct": round(100 * p["free"] / p["total"], 1) if p["total"] else 0,
            "free_min_price": p["free_min_price"],
            "free_by_rooms": dict(p["free_rooms"]),
        }
    total = Counter()
    for p in by_project.values():
        total.update({"total": p["total"], "free": p["free"], "reserved": p["reserved"], "other": p["other"]})
    return {
        "generated_at": generated_at,
        "source": "https://psk-info.ru/api/flats/",
        "totals": {
            "total": total["total"],
            "free": total["free"],
            "reserved": total["reserved"],
            "other": total["other"],
        },
        "projects": projects,
    }


def main():
    raw, count = fetch_all()
    flats = [{k: f.get(k) for k in KEEP} for f in raw]
    if count is not None and len(flats) != count:
        print(f"Внимание: получено {len(flats)} из {count} записей")
    generated_at = datetime.now(timezone.utc).isoformat(timespec="seconds")

    API_DIR.mkdir(exist_ok=True)
    (API_DIR / "flats.json").write_text(json.dumps({
        "generated_at": generated_at,
        "source": "https://psk-info.ru/api/flats/",
        "count": len(flats),
        "flats": flats,
    }, ensure_ascii=False, indent=2), encoding="utf-8")

    avail = availability(flats, generated_at)
    (API_DIR / "availability.json").write_text(
        json.dumps(avail, ensure_ascii=False, indent=2), encoding="utf-8")

    t = avail["totals"]
    print(f"Лотов: {t['total']}, свободно: {t['free']}, бронь: {t['reserved']}")
    for slug, p in avail["projects"].items():
        print(f"  {slug}: всего {p['total']}, свободно {p['free']}, бронь {p['reserved']}")


if __name__ == "__main__":
    main()
