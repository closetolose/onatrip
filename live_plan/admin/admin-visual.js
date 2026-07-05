(function () {
  "use strict";

  var STYLE_PRESETS = [
    { key: "padding", label: "Padding", placeholder: "1rem" },
    { key: "margin", label: "Margin", placeholder: "0.5rem 0" },
    { key: "background", label: "Background", placeholder: "#ffffff" },
    { key: "background-color", label: "Background color", placeholder: "#ffffff" },
    { key: "color", label: "Color", placeholder: "#23212c" },
    { key: "border-radius", label: "Radius", placeholder: "1rem" },
    { key: "font-size", label: "Font size", placeholder: "1rem" },
    { key: "font-weight", label: "Font weight", placeholder: "700" },
    { key: "max-width", label: "Max width", placeholder: "40rem" },
    { key: "gap", label: "Gap", placeholder: "0.75rem" },
    { key: "box-shadow", label: "Shadow", placeholder: "0 8px 24px rgba(0,0,0,.08)" },
    { key: "opacity", label: "Opacity", placeholder: "1" },
    { key: "text-align", label: "Text align", placeholder: "left" },
  ];

  var frame = document.getElementById("visual-frame");
  var selected = null;
  var highlightEl = null;
  var cssTimer = null;
  var pageCatalog = null;

  function pagesApi() {
    return window.AdminPages || {};
  }

  function layoutData() {
    return pagesApi().getLayout ? pagesApi().getLayout() : null;
  }

  function currentPageType() {
    return document.getElementById("visual-page-type").value;
  }

  function previewUrl() {
    var page = currentPageType();
    if (page === "index") return "/preview/index.html";
    if (page === "chapter") {
      var chapterId = document.getElementById("visual-chapter-select").value || "thailand";
      return "/preview/chapters/" + chapterId + ".html";
    }
    var dayNum = Number(document.getElementById("visual-day-num").value || 2);
    return "/preview/days/" + String(dayNum).padStart(2, "0") + ".html";
  }

  function setStatus(text, kind) {
    var el = document.getElementById("visual-status");
    if (!el) return;
    el.textContent = text || "";
    el.className = "status" + (kind ? " " + kind : "");
  }

  function pageRootClass(page) {
    return page === "index" ? "index-page" : page === "chapter" ? "chapter-body" : "day-body";
  }

  function catalogForPage(page) {
    if (!pageCatalog) return [];
    return (pageCatalog[page] || []).slice();
  }

  function sectionMeta(page, sectionId) {
    return catalogForPage(page).find(function (item) { return item.id === sectionId; });
  }

  function findSectionRecord(page, sectionId) {
    var layout = layoutData();
    if (!layout) return null;
    var sections = layout.pages[page].sections;
    return sections.find(function (item) { return item.id === sectionId; });
  }

  function findTileRecord(tileId) {
    var layout = layoutData();
    if (!layout) return null;
    if (!layout.tiles) layout.tiles = {};
    if (!layout.tiles[tileId]) layout.tiles[tileId] = {};
    return layout.tiles[tileId];
  }

  function tileSelector(tileId) {
    return 'body.index-page .social-tiles .tile-link[data-tile-id="' + tileId + '"]';
  }

  function tileLabel(tileId) {
    var labels = { thailand: "Таиланд", vietnam: "Вьетнам", china: "Китай" };
    return "Плитка · " + (labels[tileId] || tileId);
  }

  function tileStyleKeys() {
    return ["face_color", "hover_color", "edge_dark", "edge_light"];
  }

  function tileStylePresets() {
    return [
      { key: "face_color", label: "Лицо плитки", placeholder: "#ffffff" },
      { key: "hover_color", label: "Hover", placeholder: "#fcbd1c" },
      { key: "edge_dark", label: "Бок слева", placeholder: "#c99710" },
      { key: "edge_light", label: "Бок снизу", placeholder: "#fdd550" },
    ];
  }

  function findCustomRule(selector) {
    var layout = layoutData();
    if (!layout) return null;
    return (layout.custom_rules || []).find(function (rule) { return rule.selector === selector; });
  }

  function upsertCustomRule(page, selector, label, styles) {
    var layout = layoutData();
    if (!layout.custom_rules) layout.custom_rules = [];
    var rule = findCustomRule(selector);
    if (!rule) {
      rule = { selector: selector, label: label, page: page, styles: {} };
      layout.custom_rules.push(rule);
    }
    rule.styles = styles;
    rule.label = label;
    rule.page = page;
    pagesApi().setLayout(layout);
  }

  function removeCustomRule(selector) {
    var layout = layoutData();
    if (!layout || !layout.custom_rules) return;
    layout.custom_rules = layout.custom_rules.filter(function (rule) {
      return rule.selector !== selector;
    });
    pagesApi().setLayout(layout);
  }

  function cssPath(el, root) {
    var parts = [];
    var node = el;
    while (node && node !== root && node !== node.ownerDocument.body) {
      var part = node.tagName.toLowerCase();
      if (node.id) {
        parts.unshift("#" + node.id);
        break;
      }
      if (node.classList && node.classList.length) {
        part += "." + Array.from(node.classList)[0];
      }
      parts.unshift(part);
      node = node.parentElement;
    }
    var rootSelector = root.matches("[data-section]")
      ? '[data-section="' + root.getAttribute("data-section") + '"]'
      : ".trip-main";
    return parts.length ? rootSelector + " " + parts.join(" ") : rootSelector;
  }

  function resolveTarget(el, page) {
    var sectionEl = el.closest("[data-section]");
    if (sectionEl) {
      var sectionId = sectionEl.getAttribute("data-section");
      var meta = sectionMeta(page, sectionId);
      var isExactSection = el === sectionEl;
      if (isExactSection) {
        return {
          kind: "section",
          page: page,
          sectionId: sectionId,
          label: meta ? meta.label : sectionId,
          selector: meta ? meta.selector : '[data-section="' + sectionId + '"]',
        };
      }
      var selector = cssPath(el, sectionEl);
      var label = el.tagName.toLowerCase();
      if (el.classList && el.classList.length) label += "." + el.classList[0];
      return {
        kind: "custom",
        page: page,
        sectionId: sectionId,
        label: label,
        selector: selector,
      };
    }
    if (page === "index" && el.closest(".trip-main")) {
      return {
        kind: "section",
        page: page,
        sectionId: "tiles",
        label: "Фон страницы",
        selector: ".trip-main",
      };
    }
    if (page === "index" && el.closest(".tile-link")) {
      var tileLink = el.closest(".tile-link");
      var tileId = tileLink.getAttribute("data-tile-id") || "";
      if (tileId) {
        return {
          kind: "tile",
          page: page,
          tileId: tileId,
          label: tileLabel(tileId),
          selector: tileSelector(tileId),
        };
      }
      return {
        kind: "custom",
        page: page,
        sectionId: "tiles",
        label: "Плитка",
        selector: "body.index-page .social-tiles .tile-link",
      };
    }
    return null;
  }

  function stylesForSelection(target) {
    if (target.kind === "tile") {
      var tile = findTileRecord(target.tileId);
      var styles = {};
      tileStyleKeys().forEach(function (key) {
        if (tile[key]) styles[key] = tile[key];
      });
      return styles;
    }
    if (target.kind === "section") {
      var section = findSectionRecord(target.page, target.sectionId);
      return section ? Object.assign({}, section.styles || {}) : {};
    }
    var rule = findCustomRule(target.selector);
    return rule ? Object.assign({}, rule.styles || {}) : {};
  }

  function writeStyles(target, styles) {
    var layout = layoutData();
    if (!layout) return;
    if (target.kind === "tile") {
      var tile = findTileRecord(target.tileId);
      tileStyleKeys().forEach(function (key) {
        if (styles[key]) tile[key] = styles[key];
        else delete tile[key];
      });
      pagesApi().setLayout(layout);
      return;
    }
    if (target.kind === "section") {
      var section = findSectionRecord(target.page, target.sectionId);
      if (section) section.styles = styles;
    } else {
      upsertCustomRule(target.page, target.selector, target.label, styles);
      return;
    }
    pagesApi().setLayout(layout);
  }

  function sectionEnabled(target) {
    var section = findSectionRecord(target.page, target.sectionId);
    return section ? section.enabled !== false : true;
  }

  function setSectionEnabled(target, enabled) {
    var section = findSectionRecord(target.page, target.sectionId);
    if (section) section.enabled = enabled;
    pagesApi().setLayout(layoutData());
  }

  function clearHighlight(doc) {
    if (highlightEl && highlightEl.parentNode) highlightEl.parentNode.removeChild(highlightEl);
    highlightEl = null;
    if (doc) {
      var old = doc.getElementById("admin-visual-highlight");
      if (old) old.remove();
    }
  }

  function drawHighlight(doc, el) {
    clearHighlight(doc);
    if (!doc || !el) return;
    var rect = el.getBoundingClientRect();
    var box = doc.createElement("div");
    box.id = "admin-visual-highlight";
    box.style.position = "fixed";
    box.style.left = rect.left + "px";
    box.style.top = rect.top + "px";
    box.style.width = rect.width + "px";
    box.style.height = rect.height + "px";
    box.style.border = "2px solid #006434";
    box.style.background = "rgba(0, 100, 52, 0.08)";
    box.style.pointerEvents = "none";
    box.style.zIndex = "99999";
    box.style.borderRadius = "8px";
    doc.body.appendChild(box);
    highlightEl = box;
  }

  function injectPreviewCss(doc) {
    var layout = layoutData();
    if (!layout) return Promise.resolve();
    return fetch("/api/layout/css", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ layout: layout }),
    })
      .then(function (r) { return r.json(); })
      .then(function (data) {
        var style = doc.getElementById("admin-visual-live-css");
        if (!style) {
          style = doc.createElement("style");
          style.id = "admin-visual-live-css";
          doc.head.appendChild(style);
        }
        style.textContent = data.css || "";
      });
  }

  function scheduleCssRefresh(doc) {
    clearTimeout(cssTimer);
    cssTimer = setTimeout(function () {
      injectPreviewCss(doc).then(function () {
        if (selected && selected.element) drawHighlight(doc, selected.element);
      });
    }, 180);
  }

  function renderInspector() {
    var empty = document.getElementById("visual-empty");
    var body = document.getElementById("visual-inspector-body");
    if (!selected) {
      empty.classList.remove("hidden");
      body.classList.add("hidden");
      document.getElementById("visual-target-label").textContent = "Кликни по элементу";
      return;
    }
    empty.classList.add("hidden");
    body.classList.remove("hidden");
    document.getElementById("visual-target-label").textContent = selected.target.label;
    document.getElementById("visual-selector").textContent = selected.target.selector;

    var toggle = document.querySelector(".visual-section-toggle");
    if (selected.target.kind === "section") {
      toggle.classList.remove("hidden");
      document.getElementById("visual-section-enabled").checked = sectionEnabled(selected.target);
    } else {
      toggle.classList.add("hidden");
    }

    var styles = stylesForSelection(selected.target);
    var presets = selected.target.kind === "tile" ? tileStylePresets() : STYLE_PRESETS;
    var fields = document.getElementById("visual-style-fields");
    fields.innerHTML = presets.map(function (preset) {
      var value = styles[preset.key] || "";
      var inputType = preset.key.indexOf("color") >= 0 ? "color" : "text";
      if (inputType === "color" && value && value.indexOf("#") !== 0) inputType = "text";
      return (
        '<label class="style-field">' + preset.label +
        '<input type="' + inputType + '" data-style-key="' + preset.key + '" value="' +
        String(value).replace(/"/g, "&quot;") + '" placeholder="' + preset.placeholder + '">' +
        "</label>"
      );
    }).join("");

    fields.querySelectorAll("[data-style-key]").forEach(function (input) {
      input.addEventListener("input", function (e) {
        var next = stylesForSelection(selected.target);
        var val = e.target.value.trim();
        if (val) next[e.target.dataset.styleKey] = val;
        else delete next[e.target.dataset.styleKey];
        writeStyles(selected.target, next);
        scheduleCssRefresh(selected.doc);
      });
    });
  }

  function attachFrameHandlers() {
    var doc = frame.contentDocument;
    if (!doc) return;

    injectPreviewCss(doc);

    if (!doc.getElementById("admin-visual-style")) {
      var style = doc.createElement("style");
      style.id = "admin-visual-style";
      style.textContent =
        "* { cursor: crosshair !important; } " +
        "a, button { cursor: crosshair !important; }";
      doc.head.appendChild(style);
    }

    doc.addEventListener("click", function (e) {
      e.preventDefault();
      e.stopPropagation();
      var page = currentPageType();
      var target = resolveTarget(e.target, page);
      if (!target) {
        setStatus("Этот элемент пока нельзя редактировать", "err");
        return;
      }
      selected = { target: target, element: e.target, doc: doc };
      drawHighlight(doc, e.target);
      renderInspector();
      setStatus("");
    }, true);

    doc.addEventListener("mouseover", function (e) {
      if (!e.target || e.target.id === "admin-visual-highlight") return;
      e.target.style.outline = "1px dashed rgba(0, 100, 52, 0.45)";
    });
    doc.addEventListener("mouseout", function (e) {
      if (e.target) e.target.style.outline = "";
    });
  }

  function loadPreview() {
    var layoutPromise = pagesApi().ensureLayout
      ? pagesApi().ensureLayout().catch(function () { return null; })
      : Promise.resolve(null);

    layoutPromise.then(function () {
      if (!pageCatalog) {
        fetch("/api/layout")
          .then(function (r) { return r.ok ? r.json() : null; })
          .then(function (data) {
            if (data && data.schema) pageCatalog = data.schema.sections_catalog;
          })
          .finally(setFrameSrc);
      } else {
        setFrameSrc();
      }
    });

    function setFrameSrc() {
      if (!frame) return;
      var url = previewUrl();
      frame.removeAttribute("srcdoc");
      frame.src = url + (url.indexOf("?") >= 0 ? "&" : "?") + "_=" + Date.now();
    }
  }

  function populateChapterSelect() {
    if (window.AdminPages && window.AdminPages.populateVisualChapterSelect) {
      window.AdminPages.populateVisualChapterSelect();
      return;
    }
    var select = document.getElementById("visual-chapter-select");
    if (!select || select.options.length) return;
  }

  function bindEvents() {
    document.getElementById("visual-page-type").addEventListener("change", function (e) {
      var page = e.target.value;
      document.getElementById("visual-chapter-wrap").classList.toggle("hidden", page !== "chapter");
      document.getElementById("visual-day-wrap").classList.toggle("hidden", page !== "day");
      selected = null;
      renderInspector();
      loadPreview();
    });
    document.getElementById("visual-chapter-select").addEventListener("change", loadPreview);
    document.getElementById("visual-day-num").addEventListener("change", loadPreview);
    document.getElementById("btn-visual-reload").addEventListener("click", loadPreview);
    document.getElementById("btn-visual-save").addEventListener("click", function () {
      pagesApi().saveLayout().then(function () {
        setStatus("Макет сохранён", "ok");
      });
    });
    document.getElementById("btn-visual-build").addEventListener("click", function () {
      pagesApi().saveLayout().then(function () {
        return pagesApi().buildSite();
      }).then(function () {
        setStatus("Сохранено и собрано", "ok");
        loadPreview();
      });
    });
    document.getElementById("visual-section-enabled").addEventListener("change", function (e) {
      if (!selected || selected.target.kind !== "section") return;
      setSectionEnabled(selected.target, e.target.checked);
      scheduleCssRefresh(selected.doc);
    });
    document.getElementById("btn-visual-clear-styles").addEventListener("click", function () {
      if (!selected) return;
      if (selected.target.kind === "tile") {
        writeStyles(selected.target, {});
      } else if (selected.target.kind === "custom") {
        removeCustomRule(selected.target.selector);
      } else {
        writeStyles(selected.target, {});
      }
      scheduleCssRefresh(selected.doc);
      renderInspector();
      setStatus("Стили сброшены", "ok");
    });
    frame.addEventListener("load", attachFrameHandlers);
    frame.addEventListener("error", function () {
      setStatus("Не удалось загрузить превью. Собери сайт: python build_live_plan.py", "err");
    });
  }

  window.AdminVisual = {
    onActivate: function () {
      populateChapterSelect();
      if (!pagesApi().getChapters || !pagesApi().getChapters().length) {
        fetch("/api/chapters")
          .then(function (r) { return r.json(); })
          .then(function () { populateChapterSelect(); loadPreview(); });
      } else {
        loadPreview();
      }
    },
  };

  bindEvents();
})();
