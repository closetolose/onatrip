(function () {
  "use strict";

  var STORAGE_KEY = "liveplan_access_key";
  var gateEl = document.getElementById("gate-overlay");
  if (!gateEl) return;

  var requiredToken = (gateEl.getAttribute("data-access-token") || "").trim();
  var form = document.getElementById("gate-form");
  var input = document.getElementById("gate-input");
  var errorEl = document.getElementById("gate-error");

  function getUrlKey() {
    try {
      var params = new URLSearchParams(window.location.search);
      return (params.get("k") || "").trim();
    } catch (e) {
      return "";
    }
  }

  function getStoredKey() {
    try {
      return (sessionStorage.getItem(STORAGE_KEY) || "").trim();
    } catch (e) {
      return "";
    }
  }

  function storeKey(key) {
    try {
      sessionStorage.setItem(STORAGE_KEY, key);
    } catch (e) {}
  }

  function isAuthorized() {
    if (!requiredToken) return true;
    var key = getUrlKey() || getStoredKey();
    return key === requiredToken;
  }

  function showGate() {
    gateEl.classList.remove("hidden");
    gateEl.removeAttribute("hidden");
    gateEl.setAttribute("aria-hidden", "false");
    document.body.classList.add("gate-locked");
    if (input) {
      input.value = getUrlKey();
      input.focus();
    }
  }

  function hideGate() {
    gateEl.classList.add("hidden");
    gateEl.setAttribute("hidden", "");
    gateEl.setAttribute("aria-hidden", "true");
    document.body.classList.remove("gate-locked");
  }

  function showError() {
    if (errorEl) errorEl.classList.remove("hidden");
  }

  function hideError() {
    if (errorEl) errorEl.classList.add("hidden");
  }

  function propagateKeyToLinks() {
    if (!requiredToken) return;
    var key = getStoredKey() || getUrlKey();
    if (!key) return;

    document.querySelectorAll("a[href]").forEach(function (anchor) {
      var href = anchor.getAttribute("href");
      if (!href || href.charAt(0) === "#") return;
      if (href.indexOf("mailto:") === 0 || href.indexOf("tel:") === 0) return;
      if (/^https?:\/\//i.test(href)) return;
      try {
        var url = new URL(href, window.location.href);
        if (url.searchParams.has("k")) return;
        url.searchParams.set("k", key);
        var relative = url.pathname + url.search + url.hash;
        if (href.charAt(0) !== "/" && !/^[a-z]+:/i.test(href)) {
          var base = window.location.pathname.replace(/[^/]+$/, "");
          if (relative.indexOf(base) === 0 && base !== "/") {
            relative = relative.slice(base.length);
          }
        }
        anchor.setAttribute("href", relative);
      } catch (e) {}
    });
  }

  function initGate() {
    if (!requiredToken) {
      hideGate();
      return;
    }

    var urlKey = getUrlKey();
    if (urlKey && urlKey === requiredToken) {
      storeKey(urlKey);
    }

    if (isAuthorized()) {
      hideGate();
      propagateKeyToLinks();
      return;
    }

    showGate();
  }

  if (form) {
    form.addEventListener("submit", function (e) {
      e.preventDefault();
      hideError();
      var val = (input && input.value || "").trim();
      if (val === requiredToken) {
        storeKey(val);
        hideGate();
        propagateKeyToLinks();
      } else {
        showError();
      }
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initGate);
  } else {
    initGate();
  }

  window.LivePlanGate = {
    el: gateEl,
    init: initGate,
    isAuthorized: isAuthorized,
    propagateKeyToLinks: propagateKeyToLinks,
  };
})();
