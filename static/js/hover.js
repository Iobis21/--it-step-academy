// „სინათლე კურსორის ქვეშ“: ბარათს ვაწვდით მაუსის კოორდინატებს (--mx, --my),
// CSS კი იმ წერტილში ხატავს რბილ სინათლეს და ანათებს ჩარჩოს.
document.querySelectorAll('.flight-card, .cabin-option > span, .boarding-pass').forEach(function (el) {
  el.classList.add('spotlight');
  el.addEventListener('pointermove', function (e) {
    const rect = el.getBoundingClientRect();
    el.style.setProperty('--mx', (e.clientX - rect.left) + 'px');
    el.style.setProperty('--my', (e.clientY - rect.top) + 'px');
  });
});
