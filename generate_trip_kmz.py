# -*- coding: utf-8 -*-
"""
Generate an enriched KMZ for the trip 28.07-25.08.2026.

Sources:
 - справочник_мест_2026.md / аудит_маршрут_2026.md / пошаговый_гид_2026.md (the plan itself)
 - Паттайя.kmz (MapsMe/TravelAsk export) - 90 curated points with descriptions
 - Web research (TravelAsk, VietnamSpot, Nomado, TripChina, EastChinaTrip, etc.)
   for Bangkok / Da Nang / Ho Chi Minh City / Shanghai / Beijing

Categories (consistent color across all cities):
 - must_see      red     - главные достопримечательности
 - food          green   - рестораны, кафе, стритфуд
 - shopping      yellow  - рынки, ТЦ
 - viewpoint     brown   - смотровые площадки / фотогеничные места
 - nature        cyan    - пляжи, острова, парки, природа
 - entertainment purple  - шоу, зоопарки, музеи, спа, аттракционы
 - base          (white pin / house icon) - отели/базы
 - transport     (gray / plane icon) - аэропорты, вокзалы

Importance is encoded as a 1-3 star prefix in the name AND icon scale:
 3 = ★★★ обязательно к посещению
 2 = ★★  стоит сходить, если есть время
 1 = ★   опционально / нишевое
"""
import json
import re
import zipfile
from pathlib import Path
from xml.sax.saxutils import escape

BASE_DIR = Path(__file__).parent
OUTPUT_DIR = BASE_DIR / "маршрут_2026_maps_me"
PATTAYA_JSON = BASE_DIR / "pattaya_points.json"

STARS = {3: "★★★ ", 2: "★★ ", 1: "★ "}

# Maps.me/Organic Maps only reliably recognise their OWN named pin styles
# (id="placemark-<color>", icon href on maps.me/placemarks/*.png, NO <color>
# override, NO custom scale). Anything else (custom style ids, google paddle
# icons, inline <Style> overrides) makes the app reject the whole file as
# invalid. So every category maps to one of the 16 built-in color names below
# - never invent a new style id.
CATEGORY_MAPSME_COLOR = {
    "must_see": "red",
    "food": "green",
    "shopping": "yellow",
    "viewpoint": "brown",
    "nature": "lightblue",
    "entertainment": "purple",
    "base": "pink",
    "transport": "gray",
}

# Exact <Document> header copied BYTE-FOR-BYTE from the working Паттайя.kmz
# (MAPS.ME's own export), with the city name swapped via a plain token
# replace (__CITY__). Confirmed by isolation testing:
#   - a hand-rebuilt header (even visually identical) made MAPS.ME reject
#     the file outright, while this literal template always works;
#   - EVERY <Placemark> must also carry its OWN <TimeStamp> + per-placemark
#     <ExtendedData xmlns:mwm="https://maps.me"> block (mwm:name/description/
#     scale/visibility) - a document with only "simple" placemarks (no
#     TimeStamp/ExtendedData) was rejected even with this exact header.
# Do not reformat/re-indent this block - treat it as an opaque byte blob.
HEADER_TEMPLATE = """<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://earth.google.com/kml/2.2">
<Document>
  <Style id="placemark-red">
    <IconStyle>
      <Icon>
        <href>http://maps.me/placemarks/placemark-red.png</href>
      </Icon>
    </IconStyle>
  </Style>
  <Style id="placemark-blue">
    <IconStyle>
      <Icon>
        <href>http://maps.me/placemarks/placemark-blue.png</href>
      </Icon>
    </IconStyle>
  </Style>
  <Style id="placemark-purple">
    <IconStyle>
      <Icon>
        <href>http://maps.me/placemarks/placemark-purple.png</href>
      </Icon>
    </IconStyle>
  </Style>
  <Style id="placemark-yellow">
    <IconStyle>
      <Icon>
        <href>http://maps.me/placemarks/placemark-yellow.png</href>
      </Icon>
    </IconStyle>
  </Style>
  <Style id="placemark-pink">
    <IconStyle>
      <Icon>
        <href>http://maps.me/placemarks/placemark-pink.png</href>
      </Icon>
    </IconStyle>
  </Style>
  <Style id="placemark-brown">
    <IconStyle>
      <Icon>
        <href>http://maps.me/placemarks/placemark-brown.png</href>
      </Icon>
    </IconStyle>
  </Style>
  <Style id="placemark-green">
    <IconStyle>
      <Icon>
        <href>http://maps.me/placemarks/placemark-green.png</href>
      </Icon>
    </IconStyle>
  </Style>
  <Style id="placemark-orange">
    <IconStyle>
      <Icon>
        <href>http://maps.me/placemarks/placemark-orange.png</href>
      </Icon>
    </IconStyle>
  </Style>
  <Style id="placemark-deeppurple">
    <IconStyle>
      <Icon>
        <href>http://maps.me/placemarks/placemark-deeppurple.png</href>
      </Icon>
    </IconStyle>
  </Style>
  <Style id="placemark-lightblue">
    <IconStyle>
      <Icon>
        <href>http://maps.me/placemarks/placemark-lightblue.png</href>
      </Icon>
    </IconStyle>
  </Style>
  <Style id="placemark-cyan">
    <IconStyle>
      <Icon>
        <href>http://maps.me/placemarks/placemark-cyan.png</href>
      </Icon>
    </IconStyle>
  </Style>
  <Style id="placemark-teal">
    <IconStyle>
      <Icon>
        <href>http://maps.me/placemarks/placemark-teal.png</href>
      </Icon>
    </IconStyle>
  </Style>
  <Style id="placemark-lime">
    <IconStyle>
      <Icon>
        <href>http://maps.me/placemarks/placemark-lime.png</href>
      </Icon>
    </IconStyle>
  </Style>
  <Style id="placemark-deeporange">
    <IconStyle>
      <Icon>
        <href>http://maps.me/placemarks/placemark-deeporange.png</href>
      </Icon>
    </IconStyle>
  </Style>
  <Style id="placemark-gray">
    <IconStyle>
      <Icon>
        <href>http://maps.me/placemarks/placemark-gray.png</href>
      </Icon>
    </IconStyle>
  </Style>
  <Style id="placemark-bluegray">
    <IconStyle>
      <Icon>
        <href>http://maps.me/placemarks/placemark-bluegray.png</href>
      </Icon>
    </IconStyle>
  </Style>
  <name>__CITY__</name>
  <visibility>1</visibility>
  <ExtendedData xmlns:mwm="https://maps.me">
    <mwm:name>
      <mwm:lang code="default">__CITY__</mwm:lang>
    </mwm:name>
    <mwm:annotation>
    </mwm:annotation>
    <mwm:description>
    </mwm:description>
    <mwm:lastModified>2024-02-21T10:02:57.378Z</mwm:lastModified>
    <mwm:accessRules>Local</mwm:accessRules>
  </ExtendedData>
  """

TAIL_TEMPLATE = """
</Document>
</kml>
"""

TIMESTAMP = "2026-07-02T00:00:00.000Z"

CATEGORY_LABEL = {
    "must_see": "Must-see",
    "food": "Где поесть",
    "shopping": "Шопинг и рынки",
    "viewpoint": "Смотровые / фото",
    "nature": "Пляжи и природа",
    "entertainment": "Развлечения",
    "base": "Отели (база)",
    "transport": "Аэропорты / перелёты",
}

CITY_ORDER = ["Перелёты", "Паттайя", "Бангкок", "Да Нанг", "Хошимин", "Шанхай", "Пекин"]
CATEGORY_ORDER = ["base", "must_see", "food", "shopping", "viewpoint", "nature", "entertainment", "transport"]


# ---------------------------------------------------------------------------
# 1. Точки уже включённые в план (отели, ключевые объекты маршрута)
# ---------------------------------------------------------------------------
PLAN_POINTS = [
    # --- Перелёты ---
    ("Красноярск (KJA)", 56.1729, 92.4933, "Вылет 28.07 SU6637", "Перелёты", "transport", 3),
    ("Гуанчжоу (CAN)", 23.3924, 113.2988, "Транзит/стыковка 29.07", "Перелёты", "transport", 2),
    ("Бангкок, Суварнабхуми (BKK)", 13.6900, 100.7501, "Прилёт 29.07, вылет 07.08", "Перелёты", "transport", 3),
    ("Дананг (DAD)", 16.0439, 108.1994, "Прилёт 07.08, вылет 14.08", "Перелёты", "transport", 3),
    ("Хошимин (SGN)", 10.8188, 106.6520, "Прилёт/вылет Хошимин", "Перелёты", "transport", 3),
    ("Шанхай, Пудун (PVG)", 31.1443, 121.8083, "Прилёт 17.08, вылет 21.08", "Перелёты", "transport", 3),
    ("Пекин (PEK)", 40.0799, 116.6031, "Прилёт 21.08, вылет 23.08", "Перелёты", "transport", 3),
    ("Иркутск (IKT)", 52.2680, 104.3889, "Стыковка на обратном пути", "Перелёты", "transport", 2),

    # --- Паттайя: только база (сами достопримечательности идут из pattaya_points.json) ---
    ("Hotel Zing (база, Джомтьен)", 12.8863, 100.8731, "Отель 29.07–05.08 · zingpattaya.com", "Паттайя", "base", 3),

    # --- Бангкок ---
    ("12 The Residence DMK (база)", 13.9204, 100.6038, "Отель у аэропорта Don Mueang, 05–07.08", "Бангкок", "base", 3),
    ("Wat Pho", 13.7465, 100.4930, "✅ В плане. Храм Лежащего Будды, 46-метровая золотая статуя, родина тайского массажа. Вход ~200 ฿.", "Бангкок", "must_see", 3),
    ("Wat Arun", 13.7437, 100.4885, "✅ В плане. Храм Рассвета на западном берегу Чао Прайя, паром 4 ฿ с Tha Tien. Вход ~100 ฿.", "Бангкок", "must_see", 3),
    ("Iconsiam", 13.7266, 100.5103, "✅ В плане. Премиальный молл на набережной, фонтаны, вид на реку, must вечером.", "Бангкок", "shopping", 2),
    ("Чайнатаун (Yaowarat)", 13.7395, 100.5132, "✅ В плане. Неон, стритфуд, золотые лавки. Метро Wat Mangkon.", "Бангкок", "food", 3),
    ("Siam Paragon", 13.7462, 100.5348, "✅ В плане. Люкс-молл у BTS Siam, Siam Ocean World в подвале.", "Бангкок", "shopping", 2),
    ("Platinum Fashion Mall (Pratunam)", 13.7489, 100.5416, "✅ В плане. Оптово-розничный шопинг одеждой, дешево.", "Бангкок", "shopping", 2),

    # --- Да Нанг ---
    ("Отель в Да Нанге (база)", 16.0615, 108.2276, "7 ночей 07–14.08, все активности Grab 10–40 мин", "Да Нанг", "base", 3),
    ("Набережная Han River", 16.0615, 108.2276, "✅ В плане. Первый вечер, мосты, подсветка, кафе.", "Да Нанг", "must_see", 2),
    ("Marble Mountains", 15.9799, 108.0975, "✅ В плане. 5 известняковых холмов, пещеры, святилища, лестницы. 2-3 часа.", "Да Нанг", "must_see", 3),
    ("Пляж My Khe", 16.0471, 108.2486, "✅ В плане. Главный городской пляж, серф-школы.", "Да Нанг", "nature", 3),
    ("Lady Buddha (Linh Ung)", 16.1118, 108.2852, "✅ В плане. 67-метровая статуя на Son Tra, лучшая панорама бухты, обезьяны на дороге.", "Да Нанг", "must_see", 3),
    ("Мост Дракона (Dragon Bridge)", 16.0610, 108.2278, "✅ В плане. Шоу огня/воды по выходным ~21:00. Дата в гиде — 09.08 (вс).", "Да Нанг", "must_see", 3),
    ("Golden Bridge (Ba Na Hills)", 15.9953, 107.9786, "✅ В плане. «Руки богов», рекордная канатка, франц. деревня. В августе часто туман.", "Да Нанг", "must_see", 3),
    ("Музей чамской скульптуры", 16.0601, 108.2207, "✅ В плане. Единственный музей скульптуры Чампов. 1–1.5 ч.", "Да Нанг", "must_see", 2),
    ("Рынок Con (Chợ Cồn)", 16.0667, 108.2142, "✅ В плане. Местный крытый рынок, мало туристов.", "Да Нанг", "shopping", 2),

    # --- Хошимин ---
    ("K'ool Hotels (база)", 10.7870, 106.5930, "453–455 Hương Lộ 3, Bình Hưng Hòa, 14–16.08", "Хошимин", "base", 3),
    ("Bao's Niche", 10.8058, 106.7628, "✅ В плане. 215 Tây Hoà, Thủ Đức — нишевая парфюмерия, главная цель шопинга.", "Хошимин", "shopping", 3),
    ("Buu Long Pagoda", 10.7867, 106.8375, "✅ В плане. Тайский стиль, озеро, фотогенично. 11:00–14:00 внутрь не пускают.", "Хошимин", "must_see", 2),
    ("Phuoc Long Pagoda", 10.7870, 106.8470, "✅ В плане. Храм на острове, паром, ~800 м от Buu Long.", "Хошимин", "must_see", 2),
    ("Собор Нотр-Дам + Central Post Office", 10.7798, 106.6990, "✅ В плане. Классическая открытка District 1.", "Хошимин", "must_see", 3),
    ("Рынок Ben Thanh", 10.7724, 106.6980, "✅ В плане. Главный туристический рынок, торг уместен.", "Хошимин", "shopping", 3),
    ("Nguyen Hue Walking Street", 10.7739, 106.7044, "✅ В плане. Пешеходный бульвар, фонтаны, вечерняя прогулка.", "Хошимин", "must_see", 2),
    ("Cu Chi Tunnels", 11.1527, 106.4944, "✅ В плане. Подземные туннели войны, полдня с трансфером.", "Хошимин", "must_see", 2),

    # --- Шанхай ---
    ("Country Inn & Suites (база)", 31.2507, 121.4569, "У вокзала Shanghai Railway Station, 17–20.08", "Шанхай", "base", 3),
    ("The Louis (корабль LV)", 31.2262, 121.4494, "✅ В плане. HKRI Taikoo Hui, West Nanjing Rd. Бронь через WeChat (My LV).", "Шанхай", "must_see", 3),
    ("Maison Margiela Cafe (JC Plaza)", 31.2309, 121.4566, "✅ В плане. Кафе и бутик Margiela, рядом с The Louis.", "Шанхай", "food", 3),
    ("Shanghai Disneyland", 31.1433, 121.6570, "✅ В плане. Целый день, билет заранее ~599–719 ¥.", "Шанхай", "entertainment", 3),
    ("The Bund (Бунд)", 31.2407, 121.4906, "✅ В плане. Главный вид Шанхая, лучше на закате.", "Шанхай", "must_see", 3),
    ("Сад Юй (Yu Garden)", 31.2272, 121.4933, "✅ В плане. Классический сад Ming-style + старый город. Вход ~50 ¥.", "Шанхай", "must_see", 3),
    ("Луцзяцзуй (Lujiazui)", 31.2396, 121.4999, "✅ В плане. Небоскрёбы, смотровые площадки ~150–200 ¥.", "Шанхай", "viewpoint", 2),
    ("Тяньцзыфан (Tianzifang)", 31.2096, 121.4696, "✅ В плане. Переулки shikumen, кафе, галереи, вечер после Пудуна.", "Шанхай", "shopping", 2),

    # --- Пекин ---
    ("Huitong Jiufang (база)", 39.9012, 116.3668, "汇通九方宾馆, м. Changchun Jie, линия 2, 21–23.08", "Пекин", "base", 3),
    ("Qianmen + Dashilan", 39.8988, 116.3974, "✅ В плане. Старые торговые улицы, утка по-пекински, чай.", "Пекин", "must_see", 2),
    ("Храм Неба (Temple of Heaven)", 39.8822, 116.4066, "✅ В плане. Императорский комплекс, эхо-доска. ~34 ¥.", "Пекин", "must_see", 3),
    ("Площадь Тяньаньмэнь", 39.9042, 116.3976, "✅ В плане. Крупнейшая площадь мира, паспорт на вход.", "Пекин", "must_see", 3),
    ("Wangfujing", 39.9145, 116.4106, "✅ В плане. Главная торговая улица, ТЦ APM, странный стритфуд.", "Пекин", "shopping", 2),
    ("Lama Temple (Yonghegong)", 39.9475, 116.4111, "✅ В плане. Тибетский буддийский храм, сандаловый Будда. ~25 ¥.", "Пекин", "must_see", 2),
    ("Летний дворец (Summer Palace)", 39.9999, 116.2755, "✅ В плане. Озеро Куньминху, Long Corridor, Marble Boat. ~30 ¥.", "Пекин", "must_see", 3),
    ("798 Art District", 39.9842, 116.4955, "✅ В плане. Бывшие заводы → галереи, стрит-арт.", "Пекин", "entertainment", 2),
    ("Xidan", 39.9078, 116.3724, "✅ В плане. Торговый район у отеля, запасной план при дожде.", "Пекин", "shopping", 2),
    ("Houhai", 39.9375, 116.3838, "✅ В плане. Озёра и хутуны, бары, лодки, старый Пекин вечером.", "Пекин", "must_see", 2),
]


# ---------------------------------------------------------------------------
# 2. Дополнительные точки для Бангкока (must-see / еда / шопинг / вид)
# ---------------------------------------------------------------------------
BANGKOK_EXTRA = [
    ("Grand Palace", 13.7500, 100.4913, "Королевский дворец — национальная гордость, вместе с Wat Phra Kaew можно провести целый день.", "must_see", 3),
    ("Wat Phra Kaew (Храм Изумрудного Будды)", 13.7515, 100.4927, "Статуя Будды из цельного куска жада, на территории Grand Palace.", "must_see", 3),
    ("Wat Saket (Золотая гора)", 13.7540, 100.5069, "Храм на искусственном холме, панорама старого города со ступы.", "must_see", 2),
    ("Wat Traimit (Храм Золотого Будды)", 13.7398, 100.5140, "Статуя Будды из чистого золота (~5.5 тонн), у входа в Chinatown.", "must_see", 2),
    ("Lumpini Park", 13.7307, 100.5418, "«Центральный парк» Бангкока — оазис зелени, водоёмы, вело-дорожки, варано-мониторы.", "nature", 2),
    ("Erawan Shrine", 13.7444, 100.5406, "Индуистский храм Тао Маха Брахма среди небоскрёбов у Chit Lom, постоянные ритуальные танцы.", "must_see", 2),
    ("Jim Thompson House", 13.7502, 100.5283, "Дом-музей американского предпринимателя, коллекция тайского искусства и шёлка в саду.", "must_see", 1),
    ("Jay Fai", 13.7539, 100.5008, "Мишленовский стритфуд — крабовый омлет от «тётушки в очках». Очереди, ценник ~1000 ฿.", "food", 2),
    ("Go Ang Kaomunkai (Chinatown)", 13.7398, 100.5127, "Легендарный куриный рис за ~60 ฿ в Chinatown.", "food", 2),
    ("Sky Bar Lebua (Sirocco)", 13.7203, 100.5145, "Руфтоп-бар с 64 этажа — вид из «Мальчишника в Вегасе 2». Коктейль ~1200 ฿.", "viewpoint", 2),
    ("Vertigo, Banyan Tree", 13.7229, 100.5417, "Панорамный бар на 61 этаже, более камерный чем Sirocco. Коктейль ~600 ฿.", "viewpoint", 1),
    ("Baiyoke Sky Hotel (смотровая)", 13.7527, 100.5401, "Смотровая площадка на одном из самых высоких зданий Бангкока, вид на весь город.", "viewpoint", 2),
    ("MahaNakhon SkyWalk", 13.7239, 100.5292, "Стеклянная смотровая площадка на крыше небоскрёба MahaNakhon.", "viewpoint", 2),
    ("Chatuchak Weekend Market", 13.7999, 100.5502, "Крупнейший рынок Азии — 15000 лавок, только сб/вс. Идти утром, вода 20 ฿.", "shopping", 2),
    ("MBK Center", 13.7443, 100.5297, "8 этажей одежды, электроники, реплик брендов — бюджетный шопинг у BTS National Stadium.", "shopping", 2),
    ("Asiatique The Riverfront", 13.7042, 100.5017, "Вечерний рынок-порт на набережной: сувениры, кафе, колесо обозрения.", "shopping", 2),
    ("CentralWorld", 13.7466, 100.5395, "Один из крупнейших молов Азии рядом с Siam Paragon.", "shopping", 1),
]

# --- Да Нанг ---
DANANG_EXTRA = [
    ("Пляж Non Nuoc", 15.9963, 108.2657, "Тихий пляж у подножия Marble Mountains, меньше туристов чем My Khe.", "nature", 1),
    ("Han Market (Chợ Hàn)", 16.0678, 108.2213, "Крытый рынок в центре, специи, сувениры, торг уместен.", "shopping", 2),
    ("An Thượng (район стритфуда и баров)", 16.0353, 108.2437, "Кварталы кафе и баров рядом с My Khe — вечерняя движуха, попробовать местную кухню.", "food", 2),
    ("Vincom Plaza Danang", 16.0544, 108.2233, "Крупный ТЦ, кондиционер, кино, фудкорт при дожде.", "shopping", 1),
    ("Ночной рынок Sơn Trà", 16.0491, 108.2298, "Стритфуд, сувениры, морепродукты по вечерам.", "food", 2),
    ("La Maison 1888 (Michelin)", 16.1028, 108.2762, "Ресторан со звездой Мишлен во французском стиле в InterContinental Danang на Son Tra.", "food", 1),
    ("Кафедральный собор Дананга (Con Ga Church)", 16.0668, 108.2205, "Розовый католический собор в центре города, фотогеничное здание.", "viewpoint", 1),
]

# --- Хошимин ---
HCMC_EXTRA = [
    ("Reunification Palace", 10.7772, 106.6953, "Дворец Независимости — символ окончания войны, экскурсии по залам.", "must_see", 2),
    ("War Remnants Museum", 10.7797, 106.6917, "Музей жертв войны — тяжёлый, но важный для понимания истории Вьетнама.", "must_see", 2),
    ("Bitexco Financial Tower Skydeck", 10.7715, 106.7042, "Смотровая площадка «вертолётная площадка» на 49 этаже.", "viewpoint", 1),
    ("Landmark 81 Skyview", 10.7952, 106.7218, "Самое высокое здание Вьетнама, смотровая на верхних этажах.", "viewpoint", 1),
    ("Chợ Bình Tây (Cholon)", 10.7500, 106.6534, "Крупнейший рынок в китайском квартале Chợ Lớn, колониальная архитектура, мало туристов.", "shopping", 1),
    ("Ngọc Hoàng Pagoda (Jade Emperor)", 10.7859, 106.6949, "Даосский храм с резьбой по дереву и прудом черепах — очень атмосферно.", "must_see", 1),
    ("Тан Динь (розовая церковь)", 10.7912, 106.6903, "Ярко-розовый готический фасад, вторая по величине церковь города — любят инстаграмщики.", "viewpoint", 1),
    ("Bánh mì Huỳnh Hoa", 10.7686, 106.6913, "Легендарный банчми с горой начинки — одна из лучших точек города.", "food", 2),
    ("Vĩnh Khánh (улица морепродуктов)", 10.7581, 106.6997, "Уличные морепродукты вечером — крабы, креветки, устрицы, шумно и вкусно.", "food", 2),
    ("Bùi Viện (Walking Street)", 10.7677, 106.6931, "Туристическая улица баров и клубов — вечерняя тусовка района backpacker.", "entertainment", 1),
    ("Phở Hương Bình", 10.7860, 106.6900, "Michelin Bib Gourmand — фо с говядиной, без пафоса, для местных.", "food", 2),
]

# --- Шанхай ---
SHANGHAI_EXTRA = [
    ("Oriental Pearl Tower", 31.2397, 121.4998, "Телебашня-символ Пудуна со смотровыми площадками, вид на Бунд.", "viewpoint", 2),
    ("Shanghai Tower (обзорная)", 31.2336, 121.5054, "Одно из самых высоких зданий мира, самый быстрый лифт, вид на весь город.", "viewpoint", 2),
    ("Jade Buddha Temple", 31.2461, 121.4419, "Действующий храм с двумя статуями Будды из белого нефрита.", "must_see", 1),
    ("Nanjing Road (пешеходная)", 31.2364, 121.4762, "Главная торговая улица между Бундом и Народной площадью, магазины на любой бюджет.", "shopping", 2),
    ("French Concession", 31.2140, 121.4523, "Квартал платановых бульваров, кафе и колониальной архитектуры 1920-х — прогулка 2-3 ч.", "must_see", 2),
    ("Shanghai Museum", 31.2286, 121.4756, "Один из лучших музеев Китая: бронза, керамика, каллиграфия. Бесплатно.", "must_see", 1),
    ("Xintiandi", 31.2204, 121.4737, "Реконструированный квартал shikumen — бары, рестораны, бутики, вечерняя атмосфера.", "shopping", 1),
    ("Din Tai Fung (Shanghai IFC)", 31.2364, 121.4990, "Сетевой эталон сяолунбао (суповых пельменей) — надёжный вкус в любом филиале.", "food", 3),
    ("Jia Jia Tang Bao", 31.2318, 121.4784, "Местная легенда — сяолунбао без туристической наценки, очереди из местных.", "food", 2),
    ("Nanxiang Steamed Bun (Yuyuan)", 31.2277, 121.4923, "Историческая пельменная у сада Юй, придумавшая современный сяолунбао.", "food", 2),
]

# --- Пекин ---
BEIJING_EXTRA = [
    ("Forbidden City", 39.9163, 116.3972, "⚠️ Не в текущем плане (нет времени в транзите), но если появится доп. день — обязательно.", "must_see", 1),
    ("Great Wall (Mutianyu/Badaling)", 40.4319, 116.5704, "⚠️ Не в текущем плане — далеко от центра, требует отдельный день.", "must_see", 1),
    ("Nanluoguxiang (хутуны)", 39.9385, 116.4038, "Колоритная пешеходная улочка старого Пекина, кафе, сувениры, рикши.", "must_see", 2),
    ("Sanlitun", 39.9337, 116.4547, "Модный район баров и люксовых бутиков, ночная жизнь для экспатов.", "entertainment", 1),
    ("Beihai Park", 39.9256, 116.3898, "Императорский парк с озером и Белой пагодой, рядом с Forbidden City.", "nature", 1),
    ("Siji Minfu (утка по-пекински)", 39.9346, 116.3648, "Один из лучших вариантов утки по-пекински без диких очередей Da Dong.", "food", 2),
    ("Da Dong Roast Duck", 39.9227, 116.4351, "Утка по-пекински в современной подаче, самый известный бренд.", "food", 2),
    ("Quanjude (у Qianmen)", 39.8974, 116.3980, "Старейший ресторан утки по-пекински (с 1864 года), туристическая классика.", "food", 1),
    ("Hefu Noodles", 39.9337, 116.4547, "Сетевая лапшичная — надёжный быстрый обед в Sanlitun.", "food", 1),
]

EXTRA_BY_CITY = {
    "Бангкок": BANGKOK_EXTRA,
    "Да Нанг": DANANG_EXTRA,
    "Хошимин": HCMC_EXTRA,
    "Шанхай": SHANGHAI_EXTRA,
    "Пекин": BEIJING_EXTRA,
}


# ---------------------------------------------------------------------------
# 3. Паттайя — импорт 90 точек из MapsMe/TravelAsk (готовые описания)
# ---------------------------------------------------------------------------
PATTAYA_STYLE_TO_CATEGORY = {
    "red": "must_see",
    "green": "food",
    "yellow": "shopping",
    "brown": "viewpoint",
    "lightblue": "nature",
    "blue": "nature",
    "orange": "nature",
    "purple": "entertainment",
    "deeppurple": "entertainment",
}

# Точки, которые стоит выделить как топовые (★★★) среди 90 точек Паттайи
PATTAYA_TOP = {
    "храм большого будды", "уокинг-стрит", "плавучий рынок в паттайе",
    "тропический сад нонг нуч", "мини-сиам и мини-европа", "остров ко лан",
    "пляж jomtien", "торговый центр central festival", "тц terminal 21",
}
# Нишевые/необязательные (★)
PATTAYA_LOW = {
    "pattaya dolphinarium", "тематический парк suanthai", "flower land pattaya",
    "pattaya sheep farm", "остров обезьян", "музей рипли", "вихарн сиен",
    "храм wat mai hat krathingthong", "метка travelask: храм wat huay yai",
}


def clean_name(raw):
    name = raw.strip()
    name = re.sub(r"^<!\[CDATA\[|\]\]>$", "", name)
    name = re.sub(r"^(Метка )?TravelAsk:\s*", "", name)
    return name.strip()


def clean_desc(raw):
    desc = raw.strip()
    desc = re.sub(r"^<!\[CDATA\[|\]\]>$", "", desc)
    return desc.strip()


def load_pattaya_points():
    """Pattaya points already carry a valid maps.me colour name (red, green,
    purple, yellow, brown, lightblue, blue, orange, deeppurple) straight from
    the working reference file - reuse it as-is instead of remapping through
    our abstract category system."""
    with open(PATTAYA_JSON, encoding="utf-8") as f:
        raw_points = json.load(f)
    points = []
    for p in raw_points:
        name = clean_name(p["name"])
        desc = clean_desc(p["desc"])
        color = p["style"]
        key = name.lower()
        if key in PATTAYA_TOP:
            priority = 3
        elif key in PATTAYA_LOW:
            priority = 1
        else:
            priority = 2
        points.append((name, float(p["lat"]), float(p["lon"]), desc, "Паттайя", color, priority))
    return points


# ---------------------------------------------------------------------------
# KML построение
# ---------------------------------------------------------------------------

def resolve_color(category_or_color):
    """Category name -> maps.me colour; already-a-colour (Pattaya) passes through."""
    return CATEGORY_MAPSME_COLOR.get(category_or_color, category_or_color)


def placemark(name, lat, lon, desc, category, priority):
    """Every placemark needs its OWN <TimeStamp> + <ExtendedData mwm:...>
    (name/description/scale/visibility) - confirmed by isolation testing
    that a document with only "bare" placemarks (name/description/styleUrl/
    Point, no TimeStamp/ExtendedData) gets rejected by MAPS.ME even with a
    byte-perfect document header. Coordinates are lon,lat with NO altitude
    (the working reference never has a 3rd coordinate value)."""
    display_name = STARS.get(priority, "") + name
    color = resolve_color(category)
    name_esc = escape(display_name)
    desc_esc = escape(desc)
    return f"""  <Placemark>
    <name>{name_esc}</name>
    <description>{desc_esc}</description>
    <TimeStamp><when>{TIMESTAMP}</when></TimeStamp>
    <styleUrl>#placemark-{color}</styleUrl>
    <Point><coordinates>{lon},{lat}</coordinates></Point>
    <ExtendedData xmlns:mwm="https://maps.me">
      <mwm:name>
        <mwm:lang code="default">{name_esc}</mwm:lang>
      </mwm:name>
      <mwm:description>
        <mwm:lang code="default">{desc_esc}</mwm:lang>
      </mwm:description>
      <mwm:scale>16</mwm:scale>
      <mwm:visibility>1</mwm:visibility>
    </ExtendedData>
  </Placemark>
"""


def collect_all_points():
    points = list(PLAN_POINTS)
    points += load_pattaya_points()
    for city, extra in EXTRA_BY_CITY.items():
        for name, lat, lon, desc, category, priority in extra:
            points.append((name, lat, lon, desc, city, category, priority))
    return points


def build_city_kml(city, placemarks_xml, count):
    """MAPS.ME's own exports (see Паттайя.kmz) never use <Folder> - every
    Placemark sits directly under <Document>. One KML/KMZ = one bookmark
    category/list in the app. The header is the untouched reference
    template with only the city name substituted (see HEADER_TEMPLATE)."""
    header = HEADER_TEMPLATE.replace("__CITY__", escape(city))
    return header + placemarks_xml + TAIL_TEMPLATE


def safe_filename(name):
    return re.sub(r'[\\/:*?"<>|]', "_", name)


def main():
    points = collect_all_points()

    by_city = {}
    for name, lat, lon, desc, city, category, priority in points:
        by_city.setdefault(city, []).append(placemark(name, lat, lon, desc, category, priority))

    OUTPUT_DIR.mkdir(exist_ok=True)
    for old_file in OUTPUT_DIR.glob("*.kmz"):
        old_file.unlink()

    created = []
    for i, city in enumerate(CITY_ORDER, start=1):
        if city not in by_city:
            continue
        ordered = by_city[city]
        placemarks_xml = "".join(ordered)
        kml = build_city_kml(city, placemarks_xml, len(ordered))
        out_path = OUTPUT_DIR / f"{i}_{safe_filename(city)}.kmz"
        with zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("MapsMe.kml", kml.encode("utf-8"))
        created.append((city, len(ordered), out_path))

    print(f"Output dir: {OUTPUT_DIR}")
    print(f"Total points: {len(points)}")
    for city, n, path in created:
        print(f"  {path.name}: {n} points")


if __name__ == "__main__":
    main()
