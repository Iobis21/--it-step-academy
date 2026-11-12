// ადგილების არჩევა და მგზავრების ფორმების დინამიკური შექმნა
(function () {
  const form = document.getElementById('booking-form');
  if (!form) return;

  const prices = { economy: Number(form.dataset.economy), business: Number(form.dataset.business) };
  const max = Number(form.dataset.max);
  const list = document.getElementById('passengers');
  const totalEl = document.getElementById('total');
  const errorEl = document.getElementById('seat-error');
  const bookBtn = document.getElementById('book-btn');
  const selected = new Map(); // seat -> cabin

  function render() {
    // უკვე შეყვანილი მონაცემები არ დაიკარგოს
    const saved = {};
    list.querySelectorAll('input').forEach(i => (saved[i.name] = i.value));

    list.innerHTML = '';
    if (!selected.size) {
      list.innerHTML = '<p class="muted">აირჩიე ადგილი სქემაზე</p>';
    }
    for (const seat of selected.keys()) {
      const fs = document.createElement('fieldset');
      fs.className = 'passenger';
      fs.innerHTML = `
        <legend>ადგილი ${seat}</legend>
        <input type="hidden" name="seat" value="${seat}">
        <input name="first_name_${seat}" placeholder="სახელი" required>
        <input name="last_name_${seat}" placeholder="გვარი" required>
        <input name="passport_${seat}" placeholder="პასპორტი / პირადი ნომერი" required>`;
      fs.querySelectorAll('input:not([type=hidden])').forEach(i => (i.value = saved[i.name] || ''));
      list.appendChild(fs);
    }

    let total = 0;
    selected.forEach(cabin => (total += prices[cabin]));
    totalEl.textContent = total + ' ₾';
    if (bookBtn) bookBtn.disabled = selected.size === 0;
  }

  form.querySelectorAll('.seat[data-seat]').forEach(btn => {
    btn.addEventListener('click', () => {
      errorEl.textContent = '';
      const { seat, cabin } = btn.dataset;
      if (selected.has(seat)) {
        selected.delete(seat);
        btn.classList.remove('selected');
      } else {
        const currentCabin = selected.values().next().value;
        if (currentCabin && currentCabin !== cabin) {
          errorEl.textContent = 'ყველა ადგილი ერთი კლასიდან უნდა იყოს';
          return;
        }
        if (selected.size >= max) {
          errorEl.textContent = `ერთ ჯავშანზე მაქსიმუმ ${max} მგზავრია`;
          return;
        }
        selected.set(seat, cabin);
        btn.classList.add('selected');
      }
      render();
    });
  });
})();
