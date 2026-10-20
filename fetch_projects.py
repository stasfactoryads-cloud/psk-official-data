#!/usr/bin/env python3
"""
Создаёт карточки projects/<slug>.json для всех проектов из api/marketing.json,
если их ещё нет. Заполняет данными из API (marketing.json, availability.json,
flats.json). Существующие карточки НЕ перезаписываются: там могут быть ручные правки.
Запуск: python3 fetch_projects.py   (после fetch_marketing.py и fetch_flats.py)
"""
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).parent
API = ROOT / "api"
PROJECTS = ROOT / "projects"
TODAY = datetime.now(timezone.utc).strftime("%Y-%m-%d")


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def to_number(value):
    try:
        n = float(value)
        return n if n > 0 else None
    except (TypeError, ValueError):
        return None


def min_mortgage_by_slug(flats):
    """Минимальный ежемесячный платёж по ипотеке среди свободных лотов каждого проекта."""
    result = {}
    for f in flats:
        pay, slug = f.get("dvizh_min_mortgage"), f.get("project_slug")
        if f.get("status") != "Свободно" or not pay or not slug:
            continue
        if slug not in result or pay < result[slug]:
            result[slug] = pay
    return result


def build_card(slug, m, avail, mortgage_min):
    metro = m.get("metro") or []
    first_metro = metro[0] if metro else {}
    completion = m.get("completion") or {}
    status = m.get("status") or {}
    av = avail.get(slug, {})
    price = to_number(m.get("min_price"))
    return {
        "slug": slug,
        "name": m.get("name"),
        "developer": "ГК ПСК",
        "project_class": m.get("project_class"),
        "property_type": m.get("category"),
        "address": {"value": m.get("address"), "source": "psk-info-api"},
        "metro": {
            "value": first_metro.get("name"),
            "walk_min": first_metro.get("walk_min"),
            "source": "psk-info-api",
        },
        "landing_url": m.get("landing_url"),
        "psk_info_slug": slug,
        "psk_info_id": m.get("id"),
        "status": {"value": status.get("label"), "source": "psk-info-api", "checked": TODAY},
        "construction": {"progress_pct": status.get("completion_percent"), "source": "psk-info-api", "checked": TODAY},
        "commissioning": {
            "value": f"{completion.get('quarter')} квартал {completion.get('year')}" if completion.get("year") else None,
            "source": "psk-info-api",
            "checked": TODAY,
        },
        "min_price": {
            "value": price,
            "currency": "RUB",
            "source": "psk-info-api /api/projects/ (min_price)",
            "checked": TODAY,
            "status": "partial",
            "note": "Из API, не сверено с лендингом и квартирами",
        },
        "availability": {
            "total": av.get("total"),
            "free": av.get("free"),
            "reserved": av.get("reserved"),
            "free_min_price": av.get("free_min_price"),
            "source": "api/availability.json",
            "checked": TODAY,
        },
        "mortgage": {
            "monthly_payment_example": mortgage_min.get(slug),
            "source": "psk-info-api /api/flats/ dvizh_min_mortgage (свободные лоты)",
            "status": "unverified",
            "note": "Назначение поля не подтверждено, параметры расчёта (взнос, срок, ставка, банк) не известны",
            "first_payment_pct": None,
            "term_years": None,
            "rate_pct": None,
            "bank": None,
        },
        "installment": {
            "first_payment_pct": {"value": None, "status": "unverified", "note": "Не найдено в API"},
        },
        "yield": {"claimed_pct": None},
        "promotions": [],
        "manual_overrides": {},
        "sources_checked": [f"https://psk-info.ru/api/projects/{slug}/", "api/flats.json", "api/availability.json"],
    }


def main():
    marketing = load(API / "marketing.json")["projects"]
    avail = load(API / "availability.json")["projects"]
    mortgage_min = min_mortgage_by_slug(load(API / "flats.json")["flats"])

    PROJECTS.mkdir(exist_ok=True)
    created, kept = [], []
    for slug, m in marketing.items():
        path = PROJECTS / f"{slug}.json"
        if path.exists():
            kept.append(slug)
            continue
        card = build_card(slug, m, avail, mortgage_min)
        path.write_text(json.dumps(card, ensure_ascii=False, indent=2), encoding="utf-8")
        created.append(slug)

    print(f"Создано карточек: {len(created)}, уже существовали: {len(kept)}")
    for s in created:
        print("  +", s)
    for s in kept:
        print("  =", s)


if __name__ == "__main__":
    main()
