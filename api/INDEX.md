# Индекс данных API ГК ПСК

Обновлено: 2026-10-23T05:21:05+00:00
Репозиторий: https://github.com/stasfactoryads-cloud/psk-official-data

| Файл | Что внутри | Ссылка | Обновлено |
|---|---|---|---|
| `projects.json` | Проекты: цены, ипотека, рассрочка, статусы. Структурные данные по проектам с источником и статусом проверки каждого поля. Ручные правки отдела продаж — в manual_overrides. | [raw](https://raw.githubusercontent.com/stasfactoryads-cloud/psk-official-data/main/api/projects.json) | 2026-10-23T05:21:05+00:00 |
| `marketing.json` | Маркетинг: описания, УТП, фото и видео. Текст о проекте, преимущества, инфраструктура, прямые ссылки на фото (media.photos) и видео (media.videos). | [raw](https://raw.githubusercontent.com/stasfactoryads-cloud/psk-official-data/main/api/marketing.json) | 2026-10-23T05:20:39+00:00 |
| `flats.json` | Каталог лотов: все квартиры. Все квартиры по всем проектам: цена, площадь, этаж, статус, ипотечный платёж, планировка. | [raw](https://raw.githubusercontent.com/stasfactoryads-cloud/psk-official-data/main/api/flats.json) | 2026-10-23T05:20:17+00:00 |
| `availability.json` | Срез наличия: в продаже и в броне. Свободно и в броне по каждому проекту и по каталогу в целом, минимальная цена свободного лота. | [raw](https://raw.githubusercontent.com/stasfactoryads-cloud/psk-official-data/main/api/availability.json) | 2026-10-23T05:20:17+00:00 |
| `conditions.json` | Условия продаж: акции, рассрочка, ипотека, коммерция, машиноместа. Условия по каждому проекту из ежемесячных файлов. Файл считается актуальным, если загружен не раньше 6-го числа текущего месяца. | [raw](https://raw.githubusercontent.com/stasfactoryads-cloud/psk-official-data/main/api/conditions.json) | 2026-10-21T09:35:59+00:00 |
| `landings.json` | Лендинги: посадочные страницы проектов. Все посадочные страницы по проектам, ссылки проверены запросом (HTTP-статус). Обновляется ежедневно. | [raw](https://raw.githubusercontent.com/stasfactoryads-cloud/psk-official-data/main/api/landings.json) | 2026-10-23T05:21:05+00:00 |

Все файлы публичные и читаются без авторизации.
