(function () {
  "use strict";

  const STORAGE_KEY = "trip_live_token";

  function parseIsoDate(iso) {
    const [y, m, d] = iso.split("-").map(Number);
    return new Date(y, m - 1, d);
  }

  function formatTodayLabel(day) {
    const shortDate = day.date.slice(0, 5);
    return `Сегодня, ${shortDate} — ${day.city}`;
  }

  function formatNoteTime(iso) {
    if (!iso) return "";
    try {
      return new Intl.DateTimeFormat("ru-RU", {
        day: "numeric",
        month: "short",
        hour: "2-digit",
        minute: "2-digit",
      }).format(new Date(iso));
    } catch {
      return iso;
    }
  }

  function renderHighlights(container, highlights) {
    container.innerHTML = "";
    if (!highlights || !highlights.length) {
      container.innerHTML = '<p class="empty-state">Спокойный день без крупных переездов</p>';
      return;
    }
    const ul = document.createElement("ul");
    ul.className = "highlights";
    highlights.forEach(function (h) {
      const li = document.createElement("li");
      li.innerHTML =
        '<div class="hl-time">' + escapeHtml(h.time) + "</div>" +
        '<div class="hl-icon">' + (h.icon || "📍") + "</div>" +
        '<div class="hl-body"><strong>' + escapeHtml(h.place) + "</strong>" +
        "<span>" + escapeHtml(h.action) + "</span></div>";
      ul.appendChild(li);
    });
    container.appendChild(ul);
  }

  function escapeHtml(s) {
    if (!s) return "";
    return String(s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function findDayByDate(days, today) {
    const todayIso =
      today.getFullYear() +
      "-" +
      String(today.getMonth() + 1).padStart(2, "0") +
      "-" +
      String(today.getDate()).padStart(2, "0");
    return days.find(function (d) { return d.date_iso === todayIso; });
  }

  function findTomorrow(days, today) {
    const tomorrow = new Date(today);
    tomorrow.setDate(tomorrow.getDate() + 1);
    return findDayByDate(days, tomorrow);
  }

  function dayPhase(day, today) {
    const d = parseIsoDate(day.date_iso);
    const t = new Date(today.getFullYear(), today.getMonth(), today.getDate());
    if (d.getTime() === t.getTime()) return "today";
    if (d < t) return "past";
    return "future";
  }

  function renderRoute(route, activeRegion) {
    const strip = document.getElementById("route-strip");
    if (!strip) return;
    strip.innerHTML = "";
    route.forEach(function (node) {
      const pill = document.createElement("div");
      pill.className = "route-pill";
      if (node.region === activeRegion) pill.classList.add("active");
      pill.style.setProperty("--accent", node.accent);
      pill.innerHTML =
        '<div class="date">' + escapeHtml(node.date) + "</div>" +
        '<div class="code">' + escapeHtml(node.code) + "</div>" +
        '<div class="name">' + escapeHtml(node.name) + "</div>";
      strip.appendChild(pill);
    });
  }

  function renderDaysList(days, today) {
    const list = document.getElementById("days-list");
    if (!list) return;
    list.innerHTML = "";

    days.forEach(function (day) {
      const phase = dayPhase(day, today);
      const details = document.createElement("details");
      details.className = "day-item " + phase;
      if (phase === "today") details.open = true;

      const summary = document.createElement("summary");
      summary.innerHTML =
        '<span class="day-num">День ' + day.num + "</span>" +
        '<div class="day-summary-text">' +
        '<div class="date">' + escapeHtml(day.date.slice(0, 5)) + " · " + escapeHtml(day.weekday) + "</div>" +
        '<div class="city">' + escapeHtml(day.city) + "</div></div>";

      const body = document.createElement("div");
      body.className = "day-body";
      let html = "";
      if (day.night) html += '<div class="night-line">🛏 ' + escapeHtml(day.night) + "</div>";
      if (day.highlights && day.highlights.length) {
        html += day.highlights.map(function (h) {
          return "• " + escapeHtml(h.time) + " — " + escapeHtml(h.action);
        }).join("<br>");
      } else {
        html += "Без крупных переездов";
      }
      body.innerHTML = html;

      details.appendChild(summary);
      details.appendChild(body);
      list.appendChild(details);
    });
  }

  function renderStatus(status) {
    const banner = document.getElementById("note-banner");
    if (!banner) return;
    if (!status.note) {
      banner.classList.add("hidden");
      return;
    }
    banner.classList.remove("hidden");
    banner.classList.toggle("warn", status.status === "delay" || status.status === "issue");
    document.getElementById("note-text").textContent = status.note;
    document.getElementById("note-time").textContent = status.note_updated
      ? "Обновлено: " + formatNoteTime(status.note_updated)
      : "";
  }

  function renderTrip(data) {
    const today = new Date();
    const todayDay = findDayByDate(data.days, today);
    const tomorrowDay = findTomorrow(data.days, today);

    const nowTitle = document.getElementById("now-title");
    const nowNight = document.getElementById("now-night");
    const nowHighlights = document.getElementById("now-highlights");
    const tomorrowBlock = document.getElementById("tomorrow-block");
    const tomorrowTitle = document.getElementById("tomorrow-title");
    const tomorrowEvent = document.getElementById("tomorrow-event");

    if (todayDay) {
      nowTitle.innerHTML = formatTodayLabel(todayDay).replace(" — ", ' — <span class="now-city">') + "</span>";
      nowNight.textContent = todayDay.night ? "Ночёвка: " + todayDay.night : "";
      renderHighlights(nowHighlights, todayDay.highlights);
      renderRoute(data.route, todayDay.region);
    } else {
      const start = parseIsoDate(data.meta.period_start);
      const end = parseIsoDate(data.meta.period_end);
      const t = new Date(today.getFullYear(), today.getMonth(), today.getDate());
      if (t < start) {
        nowTitle.textContent = "Поездка скоро начнётся";
        nowNight.textContent = "Старт: " + data.meta.period;
      } else if (t > end) {
        nowTitle.textContent = "Поездка завершена";
        nowNight.textContent = "Добро пожаловать домой!";
      } else {
        nowTitle.textContent = "Сегодня между этапами маршрута";
        nowNight.textContent = "";
      }
      nowHighlights.innerHTML = '<p class="empty-state">Нет записи на сегодняшнюю дату</p>';
      renderRoute(data.route, null);
    }

    if (tomorrowDay) {
      tomorrowBlock.classList.remove("hidden");
      tomorrowTitle.textContent = tomorrowDay.date.slice(0, 5) + " · " + tomorrowDay.city;
      if (tomorrowDay.main_event) {
        const ev = tomorrowDay.main_event;
        tomorrowEvent.textContent = (ev.icon || "") + " " + ev.time + " — " + ev.action;
      } else if (tomorrowDay.highlights && tomorrowDay.highlights[0]) {
        const ev = tomorrowDay.highlights[0];
        tomorrowEvent.textContent = ev.time + " — " + ev.action;
      } else {
        tomorrowEvent.textContent = tomorrowDay.night || "Спокойный день";
      }
    } else {
      tomorrowBlock.classList.add("hidden");
    }

    renderStatus(data.status);
    renderDaysList(data.days, today);
  }

  function checkAccess(tokenRequired) {
    if (!tokenRequired) return true;
    const params = new URLSearchParams(window.location.search);
    const fromUrl = params.get("k");
    if (fromUrl && fromUrl === tokenRequired) {
      sessionStorage.setItem(STORAGE_KEY, fromUrl);
      return true;
    }
    return sessionStorage.getItem(STORAGE_KEY) === tokenRequired;
  }

  function showGate(tokenRequired) {
    document.getElementById("gate").classList.remove("hidden");
    document.getElementById("app").classList.add("hidden");
    const btn = document.getElementById("gate-submit");
    const input = document.getElementById("gate-input");
    btn.addEventListener("click", function () {
      if (input.value.trim() === tokenRequired) {
        sessionStorage.setItem(STORAGE_KEY, tokenRequired);
        document.getElementById("gate").classList.add("hidden");
        document.getElementById("app").classList.remove("hidden");
        loadTrip();
      } else {
        input.style.borderColor = "#f87171";
      }
    });
  }

  function loadTrip() {
    fetch("trip.json")
      .then(function (r) { return r.json(); })
      .then(renderTrip)
      .catch(function () {
        document.getElementById("now-title").textContent = "Не удалось загрузить данные";
      });
  }

  document.addEventListener("DOMContentLoaded", function () {
    fetch("trip.json")
      .then(function (r) { return r.json(); })
      .then(function (data) {
        const token = data.meta && data.meta.access_token;
        if (token && !checkAccess(token)) {
          showGate(token);
          return;
        }
        document.getElementById("gate").classList.add("hidden");
        document.getElementById("app").classList.remove("hidden");
        renderTrip(data);
      })
      .catch(function () {
        document.getElementById("now-title").textContent = "Ошибка загрузки trip.json";
      });
  });
})();
