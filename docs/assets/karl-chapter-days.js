(function () {
  "use strict";

  if (!document.body.classList.contains("chapter-karl")) return;

  var rotateEl = document.querySelector(".pages.rotate.axis");
  var globeCamera = document.querySelector(
    ".section_top + .section_middle .camera"
  );
  var worldEl = document.querySelector(".world.axis");
  var scrollPages = document.querySelectorAll(".section_behind .page");
  var panels = Array.prototype.slice.call(
    document.querySelectorAll(".page_panel")
  );
  if (!rotateEl || !scrollPages.length || !panels.length) return;

  var total = scrollPages.length;
  var step = total > 1 ? 360 / (total - 1) : 0;
  var coarseMedia = window.matchMedia("(pointer: coarse)");
  var coarsePointer = coarseMedia.matches;
  var cameraResetTimer = null;
  var mousePointerDown = false;

  function scrollProgress() {
    var maxScroll = document.documentElement.scrollHeight - window.innerHeight;
    if (maxScroll <= 0) return 0;
    return Math.max(0, Math.min(1, window.scrollY / maxScroll));
  }

  function panelProgress() {
    return scrollProgress() * (total - 1);
  }

  /** Child panel slot on the ring (matches build in karl_index.py). */
  function panelSlotAngle(index) {
    if (total <= 1) return -180;
    return -180 + step * index;
  }

  /**
   * Parent rotation must NEGATE the active slot so that panel faces the camera.
   * (Original Webflow: parent 180° → -180° while children stay at fixed slots.)
   */
  function parentAngleForProgress(progress) {
    return -panelSlotAngle(progress);
  }

  function panelOpacity(panelIndex, progress) {
    var dist = Math.abs(progress - panelIndex);
    var cutoff = coarsePointer ? 0.26 : 0.4;
    if (dist >= cutoff) return 0;
    var falloff = coarsePointer ? 2.4 : 1.5;
    return Math.pow(Math.max(0, Math.cos(dist * (Math.PI / 2))), falloff);
  }

  function setPanelVisual(panel, opacity) {
    var item = panel.querySelector(".item.pages");
    if (!item) return;
    item.style.opacity = String(opacity);
    var visibilityAt = coarsePointer ? 0.15 : 0.08;
    item.style.visibility = opacity > visibilityAt ? "visible" : "hidden";
    var interactAt = coarsePointer ? 0.52 : 0.35;
    item.style.pointerEvents = opacity > interactAt ? "auto" : "none";
    var scale = 0.9 + opacity * 0.1;
    item.style.transform =
      "translate3d(0px, -50vw, 2vw) scale(" + scale + ")";
    var link = panel.querySelector(".karl-day-link");
    if (link) {
      link.style.pointerEvents = opacity > interactAt ? "auto" : "none";
      link.style.cursor = opacity > interactAt ? "pointer" : "default";
    }
    if (opacity > interactAt) {
      panel.classList.add("is-front");
    } else {
      panel.classList.remove("is-front");
    }
  }

  function resetSceneCameras() {
    if (!coarsePointer) return;
    document.querySelectorAll("body.chapter-karl .section_middle .camera").forEach(function (camera) {
      camera.style.transform = "";
      camera.style.webkitTransform = "";
    });
  }

  function resetGlobeCameraParallax() {
    if (!globeCamera) return;
    globeCamera.style.transform = "";
    globeCamera.style.webkitTransform = "";
  }

  function scheduleCameraReset() {
    if (coarsePointer) return;
    if (mousePointerDown) return;
    if (cameraResetTimer) {
      clearTimeout(cameraResetTimer);
    }
    cameraResetTimer = setTimeout(resetGlobeCameraParallax, 120);
  }

  function onPointerLeave(e) {
    if (e.pointerType && e.pointerType !== "mouse") return;
    scheduleCameraReset();
  }

  function accessKey() {
    try {
      var fromStorage = sessionStorage.getItem("liveplan_access_key");
      if (fromStorage) return fromStorage.trim();
    } catch (e) {}
    try {
      return (new URLSearchParams(window.location.search).get("k") || "").trim();
    } catch (e2) {
      return "";
    }
  }

  function dayUrl(href) {
    if (!href) return "";
    var key = accessKey();
    if (!key) return href;
    try {
      var url = new URL(href, window.location.href);
      if (!url.searchParams.has("k")) {
        url.searchParams.set("k", key);
      }
      var path = url.pathname;
      var base = window.location.pathname.replace(/[^/]+$/, "");
      if (base && path.indexOf(base) === 0) {
        path = path.slice(base.length);
      }
      return path + url.search + url.hash;
    } catch (e) {
      return href;
    }
  }

  function bindDayLinks() {
    document.addEventListener("click", function (e) {
      var link = e.target.closest(".karl-day-link");
      if (!link) return;
      if (link.style.pointerEvents === "none") {
        e.preventDefault();
        return;
      }
      var href = dayUrl(link.getAttribute("href"));
      if (!href) return;
      e.preventDefault();
      window.location.assign(href);
    });
  }

  function applyFrame() {
    var progress = panelProgress();
    var angle = parentAngleForProgress(progress);
    var transform = "rotateX(" + angle + "deg) rotateY(0deg) rotateZ(0deg)";

    rotateEl.style.transform = transform;
    rotateEl.style.webkitTransform = transform;
    rotateEl.style.transformStyle = "preserve-3d";
    rotateEl.style.webkitTransformStyle = "preserve-3d";

    panels.forEach(function (panel, index) {
      setPanelVisual(panel, panelOpacity(index, progress));
    });

    if (worldEl) {
      if (coarsePointer) {
        var worldFade = Math.min(1, Math.max(0, (progress - 0.06) / 0.14));
        worldEl.style.opacity = String(worldFade);
        worldEl.style.visibility = worldFade > 0.02 ? "visible" : "hidden";
      } else {
        worldEl.style.opacity = "1";
        worldEl.style.visibility = "visible";
      }
    }

    if (coarsePointer) {
      resetGlobeCameraParallax();
      resetSceneCameras();
    }
  }

  var framePending = false;
  function scheduleFrame() {
    if (framePending) return;
    framePending = true;
    window.requestAnimationFrame(function () {
      framePending = false;
      applyFrame();
    });
  }

  coarseMedia.addEventListener("change", function (e) {
    coarsePointer = e.matches;
    if (coarsePointer) {
      if (cameraResetTimer) {
        clearTimeout(cameraResetTimer);
        cameraResetTimer = null;
      }
      resetGlobeCameraParallax();
    }
  });

  var root = document.documentElement;
  root.addEventListener("pointerdown", function (e) {
    if (e.pointerType === "mouse") {
      mousePointerDown = true;
    }
  });
  root.addEventListener("pointerup", function (e) {
    if (e.pointerType === "mouse") {
      mousePointerDown = false;
    }
  });
  root.addEventListener("pointercancel", function (e) {
    if (e.pointerType === "mouse") {
      mousePointerDown = false;
    }
  });
  root.addEventListener("mouseleave", scheduleCameraReset);
  root.addEventListener("pointerleave", onPointerLeave);
  root.addEventListener("touchend", scheduleCameraReset);
  root.addEventListener("touchcancel", scheduleCameraReset);

  window.addEventListener("scroll", scheduleFrame, { passive: true });
  window.addEventListener("resize", scheduleFrame);
  window.addEventListener("load", function () {
    if (window.LivePlanGate && window.LivePlanGate.propagateKeyToLinks) {
      window.LivePlanGate.propagateKeyToLinks();
    }
    bindDayLinks();
    applyFrame();
  });
  bindDayLinks();
  applyFrame();
})();
