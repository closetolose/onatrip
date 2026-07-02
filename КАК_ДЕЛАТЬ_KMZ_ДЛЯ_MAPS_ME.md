# Как правильно составлять KMZ-файлы для Maps.me (Organic Maps)

Инструкция основана на серии практических тестов на реальном устройстве.
Maps.me использует **свой собственный, очень строгий парсер KML** — он не
соответствует общему стандарту KML/OGC и отклоняет файлы, которые
формально являются валидным XML, но не соответствуют его внутренним
ожиданиям. Ниже — только то, что подтверждено тестами.

## TL;DR — минимальный чек-лист

1. KMZ — это ZIP-архив с одним файлом `MapsMe.kml` внутри (имя важно).
2. `<kml xmlns="http://earth.google.com/kml/2.2">` — именно этот namespace, не `http://www.opengis.net/kml/2.2`.
3. **Никаких `<Folder>`** — все `<Placemark>` лежат прямо в `<Document>`. Один KMZ = один список закладок в приложении.
4. Заголовок `<Document>` должен идти в строгом порядке: сначала все `<Style>`, потом `<name>`, `<visibility>`, потом `<ExtendedData xmlns:mwm="https://maps.me">` с полями `mwm:name` / `mwm:annotation` / `mwm:description` / `mwm:lastModified` / `mwm:accessRules`.
5. Цвет пина — **только** через `<styleUrl>#placemark-ЦВЕТ</styleUrl>`, где ЦВЕТ — одно из 16 зашитых в приложение названий (см. ниже). Свои стили/цвета не работают.
6. **Каждый `<Placemark>` обязан содержать**:
   - `<TimeStamp><when>...</when></TimeStamp>`
   - собственный `<ExtendedData xmlns:mwm="https://maps.me">` с `mwm:name` и `mwm:description`
   - координаты БЕЗ высоты: `<coordinates>lon,lat</coordinates>` (не `lon,lat,0`)
7. Самый безопасный способ — не собирать заголовок `<Document>` вручную, а **скопировать его один-в-один** из любого файла, который точно открывается в Maps.me, и менять только текст названия.

## Разбор по пунктам (что именно тестировалось и почему)

### 1. Имя файла внутри архива

Рабочий образец использует `MapsMe.kml`. Это стоит сохранять как есть —
не факт, что `doc.kml` тоже сработает во всех версиях приложения.

### 2. Один плоский список, без папок

Первые попытки использовали `<Folder>` для группировки точек по
категориям внутри одного `<Document>`. Ни один такой файл не
импортировался. Настоящие экспорты Maps.me никогда не используют
`<Folder>` — весь список точек лежит прямо в `<Document>`. Если нужно
несколько категорий — делайте несколько отдельных KMZ-файлов (каждый
станет отдельным списком закладок в приложении).

### 3. Только 16 предустановленных цветов

Maps.me не читает произвольные `<Style>` с `<color>`/`<scale>` — у него
зашито ровно 16 имён стилей, у каждого готовая иконка-png на
`http://maps.me/placemarks/placemark-ЦВЕТ.png`:

```
red, blue, purple, yellow, pink, brown, green, orange,
deeppurple, lightblue, cyan, teal, lime, deeporange, gray, bluegray
```

Блок стилей в `<Document>` должен содержать все 16 `<Style>` в таком виде
(без `<color>`, без `<scale>`):

```xml
<Style id="placemark-red">
  <IconStyle>
    <Icon>
      <href>http://maps.me/placemarks/placemark-red.png</href>
    </Icon>
  </IconStyle>
</Style>
```

Любое отклонение (свой `id`, `<color>`, другой хост иконки) —
и приложение целиком отклоняет файл как некорректный, а не просто
игнорирует один стиль.

### 4. Обязательный `<ExtendedData xmlns:mwm="https://maps.me">` на уровне `<Document>`

Без этого блока файл считается некорректным. Обязательные поля внутри —
`mwm:name`, `mwm:annotation`, `mwm:description`, `mwm:lastModified`,
`mwm:accessRules`. Даже если `annotation`/`description` пустые — теги
всё равно должны присутствовать.

Порядок тегов в `<Document>` важен: `<Style>`×16 → `<name>` →
`<visibility>` → `<ExtendedData>` → `<Placemark>`×N. Никакого
`<description>` на уровне `<Document>` быть не должно — само наличие
этого тега (даже без `ExtendedData`) достаточно, чтобы файл отклонили.

### 5. Самое неочевидное: заголовок нельзя пересобирать вручную

Это заняло больше всего времени. Даже когда собранный вручную заголовок
**визуально совпадал** побайтово (проверено `diff`) с рабочим образцом
по всем видимым тегам — файл всё равно отклонялся. При этом тот же самый
заголовок, взятый **как сырая строка напрямую из рабочего файла**
(`original[:original.index("<Placemark>")]`), с теми же самыми точками —
работал. Причина осталась не до конца ясна (скорее всего, невидимая
разница в пробелах/переносах строк при ручной пересборке через f-string),
но практический вывод однозначный:

> Не пересобирайте XML-заголовок вручную по описанию. Возьмите готовый
> рабочий `.kmz`, извлеките из него весь текст до первого `<Placemark>`,
> и используйте как шаблон, подставляя туда только название документа
> (простой заменой текста, а не пересборкой тегов).

### 6. Каждая точка обязана иметь `<TimeStamp>` и собственный `<ExtendedData>`

Второе по важности открытие. Точки в формате-минимум:

```xml
<Placemark>
  <name>...</name>
  <description>...</description>
  <styleUrl>#placemark-red</styleUrl>
  <Point><coordinates>100.5,13.7,0</coordinates></Point>
</Placemark>
```

— **не работают**, если в файле нет вообще ни одной "полной" точки.
Zато полная версия работает всегда, даже если реальных
(экспортированных из OSM) точек в файле вообще нет:

```xml
<Placemark>
  <name>Wat Pho</name>
  <description>Храм лежащего Будды.</description>
  <TimeStamp><when>2026-07-02T00:00:00.000Z</when></TimeStamp>
  <styleUrl>#placemark-red</styleUrl>
  <Point><coordinates>100.493,13.7465</coordinates></Point>
  <ExtendedData xmlns:mwm="https://maps.me">
    <mwm:name>
      <mwm:lang code="default">Wat Pho</mwm:lang>
    </mwm:name>
    <mwm:description>
      <mwm:lang code="default">Храм лежащего Будды.</mwm:lang>
    </mwm:description>
    <mwm:scale>16</mwm:scale>
    <mwm:visibility>1</mwm:visibility>
  </ExtendedData>
</Placemark>
```

Поля `mwm:featureTypes`, `mwm:customName`, `mwm:icon` — опциональные,
встречаются не у всех точек даже в родном экспорте Maps.me, их можно не
добавлять.

Координаты — **только два числа** `долгота,широта`, без третьего
(высоты). В образце Maps.me высота не используется никогда.

### 7. Экранирование текста

Имя и описание должны проходить через XML-экранирование
(`xml.sax.saxutils.escape` в Python или аналог) — амперсанды, `<`, `>` в
тексте описаний (например, в валютных пометках вроде `฿`, эмодзи ✅ —
это не проблема, они прошли все тесты нормально) должны быть безопасно
закодированы, иначе получится невалидный XML.

## Полный шаблон файла

```xml
<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://earth.google.com/kml/2.2">
<Document>
  <Style id="placemark-red">
    <IconStyle><Icon><href>http://maps.me/placemarks/placemark-red.png</href></Icon></IconStyle>
  </Style>
  <!-- ... остальные 15 стилей в том же виде ... -->
  <name>Название списка</name>
  <visibility>1</visibility>
  <ExtendedData xmlns:mwm="https://maps.me">
    <mwm:name>
      <mwm:lang code="default">Название списка</mwm:lang>
    </mwm:name>
    <mwm:annotation>
    </mwm:annotation>
    <mwm:description>
    </mwm:description>
    <mwm:lastModified>2026-07-02T00:00:00.000Z</mwm:lastModified>
    <mwm:accessRules>Local</mwm:accessRules>
  </ExtendedData>
  <Placemark>
    <name>Точка 1</name>
    <description>Описание</description>
    <TimeStamp><when>2026-07-02T00:00:00.000Z</when></TimeStamp>
    <styleUrl>#placemark-red</styleUrl>
    <Point><coordinates>100.493,13.7465</coordinates></Point>
    <ExtendedData xmlns:mwm="https://maps.me">
      <mwm:name><mwm:lang code="default">Точка 1</mwm:lang></mwm:name>
      <mwm:description><mwm:lang code="default">Описание</mwm:lang></mwm:description>
      <mwm:scale>16</mwm:scale>
      <mwm:visibility>1</mwm:visibility>
    </ExtendedData>
  </Placemark>
  <!-- остальные Placemark -->
</Document>
</kml>
```

Упаковать в KMZ:

```python
import zipfile
with zipfile.ZipFile("Мой_список.kmz", "w", zipfile.ZIP_DEFLATED) as zf:
    zf.writestr("MapsMe.kml", kml_text.encode("utf-8"))
```

## Готовый рабочий генератор

Весь описанный рецепт уже реализован в `generate_trip_kmz.py` в этой же
папке — можно использовать его как рабочий пример или основу для новых
списков точек.
