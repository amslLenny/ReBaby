
console.log('ReBaby: script chargé');
window.addEventListener('load', ()=>{
  document.querySelectorAll('img').forEach(img=>{
    img.style.opacity = 1;
  });
});

// AOS init (si pas déjà présent)
if (window.AOS) {
  AOS.init({ duration: 800, once: true });
}

// Parallax-like: déplacer l'image bébé légèrement au scroll
(function() {
  const baby = document.querySelector('.hero-baby');
  if (!baby) return;
  window.addEventListener('scroll', () => {
    const sc = window.scrollY || window.pageYOffset;
    // on déplace verticalement proportionnellement au scroll (valeurs réglables)
    const offset = Math.min(60, sc * 0.12);
    baby.style.transform = `translateY(-${offset}px)`;
  }, { passive: true });
})();
