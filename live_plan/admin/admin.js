(function () {
  "use strict";

  var days = [];
  var currentDay = null;
  var blocks = [];
  var dayMeta = { totals: "" };
  var cropper = null;
  var editingBlockIndex = -1;
  var accessToken = "";
  var sortable = null;
  var siteSettings = null;
  var siteSchema = [];
  var currentView = "days";

  var els = {
    daysList: document.getElementById("days-list"),
    emptyState: document.getElementById("empty-state"),
    editorPanel: document.getElementById("editor-panel"),
    editorDayLabel: document.getElementById("editor-day-label"),
    editorTitle: document.getElementById("editor-title"),
    blocksList: document.getElementById("blocks-list"),
    metaTotals: document.getElementById("meta-totals"),
    status: document.getElementById("status"),
    photoFileInput: document.getElementById("photo-file-input"),
    modal: document.getElementById("modal"),
    cropImage: document.getElementById("crop-image"),
    cropCaption: document.getElementById("crop-caption"),
    sitePanel: document.getElementById("site-panel"),
    siteSections: document.getElementById("site-sections"),
    siteStatus: document.getElementById("site-status"),
    statusNote: document.getElementById("status-note"),
    statusKind: document.getElementById("status-kind"),
  };

  function setSiteStatus(text, kind) {
    els.siteStatus.textContent = text || "";
    els.siteStatus.className = "status" + (kind ? " " + kind : "");
  }

  function mediaUrl(url) {
    if (!url) return "";
    if (url.startsWith("http://") || url.startsWith("https://") || url.startsWith("/")) {
      return url;
    }
    return "/" + url.replace(/^\/+/, "");
  }

  function setStatus(text, kind) {
    els.status.textContent = text || "";
    els.status.className = "status" + (kind ? " " + kind : "");
  }

  function currentDayMeta() {
    return days.find(function (d) { return d.num === currentDay; });
  }

  function renderDaysList() {
    els.daysList.innerHTML = "";
    days.forEach(function (day) {
      var btn = document.createElement("button");
      btn.type = "button";
      btn.className = "day-btn" + (day.num === currentDay ? " active" : "");
      btn.innerHTML =
        '<div class="num">день ' + day.num + "</div>" +
        '<div class="title">' + day.date.slice(0, 5) + " · " + day.weekday + "</div>" +
        '<div class="city">' + day.city + "</div>";
      btn.addEventListener("click", function () { selectDay(day.num); });
      els.daysList.appendChild(btn);
    });
  }

  function syncBlocksFromDom() {
    var next = [];
    els.blocksList.querySelectorAll(".block-item").forEach(function (node) {
      var idx = Number(node.dataset.index);
      var block = blocks[idx];
      if (!block) return;
      if (block.type === "text") {
        var ta = node.querySelector("textarea");
        next.push({ type: "text", content: ta ? ta.value : block.content });
      } else if (block.type === "photo") {
        next.push({
          type: "photo",
          url: block.url,
          caption: block.caption || "",
        });
      }
    });
    blocks = next;
  }

  function syncBlocksFromDomIfPresent() {
    if (!els.blocksList.querySelector(".block-item")) return;
    syncBlocksFromDom();
  }

  function renderBlocks() {
    els.blocksList.innerHTML = "";

    if (!blocks.length) {
      els.blocksList.innerHTML = '<div class="blocks-empty">Нет блоков. Добавь текст или фото.</div>';
      return;
    }

    blocks.forEach(function (block, index) {
      var item = document.createElement("div");
      item.className = "block-item block-" + block.type;
      item.dataset.index = String(index);

      if (block.type === "text") {
        item.innerHTML =
          '<div class="block-head">' +
          '<span class="block-type">Текст</span>' +
          '<span class="drag-handle">⠿</span>' +
          '<button type="button" class="icon-btn block-delete" title="Удалить">✕</button>' +
          "</div>" +
          '<textarea rows="3" placeholder="Текст для родных"></textarea>';
        item.querySelector("textarea").value = block.content || "";
      } else if (block.type === "photo") {
        item.innerHTML =
          '<div class="block-head">' +
          '<span class="block-type">Фото</span>' +
          '<span class="drag-handle">⠿</span>' +
          '<button type="button" class="icon-btn block-delete" title="Удалить">✕</button>' +
          "</div>" +
          '<div class="photo-preview">' +
          '<img src="' + mediaUrl(block.url) + '" alt="">' +
          '<div class="photo-meta">' +
          '<div class="photo-caption">' + escapeHtml(block.caption || "Без подписи") + "</div>" +
          '<button type="button" class="btn secondary btn-edit-photo">Редактировать</button>' +
          "</div></div>";
      }

      item.querySelector(".block-delete").addEventListener("click", function (e) {
        e.stopPropagation();
        syncBlocksFromDomIfPresent();
        var idx = Number(item.dataset.index);
        blocks.splice(idx, 1);
        renderBlocks();
        setStatus("Блок удалён. Нажми «Сохранить».", "ok");
      });

      if (block.type === "photo") {
        item.querySelector(".btn-edit-photo").addEventListener("click", function () {
          syncBlocksFromDomIfPresent();
          openPhotoEditor(Number(item.dataset.index));
        });
      }

      els.blocksList.appendChild(item);
    });

    if (sortable) sortable.destroy();
    sortable = Sortable.create(els.blocksList, {
      animation: 150,
      handle: ".drag-handle",
      draggable: ".block-item",
      onEnd: function () {
        syncBlocksFromDomIfPresent();
        var next = [];
        els.blocksList.querySelectorAll(".block-item").forEach(function (node) {
          var block = blocks[Number(node.dataset.index)];
          if (block) next.push(block);
        });
        blocks = next;
        renderBlocks();
      },
    });
  }

  function syncMetaFromDom() {
    dayMeta = { totals: els.metaTotals.value.trim() };
  }

  function renderMetaFields() {
    els.metaTotals.value = dayMeta.totals || "";
  }

  function escapeAttr(s) {
    return escapeHtml(s).replace(/"/g, "&quot;");
  }

  function escapeHtml(s) {
    if (!s) return "";
    return String(s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function loadDayData(data) {
    blocks = (data.blocks || []).map(function (b) {
      if (b.type === "text") return { type: "text", content: b.content || "" };
      if (b.type === "photo") return { type: "photo", url: b.url, caption: b.caption || "" };
      return null;
    }).filter(Boolean);

    dayMeta = { totals: (data.meta && data.meta.totals) || "" };
  }

  function selectDay(dayNum) {
    currentDay = dayNum;
    renderDaysList();
    fetch("/api/media/" + dayNum)
      .then(function (r) { return r.json(); })
      .then(function (data) {
        loadDayData(data);

        var meta = currentDayMeta();
        els.emptyState.classList.add("hidden");
        els.editorPanel.classList.remove("hidden");
        els.editorDayLabel.textContent = "день " + dayNum;
        els.editorTitle.textContent = meta ? meta.city : "";
        renderMetaFields();
        renderBlocks();
        setStatus("");
      })
      .catch(function () { setStatus("Не удалось загрузить день", "err"); });
  }

  function saveDay() {
    if (!currentDay) return Promise.resolve();
    syncBlocksFromDomIfPresent();
    syncMetaFromDom();
    return fetch("/api/media/" + currentDay, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        blocks: blocks,
        meta: dayMeta,
      }),
    })
      .then(function (r) { return r.json(); })
      .then(function () {
        setStatus("Сохранено", "ok");
      })
      .catch(function () { setStatus("Ошибка сохранения", "err"); });
  }

  function buildSite() {
    setStatus("Сборка…");
    return fetch("/api/build", { method: "POST" })
      .then(function (r) { return r.json(); })
      .then(function (data) {
        if (data.ok) setStatus("Сайт собран. Можно пушить docs/ на GitHub.", "ok");
        else setStatus("Ошибка сборки: " + (data.stderr || data.stdout || ""), "err");
        return data;
      })
      .catch(function () { setStatus("Ошибка сборки", "err"); });
  }

  window.AdminCore = {
    buildSite: buildSite,
    saveSiteAll: saveSiteAll,
    switchView: switchView,
    mediaUrl: mediaUrl,
    escapeHtml: escapeHtml,
  };

  function addTextBlock() {
    syncBlocksFromDomIfPresent();
    blocks.push({ type: "text", content: "" });
    renderBlocks();
    var last = els.blocksList.querySelector(".block-item:last-child textarea");
    if (last) last.focus();
  }

  function uploadPhoto(file) {
    if (!currentDay || !file) return;
    setStatus("Загрузка…");
    var form = new FormData();
    form.append("file", file);
    fetch("/api/upload/" + currentDay, { method: "POST", body: form })
      .then(function (r) { return r.json(); })
      .then(function (data) {
        syncBlocksFromDomIfPresent();
        blocks.push({ type: "photo", url: data.url, caption: "" });
        renderBlocks();
        setStatus("Фото добавлено. Нажми «Сохранить».", "ok");
      })
      .catch(function () { setStatus("Ошибка загрузки", "err"); });
  }

  function closeModal() {
    if (cropper) {
      cropper.destroy();
      cropper = null;
    }
    els.modal.classList.add("hidden");
    editingBlockIndex = -1;
  }

  function openPhotoEditor(index) {
    editingBlockIndex = index;
    var block = blocks[index];
    if (!block || block.type !== "photo") return;

    var isLocal = block.url.indexOf("media/day-") === 0;
    els.cropCaption.value = block.caption || "";
    els.cropImage.src = mediaUrl(block.url);
    els.modal.classList.remove("hidden");
    document.getElementById("btn-apply-crop").textContent = isLocal ? "Применить обрезку" : "Сохранить подпись";

    els.cropImage.onload = function () {
      if (cropper) cropper.destroy();
      cropper = null;
      if (isLocal) {
        cropper = new Cropper(els.cropImage, {
          viewMode: 1,
          aspectRatio: NaN,
          autoCropArea: 1,
          responsive: true,
        });
      }
    };
  }

  function applyPhotoEdit() {
    if (editingBlockIndex < 0 || !currentDay) return;
    var block = blocks[editingBlockIndex];
    if (!block || block.type !== "photo") return;

    block.caption = els.cropCaption.value.trim();
    var isLocal = block.url.indexOf("media/day-") === 0;

    if (!isLocal || !cropper) {
      closeModal();
      renderBlocks();
      setStatus("Подпись обновлена. Нажми «Сохранить».", "ok");
      return;
    }

    var canvas = cropper.getCroppedCanvas({ maxWidth: 1600, maxHeight: 1600 });
    if (!canvas) return;

    canvas.toBlob(function (blob) {
      var form = new FormData();
      form.append("file", blob, "crop.jpg");
      form.append("source_url", block.url);
      fetch("/api/crop/" + currentDay, { method: "POST", body: form })
        .then(function (r) { return r.json(); })
        .then(function (data) {
          block.url = data.url;
          closeModal();
          renderBlocks();
          setStatus("Фото обновлено. Нажми «Сохранить».", "ok");
        })
        .catch(function () { setStatus("Ошибка обрезки", "err"); });
    }, "image/jpeg", 0.9);
  }

  function deleteEditingBlock() {
    if (editingBlockIndex < 0) return;
    syncBlocksFromDomIfPresent();
    blocks.splice(editingBlockIndex, 1);
    closeModal();
    renderBlocks();
    setStatus("Блок удалён. Нажми «Сохранить».", "ok");
  }

  function previewDay() {
    if (!currentDay) return;
    var url = "/preview/days/" + String(currentDay).padStart(2, "0") + ".html";
    if (accessToken) url += "?k=" + encodeURIComponent(accessToken);
    window.open(url, "_blank");
  }

  function switchView(view) {
    currentView = view;
    document.getElementById("nav-days").classList.toggle("active", view === "days");
    document.getElementById("nav-chapters").classList.toggle("active", view === "chapters");
    document.getElementById("nav-layout").classList.toggle("active", view === "layout");
    document.getElementById("nav-visual").classList.toggle("active", view === "visual");
    document.getElementById("nav-site").classList.toggle("active", view === "site");
    els.daysList.classList.toggle("hidden", view !== "days");
    var chaptersList = document.getElementById("chapters-list");
    if (chaptersList) chaptersList.classList.toggle("hidden", view !== "chapters");
    els.emptyState.classList.toggle("hidden", view !== "days" || currentDay !== null);
    els.editorPanel.classList.toggle("hidden", view !== "days" || !currentDay);
    document.querySelector(".layout").classList.toggle("layout-visual-mode", view === "visual");
    els.sitePanel.classList.toggle("hidden", view !== "site");
    var chaptersPanel = document.getElementById("chapters-panel");
    if (chaptersPanel) chaptersPanel.classList.toggle("hidden", view !== "chapters");
    var layoutPanel = document.getElementById("layout-panel");
    if (layoutPanel) layoutPanel.classList.toggle("hidden", view !== "layout");
    var visualPanel = document.getElementById("visual-panel");
    if (visualPanel) visualPanel.classList.toggle("hidden", view !== "visual");
    var visualSidebar = document.getElementById("visual-sidebar");
    if (visualSidebar) visualSidebar.classList.toggle("hidden", view !== "visual");
    document.getElementById("sidebar-subtitle").textContent =
      view === "site" ? "оформление и тексты" :
      view === "layout" ? "порядок и стили секций" :
      view === "visual" ? "клик → стили элемента" :
      view === "chapters" ? "главы и hero" :
      "день и контент";
    if (window.AdminPages && window.AdminPages.onViewChange) {
      window.AdminPages.onViewChange(view);
    }
  }

  function getNestedValue(obj, sectionId, key) {
    if (sectionId === "custom_css") return obj.custom_css || "";
    return (obj[sectionId] && obj[sectionId][key]) || "";
  }

  function setNestedValue(obj, sectionId, key, value) {
    if (sectionId === "custom_css") {
      obj.custom_css = value;
      return;
    }
    if (!obj[sectionId]) obj[sectionId] = {};
    obj[sectionId][key] = value;
  }

  function renderSiteForm() {
    if (!siteSettings || !siteSchema.length) return;
    els.siteSections.innerHTML = "";

    siteSchema.forEach(function (section) {
      var wrap = document.createElement("section");
      wrap.className = "panel site-section";
      var head = document.createElement("div");
      head.className = "panel-head";
      head.innerHTML = "<h3>" + escapeHtml(section.title) + "</h3>";
      wrap.appendChild(head);
      if (section.hint) {
        var hint = document.createElement("p");
        hint.className = "site-hint";
        hint.textContent = section.hint;
        wrap.appendChild(hint);
      }

      var grid = document.createElement("div");
      grid.className = "site-fields";
      (section.fields || []).forEach(function (field) {
        var label = document.createElement("label");
        if (field.type === "textarea") label.className = "field-wide";
        label.innerHTML = escapeHtml(field.label);
        var input;
        if (field.type === "textarea") {
          input = document.createElement("textarea");
          input.rows = 8;
          input.value = getNestedValue(siteSettings, section.id, field.key);
        } else if (field.type === "color") {
          input = document.createElement("input");
          input.type = "color";
          input.value = getNestedValue(siteSettings, section.id, field.key) || "#000000";
        } else {
          input = document.createElement("input");
          input.type = "text";
          input.value = getNestedValue(siteSettings, section.id, field.key);
        }
        input.dataset.section = section.id;
        input.dataset.key = field.key;
        label.appendChild(input);
        grid.appendChild(label);
      });
      wrap.appendChild(grid);
      els.siteSections.appendChild(wrap);
    });
  }

  function collectSiteSettingsFromForm() {
    var next = JSON.parse(JSON.stringify(siteSettings));
    els.siteSections.querySelectorAll("input, textarea").forEach(function (input) {
      setNestedValue(next, input.dataset.section, input.dataset.key, input.value);
    });
    return next;
  }

  function saveSiteSettings() {
    var payload = collectSiteSettingsFromForm();
    setSiteStatus("Сохранение…");
    return fetch("/api/site-settings", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    })
      .then(function (r) { return r.json(); })
      .then(function (data) {
        siteSettings = data.settings;
        accessToken = (siteSettings.meta && siteSettings.meta.access_token) || accessToken;
        setSiteStatus("Настройки сайта сохранены", "ok");
      })
      .catch(function () { setSiteStatus("Ошибка сохранения", "err"); });
  }

  function saveStatusNote() {
    return fetch("/api/status", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        note: els.statusNote.value,
        note_updated: new Date().toISOString(),
        status: els.statusKind.value,
      }),
    });
  }

  function saveSiteAll() {
    return saveSiteSettings().then(saveStatusNote);
  }

  function previewSite() {
    var url = "/preview/index.html";
    if (accessToken) url += "?k=" + encodeURIComponent(accessToken);
    window.open(url, "_blank");
  }

  function resetSiteSettings() {
    if (!window.confirm("Сбросить все настройки сайта к умолчанию?")) return;
    fetch("/api/site-settings/reset", { method: "POST" })
      .then(function (r) { return r.json(); })
      .then(function (data) {
        siteSettings = data.settings;
        renderSiteForm();
        setSiteStatus("Сброшено к умолчанию", "ok");
      })
      .catch(function () { setSiteStatus("Ошибка сброса", "err"); });
  }

  document.getElementById("btn-add-text").addEventListener("click", addTextBlock);
  document.getElementById("btn-save").addEventListener("click", saveDay);
  document.getElementById("btn-build").addEventListener("click", function () {
    saveDay().then(buildSite);
  });
  document.getElementById("btn-preview").addEventListener("click", function () {
    saveDay().then(buildSite).then(previewDay);
  });
  document.getElementById("modal-close").addEventListener("click", closeModal);
  document.getElementById("btn-apply-crop").addEventListener("click", applyPhotoEdit);
  document.getElementById("btn-delete-block").addEventListener("click", deleteEditingBlock);
  els.photoFileInput.addEventListener("change", function (e) {
    if (e.target.files && e.target.files[0]) uploadPhoto(e.target.files[0]);
    e.target.value = "";
  });

  document.getElementById("nav-days").addEventListener("click", function () { switchView("days"); });
  document.getElementById("nav-chapters").addEventListener("click", function () { switchView("chapters"); });
  document.getElementById("nav-layout").addEventListener("click", function () { switchView("layout"); });
  document.getElementById("nav-visual").addEventListener("click", function () { switchView("visual"); });
  document.getElementById("nav-site").addEventListener("click", function () { switchView("site"); });
  document.getElementById("btn-save-site").addEventListener("click", saveSiteAll);
  document.getElementById("btn-build-site").addEventListener("click", function () {
    saveSiteAll().then(buildSite);
  });
  document.getElementById("btn-preview-site").addEventListener("click", function () {
    saveSiteAll().then(buildSite).then(previewSite);
  });
  document.getElementById("btn-reset-site").addEventListener("click", resetSiteSettings);

  function loadInitialData() {
    if (window.ADMIN_OFFLINE) {
      els.emptyState.innerHTML =
        "<strong>Нет подключения к серверу</strong><br><br>" +
        "1. В терминале: <code>python admin_server.py</code><br>" +
        "2. Открой <a href=\"http://127.0.0.1:5050/\">http://127.0.0.1:5050/</a><br><br>" +
        "Не открывай файл index.html напрямую.";
      return;
    }
    setStatus("Загрузка…");
    fetch("/api/days")
      .then(function (r) {
        if (!r.ok) throw new Error("days");
        return r.json();
      })
      .then(function (data) {
        days = data;
        renderDaysList();
        if (days.length) selectDay(days[0].num);
        else setStatus("Нет дней — сначала собери сайт: python build_live_plan.py", "err");
      })
      .catch(function () {
        els.emptyState.innerHTML =
          "<strong>Не удалось загрузить дни</strong><br><br>" +
          "Перезапусти сервер: <code>python admin_server.py</code><br>" +
          "Затем собери сайт: <code>python build_live_plan.py</code>";
        setStatus("Не удалось загрузить дни. Перезапусти admin_server.py", "err");
      });

    fetch("/api/config")
      .then(function (r) { return r.ok ? r.json() : {}; })
      .then(function (data) {
        accessToken = data.access_token || "";
      })
      .catch(function () {});

    fetch("/api/site-settings")
      .then(function (r) {
        if (!r.ok) throw new Error("site-settings");
        return r.json();
      })
      .then(function (data) {
        siteSettings = data.settings;
        siteSchema = data.schema || [];
        renderSiteForm();
      })
      .catch(function () {
        setSiteStatus("Вкладка «Сайт»: перезапусти admin_server.py (python admin_server.py)", "err");
      });

    fetch("/api/status")
      .then(function (r) { return r.ok ? r.json() : { note: "", status: "ok" }; })
      .then(function (data) {
        els.statusNote.value = data.note || "";
        els.statusKind.value = data.status || "ok";
      })
      .catch(function () {});
  }

  loadInitialData();
})();
