(function () {
  "use strict";

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

  document.querySelectorAll("[data-carousel]").forEach(initCarousel);
})();
