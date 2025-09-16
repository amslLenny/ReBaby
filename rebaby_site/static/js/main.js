
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

function toggleMenu() {
  const menu = document.getElementById("navMenu");
  menu.style.display = (menu.style.display === "block") ? "none" : "block";
}

function toggleMenu(){
  const btn = document.getElementById('hamburgerBtn');
  const menu = document.getElementById('navMenu');
  const expanded = btn.getAttribute('aria-expanded') === 'true';
  btn.setAttribute('aria-expanded', String(!expanded));
  menu.style.display = expanded ? 'none' : 'block';
  menu.setAttribute('aria-hidden', String(expanded));
}
window.addEventListener('click', function(e){
  const menu = document.getElementById('navMenu');
  const btn = document.getElementById('hamburgerBtn');
  if(!menu || !btn) return;
  if(menu.style.display === 'block' && !btn.contains(e.target) && !menu.contains(e.target)){
    menu.style.display = 'none';
    btn.setAttribute('aria-expanded','false');
    menu.setAttribute('aria-hidden','true');
  }
});
