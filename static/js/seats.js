// ადგილების არჩევა (ცალმხრივი და ორმხრივი ფრენისთვის) და მგზავრების ფორმები
(function () {
  const form = document.getElementById('booking-form');
  if (!form) return;

  const max = Number(form.dataset.max);
  const list = document.getElementById('passengers');
  const totalEl = document.getElementById('total');
  const errorEl = document.getElementById('seat-error');
  const bookBtn = document.getElementById('book-btn');

  // leg: 'out' — წასვლა, 'ret' — დაბრუნება
  const legs = {};
  form.querySelectorAll('.seat-map').forEach(map => {
    legs[map.dataset.leg] = {
      prices: { economy: Number(map.dataset.economy), business: Number(map.dataset.business) },
      selected: new Map(), // seat -> cabin
    };
  });
  const hasReturn = 'ret' in legs;

  function cabinInUse() {
    for (const leg of Object.values(legs)) {
      const first = leg.selected.values().next().value;
      if (first) return first;
    }
    return null;
  }

  function render() {
    const saved = {};
    list.querySelectorAll('input').forEach(i => (saved[i.name] = i.value));
    list.innerHTML = '';

    const outSeats = [...legs.out.selected.keys()];
    const retSeats = hasReturn ? [...legs.ret.selected.keys()] : [];
    if (!outSeats.length) list.innerHTML = '<p class="muted">აირჩიე ადგილი სქემაზე</p>';

    outSeats.forEach((seat, i) => {
      const retSeat = retSeats[i];
      const fs = document.createElement('fieldset');
      fs.className = 'passenger';
      fs.innerHTML = `
        <legend>მგზავრი ${i + 1} · ${seat}${hasReturn ? ' / ' + (retSeat || '—') : ''}</legend>
        <input type="hidden" name="seat" value="${seat}">
        ${retSeat ? `<input type="hidden" name="return_seat" value="${retSeat}">` : ''}
        <input name="first_name_${seat}" placeholder="სახელი" required>
        <input name="last_name_${seat}" placeholder="გვარი" required>
        <input name="passport_${seat}" placeholder="პასპორტი / პირადი ნომერი" required>`;
      fs.querySelectorAll('input:not([type=hidden])').forEach(inp => (inp.value = saved[inp.name] || ''));
      list.appendChild(fs);
    });

    let total = 0;
    for (const leg of Object.values(legs)) leg.selected.forEach(cabin => (total += leg.prices[cabin]));
    totalEl.textContent = total + ' ₾';

    let ready = outSeats.length > 0;
    if (hasReturn && retSeats.length !== outSeats.length) {
      ready = false;
      if (outSeats.length) errorEl.textContent = `დაბრუნებისთვის აირჩიე ${outSeats.length} ადგილი (არჩეულია ${retSeats.length})`;
    } else if (errorEl.dataset.soft) {
      errorEl.textContent = '';
    }
    errorEl.dataset.soft = '1';
    if (bookBtn) bookBtn.disabled = !ready;
  }

  form.querySelectorAll('.seat-map').forEach(map => {
    const leg = legs[map.dataset.leg];
    map.querySelectorAll('.seat[data-seat]').forEach(btn => {
      btn.addEventListener('click', () => {
        errorEl.textContent = '';
        const { seat, cabin } = btn.dataset;
        if (leg.selected.has(seat)) {
          leg.selected.delete(seat);
          btn.classList.remove('selected');
        } else {
          const current = cabinInUse();
          if (current && current !== cabin) {
            errorEl.textContent = 'ყველა ადგილი ერთი კლასიდან უნდა იყოს';
            return;
          }
          const limit = map.dataset.leg === 'ret' ? legs.out.selected.size : max;
          if (leg.selected.size >= limit) {
            errorEl.textContent = map.dataset.leg === 'ret'
              ? 'დაბრუნებისთვის იმდენივე ადგილი აირჩიე, რამდენი მგზავრიცაა'
              : `ერთ ჯავშანზე მაქსიმუმ ${max} მგზავრია`;
            return;
          }
          leg.selected.set(seat, cabin);
          btn.classList.add('selected');
        }
        // წასვლის ადგილის მოხსნისას ზედმეტი დაბრუნების ადგილებიც მოიხსნება
        if (hasReturn) {
          while (legs.ret.selected.size > legs.out.selected.size) {
            const last = [...legs.ret.selected.keys()].pop();
            legs.ret.selected.delete(last);
            form.querySelector(`.seat-map[data-leg="ret"] [data-seat="${last}"]`).classList.remove('selected');
          }
        }
        render();
      });
    });
  });
})();
