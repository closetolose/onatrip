(function () {
  "use strict";

  var STORAGE_KEY = "trip_live_token";
  var meta = document.querySelector('meta[name="trip-access-token"]');
  var tokenRequired = meta ? meta.getAttribute("content") : "";

  function checkAccess() {
    if (!tokenRequired) return true;
    var params = new URLSearchParams(window.location.search);
    var fromUrl = params.get("k");
    if (fromUrl && fromUrl === tokenRequired) {
      sessionStorage.setItem(STORAGE_KEY, fromUrl);
      return true;
    }
    return sessionStorage.getItem(STORAGE_KEY) === tokenRequired;
  }

  function showApp() {
    document.getElementById("gate").classList.add("hidden");
    document.getElementById("app").classList.remove("hidden");
  }

  function showGate() {
    document.getElementById("gate").classList.remove("hidden");
    document.getElementById("app").classList.add("hidden");
    document.getElementById("gate-submit").addEventListener("click", function () {
      var input = document.getElementById("gate-input");
      if (input.value.trim() === tokenRequired) {
        sessionStorage.setItem(STORAGE_KEY, tokenRequired);
        showApp();
      } else {
        input.style.borderColor = "#f87171";
      }
    });
  }

  document.addEventListener("DOMContentLoaded", function () {
    if (tokenRequired && !checkAccess()) {
      showGate();
    } else {
      showApp();
    }
  });
})();
