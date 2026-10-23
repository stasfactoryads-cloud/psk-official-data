#!/usr/bin/env python3
"""
Собирает УТП проектов из данных, а не из слайдов psk-info.

Блоки УТП:
  Расположение      — ручная фраза локации (projects/<slug>.json → utp_manual.location)
  Транспорт         — метро и время пешком/на машине (api/marketing.json)
  Квартиры          — всего квартир в проекте (api/availability.json)
  Минимальная цена  — от какой цены есть свободные квартиры (api/availability.json)
  Особенности       — ручные пункты (projects/<slug>.json → utp_manual.features)
  Рядом             — ключевая инфраструктура (api/marketing.json)
  Условия покупки   — ипотека, рассрочка, акции — только если есть в conditions.json
  Застройщик        — юрлицо проекта (developer_legal) и описание группы ПСК

Выход: api/utp.json. Запуск: python3 build_utp.py. Только стандартная библиотека.
"""
import json
import re
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).parent
API = ROOT / "api"
PROJECTS = ROOT / "projects"
OUT = API / "utp.json"

GROUP_TEXT = (
    "ГК ПСК — более 60 объектов, из них более 20 собственных девелоперских проектов. "
    "Многократный обладатель знака «Надежный застройщик России». "
    "В 2025 г. — топ-3 строительных компаний Санкт-Петербурга по объёму текущего строительства."
)


def load(path):
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def clean(text):
    return re.sub(r"\s+", " ", re.sub(r"<br\s*/?>", " ", text or "")).strip()


def flats_word(n):
    if n % 100 in (11, 12, 13, 14) or n % 10 in (0, 5, 6, 7, 8, 9):
        return "квартир"
    if n % 10 == 1:
        return "квартира"
    return "квартиры"


def million(value):
    return f"{value / 1e6:.1f}".replace(".", ",")


def main():
    mk = load(API / "marketing.json").get("projects", {})
    marketing = {p["slug"]: p for p in (mk.values() if isinstance(mk, dict) else mk)}
    avail = load(API / "availability.json").get("projects", {})
    cond = load(API / "conditions.json").get("projects", {})

    out = {}
    for path in sorted(PROJECTS.glob("*.json")):
        card = json.loads(path.read_text(encoding="utf-8"))
        slug = card["slug"]
        m = marketing.get(slug, {})
        manual = card.get("utp_manual") or {}
        a = avail.get(slug, {})
        c = cond.get(slug, {})
        bullets = []

        if manual.get("location"):
            bullets.append({"title": "Расположение", "text": manual["location"]})

        metro = (m.get("metro") or [{}])[0]
        if metro.get("name"):
            if metro.get("walk_min"):
                transport = f"м. {metro['name']}, {metro['walk_min']} мин пешком"
            elif metro.get("car_min"):
                transport = f"м. {metro['name']}, {metro['car_min']} мин на машине"
            else:
                transport = f"м. {metro['name']}"
            bullets.append({"title": "Транспорт", "text": transport})

        if a.get("total") and a.get("free"):
            bullets.append({"title": "Квартиры", "text": f"{a['total']} {flats_word(a['total'])} в проекте"})
        if a.get("free_min_price"):
            bullets.append({"title": "Минимальная цена", "text": f"от {million(a['free_min_price'])} млн ₽ за свободную квартиру"})

        if manual.get("features"):
            bullets.append({"title": "Особенности", "text": "; ".join(manual["features"])})

        infra = [clean(i.get("title")) for i in (m.get("infrastructure") or []) if i.get("title")][:3]
        if infra:
            bullets.append({"title": "Рядом", "text": ", ".join(infra)})

        terms = []
        if c.get("mortgage"):
            terms.append("ипотека банков-партнёров")
        if c.get("installment"):
            terms.append("рассрочка от застройщика")
        if c.get("promotions"):
            terms.append("акции и скидки")
        if terms:
            bullets.append({"title": "Условия покупки", "text": "; ".join(terms)})

        dev = card.get("developer_legal")
        prefix = f"Застройщик — {dev}, группа ПСК. " if dev else "Застройщик — группа ПСК. "
        bullets.append({"title": "Застройщик", "text": prefix + GROUP_TEXT})

        out[slug] = {"name": card.get("name"), "bullets": bullets}

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "description": "УТП проектов, собранные из данных. Ручные фразы — в projects/<slug>.json, поле utp_manual.",
        "projects": out,
    }
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"УТП собраны для {len(out)} проектов → {OUT}")


if __name__ == "__main__":
    main()
