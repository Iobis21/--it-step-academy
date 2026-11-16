// კლასის არჩევა, ადგილების არჩევა თვითმფრინავის სქემაზე (ცალმხრივი/ორმხრივი) და მგზავრების ფორმები
(function () {
  const form = document.getElementById('booking-form');
  if (!form) return;

  const max = Number(form.dataset.max);
  const list = document.getElementById('passengers');
  const totalEl = document.getElementById('total');
  const errorEl = document.getElementById('seat-error');
  const bookBtn = document.getElementById('book-btn');
  const cabinRadios = form.querySelectorAll('input[name="cabin"]');

  // leg: 'out' — წასვლა, 'ret' — დაბრუნება
  const legs = {};
  form.querySelectorAll('.plane').forEach(plane => {
    legs[plane.dataset.leg] = {
      plane,
      prices: { economy: Number(plane.dataset.economy), business: Number(plane.dataset.business) },
      selected: [], // არჩეული ადგილები თანმიმდევრობით
    };
  });
  const hasReturn = 'ret' in legs;

  const currentCabin = () => form.querySelector('input[name="cabin"]:checked')?.value || 'economy';

  function applyCabin() {
    const cabin = currentCabin();
    for (const leg of Object.values(legs)) {
      leg.selected = [];
      leg.plane.querySelectorAll('.seat[data-seat]').forEach(btn => {
        btn.classList.remove('selected');
        const off = btn.dataset.cabin !== cabin;
        btn.classList.toggle('off', off);
        btn.disabled = off || btn.classList.contains('taken');
      });
      leg.plane.querySelectorAll('.cabin-section').forEach(sec =>
        sec.classList.toggle('active', sec.dataset.section === cabin));
    }
    errorEl.textContent = '';
    render();
  }

  const maxChecked = Number(form.dataset.maxChecked || 3);
  const priceLines = document.getElementById('price-lines');
  const num = (el, key) => Number(el.dataset[key] || 0);

  // დამატებითი ბარგის ფასი ერთ მგზავრზე — ჯამი ყველა ფრენაზე (წასვლა + დაბრუნება)
  function bagPrices(cabin) {
    const key = cabin === 'business' ? 'Business' : 'Economy';
    let xcabin = 0, xchecked = 0;
    for (const leg of Object.values(legs)) {
      xcabin += num(leg.plane, 'xcabin' + key);
      xchecked += num(leg.plane, 'xchecked' + key);
    }
    return {
      xcabin, xchecked,
      checkedKg: num(legs.out.plane, 'checkedKg' + key),
      cabinKg: num(legs.out.plane, 'cabinKgEconomy'),
    };
  }

  function render() {
    const saved = {};
    list.querySelectorAll('input, select').forEach(i => {
      saved[i.name] = i.type === 'checkbox' ? (i.checked ? '1' : '') : i.value;
    });
    list.innerHTML = '';
    const bp = bagPrices(currentCabin());

    const outSeats = legs.out.selected;
    const retSeats = hasReturn ? legs.ret.selected : [];
    if (!outSeats.length) list.innerHTML = '<p class="muted">აირჩიე ადგილი თვითმფრინავის სქემაზე</p>';

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
        <input name="passport_${seat}" placeholder="პასპორტი / პირადი ნომერი" required>
        <div class="bag-extras">
          ${bp.xcabin ? `
          <label class="check">
            <input type="checkbox" name="cabin_bag_${seat}" value="1" data-bag>
            ხელბარგი ${bp.cabinKg} კგ <b>+${bp.xcabin} ₾</b>
          </label>` : ''}
          <label class="bag-select">დამატებითი ჩემოდანი ${bp.checkedKg} კგ
            <select name="checked_${seat}" data-bag>
              ${Array.from({ length: maxChecked + 1 }, (_, n) =>
                `<option value="${n}">${n ? n + ' ც. (+' + n * bp.xchecked + ' ₾)' : 'არა'}</option>`).join('')}
            </select>
          </label>
        </div>`;
      fs.querySelectorAll('input:not([type=hidden]), select').forEach(inp => {
        if (inp.type === 'checkbox') inp.checked = saved[inp.name] === '1';
        else if (saved[inp.name] !== undefined) inp.value = saved[inp.name];
      });
      fs.querySelectorAll('[data-bag]').forEach(inp => inp.addEventListener('change', updateTotal));
      list.appendChild(fs);
    });

    updateTotal();

    let ready = outSeats.length > 0;
    if (hasReturn && outSeats.length && retSeats.length !== outSeats.length) {
      ready = false;
      errorEl.textContent = `დაბრუნებისთვის აირჩიე ${outSeats.length} ადგილი (არჩეულია ${retSeats.length})`;
    } else if (errorEl.dataset.kind === 'count') {
      errorEl.textContent = '';
    }
    errorEl.dataset.kind = hasReturn && !ready && outSeats.length ? 'count' : '';
    if (bookBtn) bookBtn.disabled = !ready;
  }

  function updateTotal() {
    const cabin = currentCabin();
    const bp = bagPrices(cabin);
    let tickets = 0;
    for (const leg of Object.values(legs)) tickets += leg.selected.length * leg.prices[cabin];

    let cabinBags = 0, checked = 0;
    list.querySelectorAll('input[name^="cabin_bag_"]:checked').forEach(() => cabinBags++);
    list.querySelectorAll('select[name^="checked_"]').forEach(s => (checked += Number(s.value)));
    const baggage = cabinBags * bp.xcabin + checked * bp.xchecked;

    const lines = [];
    if (tickets) lines.push(`<span>ბილეთები (${legs.out.selected.length} მგზ.)</span><b>${tickets} ₾</b>`);
    if (cabinBags) lines.push(`<span>ხელბარგი × ${cabinBags}</span><b>${cabinBags * bp.xcabin} ₾</b>`);
    if (checked) lines.push(`<span>ჩემოდანი × ${checked}</span><b>${checked * bp.xchecked} ₾</b>`);
    priceLines.innerHTML = lines.map(l => `<div>${l}</div>`).join('');
    totalEl.textContent = (tickets + baggage) + ' ₾';
  }

  Object.entries(legs).forEach(([name, leg]) => {
    leg.plane.querySelectorAll('.seat[data-seat]').forEach(btn => {
      btn.addEventListener('click', () => {
        errorEl.textContent = '';
        const seat = btn.dataset.seat;
        const idx = leg.selected.indexOf(seat);
        if (idx >= 0) {
          leg.selected.splice(idx, 1);
          btn.classList.remove('selected');
        } else {
          const limit = name === 'ret' ? legs.out.selected.length : max;
          if (leg.selected.length >= limit) {
            errorEl.textContent = name === 'ret'
              ? (limit ? 'დაბრუნებისთვის იმდენივე ადგილი აირჩიე, რამდენი მგზავრიცაა' : 'ჯერ წასვლის ადგილები აირჩიე')
              : `ერთ ჯავშანზე მაქსიმუმ ${max} მგზავრია`;
            return;
          }
          leg.selected.push(seat);
          btn.classList.add('selected');
        }
        // წასვლის ადგილის მოხსნისას ზედმეტი დაბრუნების ადგილებიც მოიხსნება
        if (hasReturn) {
          while (legs.ret.selected.length > legs.out.selected.length) {
            const last = legs.ret.selected.pop();
            legs.ret.plane.querySelector(`[data-seat="${last}"]`).classList.remove('selected');
          }
        }
        render();
      });
    });
  });

  cabinRadios.forEach(r => r.addEventListener('change', applyCabin));
  applyCabin();
})();
