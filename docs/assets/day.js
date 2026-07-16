(function () {
  "use strict";

  function prefersReducedMotion() {
    return window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  }

  function initCarousel(root) {
    var track = root.querySelector(".day-carousel-track");
    var slides = Array.prototype.slice.call(root.querySelectorAll(".day-carousel-slide"));
    if (!track || slides.length < 2) return;

    var prevBtn = root.querySelector(".day-carousel-prev");
    var nextBtn = root.querySelector(".day-carousel-next");
    var dotsHost = root.querySelector(".day-carousel-dots");
    var index = 0;

    function scrollTo(i) {
      index = (i + slides.length) % slides.length;
      var slide = slides[index];
      track.scrollTo({ left: slide.offsetLeft, behavior: "smooth" });
      updateDots();
    }

    function updateDots() {
      if (!dotsHost) return;
      dotsHost.querySelectorAll(".day-carousel-dot").forEach(function (dot, i) {
        dot.setAttribute("aria-selected", i === index ? "true" : "false");
        dot.classList.toggle("is-active", i === index);
      });
    }

    if (dotsHost) {
      dotsHost.innerHTML = "";
      slides.forEach(function (_slide, i) {
        var dot = document.createElement("button");
        dot.type = "button";
        dot.className = "day-carousel-dot";
        dot.setAttribute("role", "tab");
        dot.setAttribute("aria-label", "Слайд " + (i + 1));
        dot.addEventListener("click", function () {
          scrollTo(i);
        });
        dotsHost.appendChild(dot);
      });
    }

    if (prevBtn) {
      prevBtn.addEventListener("click", function () {
        scrollTo(index - 1);
      });
    }
    if (nextBtn) {
      nextBtn.addEventListener("click", function () {
        scrollTo(index + 1);
      });
    }

    track.addEventListener(
      "scroll",
      function () {
        var center = track.scrollLeft + track.clientWidth / 2;
        var nearest = index;
        var nearestDist = Infinity;
        slides.forEach(function (slide, i) {
          var slideCenter = slide.offsetLeft + slide.clientWidth / 2;
          var dist = Math.abs(center - slideCenter);
          if (dist < nearestDist) {
            nearestDist = dist;
            nearest = i;
          }
        });
        if (nearest !== index) {
          index = nearest;
          updateDots();
        }
      },
      { passive: true }
    );

    root.addEventListener("keydown", function (e) {
      if (e.key === "ArrowLeft") scrollTo(index - 1);
      if (e.key === "ArrowRight") scrollTo(index + 1);
    });

    updateDots();
  }

  function initReveal() {
    if (prefersReducedMotion()) return;

    var blocks = Array.prototype.slice.call(
      document.querySelectorAll(".day-story > .day-block")
    );
    if (!blocks.length) return;

    blocks.forEach(function (block) {
      block.classList.add("day-reveal-pending");
    });

    var observer = new IntersectionObserver(
      function (entries) {
        entries.forEach(function (entry) {
          if (!entry.isIntersecting) return;
          entry.target.classList.add("day-reveal-visible");
          entry.target.classList.remove("day-reveal-pending");
          observer.unobserve(entry.target);
        });
      },
      { root: null, rootMargin: "0px 0px -8% 0px", threshold: 0.12 }
    );

    blocks.forEach(function (block) {
      observer.observe(block);
    });
  }

  function initParallax() {
    if (prefersReducedMotion()) return;

    var cover = document.querySelector(".day-cover--has-image");
    var coverInner = cover ? cover.querySelector(".day-cover-inner") : null;
    var photoFrames = Array.prototype.slice.call(
      document.querySelectorAll("[data-parallax-photo]")
    );
    var ticking = false;

    function clamp(value, min, max) {
      return Math.min(max, Math.max(min, value));
    }

    function update() {
      var scrollY = window.scrollY || window.pageYOffset;
      var viewportH = window.innerHeight;

      if (cover) {
        var coverRect = cover.getBoundingClientRect();
        var coverHeight = cover.offsetHeight || 1;
        var localScroll = clamp(scrollY, 0, coverHeight);
        var progress = localScroll / coverHeight;

        cover.style.setProperty("--day-cover-shift", (localScroll * 0.38) + "px");
        cover.style.setProperty("--day-cover-scale", String(1.08 + progress * 0.05));

        if (coverInner) {
          cover.style.setProperty("--day-cover-text-shift", (localScroll * 0.16) + "px");
          cover.style.setProperty(
            "--day-cover-text-opacity",
            String(1 - clamp(progress * 1.15, 0, 1))
          );
        }
      }

      photoFrames.forEach(function (frame) {
        var rect = frame.getBoundingClientRect();
        if (rect.bottom < 0 || rect.top > viewportH) return;
        var center = rect.top + rect.height * 0.5;
        var offset = (center - viewportH * 0.5) * 0.14;
        frame.style.setProperty("--day-photo-shift", offset.toFixed(2) + "px");
      });

      ticking = false;
    }

    function onScroll() {
      if (ticking) return;
      ticking = true;
      window.requestAnimationFrame(update);
    }

    window.addEventListener("scroll", onScroll, { passive: true });
    window.addEventListener("resize", onScroll, { passive: true });
    update();
  }

  document.querySelectorAll("[data-carousel]").forEach(initCarousel);
  initReveal();
  initParallax();
})();
