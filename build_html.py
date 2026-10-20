#!/usr/bin/env python3
"""
Собирает единую HTML-страницу api/API.html со всеми данными из api/*.json.
Страница самодостаточная: данные встроены, внешних ресурсов нет.
Запуск: python3 build_html.py   (после fetch_*.py и build.py)
"""
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).parent
API = ROOT / "api"
OUT = API / "API.html"
FILES = ["projects.json", "marketing.json", "flats.json", "availability.json", "index.json"]

TEMPLATE = r"""<!doctype html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>ГК ПСК: данные API</title>
<style>
:root { --bg:#f6f7f9; --card:#fff; --ink:#1d2330; --muted:#6b7280; --line:#e3e6eb; --accent:#2563eb; --ok:#15803d; --warn:#b45309; }
@media (prefers-color-scheme: dark) { :root { --bg:#0f1115; --card:#181b22; --ink:#e7e9ee; --muted:#9aa3b2; --line:#2a2f3a; --accent:#60a5fa; } }
* { box-sizing: border-box; }
body { margin:0; font:15px/1.5 -apple-system, "Segoe UI", Roboto, sans-serif; background:var(--bg); color:var(--ink); }
header { padding:20px 16px 0; max-width:1200px; margin:0 auto; }
h1 { font-size:22px; margin:0 0 4px; }
.meta { color:var(--muted); font-size:13px; }
nav { display:flex; gap:6px; flex-wrap:wrap; margin:14px 0 0; border-bottom:1px solid var(--line); }
nav button { background:none; border:0; padding:10px 12px; cursor:pointer; color:var(--muted); font:inherit; border-bottom:2px solid transparent; }
nav button.active { color:var(--accent); border-bottom-color:var(--accent); }
main { max-width:1200px; margin:0 auto; padding:16px; }
.grid { display:grid; grid-template-columns:repeat(auto-fill,minmax(200px,1fr)); gap:12px; margin-bottom:16px; }
.card { background:var(--card); border:1px solid var(--line); border-radius:10px; padding:14px; }
.card .n { font-size:24px; font-weight:600; }
.card .l { color:var(--muted); font-size:13px; }
table { width:100%; border-collapse:collapse; background:var(--card); border:1px solid var(--line); border-radius:10px; overflow:hidden; font-size:14px; }
th, td { padding:8px 10px; border-bottom:1px solid var(--line); text-align:left; vertical-align:top; }
th { background:var(--bg); font-weight:600; position:sticky; top:0; }
td.num, th.num { text-align:right; white-space:nowrap; }
.wrap { overflow-x:auto; max-height:70vh; border-radius:10px; }
.controls { display:flex; gap:8px; flex-wrap:wrap; margin-bottom:12px; }
input, select { padding:8px 10px; border:1px solid var(--line); border-radius:8px; background:var(--card); color:var(--ink); font:inherit; }
input { min-width:240px; }
.proj { background:var(--card); border:1px solid var(--line); border-radius:10px; padding:16px; margin-bottom:14px; }
.proj h3 { margin:0 0 6px; font-size:18px; }
.tag { display:inline-block; font-size:12px; padding:2px 8px; border-radius:999px; border:1px solid var(--line); color:var(--muted); margin:2px 4px 2px 0; }
.ok { color:var(--ok); } .warn { color:var(--warn); }
.desc { white-space:pre-wrap; margin:10px 0; }
ul { margin:6px 0; padding-left:20px; }
a { color:var(--accent); }
.gallery { display:flex; gap:6px; overflow-x:auto; padding:6px 0; }
.gallery img { height:90px; border-radius:6px; border:1px solid var(--line); }
.hidden { display:none; }
.small { font-size:13px; color:var(--muted); }
</style>
</head>
<body>
<header>
  <h1>ГК ПСК: данные API</h1>
  <div class="meta" id="gen"></div>
  <nav id="tabs">
    <button data-tab="overview" class="active">Наличие</button>
    <button data-tab="projects">Проекты</button>
    <button data-tab="marketing">Маркетинг</button>
    <button data-tab="flats">Лоты</button>
    <button data-tab="files">Файлы</button>
  </nav>
</header>
<main>
  <section id="overview"></section>
  <section id="projects" class="hidden"></section>
  <section id="marketing" class="hidden"></section>
  <section id="flats" class="hidden"></section>
  <section id="files" class="hidden"></section>
</main>
<script>
const DATA = __DATA__;

const $ = (s) => document.querySelector(s);
const el = (tag, attrs = {}, ...kids) => {
  const n = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (k === "class") n.className = v;
    else if (k === "href") n.href = v;
    else if (k === "src") n.src = v;
    else n.setAttribute(k, v);
  }
  for (const k of kids.flat()) {
    if (k === null || k === undefined || k === false) continue;
    n.append(k instanceof Node ? k : document.createTextNode(String(k)));
  }
  return n;
};
const rub = (v) => (v === null || v === undefined || v === "" || isNaN(+v)) ? "—" : Math.round(+v).toLocaleString("ru-RU") + " ₽";
const num = (v) => (v === null || v === undefined || v === "") ? "—" : (+v).toLocaleString("ru-RU");
const val = (x) => (x && typeof x === "object" && "value" in x) ? x.value : x;
const pct = (a, b) => b ? Math.round(1000 * a / b) / 10 : 0;

// ---- шапка и вкладки ----
$("#gen").textContent = "Данные на " + new Date(DATA.generated).toLocaleString("ru-RU") + " · источник: psk-info.ru и ручные карточки проектов";
document.querySelectorAll("#tabs button").forEach((b) => b.onclick = () => {
  document.querySelectorAll("#tabs button").forEach((x) => x.classList.toggle("active", x === b));
  document.querySelectorAll("main > section").forEach((s) => s.classList.toggle("hidden", s.id !== b.dataset.tab));
});

// ---- Наличие ----
function renderOverview() {
  const av = DATA.availability, t = av.totals;
  const cards = el("div", { class: "grid" },
    el("div", { class: "card" }, el("div", { class: "n" }, num(t.total)), el("div", { class: "l" }, "всего лотов")),
    el("div", { class: "card" }, el("div", { class: "n ok" }, num(t.free)), el("div", { class: "l" }, "в активной продаже (" + pct(t.free, t.total) + "%)")),
    el("div", { class: "card" }, el("div", { class: "n warn" }, num(t.reserved)), el("div", { class: "l" }, "в броне (" + pct(t.reserved, t.total) + "%)")),
    el("div", { class: "card" }, el("div", { class: "n" }, num(Object.keys(av.projects).length)), el("div", { class: "l" }, "проектов"))
  );
  const rows = Object.entries(av.projects).map(([slug, p]) =>
    el("tr", {},
      el("td", {}, p.project_name || slug, el("div", { class: "small" }, slug)),
      el("td", { class: "num" }, num(p.total)),
      el("td", { class: "num ok" }, num(p.free)),
      el("td", { class: "num warn" }, num(p.reserved)),
      el("td", { class: "num" }, p.free_share_pct + "%"),
      el("td", { class: "num" }, rub(p.free_min_price))
    ));
  const table = el("div", { class: "wrap" }, el("table", {},
    el("thead", {}, el("tr", {},
      el("th", {}, "Проект"), el("th", { class: "num" }, "Всего"), el("th", { class: "num" }, "Свободно"),
      el("th", { class: "num" }, "Бронь"), el("th", { class: "num" }, "Доля свободных"), el("th", { class: "num" }, "Мин. цена свободного"))),
    el("tbody", {}, rows)));
  $("#overview").replaceChildren(
    el("p", { class: "small" }, "Срез на " + new Date(av.generated_at).toLocaleString("ru-RU") + ". Свободно = статус «Свободно», в броне = «Бронь»."),
    cards, table);
}

// ---- Проекты ----
function renderProjects() {
  const projects = DATA.projects.projects || [];
  const av = DATA.availability.projects;
  const blocks = projects.map((p) => {
    const a = av[p.slug] || {};
    const mort = p.mortgage && p.mortgage.monthly_payment_example;
    return el("div", { class: "proj" },
      el("h3", {}, p.name || p.slug),
      el("div", {},
        el("span", { class: "tag" }, p.project_class || "класс —"),
        el("span", { class: "tag" }, val(p.status) && (p.status.value || p.status)),
        el("span", { class: "tag" }, "сдача: " + (p.commissioning ? val(p.commissioning) : "—"))),
      el("p", {}, "Адрес: ", val(p.address) || "—"),
      el("p", {}, "Метро: ", val(p.metro) || "—", p.metro && p.metro.walk_min ? " (" + p.metro.walk_min + " мин пешком)" : ""),
      el("p", {}, "Минимальная цена: ", el("b", {}, rub(val(p.min_price))), el("span", { class: "small" }, "  статус: " + ((p.min_price && p.min_price.status) || "—"))),
      el("p", {}, "Наличие: свободно ", el("b", { class: "ok" }, num(a.free)), ", в броне ", el("b", { class: "warn" }, num(a.reserved)), " из ", num(a.total)),
      el("p", {}, "Ипотека, минимальный платёж (свободные лоты): ", mort ? rub(mort) : "не подтверждено", el("span", { class: "small" }, "  статус: " + ((p.mortgage && p.mortgage.status) || "—"))),
      p.landing_url ? el("p", {}, "Лендинг: ", el("a", { href: p.landing_url, target: "_blank" }, p.landing_url)) : null,
      (p.data_conflicts && p.data_conflicts.length) ? el("p", { class: "warn" }, "Открытые вопросы: " + p.data_conflicts.map((c) => c.field).join(", ")) : null
    );
  });
  $("#projects").replaceChildren(
    el("p", { class: "small" }, "Карточки из projects/. Поля с пометкой «не подтверждено» нельзя использовать без проверки."),
    ...blocks);
}

// ---- Маркетинг ----
function renderMarketing() {
  const items = Object.values(DATA.marketing.projects || {});
  const blocks = items.map((p) => {
    const photos = (p.media && p.media.photos) || [];
    const videos = (p.media && p.media.videos) || [];
    return el("div", { class: "proj" },
      el("h3", {}, p.name || p.slug),
      el("div", { class: "small" }, p.address || "", p.min_price ? " · от " + rub(p.min_price) : ""),
      el("div", { class: "desc" }, p.description || "Описание не заполнено"),
      p.usps && p.usps.length ? el("div", {}, el("b", {}, "УТП"), el("ul", {}, p.usps.map((u) => el("li", {}, u.title ? u.title + (u.text ? ": " + u.text : "") : u.text)))) : null,
      p.advantages && p.advantages.length ? el("div", {}, el("b", {}, "Преимущества"), el("ul", {}, p.advantages.map((a) => el("li", {}, a.name ? a.name + (a.text ? " — " + a.text : "") : a.text)))) : null,
      el("div", {}, el("b", {}, "Видео: "), videos.length ? videos.map((v) => el("div", {}, el("a", { href: v, target: "_blank" }, v))) : el("span", { class: "small" }, "нет")),
      el("div", {}, el("b", {}, "Фото: "), photos.length + " шт.", photos.length ? el("div", { class: "gallery" }, photos.slice(0, 12).map((u) => el("a", { href: u, target: "_blank" }, el("img", { src: u, loading: "lazy", alt: "" })))) : null),
      p.virtual_tour_url ? el("p", {}, "Виртуальный тур: ", el("a", { href: p.virtual_tour_url, target: "_blank" }, p.virtual_tour_url)) : null
    );
  });
  $("#marketing").replaceChildren(
    el("p", { class: "small" }, "Данные из карточек psk-info.ru. Перед использованием в рекламе сверяйте с действующим лендингом и отделом маркетинга."),
    ...blocks);
}

// ---- Лоты ----
function renderFlats() {
  const flats = DATA.flats.flats || [];
  const projects = [...new Set(flats.map((f) => f.project_slug))].sort();
  const search = el("input", { type: "search", placeholder: "Номер, проект, отделка…" });
  const status = el("select", {}, el("option", { value: "" }, "Все статусы"), el("option", { value: "Свободно" }, "Свободно"), el("option", { value: "Бронь" }, "Бронь"));
  const proj = el("select", {}, el("option", { value: "" }, "Все проекты"), projects.map((s) => el("option", { value: s }, s)));
  const count = el("span", { class: "small" });
  const body = el("tbody");
  const LIMIT = 500;
  function draw() {
    const q = search.value.trim().toLowerCase(), st = status.value, pr = proj.value;
    const list = flats.filter((f) =>
      (!st || f.status === st) && (!pr || f.project_slug === pr) &&
      (!q || [f.number, f.project_name, f.project_slug, f.finishing].some((x) => String(x || "").toLowerCase().includes(q))));
    count.textContent = "Найдено: " + num(list.length) + (list.length > LIMIT ? " (показаны первые " + LIMIT + ")" : "");
    body.replaceChildren(...list.slice(0, LIMIT).map((f) => el("tr", {},
      el("td", {}, f.number, el("div", { class: "small" }, f.project_slug)),
      el("td", { class: "num" }, f.rooms === 0 ? "студия" : num(f.rooms)),
      el("td", { class: "num" }, f.area ? f.area + " м²" : "—"),
      el("td", { class: "num" }, (f.floor || "—") + "/" + (f.max_floor || "—")),
      el("td", { class: f.status === "Свободно" ? "ok" : "warn" }, f.status),
      el("td", { class: "num" }, rub(f.price)),
      el("td", { class: "num" }, rub(f.dvizh_min_mortgage)),
      el("td", {}, f.finishing || "—"))));
  }
  [search, status, proj].forEach((c) => c.addEventListener(c.tagName === "INPUT" ? "input" : "change", draw));
  $("#flats").replaceChildren(
    el("div", { class: "controls" }, search, status, proj, count),
    el("div", { class: "wrap" }, el("table", {},
      el("thead", {}, el("tr", {},
        el("th", {}, "Лот"), el("th", { class: "num" }, "Комнат"), el("th", { class: "num" }, "Площадь"),
        el("th", { class: "num" }, "Этаж"), el("th", {}, "Статус"), el("th", { class: "num" }, "Цена"),
        el("th", { class: "num" }, "Ипотека, мес."), el("th", {}, "Отделка"))), body)));
  draw();
}

// ---- Файлы ----
function renderFiles() {
  const idx = DATA.index;
  $("#files").replaceChildren(
    el("p", { class: "small" }, "Репозиторий: ", el("a", { href: idx.repository, target: "_blank" }, idx.repository)),
    el("p", { class: "small" }, "Все файлы публичные. Ссылки ниже ведут на актуальные версии в ветке main."),
    el("table", {},
      el("thead", {}, el("tr", {}, el("th", {}, "Файл"), el("th", {}, "Что внутри"), el("th", {}, "Обновлён"), el("th", {}, "Ссылка"))),
      el("tbody", {}, idx.files.map((f) => el("tr", {},
        el("td", {}, el("code", {}, f.file)),
        el("td", {}, f.title + ". " + f.description),
        el("td", {}, f.generated_at ? new Date(f.generated_at).toLocaleString("ru-RU") : "—"),
        el("td", {}, el("a", { href: f.url, target: "_blank" }, "raw")))))));
}

renderOverview(); renderProjects(); renderMarketing(); renderFlats(); renderFiles();
</script>
</body>
</html>
"""


def read(name):
    return json.loads((API / name).read_text(encoding="utf-8"))


def main():
    bundle = {"generated": datetime.now(timezone.utc).isoformat(timespec="seconds")}
    keys = {"projects.json": "projects", "marketing.json": "marketing",
            "flats.json": "flats", "availability.json": "availability", "index.json": "index"}
    for f in FILES:
        bundle[keys[f]] = read(f)
    # безопасная вставка JSON в <script>: экранируем «</» и «<!--»
    data = json.dumps(bundle, ensure_ascii=False).replace("</", "<\\/").replace("<!--", "<\\!--")
    OUT.write_text(TEMPLATE.replace("__DATA__", data), encoding="utf-8")
    print(f"Страница собрана: {OUT} ({OUT.stat().st_size // 1024} КБ)")


if __name__ == "__main__":
    main()
