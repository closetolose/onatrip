(function () {
  "use strict";

  var days = [];
  var currentDay = null;
  var blocks = [];
  var dayHero = { eyebrow: "", title: "", meta: "" };
  var heroDefaults = { eyebrow: "", title: "", meta: "" };
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
    heroEyebrow: null,
    heroTitle: null,
    heroMeta: null,
    status: document.getElementById("status"),
    photoFileInput: document.getElementById("photo-file-input"),
    modal: document.getElementById("modal"),
    cropImage: document.getElementById("crop-image"),
    cropCaption: document.getElementById("crop-caption"),
    siteSections: document.getElementById("site-sections"),
    tilesStatus: document.getElementById("tiles-status"),
    statusNote: document.getElementById("status-note"),
    statusKind: document.getElementById("status-kind"),
  };

  function setTilesStatus(text, kind) {
    if (!els.tilesStatus) return;
    els.tilesStatus.textContent = text || "";
    els.tilesStatus.className = "status" + (kind ? " " + kind : "");
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

  function mediaPathFromSrc(src) {
    if (!src) return "";
    var marker = "media/day-";
    var pos = src.indexOf(marker);
    if (pos < 0) return "";
    return src.slice(pos).split("?")[0];
  }

  function sideUrlFromNode(node, fallbackUrl) {
    if (node.dataset.url) return node.dataset.url;
    var img = node.querySelector(".side-photo-preview img");
    if (img) {
      var fromImg = mediaPathFromSrc(img.getAttribute("src") || "");
      if (fromImg) return fromImg;
    }
    return fallbackUrl || "";
  }

  function syncBlockFromNode(node) {
    var idx = Number(node.dataset.index);
    var block = blocks[idx];
    if (!block) return null;
    if (block.type === "text") {
      var ta = node.querySelector("textarea");
      return { type: "text", content: ta ? ta.value : block.content };
    }
    if (block.type === "photo") {
      return { type: "photo", url: block.url, caption: block.caption || "" };
    }
    if (block.type === "carousel") {
      var photos = [];
      node.querySelectorAll(".carousel-photo").forEach(function (photoNode, photoIndex) {
        var source = block.photos && block.photos[photoIndex];
        var img = photoNode.querySelector("img");
        var url = (source && source.url) || mediaPathFromSrc(img ? img.getAttribute("src") || "" : "");
        if (!url) return;
        var captionInput = photoNode.querySelector(".carousel-caption");
        photos.push({
          url: url,
          caption: captionInput ? captionInput.value.trim() : ((source && source.caption) || ""),
        });
      });
      return { type: "carousel", photos: photos };
    }
    if (block.type === "side") {
      var sideTa = node.querySelector(".side-content");
      var sideCaption = node.querySelector(".side-caption");
      var sideToggle = node.querySelector(".side-toggle-btn.is-active");
      return {
        type: "side",
        side: sideToggle ? sideToggle.dataset.side : (block.side || "left"),
        url: sideUrlFromNode(node, block.url),
        caption: sideCaption ? sideCaption.value.trim() : (block.caption || "").trim(),
        content: sideTa ? sideTa.value.trim() : (block.content || "").trim(),
      };
    }
    return null;
  }

  function syncBlocksFromDom() {
    var next = [];
    els.blocksList.querySelectorAll(".block-item").forEach(function (node) {
      var synced = syncBlockFromNode(node);
      if (synced) next.push(synced);
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
      els.blocksList.innerHTML = '<div class="blocks-empty">Нет блоков. Добавь текст, фото или боковую секцию.</div>';
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
      } else if (block.type === "carousel") {
        var photosHtml = (block.photos || []).map(function (photo, photoIndex) {
          return (
            '<div class="carousel-photo" data-photo-index="' + photoIndex + '">' +
            '<img src="' + mediaUrl(photo.url) + '" alt="">' +
            '<input type="text" class="carousel-caption" placeholder="Подпись к фото" value="' +
            escapeHtml(photo.caption || "") + '">' +
            '<button type="button" class="icon-btn carousel-photo-delete" title="Удалить фото">✕</button>' +
            "</div>"
          );
        }).join("");
        item.innerHTML =
          '<div class="block-head">' +
          '<span class="block-type">Карусель</span>' +
          '<span class="drag-handle">⠿</span>' +
          '<button type="button" class="icon-btn block-delete" title="Удалить">✕</button>' +
          "</div>" +
          '<div class="carousel-photos">' + (photosHtml || '<div class="carousel-empty">Добавь фото в карусель</div>') + "</div>" +
          '<label class="btn secondary upload-btn carousel-upload">' +
          "+ Фото в карусель" +
          '<input type="file" accept="image/*" hidden>' +
          "</label>";
      } else if (block.type === "side") {
        var sidePosition = block.side === "right" ? "right" : "left";
        if (block.url) item.dataset.url = block.url;
        var sidePhotoHtml = block.url
          ? (
            '<div class="side-photo-preview">' +
            '<img src="' + mediaUrl(block.url) + '" alt="">' +
            '<label class="btn secondary upload-btn side-replace">' +
            "Заменить" +
            '<input type="file" accept="image/*" hidden>' +
            "</label></div>"
          )
          : (
            '<label class="btn secondary upload-btn side-upload">' +
            "+ Загрузить фото" +
            '<input type="file" accept="image/*" hidden>' +
            "</label>"
          );
        item.innerHTML =
          '<div class="block-head">' +
          '<span class="block-type">Фото + текст</span>' +
          '<span class="drag-handle">⠿</span>' +
          '<button type="button" class="icon-btn block-delete" title="Удалить">✕</button>' +
          "</div>" +
          '<div class="side-layout">' +
          '<div class="side-controls">' +
          '<div class="side-toggle" role="group" aria-label="Позиция фото">' +
          '<button type="button" class="btn secondary side-toggle-btn' + (sidePosition === "left" ? " is-active" : "") + '" data-side="left">Фото слева</button>' +
          '<button type="button" class="btn secondary side-toggle-btn' + (sidePosition === "right" ? " is-active" : "") + '" data-side="right">Фото справа</button>' +
          "</div>" +
          sidePhotoHtml +
          '<input type="text" class="side-caption" placeholder="Подпись к фото (необязательно)" value="' +
          escapeAttr(block.caption || "") + '">' +
          "</div>" +
          '<textarea class="side-content" rows="5" placeholder="Текст рядом с фото"></textarea>' +
          "</div>";
        item.querySelector(".side-content").value = block.content || "";
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

      if (block.type === "carousel") {
        var uploadInput = item.querySelector(".carousel-upload input");
        if (uploadInput) {
          uploadInput.addEventListener("change", function (e) {
            if (e.target.files && e.target.files[0]) {
              uploadPhotoToCarousel(Number(item.dataset.index), e.target.files[0]);
            }
            e.target.value = "";
          });
        }
        item.querySelectorAll(".carousel-photo-delete").forEach(function (btn) {
          btn.addEventListener("click", function (e) {
            e.stopPropagation();
            syncBlocksFromDomIfPresent();
            var blockIndex = Number(item.dataset.index);
            var photoIndex = Number(btn.closest(".carousel-photo").dataset.photoIndex);
            if (blocks[blockIndex] && blocks[blockIndex].photos) {
              blocks[blockIndex].photos.splice(photoIndex, 1);
              renderBlocks();
              setStatus("Фото удалено из карусели. Нажми «Сохранить».", "ok");
            }
          });
        });
      }

      if (block.type === "side") {
        item.querySelectorAll(".side-toggle-btn").forEach(function (btn) {
          btn.addEventListener("click", function () {
            syncBlocksFromDomIfPresent();
            var idx = Number(item.dataset.index);
            if (blocks[idx]) {
              blocks[idx].side = btn.dataset.side;
              renderBlocks();
            }
          });
        });
        var sideUpload = item.querySelector(".side-upload input, .side-replace input");
        if (sideUpload) {
          sideUpload.addEventListener("change", function (e) {
            if (e.target.files && e.target.files[0]) {
              uploadPhotoToSide(Number(item.dataset.index), e.target.files[0]);
            }
            e.target.value = "";
          });
        }
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
        renderBlocks();
      },
    });
  }

  function heroInputs() {
    var panel = document.getElementById("editor-panel");
    if (!panel) return { eyebrow: null, title: null, meta: null };
    return {
      eyebrow: panel.querySelector("#hero-eyebrow"),
      title: panel.querySelector("#hero-title"),
      meta: panel.querySelector("#hero-meta"),
    };
  }

  function syncHeroFromDom() {
    var inputs = heroInputs();
    if (!inputs.eyebrow || !inputs.title || !inputs.meta) {
      throw new Error("поля hero не найдены — обнови страницу (Ctrl+Shift+R)");
    }
    dayHero = {
      eyebrow: inputs.eyebrow.value.trim(),
      title: inputs.title.value.trim(),
      meta: inputs.meta.value.trim(),
    };
  }

  function renderHeroFields() {
    var inputs = heroInputs();
    if (!inputs.eyebrow || !inputs.title || !inputs.meta) return;
    inputs.eyebrow.value = dayHero.eyebrow || "";
    inputs.title.value = dayHero.title || "";
    inputs.meta.value = dayHero.meta || "";
    inputs.eyebrow.placeholder = heroDefaults.eyebrow || "";
    inputs.title.placeholder = heroDefaults.title || "";
    inputs.meta.placeholder = heroDefaults.meta || "";
  }

  function heroPayloadMatches(written, expected) {
    if (!written) return false;
    expected = expected || {};
    return (written.eyebrow || "").trim() === (expected.eyebrow || "").trim()
      && (written.title || "").trim() === (expected.title || "").trim()
      && (written.meta || "").trim() === (expected.meta || "").trim();
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
      if (b.type === "carousel") {
        return {
          type: "carousel",
          photos: (b.photos || []).map(function (p) {
            return { url: p.url, caption: p.caption || "" };
          }),
        };
      }
      if (b.type === "side") {
        return {
          type: "side",
          side: b.side === "right" ? "right" : "left",
          url: b.url || "",
          caption: b.caption || "",
          content: b.content || "",
        };
      }
      return null;
    }).filter(Boolean);

    dayHero = {
      eyebrow: (data.hero && data.hero.eyebrow) || "",
      title: (data.hero && data.hero.title) || "",
      meta: (data.hero && data.hero.meta) || "",
    };
    heroDefaults = data.defaults || heroDefaults;
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
        els.editorTitle.textContent = dayHero.title || (meta ? meta.city : "");
        renderHeroFields();
        renderBlocks();
        setStatus("");
      })
      .catch(function () { setStatus("Не удалось загрузить день", "err"); });
  }

  function cleanPhotoItem(item) {
    if (!item) return null;
    var url = typeof item === "string" ? item : item.url;
    if (!url || !String(url).trim()) return null;
    return {
      url: String(url).trim(),
      caption: (typeof item === "object" && item.caption ? item.caption : "").trim(),
    };
  }

  function cleanBlocksClient(blocks) {
    var cleaned = [];
    (blocks || []).forEach(function (block) {
      if (!block || !block.type) return;
      if (block.type === "text") {
        var text = (block.content || "").trim();
        if (text) cleaned.push({ type: "text", content: text });
      } else if (block.type === "photo") {
        var photoUrl = (block.url || "").trim();
        if (photoUrl) {
          cleaned.push({
            type: "photo",
            url: photoUrl,
            caption: (block.caption || "").trim(),
          });
        }
      } else if (block.type === "carousel") {
        var photos = [];
        (block.photos || []).forEach(function (item) {
          var photo = cleanPhotoItem(item);
          if (photo) photos.push(photo);
        });
        if (photos.length) cleaned.push({ type: "carousel", photos: photos });
      } else if (block.type === "side") {
        var sideUrl = (block.url || "").trim();
        var sideText = (block.content || "").trim();
        if (sideUrl || sideText) {
          cleaned.push({
            type: "side",
            side: block.side === "right" ? "right" : "left",
            url: sideUrl,
            caption: (block.caption || "").trim(),
            content: sideText,
          });
        }
      }
    });
    return cleaned;
  }

  function normalizeBlockForCompare(block) {
    if (!block) return block;
    if (block.type === "text") {
      return { type: "text", content: (block.content || "").trim() };
    }
    if (block.type === "photo") {
      return {
        type: "photo",
        url: (block.url || "").trim(),
        caption: (block.caption || "").trim(),
      };
    }
    if (block.type === "side") {
      return {
        type: "side",
        side: block.side === "right" ? "right" : "left",
        url: (block.url || "").trim(),
        caption: (block.caption || "").trim(),
        content: (block.content || "").trim(),
      };
    }
    if (block.type === "carousel") {
      return {
        type: "carousel",
        photos: (block.photos || []).map(function (photo) {
          return {
            url: (photo.url || "").trim(),
            caption: (photo.caption || "").trim(),
          };
        }),
      };
    }
    return block;
  }

  function saveDay() {
    if (!currentDay) return Promise.reject(new Error("day not selected"));
    try {
      syncBlocksFromDomIfPresent();
      syncHeroFromDom();
    } catch (err) {
      setStatus("Ошибка формы: " + err.message, "err");
      return Promise.reject(err);
    }
    var payload = {
      hero: dayHero,
      blocks: cleanBlocksClient(blocks),
    };
    return fetch("/api/media/" + currentDay + "/save", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    })
      .then(function (r) {
        return r.json().then(function (data) {
          if (!r.ok || !data.ok) {
            throw new Error((data && data.error) || ("HTTP " + r.status));
          }
          return data;
        });
      })
      .then(function (data) {
        loadDayData(data);
        renderHeroFields();
        renderBlocks();
        var day = days.find(function (d) { return d.num === currentDay; });
        if (day && dayHero.title) day.city = dayHero.title;
        renderDaysList();
        els.editorTitle.textContent = dayHero.title || els.editorTitle.textContent;
        setStatus("Сохранено", "ok");
        return data;
      })
      .catch(function (err) {
        setStatus("Ошибка сохранения: " + (err.message || "неизвестная"), "err");
        throw err;
      });
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
    previewSite: previewSite,
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

  function uploadPhotoToCarousel(blockIndex, file) {
    if (!currentDay || !file) return;
    setStatus("Загрузка…");
    var form = new FormData();
    form.append("file", file);
    fetch("/api/upload/" + currentDay, { method: "POST", body: form })
      .then(function (r) { return r.json(); })
      .then(function (data) {
        syncBlocksFromDomIfPresent();
        var block = blocks[blockIndex];
        if (!block || block.type !== "carousel") return;
        if (!block.photos) block.photos = [];
        block.photos.push({ url: data.url, caption: "" });
        renderBlocks();
        setStatus("Фото добавлено в карусель. Нажми «Сохранить».", "ok");
      })
      .catch(function () { setStatus("Ошибка загрузки", "err"); });
  }

  function addCarouselBlock() {
    syncBlocksFromDomIfPresent();
    blocks.push({ type: "carousel", photos: [] });
    renderBlocks();
    setStatus("Карусель добавлена. Загрузи в неё фото.", "ok");
  }

  function addSideBlock() {
    syncBlocksFromDomIfPresent();
    blocks.push({ type: "side", side: "left", url: "", caption: "", content: "" });
    renderBlocks();
    var last = els.blocksList.querySelector(".block-item:last-child .side-content");
    if (last) last.focus();
    setStatus("Боковой блок добавлен. Загрузи фото и напиши текст.", "ok");
  }

  function uploadPhotoToSide(blockIndex, file) {
    if (!currentDay || !file) return;
    setStatus("Загрузка…");
    var form = new FormData();
    form.append("file", file);
    fetch("/api/upload/" + currentDay, { method: "POST", body: form })
      .then(function (r) { return r.json(); })
      .then(function (data) {
        if (!data.url) throw new Error("no url");
        syncBlocksFromDomIfPresent();
        var block = blocks[blockIndex];
        if (!block || block.type !== "side") {
          block = blocks.find(function (b) { return b.type === "side" && !b.url; });
        }
        if (!block) {
          throw new Error("side block not found");
        }
        block.url = data.url;
        renderBlocks();
        return saveDay();
      })
      .then(function () {
        setStatus("Фото добавлено и сохранено.", "ok");
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
    document.getElementById("nav-tiles").classList.toggle("active", view === "tiles");
    document.getElementById("nav-chapters").classList.toggle("active", view === "chapters");
    document.getElementById("nav-days").classList.toggle("active", view === "days");
    els.daysList.classList.toggle("hidden", view !== "days");
    var chaptersList = document.getElementById("chapters-list");
    if (chaptersList) chaptersList.classList.toggle("hidden", view !== "chapters");
    var tilesHint = document.getElementById("tiles-sidebar-hint");
    if (tilesHint) tilesHint.classList.toggle("hidden", view !== "tiles");
    els.emptyState.classList.toggle("hidden", view !== "days" || currentDay !== null);
    els.editorPanel.classList.toggle("hidden", view !== "days" || !currentDay);
    var tilesPanel = document.getElementById("tiles-panel");
    if (tilesPanel) tilesPanel.classList.toggle("hidden", view !== "tiles");
    var chaptersPanel = document.getElementById("chapters-panel");
    if (chaptersPanel) chaptersPanel.classList.toggle("hidden", view !== "chapters");
    document.getElementById("sidebar-subtitle").textContent =
      view === "tiles" ? "плитки и оформление" :
      view === "chapters" ? "главы — текст и цвета" :
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
    setTilesStatus("Сохранение…");
    return fetch("/api/site-settings", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    })
      .then(function (r) { return r.json(); })
      .then(function (data) {
        siteSettings = data.settings;
        accessToken = (siteSettings.meta && siteSettings.meta.access_token) || accessToken;
        setTilesStatus("Настройки сайта сохранены", "ok");
      })
      .catch(function () { setTilesStatus("Ошибка сохранения", "err"); });
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
        setTilesStatus("Сброшено к умолчанию", "ok");
      })
      .catch(function () { setTilesStatus("Ошибка сброса", "err"); });
  }

  document.getElementById("btn-add-text").addEventListener("click", addTextBlock);
  document.getElementById("btn-add-carousel").addEventListener("click", addCarouselBlock);
  document.getElementById("btn-add-side").addEventListener("click", addSideBlock);
  document.getElementById("btn-save").addEventListener("click", saveDay);
  document.getElementById("btn-build").addEventListener("click", function () {
    saveDay().then(buildSite).catch(function () {});
  });
  document.getElementById("btn-preview").addEventListener("click", function () {
    saveDay().then(buildSite).then(previewDay).catch(function () {});
  });
  document.getElementById("modal-close").addEventListener("click", closeModal);
  document.getElementById("btn-apply-crop").addEventListener("click", applyPhotoEdit);
  document.getElementById("btn-delete-block").addEventListener("click", deleteEditingBlock);
  els.photoFileInput.addEventListener("change", function (e) {
    if (e.target.files && e.target.files[0]) uploadPhoto(e.target.files[0]);
    e.target.value = "";
  });

  document.getElementById("nav-tiles").addEventListener("click", function () { switchView("tiles"); });
  document.getElementById("nav-chapters").addEventListener("click", function () { switchView("chapters"); });
  document.getElementById("nav-days").addEventListener("click", function () { switchView("days"); });
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
    fetch("/api/version")
      .then(function (r) { return r.ok ? r.json() : null; })
      .then(function (info) {
        if (!info || !info.features || info.features.indexOf("hero") === -1) {
          setStatus("Старый admin_server — останови и запусти заново: python admin_server.py", "err");
        }
      })
      .catch(function () {});
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
        setTilesStatus("Перезапусти admin_server.py (python admin_server.py)", "err");
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
