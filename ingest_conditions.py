#!/usr/bin/env python3
"""
Читает ежемесячные файлы условий продаж (xlsx) из папки conditions/incoming/
и раскладывает условия по проектам.

Выход:
  api/conditions.json            — условия по проектам + статус актуальности документов
  projects/<slug>.json           — поля conditions_status и conditions_as_of (остальное не трогаем)

Правило актуальности: документ должен быть загружен не раньше порогового дня месяца
(по умолчанию 6-е число текущего месяца). Дата берётся из имени файла (dd.mm.yyyy).
Если даты в имени нет, статус «дата не указана» и файл требует подтверждения.

Запуск: python3 ingest_conditions.py
Только стандартная библиотека и openpyxl (pip install openpyxl).
"""
import json
import re
import sys
from datetime import date, datetime, timezone
from pathlib import Path

import openpyxl

ROOT = Path(__file__).parent
INCOMING = ROOT / "conditions" / "incoming"
API_OUT = ROOT / "api" / "conditions.json"
PROJECTS = ROOT / "projects"
THRESHOLD_DAY = 6

# Ключевые слова заголовков → slug проекта в API. Порядок важен: более длинные — раньше.
KEYWORDS = [
    ("ГАЛЕРНАЯ", "galernaya-gavan"),
    ("АССАМБЛЕЯ", "assambleya-klubnyj-kvartal"),
    ("ОПТИМИСТ", "optimist-zhiloj-kompleks"),
    ("СЕЗОНЫ", "sezony-vidovoj-kompleks"),
    ("RESPECT", "zhk-respect"),
    ("PLUS", "plus-pulkovskij"),
    ("INDUSTRIAL", "industrial-avenir"),
    ("LADOZHSKY", "ladozhsky"),
    ("FRIENDS", "friends"),
    ("АКВАТОРИЯ", "akvatoriya-premialnyj-dom"),
    ("BAKUNINA", "bakunina33"),
    ("КОРОНА", "korona"),
]
# Проекты из файлов, которых нет в API: попадают в список на проверку, не в публикацию.
NOT_IN_API = ["MOSKOVSKY", "KIROVSKY", "PUTILOV"]

# Листы, которые не содержат условий продаж (инструкции и служебные).
SKIP_SHEETS = ("Инструкция",)

# Тип данных листа: как трактовать строки.
SECTION_BY_SHEET = [
    ("Программы по ипотеке", "mortgage"),
    ("ИПОТЕКА", "mortgage"),
    ("Условия выдачи", "mortgage"),
    ("РАССРОЧКА", "installment"),
    ("РАССРОЧКИ", "installment"),
    ("АКЦИИ", "promotions"),
    ("ММ_Келлеры", "parking_storage"),
    ("КП", "commercial"),
    ("Коммерция", "commercial"),
]
EMPTY = {None, "", "-", "—", "_", "–"}
YES = {"V", "v", "V ", "✓"}  # отметка «да» в таблицах условий


def as_value(text):
    return "да" if text in YES else text


def norm(text):
    return re.sub(r"[\s\-_.,()«»\"']", "", str(text or "")).upper()


def match_slug(text, column_text=""):
    """Слаг проекта по тексту заголовка. Для Корона: «апартаменты» → korona_apart."""
    n = norm(text)
    for kw, slug in KEYWORDS:
        if kw in n:
            if slug == "korona" and "АПАРТ" in n:
                return "korona_apart"
            return slug
    return None


def is_not_in_api(text):
    n = norm(text)
    return any(k in n for k in NOT_IN_API)


def section_for(sheet_name):
    for key, section in SECTION_BY_SHEET:
        if key in sheet_name:
            return section
    return "other"


def cell_text(v):
    if v is None:
        return ""
    return re.sub(r"\s+", " ", str(v)).strip()


def file_date(name):
    m = re.search(r"(\d{2})\.(\d{2})\.(\d{4})", name)
    if m:
        d, mo, y = map(int, m.groups())
        try:
            return date(y, mo, d)
        except ValueError:
            return None
    return None


HEADER_LABELS = ("ПРОГРАММА", "ПРОЕКТ", "ФОРМА ОПЛАТЫ", "НАИМЕНОВАНИЕ ОБЪЕКТА", "БАНК")


def find_header_row(ws):
    """Строка-шапка: несколько ячеек с названиями проектов, либо одна ячейка-проект в строке «Программа/Проект»."""
    # шапка всегда в первых строках листа; строки ниже — данные, даже если в них есть названия проектов
    for r_idx, row in enumerate(ws.iter_rows(min_row=1, max_row=min(ws.max_row, 6), values_only=True), start=1):
        hits = [c for c in row if c and match_slug(c)]
        first_label = next((cell_text(c) for c in row if cell_text(c)), "")
        if len(hits) >= 2 or (hits and norm(first_label) in {norm(x) for x in HEADER_LABELS}):
            return r_idx
    return None


def extract_header_sheet(ws, section, sheet_name, out, unmatched):
    """Лист, где проекты — колонки (шапка). Строки — условия."""
    h = find_header_row(ws)
    if h is None:
        return 0
    header = [cell_text(c) for c in next(ws.iter_rows(min_row=h, max_row=h, values_only=True))]
    label_idx = next((i for i, t in enumerate(header) if t), 0)  # колонка с названиями строк
    cols = {}
    for idx, text in enumerate(header):
        if idx <= label_idx or not text:
            continue
        slug = match_slug(text)
        if slug:
            cols[idx] = (slug, text)
        elif is_not_in_api(text):
            unmatched.add(text)
    count = 0
    last_label = ""
    for row in ws.iter_rows(min_row=h + 1, max_row=ws.max_row, values_only=True):
        if not row:
            continue
        label_raw = cell_text(row[label_idx]) if label_idx < len(row) else ""
        if label_raw:
            last_label = label_raw  # объединённые ячейки: название действует на строки ниже
        if not last_label:
            continue
        for idx, (slug, column) in cols.items():
            value = cell_text(row[idx]) if idx < len(row) else ""
            if value in EMPTY:
                continue
            out.setdefault(slug, {}).setdefault(section, []).append({
                "source": sheet_name, "column": column, "label": last_label, "condition": as_value(value),
            })
            count += 1
    return count


def extract_rows_sheet(ws, section, sheet_name, out, unmatched):
    """Лист, где проект написан в колонке A, а строки под ним — условия этого проекта."""
    current = None
    count = 0
    for row in ws.iter_rows(min_row=1, max_row=ws.max_row, values_only=True):
        first = cell_text(row[0]) if row else ""
        if first and first.lower() not in ("проект", "программа", "форма оплаты", "банк"):
            slug = match_slug(first)
            if slug:
                current = (slug, first)
            elif is_not_in_api(first):
                unmatched.add(first)
                current = None
            elif len(first) < 60 and any(c for c in row[1:] if c):
                # Заголовок-разделитель, например «АКЦИОННЫЕ РАССРОЧКИ», пропускаем
                continue
        if not current:
            continue
        values = [cell_text(c) for c in row[1:] if cell_text(c) not in EMPTY]
        if not values:
            continue
        slug, column = current
        out.setdefault(slug, {}).setdefault(section, []).append({
            "source": sheet_name, "column": column, "label": first or "", "condition": " / ".join(values),
        })
        count += 1
    return count


def extract_whole_sheet(ws, section, sheet_name, out, slug):
    """Лист целиком про один проект (например, «ИПОТЕКА АКВАТОРИЯ»)."""
    count = 0
    for row in ws.iter_rows(min_row=1, max_row=ws.max_row, values_only=True):
        values = [cell_text(c) for c in row if cell_text(c) not in EMPTY]
        if not values:
            continue
        out.setdefault(slug, {}).setdefault(section, []).append({
            "source": sheet_name, "column": "", "label": values[0], "condition": " / ".join(values[1:]) or values[0],
        })
        count += 1
    return count


def expiry_of(text):
    """Дата окончания из текста вида «до 30.10.2026» или «до 20.03.2029»."""
    m = re.search(r"до\s+(\d{2})\.(\d{2})\.(\d{2,4})", text)
    if not m:
        return None
    d, mo, y = map(int, m.groups())
    y = y + 2000 if y < 100 else y
    try:
        return date(y, mo, d).isoformat()
    except ValueError:
        return None


def process_file(path, out, unmatched, report):
    name = path.name
    as_of = file_date(name)
    wb = openpyxl.load_workbook(path, data_only=True)
    sheets_done = []
    for ws in wb.worksheets:
        if any(s in ws.title for s in SKIP_SHEETS):
            continue
        section = section_for(ws.title)
        if section == "other":
            continue
        if "АКВАТОРИЯ" in norm(ws.title):
            # лист целиком про «Акваторию»
            n = extract_whole_sheet(ws, section, ws.title, out, "akvatoriya-premialnyj-dom")
        elif find_header_row(ws) is not None:
            # проекты — колонки в шапке листа
            n = extract_header_sheet(ws, section, ws.title, out, unmatched)
        else:
            # проекты — строки в колонке A
            n = extract_rows_sheet(ws, section, ws.title, out, unmatched)
        sheets_done.append({"sheet": ws.title, "section": section, "rows_taken": n})
    report.append({"file": name, "as_of": as_of.isoformat() if as_of else None, "sheets": sheets_done})


def document_status(as_of, today):
    threshold = date(today.year, today.month, THRESHOLD_DAY)
    if as_of is None:
        return "дата не указана"
    if today < threshold:
        # до 6-го числа действует файл прошлого месяца
        prev_threshold = date(today.year if today.month > 1 else today.year - 1,
                              today.month - 1 if today.month > 1 else 12, THRESHOLD_DAY)
        return "актуально" if as_of >= prev_threshold else "устарело"
    return "актуально" if as_of >= threshold else "устарело"


def mark_expired(out, today):
    for slug, sections in out.items():
        for section, items in sections.items():
            for item in items:
                exp = expiry_of(item["condition"])
                if exp:
                    item["valid_to"] = exp
                    item["expired"] = date.fromisoformat(exp) < today


def main():
    today = date.today()
    files = sorted(p for p in INCOMING.glob("*.xlsx") if not p.name.startswith("~$"))
    if not files:
        print(f"Нет файлов в {INCOMING}. Положите туда выгрузки условий (xlsx).")
        sys.exit(1)

    out, unmatched, report = {}, set(), []
    for path in files:
        process_file(path, out, unmatched, report)
    mark_expired(out, today)

    documents = []
    for r in report:
        as_of = date.fromisoformat(r["as_of"]) if r["as_of"] else None
        documents.append({
            "file": r["file"],
            "as_of": r["as_of"],
            "status": document_status(as_of, today),
            "sheets": r["sheets"],
        })
    statuses = {d["status"] for d in documents}
    overall = "актуально" if statuses == {"актуально"} else ("устарело" if "устарело" in statuses else "требует проверки")

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "threshold_day": THRESHOLD_DAY,
        "status": overall,
        "documents": documents,
        "not_in_api": sorted(unmatched),
        "projects": out,
    }
    API_OUT.parent.mkdir(exist_ok=True)
    API_OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    # Статус обновляем в карточках проектов, в которых есть условия
    for slug in out:
        card_path = PROJECTS / f"{slug}.json"
        if not card_path.exists():
            continue
        card = json.loads(card_path.read_text(encoding="utf-8"))
        card["conditions_status"] = overall
        card["conditions_as_of"] = max((d["as_of"] for d in documents if d["as_of"]), default=None)
        card_path.write_text(json.dumps(card, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"Файлов: {len(files)}; статус условий: {overall}")
    for d in documents:
        print(f"  {d['file']}: дата {d['as_of'] or '—'}, {d['status']}")
    print(f"Проектов с условиями: {len(out)}")
    for slug in sorted(out):
        counts = {k: len(v) for k, v in out[slug].items()}
        print(f"  {slug}: {counts}")
    if unmatched:
        print("Нет в API, требуют решения:", ", ".join(sorted(unmatched)))


if __name__ == "__main__":
    main()
