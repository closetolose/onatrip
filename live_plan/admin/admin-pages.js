(function () {
  "use strict";

  var chapters = [];
  var currentChapterId = null;
  var chapterOverride = {
    title: "",
    description: "",
    hero_image: "",
    page_bg: "",
    badges: [],
    highlights: [],
    day_overrides: {},
    karl: {},
  };
  var karlDefaults = {};
  var layoutData = null;
  var layoutSchema = null;
  var layoutSortable = null;
  var currentLayoutPage = "index";

  var TILE_CHAPTERS = [
    { id: "thailand", label: "Таиланд" },
    { id: "vietnam", label: "Вьетнам" },
    { id: "china", label: "Китай" },
  ];

  var TILE_COLOR_FIELDS = [
    { key: "face_color", label: "Лицо", default: "#ffffff" },
    { key: "hover_color", label: "Hover", default: "#fcbd1c" },
    { key: "edge_dark", label: "Бок слева", default: "#b1b1b1" },
    { key: "edge_light", label: "Бок снизу", default: "#b1b1b1" },
  ];

  var TILE_DEFAULTS = {
    thailand: { face_color: "#ffffff", hover_color: "#fcbd1c", edge_dark: "#c99710", edge_light: "#fdd550" },
    vietnam: { face_color: "#ffffff", hover_color: "#a6dfff", edge_dark: "#7fb8e5", edge_light: "#c5ebff" },
    china: { face_color: "#ffffff", hover_color: "#efe4cf", edge_dark: "#d5c9ad", edge_light: "#f7f2e5" },
  };

  var STYLE_PRESETS = [
    { key: "padding", label: "Padding" },
    { key: "margin", label: "Margin" },
    { key: "background", label: "Background" },
    { key: "color", label: "Color" },
    { key: "border-radius", label: "Radius" },
    { key: "font-size", label: "Font size" },
    { key: "max-width", label: "Max width" },
    { key: "gap", label: "Gap" },
    { key: "box-shadow", label: "Shadow" },
    { key: "opacity", label: "Opacity" },
  ];

  function setStatus(id, text, kind) {
    var el = document.getElementById(id);
    if (!el) return;
    el.textContent = text || "";
    el.className = "status" + (kind ? " " + kind : "");
  }

  function mediaUrl(url) {
    return window.AdminCore ? window.AdminCore.mediaUrl(url) : url;
  }

  function escapeHtml(s) {
    return window.AdminCore ? window.AdminCore.escapeHtml(s) : s;
  }

  function buildSite() {
    return window.AdminCore ? window.AdminCore.buildSite() : Promise.resolve();
  }

  function currentChapter() {
    return chapters.find(function (ch) { return ch.id === currentChapterId; });
  }

  function renderChaptersList() {
    var list = document.getElementById("chapters-list");
    if (!list) return;
    list.innerHTML = "";
    chapters.forEach(function (chapter) {
      var btn = document.createElement("button");
      btn.type = "button";
      btn.className = "day-btn" + (chapter.id === currentChapterId ? " active" : "");
      btn.innerHTML =
        '<div class="num">' + escapeHtml(chapter.title) + "</div>" +
        '<div class="title">' + chapter.date_from + " — " + chapter.date_to + "</div>" +
        '<div class="city">' + chapter.day_count + " дн.</div>";
      btn.addEventListener("click", function () { selectChapter(chapter.id); });
      list.appendChild(btn);
    });
  }

  function renderTagList(containerId, items, onChange) {
    var container = document.getElementById(containerId);
    if (!container) return;
    container.innerHTML = "";
    items.forEach(function (value, index) {
      var row = document.createElement("div");
      row.className = "tag-row";
      row.innerHTML =
        '<input type="text" value="' + escapeHtml(value).replace(/"/g, "&quot;") + '">' +
        '<button type="button" class="icon-btn tag-delete">✕</button>';
      row.querySelector("input").addEventListener("input", function (e) {
        items[index] = e.target.value;
        onChange();
      });
      row.querySelector(".tag-delete").addEventListener("click", function () {
        items.splice(index, 1);
        onChange();
        renderTagList(containerId, items, onChange);
      });
      container.appendChild(row);
    });
  }

  function syncChapterPageBgPicker() {
    var text = document.getElementById("chapter-page-bg");
    var picker = document.getElementById("chapter-page-bg-picker");
    if (!text || !picker) return;
    var value = (text.value || "").trim();
    if (/^#[0-9a-fA-F]{6}$/.test(value)) {
      picker.value = value;
    }
  }

  function updateChapterPageBgHint() {
    var hint = document.getElementById("chapter-page-bg-hint");
    var chapter = currentChapter();
    if (!hint || !chapter) return;
    var accent = chapter.bg || "#fcbd1c";
    hint.textContent =
      "Пусто — общий Paper из «Сайт». Акцент страны (бейджи, точки): " + accent + ".";
  }

  var KARL_TEXT_KEYS = [
    "nav_home", "nav_route", "nav_main", "nav_play", "nav_contact",
    "panel_a", "panel_b_a", "panel_b_b",
    "panel_c_before", "panel_c_after",
    "panel_d_b", "panel_d_c",
    "panel_e_c", "panel_e_b",
  ];

  var KARL_COLOR_KEYS = ["sky", "globe", "ink", "text_on_globe", "text_on_sky"];

  var KARL_KEYS = KARL_TEXT_KEYS.concat(KARL_COLOR_KEYS);

  function karlEffective(key) {
    var stored = chapterOverride.karl && chapterOverride.karl[key];
    if (stored !== undefined && stored !== null && String(stored).trim() !== "") {
      return String(stored).trim();
    }
    return karlDefaults[key] || "";
  }

  function syncKarlFromDom() {
    var next = {};
    document.querySelectorAll("#chapter-karl-panel [data-karl-key]").forEach(function (node) {
      var key = node.dataset.karlKey;
      if (node.type === "color") return;
      var value = (node.value || "").trim();
      if (!value) return;
      var def = karlDefaults[key] || "";
      if (value !== String(def)) {
        next[key] = value;
      }
    });
    document.querySelectorAll("#chapter-karl-colors-panel [data-karl-key]").forEach(function (node) {
      var key = node.dataset.karlKey;
      if (node.type !== "color") return;
      var value = (node.value || "").trim();
      if (!/^#[0-9a-fA-F]{6}$/.test(value)) return;
      var def = karlDefaults[key] || "";
      if (value !== String(def)) {
        next[key] = value;
      }
    });
    chapterOverride.karl = next;
  }

  function fillKarlForm() {
    var textPanel = document.getElementById("chapter-karl-panel");
    var colorsPanel = document.getElementById("chapter-karl-colors-panel");
    var chapter = currentChapter();
    var showKarl = chapter && ["thailand", "vietnam", "china"].indexOf(chapter.id) >= 0;
    if (textPanel) textPanel.classList.toggle("hidden", !showKarl);
    if (colorsPanel) colorsPanel.classList.toggle("hidden", !showKarl);
    if (!showKarl) return;

    document.querySelectorAll("#chapter-karl-panel [data-karl-key], #chapter-karl-colors-panel [data-karl-key]").forEach(function (node) {
      var key = node.dataset.karlKey;
      var value = karlEffective(key);
      if (node.tagName === "TEXTAREA") {
        node.value = value;
        node.placeholder = karlDefaults[key] || node.placeholder || "";
      } else if (node.type === "range") {
        node.value = value || node.getAttribute("min") || "0";
        var out = document.getElementById(node.id + "-val");
        if (out) out.textContent = node.value;
      } else if (node.type === "color") {
        var colorVal = value;
        if (!/^#[0-9a-fA-F]{6}$/.test(colorVal)) {
          colorVal = karlDefaults[key] || "#333333";
        }
        node.value = colorVal;
      } else {
        node.value = value;
        node.placeholder = karlDefaults[key] || node.placeholder || "";
      }
    });

    var hint = document.getElementById("chapter-karl-hint");
    if (hint && chapter) {
      hint.textContent =
        "Копия karlgonsalves.com для «" + chapter.title +
        "». Пустое поле = пресет. Перенос строки в тексте = <br> на экране. После правок — «Собрать сайт».";
    }
  }

  function resetKarlOverrides() {
    var next = {};
    if (chapterOverride.karl) {
      KARL_COLOR_KEYS.forEach(function (key) {
        if (chapterOverride.karl[key] !== undefined) next[key] = chapterOverride.karl[key];
      });
    }
    chapterOverride.karl = next;
    fillKarlForm();
    setStatus("chapter-status", "Надписи Karl сброшены к пресету (не забудь сохранить)", "ok");
  }

  function resetKarlColors() {
    if (!chapterOverride.karl) chapterOverride.karl = {};
    KARL_COLOR_KEYS.forEach(function (key) {
      delete chapterOverride.karl[key];
    });
    fillKarlForm();
    setStatus("chapter-status", "Цвета сброшены к пресету (не забудь сохранить)", "ok");
  }

  function renderChapterHeroPreview() {
    var preview = document.getElementById("chapter-hero-preview");
    if (!preview) return;
    var url = chapterOverride.hero_image;
    preview.innerHTML = url
      ? '<img src="' + mediaUrl(url) + '" alt="Hero preview">'
      : '<div class="blocks-empty">Hero не задан — будет дефолтное фото</div>';
  }

  function renderDayOverrides() {
    var container = document.getElementById("chapter-days-overrides");
    var chapter = currentChapter();
    if (!container || !chapter) return;
    container.innerHTML = "";
    chapter.days.forEach(function (day) {
      var override = chapterOverride.day_overrides[String(day.num)] || {};
      var item = document.createElement("div");
      item.className = "step-item";
      item.innerHTML =
        '<div class="step-head"><span class="block-type">День ' + day.num + " · " + day.date_short + '</span></div>' +
        '<div class="step-fields">' +
        '<input data-day="' + day.num + '" data-field="city" placeholder="Город" value="' + escapeHtml(override.city || "") + '">' +
        '<input data-day="' + day.num + '" data-field="tag" placeholder="Тег (пляж, остров...)" value="' + escapeHtml(override.tag || "") + '">' +
        '<textarea data-day="' + day.num + '" data-field="summary" rows="2" placeholder="Краткое описание">' + escapeHtml(override.summary || "") + "</textarea>" +
        "</div>";
      container.appendChild(item);
    });
  }

  function syncDayOverridesFromDom() {
    var chapter = currentChapter();
    if (!chapter) return;
    var next = {};
    document.querySelectorAll("#chapter-days-overrides [data-day]").forEach(function (node) {
      var dayNum = node.dataset.day;
      var field = node.dataset.field;
      var value = node.value.trim();
      if (!value) return;
      if (!next[dayNum]) next[dayNum] = {};
      next[dayNum][field] = value;
    });
    chapterOverride.day_overrides = next;
  }

  function fillChapterForm() {
    var chapter = currentChapter();
    document.getElementById("chapter-editor-title").textContent = chapter ? chapter.title : "Выбери главу";
    document.getElementById("chapter-title").value = chapterOverride.title || "";
    document.getElementById("chapter-description").value = chapterOverride.description || "";
    document.getElementById("chapter-hero-url").value = chapterOverride.hero_image || "";
    document.getElementById("chapter-page-bg").value = chapterOverride.page_bg || "";
    syncChapterPageBgPicker();
    updateChapterPageBgHint();
    renderTagList("chapter-badges-list", chapterOverride.badges, function () {});
    renderTagList("chapter-highlights-list", chapterOverride.highlights, function () {});
    renderChapterHeroPreview();
    renderDayOverrides();
    fillKarlForm();
  }

  function selectChapter(chapterId) {
    currentChapterId = chapterId;
    renderChaptersList();
    fetch("/api/chapters/" + chapterId)
      .then(function (r) { return r.json(); })
      .then(function (data) {
        chapterOverride = {
          title: data.override.title || "",
          description: data.override.description || "",
          hero_image: data.override.hero_image || "",
          page_bg: data.override.page_bg || "",
          badges: (data.override.badges || []).slice(),
          highlights: (data.override.highlights || []).slice(),
          day_overrides: JSON.parse(JSON.stringify(data.override.day_overrides || {})),
          karl: JSON.parse(JSON.stringify(data.override.karl || {})),
        };
        karlDefaults = data.karl_defaults || {};
        fillChapterForm();
        setStatus("chapter-status", "");
      })
      .catch(function () { setStatus("chapter-status", "Не удалось загрузить главу", "err"); });
  }

  function saveChapter() {
    if (!currentChapterId) return Promise.resolve();
    syncDayOverridesFromDom();
    syncKarlFromDom();
    return fetch("/api/chapters/" + currentChapterId, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(chapterOverride),
    })
      .then(function (r) { return r.json(); })
      .then(function () {
        setStatus(
          "chapter-status",
          "Глава сохранена. Нажми «Собрать сайт», затем обнови страницу (Ctrl+Shift+R).",
          "ok"
        );
      })
      .catch(function () { setStatus("chapter-status", "Ошибка сохранения", "err"); });
  }

  function uploadChapterHero(file) {
    if (!currentChapterId || !file) return;
    var form = new FormData();
    form.append("file", file);
    fetch("/api/chapters/" + currentChapterId + "/upload-hero", { method: "POST", body: form })
      .then(function (r) { return r.json(); })
      .then(function (data) {
        chapterOverride.hero_image = data.url;
        document.getElementById("chapter-hero-url").value = data.url;
        renderChapterHeroPreview();
        setStatus("chapter-status", "Hero загружен. Нажми «Сохранить».", "ok");
      })
      .catch(function () { setStatus("chapter-status", "Ошибка загрузки hero", "err"); });
  }

  function previewChapter() {
    if (!currentChapterId) return;
    window.open("/preview/chapters/" + currentChapterId + ".html", "_blank");
  }

  function pageSections() {
    return layoutData.pages[currentLayoutPage].sections;
  }

  function sectionLabel(sectionId) {
    var catalog = layoutSchema.sections_catalog[currentLayoutPage] || [];
    var item = catalog.find(function (entry) { return entry.id === sectionId; });
    return item ? item.label : sectionId;
  }

  function syncLayoutPageFromSelect() {
    var select = document.getElementById("layout-page-select");
    if (select) currentLayoutPage = select.value || "index";
  }

  function tileDefaults(chapterId) {
    if (layoutSchema && layoutSchema.tile_defaults && layoutSchema.tile_defaults[chapterId]) {
      return layoutSchema.tile_defaults[chapterId];
    }
    return TILE_DEFAULTS[chapterId] || TILE_DEFAULTS.china;
  }

  function ensureTilesMap() {
    if (!layoutData.tiles) layoutData.tiles = {};
  }

  function renderLayoutTiles() {
    var list = document.getElementById("layout-tiles-list");
    if (!list || !layoutData) return;
    ensureTilesMap();
    list.innerHTML = "";
    TILE_CHAPTERS.forEach(function (tile) {
      var data = layoutData.tiles[tile.id] || {};
      var defaults = tileDefaults(tile.id);
      var item = document.createElement("div");
      item.className = "layout-section-item";
      var fieldsHtml = TILE_COLOR_FIELDS.map(function (field) {
        var value = data[field.key] || defaults[field.key] || field.default || "";
        return (
          '<label class="style-field">' + field.label +
          '<input type="color" data-tile-id="' + tile.id + '" data-tile-key="' + field.key + '" value="' +
          String(value).replace(/"/g, "&quot;") + '">' +
          "</label>"
        );
      }).join("");
      item.innerHTML =
        '<div class="layout-section-head"><strong>' + escapeHtml(tile.label) + "</strong></div>" +
        '<div class="layout-styles">' + fieldsHtml + "</div>";
      list.appendChild(item);
    });
    list.querySelectorAll("[data-tile-id]").forEach(function (input) {
      input.addEventListener("input", function (e) {
        var chapterId = e.target.dataset.tileId;
        var key = e.target.dataset.tileKey;
        ensureTilesMap();
        if (!layoutData.tiles[chapterId]) layoutData.tiles[chapterId] = {};
        layoutData.tiles[chapterId][key] = e.target.value;
      });
    });
  }

  function renderLayoutSections() {
    syncLayoutPageFromSelect();
    var container = document.getElementById("layout-sections-list");
    if (!container || !layoutData) return;
    container.innerHTML = "";
    var sections = pageSections().slice().sort(function (a, b) { return a.order - b.order; });

    sections.forEach(function (section) {
      var item = document.createElement("div");
      item.className = "layout-section-item";
      item.dataset.id = section.id;

      var stylesHtml = STYLE_PRESETS.map(function (preset) {
        var value = (section.styles && section.styles[preset.key]) || "";
        return (
          '<label class="style-field">' + preset.label +
          '<input type="text" data-style-key="' + preset.key + '" value="' + escapeHtml(value).replace(/"/g, "&quot;") + '" placeholder="например 1rem">' +
          "</label>"
        );
      }).join("");

      item.innerHTML =
        '<div class="layout-section-head">' +
        '<label class="layout-toggle"><input type="checkbox" ' + (section.enabled ? "checked" : "") + '> ' + escapeHtml(sectionLabel(section.id)) + "</label>" +
        '<span class="drag-handle">⠿</span>' +
        "</div>" +
        '<div class="layout-styles">' + stylesHtml + "</div>";

      item.querySelector('input[type="checkbox"]').addEventListener("change", function (e) {
        section.enabled = e.target.checked;
      });
      item.querySelectorAll("[data-style-key]").forEach(function (input) {
        input.addEventListener("input", function (e) {
          if (!section.styles) section.styles = {};
          var val = e.target.value.trim();
          if (val) section.styles[e.target.dataset.styleKey] = val;
          else delete section.styles[e.target.dataset.styleKey];
        });
      });
      container.appendChild(item);
    });

    renderLayoutTiles();

    if (layoutSortable) layoutSortable.destroy();
    layoutSortable = Sortable.create(container, {
      animation: 150,
      handle: ".drag-handle",
      draggable: ".layout-section-item",
      onEnd: function () {
        var ordered = [];
        container.querySelectorAll(".layout-section-item").forEach(function (node, index) {
          var section = sections.find(function (s) { return s.id === node.dataset.id; });
          if (section) {
            section.order = index;
            ordered.push(section);
          }
        });
        layoutData.pages[currentLayoutPage].sections = ordered;
      },
    });
  }

  function saveLayout() {
    setStatus("tiles-status", "Сохранение…");
    return fetch("/api/layout", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ layout: layoutData }),
    })
      .then(function (r) { return r.json(); })
      .then(function (data) {
        layoutData = data.layout;
        setStatus("tiles-status", "Плитки сохранены", "ok");
      })
      .catch(function () { setStatus("tiles-status", "Ошибка сохранения", "err"); });
  }

  function saveTiles() {
    setStatus("tiles-status", "Сохранение…");
    return saveLayout()
      .then(function () {
        return window.AdminCore && window.AdminCore.saveSiteAll
          ? window.AdminCore.saveSiteAll()
          : Promise.resolve();
      })
      .then(function () {
        setStatus("tiles-status", "Сохранено", "ok");
      })
      .catch(function () {
        setStatus("tiles-status", "Ошибка сохранения", "err");
      });
  }

  function previewTiles() {
    if (window.AdminCore && window.AdminCore.previewSite) {
      window.AdminCore.previewSite();
    } else {
      window.open("/preview/index.html", "_blank");
    }
  }

  function loadChapters() {
    return fetch("/api/chapters")
      .then(function (r) { return r.json(); })
      .then(function (data) {
        chapters = data;
        renderChaptersList();
        populateVisualChapterSelect();
        if (chapters.length && !currentChapterId) selectChapter(chapters[0].id);
      })
      .catch(function () { setStatus("chapter-status", "Не удалось загрузить главы", "err"); });
  }

  function populateVisualChapterSelect() {
    var select = document.getElementById("visual-chapter-select");
    if (!select || !chapters.length) return;
    select.innerHTML = chapters.map(function (ch) {
      return '<option value="' + ch.id + '">' + ch.title + "</option>";
    }).join("");
  }

  function loadLayout() {
    return fetch("/api/layout")
      .then(function (r) { return r.json(); })
      .then(function (data) {
        layoutData = data.layout;
        layoutSchema = data.schema;
        currentLayoutPage = "index";
        renderLayoutTiles();
      })
      .catch(function () { setStatus("tiles-status", "Не удалось загрузить плитки", "err"); });
  }

  function bindEvents() {
    document.getElementById("btn-save-chapter").addEventListener("click", saveChapter);
    document.getElementById("btn-build-chapter").addEventListener("click", function () {
      saveChapter().then(buildSite);
    });
    document.getElementById("btn-preview-chapter").addEventListener("click", function () {
      saveChapter().then(buildSite).then(previewChapter);
    });
    document.getElementById("btn-add-badge").addEventListener("click", function () {
      chapterOverride.badges.push("");
      renderTagList("chapter-badges-list", chapterOverride.badges, function () {});
    });
    document.getElementById("btn-add-highlight").addEventListener("click", function () {
      chapterOverride.highlights.push("");
      renderTagList("chapter-highlights-list", chapterOverride.highlights, function () {});
    });
    document.getElementById("chapter-title").addEventListener("input", function (e) {
      chapterOverride.title = e.target.value;
    });
    document.getElementById("chapter-description").addEventListener("input", function (e) {
      chapterOverride.description = e.target.value;
    });
    document.getElementById("chapter-hero-url").addEventListener("input", function (e) {
      chapterOverride.hero_image = e.target.value.trim();
      renderChapterHeroPreview();
    });
    document.getElementById("chapter-page-bg").addEventListener("input", function (e) {
      chapterOverride.page_bg = e.target.value.trim();
      syncChapterPageBgPicker();
    });
    document.getElementById("chapter-page-bg-picker").addEventListener("input", function (e) {
      chapterOverride.page_bg = e.target.value;
      document.getElementById("chapter-page-bg").value = e.target.value;
    });
    document.getElementById("btn-clear-chapter-bg").addEventListener("click", function () {
      chapterOverride.page_bg = "";
      document.getElementById("chapter-page-bg").value = "";
      syncChapterPageBgPicker();
    });
    document.getElementById("chapter-hero-file").addEventListener("change", function (e) {
      if (e.target.files && e.target.files[0]) uploadChapterHero(e.target.files[0]);
      e.target.value = "";
    });
    var btnResetKarl = document.getElementById("btn-reset-karl");
    if (btnResetKarl) btnResetKarl.addEventListener("click", resetKarlOverrides);
    var btnResetKarlColors = document.getElementById("btn-reset-karl-colors");
    if (btnResetKarlColors) btnResetKarlColors.addEventListener("click", resetKarlColors);
    document.querySelectorAll("#chapter-karl-panel [data-karl-key], #chapter-karl-colors-panel [data-karl-key]").forEach(function (node) {
      node.addEventListener("input", function () {
        if (node.type === "range") {
          var out = document.getElementById(node.id + "-val");
          if (out) out.textContent = node.value;
        }
      });
    });

    var btnSaveTiles = document.getElementById("btn-save-tiles");
    if (btnSaveTiles) btnSaveTiles.addEventListener("click", saveTiles);
    var btnBuildTiles = document.getElementById("btn-build-tiles");
    if (btnBuildTiles) btnBuildTiles.addEventListener("click", function () {
      saveTiles().then(buildSite);
    });
    var btnPreviewTiles = document.getElementById("btn-preview-tiles");
    if (btnPreviewTiles) btnPreviewTiles.addEventListener("click", function () {
      saveTiles().then(buildSite).then(previewTiles);
    });
  }

  window.AdminPages = {
    onViewChange: function (view) {
      if (view === "tiles") {
        if (!layoutData) loadLayout();
        else renderLayoutTiles();
      }
      if (view === "chapters" && !chapters.length) loadChapters();
    },
    saveTiles: saveTiles,
    getLayout: function () { return layoutData; },
    setLayout: function (data) { layoutData = data; },
    saveLayout: saveLayout,
    populateVisualChapterSelect: populateVisualChapterSelect,
    getChapters: function () { return chapters; },
    ensureLayout: loadLayout,
    getStylePresets: function () { return STYLE_PRESETS.slice(); },
    buildSite: function () {
      return window.AdminCore && window.AdminCore.buildSite
        ? window.AdminCore.buildSite()
        : Promise.resolve();
    },
  };

  bindEvents();
  loadChapters();
  loadLayout().catch(function () {});
})();
