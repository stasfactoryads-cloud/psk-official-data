#!/usr/bin/env python3
"""
Создаёт индекс всех данных API: api/index.json (для агентов) и api/INDEX.md (для людей).
Запускать после fetch_marketing.py, fetch_flats.py и build.py.
Запуск: python3 write_index.py
"""
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).parent
API = ROOT / "api"
RAW = "https://raw.githubusercontent.com/stasfactoryads-cloud/psk-official-data/main/api/"
REPO = "https://github.com/stasfactoryads-cloud/psk-official-data"

FILES = [
    {
        "file": "projects.json",
        "title": "Проекты: цены, ипотека, рассрочка, статусы",
        "description": "Структурные данные по проектам с источником и статусом проверки каждого поля. Ручные правки отдела продаж — в manual_overrides.",
        "count_key": "count",
    },
    {
        "file": "marketing.json",
        "title": "Маркетинг: описания, УТП, фото и видео",
        "description": "Текст о проекте, преимущества, инфраструктура, прямые ссылки на фото (media.photos) и видео (media.videos).",
        "count_key": "count",
    },
    {
        "file": "flats.json",
        "title": "Каталог лотов: все квартиры",
        "description": "Все квартиры по всем проектам: цена, площадь, этаж, статус, ипотечный платёж, планировка.",
        "count_key": "count",
    },
    {
        "file": "availability.json",
        "title": "Срез наличия: в продаже и в броне",
        "description": "Свободно и в броне по каждому проекту и по каталогу в целом, минимальная цена свободного лота.",
        "count_key": None,
    },
    {
        "file": "conditions.json",
        "title": "Условия продаж: акции, рассрочка, ипотека, коммерция, машиноместа",
        "description": "Условия по каждому проекту из ежемесячных файлов. Файл считается актуальным, если загружен не раньше 6-го числа текущего месяца.",
        "count_key": None,
    },
    {
        "file": "landings.json",
        "title": "Лендинги: посадочные страницы проектов",
        "description": "Все посадочные страницы по проектам, ссылки проверены запросом (HTTP-статус). Обновляется ежедневно.",
        "count_key": None,
    },
]


def build_alerts():
    cond = load(API / "conditions.json") or {}
    alerts = []
    status = cond.get("status")
    if status and status != "актуально":
        for d in cond.get("documents", []):
            if d.get("status") != "актуально":
                alerts.append({
                    "type": "conditions_outdated",
                    "file": d.get("file"),
                    "as_of": d.get("as_of"),
                    "message": f"Условия продаж не актуализированы: {d.get('file')} — {d.get('status')}. Загрузите файл до 6 числа месяца.",
                })
    for name in cond.get("not_in_api", []):
        alerts.append({"type": "project_not_in_api", "project": name,
                       "message": f"Проект «{name}» есть в условиях, но не заведён в API."})
    return alerts


def load(path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def main():
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    entries = []
    for f in FILES:
        data = load(API / f["file"]) or {}
        entry = {
            "file": f["file"],
            "title": f["title"],
            "description": f["description"],
            "url": RAW + f["file"],
            "generated_at": data.get("generated_at"),
        }
        if f["count_key"] and data.get(f["count_key"]) is not None:
            entry["count"] = data[f["count_key"]]
        if f["file"] == "availability.json":
            entry["totals"] = data.get("totals")
        entries.append(entry)

    alerts = build_alerts()
    index = {
        "generated_at": now,
        "repository": REPO,
        "base_url": RAW,
        "alerts": alerts,
        "files": entries,
    }
    (API / "index.json").write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = [
        "# Индекс данных API ГК ПСК",
        "",
        f"Обновлено: {now}",
        f"Репозиторий: {REPO}",
        "",
        "| Файл | Что внутри | Ссылка | Обновлено |",
        "|---|---|---|---|",
    ]
    for e in entries:
        lines.append(f"| `{e['file']}` | {e['title']}. {e['description']} | [raw]({e['url']}) | {e.get('generated_at') or '—'} |")
    lines += ["", "Все файлы публичные и читаются без авторизации."]
    (API / "INDEX.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"Индекс: {len(entries)} файлов → {API / 'index.json'} и {API / 'INDEX.md'}")


if __name__ == "__main__":
    main()
