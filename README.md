# Elvane — лендинг

Сайт приложения Elvane для домена [elvane.cloud](https://elvane.cloud). Vue 3 + Vite, анимации — GSAP
(ScrollTrigger, SplitText) и Lenis. Цвета, шрифты и знак — из дизайн-системы приложения
(`elvane_app/Packages/DesignSystem`): Glacier, Pine, Lake, Summit, Onest и Martian Mono.

## Запуск

```bash
npm install
npm run dev        # http://localhost:5173
npm run build      # статика в dist/ — её и выкладываем на elvane.cloud
npm run preview
```

## Идея

Страница — это подъём. Сверху вы стоите у начала тропы (1 717 м), каждая секция — отметка на пути,
внизу — вершина Большого Чимгана (3 309 м). Высоту показывает альтиметр у левого края
(на телефоне — в шапке).

Рельеф настоящий: горизонтали в первом экране и на карте маршрута строятся в браузере из сетки высот,
вырезанной из пакета региона «Западный Тянь-Шань», а маршрут — кратчайший путь по тому же графу троп,
по которому маршруты строит приложение.

## Устройство

```
index.html
src/
  main.js                 точка входа, директивы v-split и v-reveal
  App.vue                 интро, загрузка рельефа и шрифтов, порядок секций
  config.js               ссылки (App Store, бот) и высоты начала и конца
  components/
    HeroSection.vue       карта-герой: горизонталь под курсором, высота и координаты
    ManifestSection.vue   текст, который загорается по словам; «один инструмент вместо…»
    ForecastSection.vue   высотный ползунок по силуэту склона и лента окон на 7 дней
    RouteSection.vue      офлайн-карта: маршрут, точки по пути, профиль высот
    SafetySection.vue     кольцо контрольного срока и SOS
    WhoSection.vue        для кого: альпинисты, хайкеры, рыбаки, охотники, лыжники
    CoverSection.vue      регионы и числа
    SummitSection.vue     вершина: кнопки и подвал
    SiteHeader.vue, AltimeterRail.vue, MarkLabel.vue, RollingNumber.vue, BrandMark.vue
  composables/
    motion.js             GSAP, ScrollTrigger, Lenis, общие появления
    altitude.js           высота страницы по прокрутке
  lib/
    terrain.js            сетка высот → горизонтали (d3-contour), отмывка рельефа
    topo.js               карта на canvas в светлом и тёмном стиле
    format.js             числа как в приложении: 3 309 м, −6°
  i18n/                   ru.js, en.js — тексты; язык выбирается как в приложении
  data/                   маршрут, силуэт, точки, регионы — собираются скриптом
public/data/terrain.bin   сетка высот (uint16, метры)
scripts/build-data.py     сборка данных из репозитория бэкенда
```

## Данные

`npm run data` (нужны Python 3 с numpy и Pillow и собранные пакеты карт в
`../elvane_backend/tools/tiles/out`) пересобирает `public/data/terrain.bin` и `src/data/*.json`:
рельеф и маршрут на Большой Чимган, силуэт для ползунка, точки вокруг маршрута, регионы и их размеры.
Результат лежит в репозитории — для сборки сайта бэкенд не нужен.

## Что настроить перед запуском

- `src/config.js`: `STORE_URL` — ссылка на App Store (пока `null`, кнопки пишут «Скоро в App Store»);
  `BOT_URL` — бот в Telegram.
- Картинку для соцсетей (`og:image`) — положить в `public/` и добавить тег в `index.html`.

## Языки

Русский и английский. По умолчанию — русский для ru и языков СНГ, английский для остальных; выбор
запоминается, `?lang=en` открывает нужный язык по ссылке.
