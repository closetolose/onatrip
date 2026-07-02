(function () {
  "use strict";

  var days = [];
  var currentDay = null;
  var photos = [];
  var intro = "";
  var cropper = null;
  var editingIndex = -1;
  var accessToken = "";
  var sortable = null;

  var els = {
    daysList: document.getElementById("days-list"),
    emptyState: document.getElementById("empty-state"),
    editorPanel: document.getElementById("editor-panel"),
    editorDayLabel: document.getElementById("editor-day-label"),
    editorTitle: document.getElementById("editor-title"),
    intro: document.getElementById("intro"),
    photoGrid: document.getElementById("photo-grid"),
    status: document.getElementById("status"),
    fileInput: document.getElementById("file-input"),
    modal: document.getElementById("modal"),
    cropImage: document.getElementById("crop-image"),
    cropCaption: document.getElementById("crop-caption"),
  };

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
        '<div class="num">День ' + day.num + "</div>" +
        '<div class="title">' + day.date.slice(0, 5) + " · " + day.weekday + "</div>" +
        '<div class="city">' + day.city + "</div>";
      btn.addEventListener("click", function () { selectDay(day.num); });
      els.daysList.appendChild(btn);
    });
  }

  function renderPhotos() {
    els.photoGrid.innerHTML = "";
    photos.forEach(function (photo, index) {
      var item = document.createElement("div");
      item.className = "photo-item";
      item.dataset.index = String(index);
      item.innerHTML =
        '<img src="' + mediaUrl(photo.url) + '" alt="">' +
        '<div class="cap">' + (photo.caption || "Без подписи") + "</div>";
      item.addEventListener("click", function () { openEditor(index); });
      els.photoGrid.appendChild(item);
    });

    if (sortable) sortable.destroy();
    sortable = Sortable.create(els.photoGrid, {
      animation: 150,
      draggable: ".photo-item",
      onEnd: function () {
        var next = [];
        els.photoGrid.querySelectorAll(".photo-item").forEach(function (node) {
          next.push(photos[Number(node.dataset.index)]);
        });
        photos = next;
        renderPhotos();
      },
    });
  }

  function selectDay(dayNum) {
    currentDay = dayNum;
    renderDaysList();
    fetch("/api/media/" + dayNum)
      .then(function (r) { return r.json(); })
      .then(function (data) {
        intro = data.intro || "";
        photos = (data.photos || []).map(function (p) {
          if (typeof p === "string") return { url: p, caption: "" };
          return { url: p.url, caption: p.caption || "" };
        });
        var meta = currentDayMeta();
        els.emptyState.classList.add("hidden");
        els.editorPanel.classList.remove("hidden");
        els.editorDayLabel.textContent = "День " + dayNum;
        els.editorTitle.textContent = meta ? meta.city : "";
        els.intro.value = intro;
        renderPhotos();
        setStatus("");
      })
      .catch(function () { setStatus("Не удалось загрузить день", "err"); });
  }

  function saveDay() {
    if (!currentDay) return;
    intro = els.intro.value.trim();
    return fetch("/api/media/" + currentDay, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ intro: intro, photos: photos }),
    })
      .then(function (r) { return r.json(); })
      .then(function () { setStatus("Сохранено", "ok"); })
      .catch(function () { setStatus("Ошибка сохранения", "err"); });
  }

  function buildSite() {
    setStatus("Сборка…");
    return fetch("/api/build", { method: "POST" })
      .then(function (r) { return r.json(); })
      .then(function (data) {
        if (data.ok) {
          setStatus("Сайт собран. Можно пушить docs/ на GitHub.", "ok");
        } else {
          setStatus("Ошибка сборки: " + (data.stderr || data.stdout || ""), "err");
        }
      })
      .catch(function () { setStatus("Ошибка сборки", "err"); });
  }

  function uploadFiles(fileList) {
    if (!currentDay || !fileList.length) return;
    setStatus("Загрузка…");
    var chain = Promise.resolve();
    Array.from(fileList).forEach(function (file) {
      chain = chain.then(function () {
        var form = new FormData();
        form.append("file", file);
        return fetch("/api/upload/" + currentDay, { method: "POST", body: form })
          .then(function (r) { return r.json(); })
          .then(function (data) {
            if (data.url) photos.push({ url: data.url, caption: "" });
          });
      });
    });
    chain.then(function () {
      renderPhotos();
      setStatus("Фото загружены. Не забудь сохранить.", "ok");
    });
  }

  function closeModal() {
    if (cropper) {
      cropper.destroy();
      cropper = null;
    }
    els.modal.classList.add("hidden");
    editingIndex = -1;
  }

  function openEditor(index) {
    editingIndex = index;
    var photo = photos[index];
    var isLocal = photo.url.indexOf("media/day-") === 0;
    els.cropCaption.value = photo.caption || "";
    els.cropImage.src = mediaUrl(photo.url);
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

  function applyCrop() {
    if (editingIndex < 0 || !currentDay) return;
    var photo = photos[editingIndex];
    var isLocal = photo.url.indexOf("media/day-") === 0;
    photos[editingIndex].caption = els.cropCaption.value.trim();

    if (!isLocal || !cropper) {
      closeModal();
      renderPhotos();
      setStatus("Подпись обновлена. Нажми «Сохранить».", "ok");
      return;
    }

    var canvas = cropper.getCroppedCanvas({ maxWidth: 1600, maxHeight: 1600 });
    if (!canvas) return;

    canvas.toBlob(function (blob) {
      var form = new FormData();
      form.append("file", blob, "crop.jpg");
      form.append("source_url", photos[editingIndex].url);
      fetch("/api/crop/" + currentDay, { method: "POST", body: form })
        .then(function (r) { return r.json(); })
        .then(function (data) {
          photos[editingIndex].url = data.url;
          closeModal();
          renderPhotos();
          setStatus("Обрезка применена. Нажми «Сохранить».", "ok");
        })
        .catch(function () { setStatus("Ошибка обрезки", "err"); });
    }, "image/jpeg", 0.9);
  }

  function deletePhoto() {
    if (editingIndex < 0) return;
    photos.splice(editingIndex, 1);
    closeModal();
    renderPhotos();
    setStatus("Фото удалено из списка. Нажми «Сохранить».", "ok");
  }

  function previewDay() {
    if (!currentDay) return;
    var url = "/preview/days/" + String(currentDay).padStart(2, "0") + ".html";
    if (accessToken) url += "?k=" + encodeURIComponent(accessToken);
    window.open(url, "_blank");
  }

  document.getElementById("btn-save").addEventListener("click", saveDay);
  document.getElementById("btn-build").addEventListener("click", function () {
    saveDay().then(buildSite);
  });
  document.getElementById("btn-preview").addEventListener("click", function () {
    saveDay().then(buildSite).then(previewDay);
  });
  document.getElementById("modal-close").addEventListener("click", closeModal);
  document.getElementById("btn-apply-crop").addEventListener("click", applyCrop);
  document.getElementById("btn-delete-photo").addEventListener("click", deletePhoto);
  els.fileInput.addEventListener("change", function (e) {
    uploadFiles(e.target.files);
    e.target.value = "";
  });
  els.intro.addEventListener("input", function () {
    intro = els.intro.value;
  });

  Promise.all([
    fetch("/api/days").then(function (r) { return r.json(); }),
    fetch("/api/config").then(function (r) { return r.json(); }),
  ])
    .then(function (results) {
      days = results[0];
      accessToken = results[1].access_token || "";
      renderDaysList();
      if (days.length) selectDay(days[0].num);
    })
    .catch(function () { setStatus("Не удалось загрузить данные", "err"); });
})();
