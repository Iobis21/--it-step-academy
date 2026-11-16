// ცალმხრივი / ორმხრივი გადამრთველი და „საიდან ⇄ სად“ ღილაკი
(function () {
  document.querySelectorAll('form').forEach(form => {
    const radios = form.querySelectorAll('input[name="trip_type"]');
    if (!radios.length) return;
    const returnFields = form.querySelectorAll('[data-return-field]');

    function update() {
      const isReturn = form.querySelector('input[name="trip_type"]:checked')?.value === 'return';
      returnFields.forEach(el => {
        el.hidden = !isReturn;
        el.querySelectorAll('input').forEach(i => (i.disabled = !isReturn));
      });
    }
    radios.forEach(r => r.addEventListener('change', update));
    update();

    const swap = form.querySelector('[data-swap]');
    if (swap) {
      swap.addEventListener('click', () => {
        const from = form.querySelector('[name="origin"]');
        const to = form.querySelector('[name="destination"]');
        [from.value, to.value] = [to.value, from.value];
      });
    }
  });
})();
