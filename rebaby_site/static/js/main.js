console.log("ReBaby: script chargé");

// ✅ Fade-in sur les images au chargement
window.addEventListener("load", () => {
  document.querySelectorAll("img").forEach((img) => {
    img.style.opacity = 1;
  });
});

// ✅ AOS init (si la librairie est chargée)
if (window.AOS) {
  AOS.init({ duration: 800, once: true });
}

// ✅ Parallax-like : bébé qui bouge au scroll
(function () {
  const baby = document.querySelector(".hero-baby");
  if (!baby) return;
  window.addEventListener(
    "scroll",
    () => {
      const sc = window.scrollY || window.pageYOffset;
      const offset = Math.min(60, sc * 0.12);
      baby.style.transform = `translateY(-${offset}px)`;
    },
    { passive: true }
  );
})();

// ✅ MENU LATERAL + OVERLAY
function toggleMenu() {
  const sideMenu = document.getElementById("sideMenu");
  const overlay = document.getElementById("overlay");

  if (!sideMenu || !overlay) return;

  sideMenu.classList.toggle("open");

  if (sideMenu.classList.contains("open")) {
    overlay.style.opacity = "1";
    overlay.style.visibility = "visible";
  } else {
    overlay.style.opacity = "0";
    overlay.style.visibility = "hidden";
  }
}

// ✅ Fermer si on clique sur l’overlay
window.addEventListener("click", (e) => {
  const sideMenu = document.getElementById("sideMenu");
  const overlay = document.getElementById("overlay");
  const hamburger = document.querySelector(".hamburger");

  if (!sideMenu || !overlay || !hamburger) return;

  if (
    sideMenu.classList.contains("open") &&
    !sideMenu.contains(e.target) &&
    !hamburger.contains(e.target)
  ) {
    sideMenu.classList.remove("open");
    overlay.style.opacity = "0";
    overlay.style.visibility = "hidden";
  }
});
