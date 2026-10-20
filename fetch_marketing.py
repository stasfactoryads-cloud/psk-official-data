#!/usr/bin/env python3
"""
Парсит карточки всех проектов с psk-info.ru/api/projects/<slug>/ и собирает
маркетинговые данные: описание, УТП, видео, галереи, ссылки.
Результат: api/marketing.json. Только стандартная библиотека.
Запуск: python3 fetch_marketing.py
"""
import html
import json
import re
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).parent
OUT = ROOT / "api" / "marketing.json"
BASE = "https://psk-info.ru/api"


def get_json(url):
    req = urllib.request.Request(url, headers={"User-Agent": "psk-official-data/1.0"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)


def strip_html(text):
    if not text:
        return ""
    text = re.sub(r"<br\s*/?>", "\n", text, flags=re.I)
    text = re.sub(r"</p>", "\n", text, flags=re.I)
    text = re.sub(r"<[^>]+>", "", text)
    text = html.unescape(text).replace("\xa0", " ")
    lines = [re.sub(r"\s+", " ", ln).strip() for ln in text.splitlines()]
    return "\n".join(ln for ln in lines if ln)


def list_projects():
    url, items = f"{BASE}/projects/", []
    while url:
        data = get_json(url)
        if isinstance(data, dict):
            items.extend(data.get("results", []))
            url = data.get("next")
        else:
            items.extend(data)
            url = None
    return items


def parse_project(slug, d):
    video_mp4 = d.get("project_video_link") or d.get("about_project_video_link")
    return {
        "id": d.get("id"),
        "slug": slug,
        "name": d.get("name"),
        "title": d.get("title"),
        "category": d.get("category_name"),
        "project_class": d.get("project_class"),
        "address": d.get("address"),
        "city": d.get("city"),
        "completion": {
            "year": d.get("completion_year"),
            "quarter": d.get("completion_quarter"),
            "year_max": d.get("completion_year_max"),
            "quarter_max": d.get("completion_quarter_max"),
        },
        "status": {
            "label": d.get("text_tag"),
            "released": d.get("released"),
            "sellable": d.get("sellable"),
            "is_coming": d.get("is_coming"),
            "completion_percent": d.get("completion_percent"),
        },
        "min_price": d.get("min_price"),
        "landing_url": d.get("landing_url"),
        "virtual_tour_url": d.get("virtual_tour_link") or None,
        "genplan_url": d.get("genplan_link") or None,
        "metro": [
            {"name": m.get("metro_name"), "walk_min": m.get("walk_time"), "car_min": m.get("car_time")}
            for m in d.get("projectmetro_set", [])
        ],
        "description_short": strip_html(d.get("about_project_text_short")),
        "description": strip_html(d.get("about_project_text")),
        "usps": [
            {"title": u.get("title"), "text": strip_html(u.get("text"))}
            for u in d.get("projectutpslide_set", [])
        ],
        "advantages": [
            {
                "name": info.get("name"),
                "text": strip_html(info.get("text")),
                "images": [g.get("image") for g in info.get("gallery_images", []) if g.get("image")],
            }
            for adv in d.get("project_advantages", [])
            for info in adv.get("advantages_info", [])
        ],
        "infrastructure": [
            {"title": i.get("title"), "time": i.get("path")}
            for i in d.get("infrastructure_advantages", [])
        ],
        "video": {
            "mp4_url": video_mp4,
            "preview_url": d.get("project_video_preview") or d.get("about_project_video_preview"),
        },
        "gallery": [s.get("image") for s in d.get("slider_images", []) if s.get("image")],
        "photo_report_preview": d.get("photo_reports_preview"),
        "tags": d.get("tags", []),
    }


def main():
    projects, errors = {}, []
    for item in list_projects():
        slug = item.get("slug")
        if not slug:
            continue
        try:
            detail = get_json(f"{BASE}/projects/{slug}/")
            projects[slug] = parse_project(slug, detail)
        except Exception as e:
            errors.append(f"{slug}: {e}")

    OUT.parent.mkdir(exist_ok=True)
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source": "https://psk-info.ru/api/projects/<slug>/",
        "count": len(projects),
        "projects": projects,
    }
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Проектов с маркетинговыми данными: {len(projects)} → {OUT}")
    with_video = [s for s, p in projects.items() if p["video"]["mp4_url"]]
    print(f"С видео: {len(with_video)}")
    for e in errors:
        print("Ошибка:", e)


if __name__ == "__main__":
    main()
