#!/usr/bin/env python3
"""
Собирает api/landings.json: актуальный список посадочных страниц (лендингов) по проектам.

Источники:
  - api/marketing.json   — ссылки из psk-info API (landing_url) и уже объединённые landing_urls
  - projects/<slug>.json — ручные ссылки и отметки о проверке

Каждая ссылка проверяется запросом: записываем HTTP-статус. Ошибка проверки не останавливает
сборку — ссылка остаётся в списке со статусом «ошибка», чтобы её было видно.

Запуск: python3 build_landings.py
Только стандартная библиотека Python.
"""
import json
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).parent
PROJECTS_DIR = ROOT / "projects"
API_DIR = ROOT / "api"
OUT = API_DIR / "landings.json"
TIMEOUT = 15
USER_AGENT = "Mozilla/5.0 (compatible; PSK-landings-check/1.0)"


def unique(items):
    seen, out = set(), []
    for x in items:
        if x and x not in seen:
            seen.add(x)
            out.append(x)
    return out


def normalize(url):
    url = url.strip()
    if url and not url.startswith(("http://", "https://")):
        url = "https://" + url
    return url


def link_type(url):
    p = urlparse(url)
    if p.netloc.endswith("psk-info.ru") and p.path.startswith("/projects/"):
        return "карточка проекта на сайте ПСК"
    return "лендинг"


def check(url):
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            return {"status": "ok", "http_code": resp.status}
    except urllib.error.HTTPError as e:
        return {"status": "ошибка", "http_code": e.code}
    except Exception as e:  # сеть, таймаут, сертификат
        return {"status": "ошибка", "http_code": None, "error": type(e).__name__}


def main():
    marketing = {}
    mp = API_DIR / "marketing.json"
    if mp.exists():
        raw = json.loads(mp.read_text(encoding="utf-8")).get("projects", {})
        items = raw.values() if isinstance(raw, dict) else raw
        for p in items:
            marketing[p["slug"]] = p

    cache, projects = {}, []
    for path in sorted(PROJECTS_DIR.glob("*.json")):
        card = json.loads(path.read_text(encoding="utf-8"))
        slug = card.get("slug") or path.stem
        m = marketing.get(slug, {})
        urls = unique(
            normalize(u) for u in
            [card.get("landing_url"), m.get("landing_url"), *(card.get("landing_urls") or []), *(m.get("landing_urls") or [])]
            if u
        )
        links = []
        for url in urls:
            if url not in cache:
                cache[url] = check(url)
            links.append({"url": url, "type": link_type(url), **cache[url]})
        projects.append({
            "slug": slug,
            "name": card.get("name"),
            "developer": card.get("developer"),
            "primary_url": urls[0] if urls else None,
            "links": links,
            "manual_check_date": card.get("landing_urls_checked"),
            "owner_confirmed": card.get("landing_urls_owner_confirmed"),
        })

    general = []
    gp = ROOT / "landings_general.json"
    if gp.exists():
        for item in json.loads(gp.read_text(encoding="utf-8")).get("pages", []):
            url = normalize(item["url"])
            if url not in cache:
                cache[url] = check(url)
            general.append({"url": url, "name": item.get("name"), "note": item.get("note"), **cache[url]})

    all_links = [l for p in projects for l in p["links"]] + general
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "description": "Посадочные страницы (лендинги) проектов ГК ПСК. Обновляется ежедневно вместе с API.",
        "summary": {
            "projects_total": len(projects),
            "projects_with_landings": sum(1 for p in projects if p["links"]),
            "links_total": len(all_links),
            "links_ok": sum(1 for l in all_links if l["status"] == "ok"),
            "links_error": sum(1 for l in all_links if l["status"] != "ok"),
            "projects_without_landings": [p["slug"] for p in projects if not p["links"]],
        },
        "general_pages": general,
        "projects": projects,
    }
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    s = payload["summary"]
    print(f"Проектов: {s['projects_total']}, с лендингами: {s['projects_with_landings']}, "
          f"ссылок: {s['links_total']} (ок: {s['links_ok']}, ошибка: {s['links_error']})")
    for l in all_links:
        if l["status"] != "ok":
            print(f"  ! {l['url']} → {l.get('http_code') or l.get('error')}")


if __name__ == "__main__":
    sys.exit(main())
