/* Overflow theme JS — My Cup Runneth Over
   Drawers, AJAX cart (drawer), variant picker, gallery, sticky add-to-cart,
   recommendations loader, announcement rotation, filters auto-submit,
   find-your-oil quiz, pick-your-oils collection builder. */
(function () {
  'use strict';
  const theme = window.theme || { moneyFormat: '${{amount}}', cartType: 'drawer', routes: { cart: '/cart', cartAdd: '/cart/add', cartChange: '/cart/change', cartUpdate: '/cart/update' } };
  const $ = (s, c) => (c || document).querySelector(s);
  const $$ = (s, c) => Array.from((c || document).querySelectorAll(s));

  /* ---------- money ---------- */
  function formatMoney(cents, format) {
    if (typeof cents === 'string') cents = cents.replace('.', '');
    const fmt = format || theme.moneyFormat || '${{amount}}';
    const match = /\{\{\s*(\w+)\s*\}\}/.exec(fmt);
    const key = match ? match[1] : 'amount';
    function withDelims(num, precision, thousands, decimal) {
      precision = precision == null ? 2 : precision;
      thousands = thousands || ',';
      decimal = decimal || '.';
      if (isNaN(num) || num == null) return '0';
      num = (num / 100).toFixed(precision);
      const parts = num.split('.');
      const dollars = parts[0].replace(/(\d)(?=(\d\d\d)+(?!\d))/g, '$1' + thousands);
      const centsPart = parts[1] ? decimal + parts[1] : '';
      return dollars + centsPart;
    }
    let value = '';
    switch (key) {
      case 'amount': value = withDelims(cents, 2); break;
      case 'amount_no_decimals': value = withDelims(cents, 0); break;
      case 'amount_with_comma_separator': value = withDelims(cents, 2, '.', ','); break;
      case 'amount_no_decimals_with_comma_separator': value = withDelims(cents, 0, '.', ','); break;
      case 'amount_with_apostrophe_separator': value = withDelims(cents, 2, "'", '.'); break;
      default: value = withDelims(cents, 2);
    }
    return fmt.replace(/\{\{\s*\w+\s*\}\}/, value);
  }

  /* ---------- toast ---------- */
  function toast(msg) {
    const t = $('#Toast');
    if (!t) return;
    t.textContent = msg;
    t.classList.add('is-visible');
    clearTimeout(t._timer);
    t._timer = setTimeout(() => t.classList.remove('is-visible'), 3200);
  }

  /* ---------- drawers ---------- */
  let lastFocus = null;
  function openDrawer(id, returnTo) {
    const d = document.getElementById(id);
    if (!d) return;
    lastFocus = returnTo || document.activeElement;
    closeDrawers(true);
    d.classList.add('is-open');
    d.setAttribute('aria-hidden', 'false');
    document.body.classList.add('drawer-open');
    const focusable = d.querySelector('input:not([type=hidden]), button:not([data-drawer-close]), a');
    if (focusable) setTimeout(() => focusable.focus(), 50);
  }
  function closeDrawers(silent) {
    $$('.drawer.is-open').forEach((d) => { d.classList.remove('is-open'); d.setAttribute('aria-hidden', 'true'); });
    document.body.classList.remove('drawer-open');
    if (!silent && lastFocus && lastFocus.focus) lastFocus.focus();
  }
  document.addEventListener('click', (e) => {
    const opener = e.target.closest('[data-drawer-open]');
    if (opener) { e.preventDefault(); openDrawer(opener.getAttribute('data-drawer-open')); return; }
    const closer = e.target.closest('[data-drawer-close]');
    if (closer) { e.preventDefault(); closeDrawers(); return; }
    const cartOpen = e.target.closest('[data-cart-open]');
    if (cartOpen && theme.cartType === 'drawer' && document.getElementById('CartDrawer')) { e.preventDefault(); openDrawer('CartDrawer'); }
  });
  document.addEventListener('keydown', (e) => { if (e.key === 'Escape') closeDrawers(); });

  /* ---------- cart ---------- */
  function cartError(data) {
    const err = new Error((data && (data.description || data.message)) || 'Could not add to cart');
    err.userFacing = true;
    return err;
  }
  async function refreshCart(open, returnTo) {
    try {
      const [cartRes, secRes] = await Promise.all([
        fetch(theme.routes.cart + '.js', { headers: { Accept: 'application/json' } }),
        fetch(theme.routes.root + '?sections=cart-drawer')
      ]);
      const cart = await cartRes.json();
      $$('[data-cart-count]').forEach((el) => { el.textContent = cart.item_count; el.classList.toggle('is-empty', cart.item_count === 0); });
      if (secRes.ok) {
        const sections = await secRes.json();
        const html = sections['cart-drawer'];
        if (html) {
          const doc = new DOMParser().parseFromString(html, 'text/html');
          const fresh = doc.querySelector('#CartDrawer .drawer__panel');
          const current = document.querySelector('#CartDrawer .drawer__panel');
          if (fresh && current) current.innerHTML = fresh.innerHTML;
        }
      }
      if (open) openDrawer('CartDrawer', returnTo);
      return cart;
    } catch (err) {
      console.warn('Cart refresh failed', err);
    }
  }

  document.addEventListener('submit', async (e) => {
    const form = e.target.closest('form[data-ajax-cart]');
    if (!form) return;
    if (theme.cartType !== 'drawer' || !document.getElementById('CartDrawer')) return; // normal submit → cart page
    e.preventDefault();
    const btn = form.querySelector('[type="submit"]');
    const original = btn ? btn.innerHTML : '';
    if (btn) { btn.disabled = true; btn.innerHTML = '<span>Adding…</span>'; }
    try {
      const res = await fetch(theme.routes.cartAdd + '.js', { method: 'POST', headers: { Accept: 'application/json', 'X-Requested-With': 'XMLHttpRequest' }, body: new FormData(form) });
      const data = await res.json();
      if (!res.ok) throw cartError(data);
      if (btn) { btn.disabled = false; btn.innerHTML = original; }
      await refreshCart(true, btn);
    } catch (err) {
      toast(err.userFacing ? err.message : 'Could not add to cart. Please check your connection and try again.');
    } finally {
      if (btn) { btn.disabled = false; btn.innerHTML = original; }
    }
  });

  async function changeLine(line, quantity) {
    try {
      const res = await fetch(theme.routes.cartChange + '.js', { method: 'POST', headers: { 'Content-Type': 'application/json', Accept: 'application/json' }, body: JSON.stringify({ line: Number(line), quantity: Number(quantity) }) });
      if (!res.ok) throw new Error('Could not update cart');
      if (document.body.classList.contains('template-cart')) { window.location.reload(); return; }
      await refreshCart(false);
    } catch (err) {
      toast(err.message);
    }
  }
  document.addEventListener('click', (e) => {
    const b = e.target.closest('[data-cart-change]');
    if (!b) return;
    e.preventDefault();
    changeLine(b.getAttribute('data-line'), b.getAttribute('data-qty'));
  });
  document.addEventListener('change', (e) => {
    const i = e.target.closest('[data-cart-qty]');
    if (i) changeLine(i.getAttribute('data-line'), i.value);
  });

  /* ---------- quantity steppers ---------- */
  document.addEventListener('click', (e) => {
    const minus = e.target.closest('[data-qty-minus]');
    const plus = e.target.closest('[data-qty-plus]');
    if (!minus && !plus) return;
    const wrap = (minus || plus).closest('.qty');
    const input = wrap && wrap.querySelector('input');
    if (!input) return;
    const min = Number(input.min || 1);
    let v = Number(input.value || min);
    v = minus ? Math.max(min, v - 1) : v + 1;
    input.value = v;
    input.dispatchEvent(new Event('change', { bubbles: true }));
  });

  /* ---------- product: variant picker ---------- */
  function initProduct(root) {
    const dataEl = root.querySelector('[data-variants-json]');
    if (!dataEl) return;
    let variants = [];
    try { variants = JSON.parse(dataEl.textContent); } catch (err) { return; }
    const idInput = root.querySelector('input[name="id"]');
    const priceEl = root.querySelector('[data-price]');
    const compareEl = root.querySelector('[data-compare-price]');
    const btn = root.querySelector('[data-add-button]');
    const btnText = root.querySelector('[data-add-text]');
    const stickyPrice = $('[data-sticky-price]');
    const groups = $$('[data-option-index]', root);
    const selected = () => groups.map((g) => { const c = g.querySelector('input:checked'); return c ? c.value : null; });

    function update(initial) {
      const opts = selected();
      const variant = groups.length
        ? variants.find((v) => v.options.every((o, i) => o === opts[i]))
        : (variants.find((v) => idInput && String(v.id) === String(idInput.value)) || variants[0]);
      groups.forEach((group, gi) => {
        $$('.option__value', group).forEach((val) => {
          const input = val.querySelector('input');
          const test = opts.slice(); test[gi] = input.value;
          const match = variants.find((v) => v.options.every((o, i) => test[i] === null || o === test[i]));
          val.classList.toggle('is-unavailable', !(match && match.available));
        });
        const lbl = group.querySelector('[data-selected-value]');
        if (lbl) lbl.textContent = opts[gi] || '';
      });
      if (!variant) {
        if (btn) btn.disabled = true;
        if (btnText) btnText.textContent = 'Unavailable';
        return;
      }
      if (idInput) idInput.value = variant.id;
      if (priceEl) priceEl.textContent = formatMoney(variant.price);
      if (compareEl) {
        const onSale = variant.compare_at_price && variant.compare_at_price > variant.price;
        compareEl.hidden = !onSale;
        if (onSale) compareEl.textContent = formatMoney(variant.compare_at_price);
        const wrap = priceEl && priceEl.closest('.price');
        if (wrap) wrap.classList.toggle('price--on-sale', !!onSale);
      }
      if (stickyPrice) stickyPrice.textContent = formatMoney(variant.price);
      if (btn) btn.disabled = !variant.available;
      if (btnText) btnText.textContent = variant.available ? (btn.getAttribute('data-add-label') || 'Add to cart') : 'Sold out';
      if (variant.featured_media && variant.featured_media.id) {
        const slide = document.querySelector('[data-media-id="' + variant.featured_media.id + '"]');
        if (slide && !initial) scrollToSlide(slide);
      }
      if (!initial && window.history && window.history.replaceState) {
        const url = new URL(window.location.href);
        url.searchParams.set('variant', variant.id);
        window.history.replaceState({}, '', url.toString());
      }
    }
    root.addEventListener('change', (e) => { if (e.target.matches('[data-option-index] input')) update(false); });
    update(true);
  }
  $$('[data-product-form]').forEach(initProduct);

  /* ---------- product: gallery ---------- */
  function scrollToSlide(slide) {
    const track = slide.parentElement;
    track.scrollTo({ left: slide.offsetLeft - track.offsetLeft, behavior: 'smooth' });
  }
  document.addEventListener('click', (e) => {
    const t = e.target.closest('[data-thumb]');
    if (!t) return;
    const s = document.querySelector('[data-media-id="' + t.getAttribute('data-thumb') + '"]');
    if (s) scrollToSlide(s);
  });
  const track = $('[data-slides]');
  if (track && 'IntersectionObserver' in window) {
    const io = new IntersectionObserver((entries) => {
      entries.forEach((en) => {
        if (en.isIntersecting && en.intersectionRatio > 0.6) {
          const id = en.target.getAttribute('data-media-id');
          $$('[data-thumb]').forEach((th) => th.classList.toggle('is-active', th.getAttribute('data-thumb') === id));
        }
      });
    }, { root: track, threshold: [0.6] });
    $$('.product__slide', track).forEach((s) => io.observe(s));
  }

  /* ---------- product: sticky add to cart ---------- */
  const mainAdd = $('[data-add-button]');
  const sticky = $('[data-sticky-atc]');
  if (mainAdd && sticky && 'IntersectionObserver' in window) {
    new IntersectionObserver(([en]) => {
      sticky.classList.toggle('is-visible', !en.isIntersecting && en.boundingClientRect.top < 0);
    }, { threshold: 0 }).observe(mainAdd);
  }
  document.addEventListener('click', (e) => {
    const b = e.target.closest('[data-sticky-submit]');
    if (!b) return;
    const form = document.getElementById(b.getAttribute('data-sticky-submit'));
    if (form) { if (form.requestSubmit) form.requestSubmit(); else form.submit(); }
  });

  /* ---------- product: share ---------- */
  document.addEventListener('click', async (e) => {
    const b = e.target.closest('[data-share]');
    if (!b) return;
    const url = b.getAttribute('data-share') || window.location.href;
    try {
      if (navigator.share) await navigator.share({ url, title: document.title });
      else { await navigator.clipboard.writeText(url); toast('Link copied'); }
    } catch (err) { /* user cancelled */ }
  });

  /* ---------- recommendations ---------- */
  $$('[data-recommendations-url]').forEach(async (el) => {
    try {
      const res = await fetch(el.getAttribute('data-recommendations-url'));
      if (!res.ok) return;
      const html = await res.text();
      const doc = new DOMParser().parseFromString(html, 'text/html');
      const inner = doc.querySelector('[data-recommendations-inner]');
      const target = el.querySelector('[data-recommendations-inner]');
      if (inner && target && inner.innerHTML.trim()) target.innerHTML = inner.innerHTML;
    } catch (err) { /* silent */ }
  });

  /* ---------- announcement rotation ---------- */
  $$('[data-announcement]').forEach((bar) => {
    const items = $$('.announcement__item', bar);
    if (items.length < 2) return;
    let i = 0;
    const interval = Number(bar.getAttribute('data-interval')) || 5000;
    setInterval(() => { items[i].classList.remove('is-active'); i = (i + 1) % items.length; items[i].classList.add('is-active'); }, interval);
  });

  /* ---------- header shadow ---------- */
  const header = $('[data-header]');
  if (header) {
    const onScroll = () => header.classList.toggle('is-scrolled', window.scrollY > 8);
    onScroll();
    window.addEventListener('scroll', onScroll, { passive: true });
  }

  /* ---------- auto-submit (sort + filters) ---------- */
  document.addEventListener('change', (e) => {
    const el = e.target.closest('[data-auto-submit]');
    if (el && el.form) el.form.submit();
  });
  document.addEventListener('click', (e) => {
    const t = e.target.closest('[data-toggle]');
    if (!t) return;
    e.preventDefault();
    const target = document.getElementById(t.getAttribute('data-toggle'));
    if (!target) return;
    if (!('toggleHidden' in target.dataset)) target.dataset.toggleHidden = String(target.hidden);
    const open = !target.classList.contains('is-open');
    target.classList.toggle('is-open', open);
    if (target.dataset.toggleHidden === 'true') target.hidden = !open;
    if (open) { const f = target.querySelector('input'); if (f) f.focus(); }
  });

  /* ---------- cart note (drawer): save on change ---------- */
  document.addEventListener('change', (e) => {
    const n = e.target.closest('[data-cart-note]');
    if (!n) return;
    fetch(theme.routes.cartUpdate + '.js', { method: 'POST', headers: { 'Content-Type': 'application/json', Accept: 'application/json' }, body: JSON.stringify({ note: n.value }) }).catch(() => {});
  });

  /* ---------- find-your-oil quiz ---------- */
  function escapeHtml(s) {
    return String(s == null ? '' : s).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  }
  function initQuiz(quiz) {
    if (quiz.dataset.quizReady) return;
    quiz.dataset.quizReady = 'true';
    let products = {};
    try { products = JSON.parse(($('[data-quiz-products]', quiz) || {}).textContent || '{}'); } catch (err) { console.warn('Quiz data could not be read', err); }
    const steps = $$('[data-quiz-step]', quiz);
    const dots = $$('[data-quiz-dot]', quiz);
    const result = $('[data-quiz-result]', quiz);
    const collectionNote = $('[data-quiz-collection]', quiz);
    const panel = $('.quiz__panel', quiz);
    let answer = null;
    function show(n) {
      steps.forEach((s) => { const on = s.getAttribute('data-quiz-step') === String(n); s.hidden = !on; s.classList.toggle('is-active', on); });
      dots.forEach((d) => d.classList.toggle('is-active', Number(d.getAttribute('data-quiz-dot')) <= n));
      const active = steps.find((s) => !s.hidden);
      const focusEl = active && active.querySelector('.quiz__q');
      if (focusEl) { focusEl.setAttribute('tabindex', '-1'); focusEl.focus({ preventScroll: true }); }
      if (panel && panel.getBoundingClientRect().top < 96) panel.scrollIntoView({ block: 'start' });
    }
    function render(forWhom) {
      const p = products[answer];
      if (!p || !result) return;
      const img = p.image ? '<img src="' + escapeHtml(p.image) + '" alt="" width="300" height="300" loading="lazy">' : '';
      const buy = p.available
        ? '<form action="' + escapeHtml(theme.routes.cartAdd) + '" method="post" data-ajax-cart class="quiz__buy"><input type="hidden" name="id" value="' + escapeHtml(p.variant) + '"><input type="hidden" name="quantity" value="1"><button type="submit" class="btn btn--primary">Add to cart · ' + escapeHtml(p.price) + '</button></form>'
        : '<p class="muted">Sold out for now.</p>';
      result.innerHTML =
        '<article class="quiz__card" style="--oil:' + escapeHtml(p.color || '') + '">' +
          '<a class="quiz__card-media" href="' + escapeHtml(p.url) + '" tabindex="-1" aria-hidden="true">' + img + '</a>' +
          '<div class="quiz__card-body">' +
            '<h3 class="quiz__card-title"><a href="' + escapeHtml(p.url) + '">' + escapeHtml(p.title) + '</a></h3>' +
            (p.refs ? '<p class="quiz__card-refs">' + escapeHtml(p.refs) + '</p>' : '') +
            (p.why ? '<p class="quiz__card-why">' + escapeHtml(p.why) + '</p>' : '') +
            (p.meaning ? '<p class="quiz__card-meaning">On the label: “' + escapeHtml(p.meaning) + '”</p>' : '') +
            '<div class="quiz__card-actions">' + buy + '<a class="link-arrow" href="' + escapeHtml(p.url) + '">Read about this oil</a></div>' +
          '</div>' +
        '</article>';
      if (collectionNote) collectionNote.hidden = !(forWhom === 'gift' || forWhom === 'church');
    }
    quiz.addEventListener('click', (e) => {
      const a = e.target.closest('[data-quiz-answer]');
      if (a) { answer = a.getAttribute('data-quiz-answer'); $$('[data-quiz-answer]', quiz).forEach((b) => b.setAttribute('aria-pressed', String(b === a))); show(2); return; }
      const f = e.target.closest('[data-quiz-for]');
      if (f) { render(f.getAttribute('data-quiz-for')); show(3); return; }
      if (e.target.closest('[data-quiz-back]')) { show(1); return; }
      if (e.target.closest('[data-quiz-restart]')) { answer = null; if (result) result.innerHTML = ''; show(1); }
    });
  }

  /* ---------- collection builder (pick any N oils) ---------- */
  function initBundle(root) {
    if (root.dataset.bundleReady) return;
    root.dataset.bundleReady = 'true';
    const size = Number(root.getAttribute('data-bundle-size')) || 6;
    const rows = $$('[data-bundle-oil]', root);
    const counts = new Map(rows.map((r) => [r, 0]));
    const slots = $$('[data-bundle-slot]', root);
    const status = $('[data-bundle-status]', root);
    const chosen = $('[data-bundle-chosen]', root);
    const property = $('[data-bundle-property]', root);
    const submit = $('[data-bundle-submit]', root);
    const reset = $('[data-bundle-reset]', root);
    const form = $('[data-bundle-form]', root);
    const label = submit ? submit.innerHTML : '';
    const soldOut = !!(submit && submit.hasAttribute('data-bundle-soldout'));
    let busy = false;
    const total = () => Array.from(counts.values()).reduce((a, b) => a + b, 0);
    const firstPlus = () => $$('[data-bundle-plus]', root).find((b) => !b.disabled);
    function picks() {
      const list = [];
      rows.forEach((r) => { const n = counts.get(r); if (n) list.push({ name: r.getAttribute('data-bundle-oil'), n, color: r.style.getPropertyValue('--oil') }); });
      return list;
    }
    function update() {
      const n = total();
      const full = n >= size;
      rows.forEach((r) => {
        const c = counts.get(r);
        $('[data-bundle-count]', r).textContent = c;
        r.classList.toggle('is-picked', c > 0);
        const minus = $('[data-bundle-minus]', r);
        const plus = $('[data-bundle-plus]', r);
        if (minus) minus.disabled = busy || c === 0;
        if (plus) plus.disabled = busy || soldOut || full || r.classList.contains('is-unavailable');
      });
      const list = picks();
      let i = 0;
      slots.forEach((s) => { s.style.removeProperty('--oil'); s.classList.remove('is-filled'); });
      list.forEach((p) => { for (let k = 0; k < p.n && i < slots.length; k++, i++) { slots[i].style.setProperty('--oil', p.color); slots[i].classList.add('is-filled'); } });
      if (status) {
        status.textContent = soldOut ? 'The collection is sold out for now'
          : full ? 'Your collection is ready'
          : n === 0 ? 'Choose ' + size + ' bottles'
          : n + ' of ' + size + ' chosen. ' + (size - n) + ' to go.';
      }
      if (chosen) chosen.innerHTML = list.map((p) => '<li style="--oil:' + escapeHtml(p.color) + '"><span></span>' + escapeHtml(p.name) + (p.n > 1 ? ' ×' + p.n : '') + '</li>').join('');
      if (property) property.value = list.map((p) => p.name + (p.n > 1 ? ' ×' + p.n : '')).join(', ');
      if (submit) submit.disabled = busy || soldOut || !full;
      if (reset) reset.hidden = n === 0;
      root.classList.toggle('is-full', full);
    }
    root.addEventListener('click', (e) => {
      if (busy) return;
      const plus = e.target.closest('[data-bundle-plus]');
      const minus = e.target.closest('[data-bundle-minus]');
      if (plus || minus) {
        const btn = plus || minus;
        const r = btn.closest('[data-bundle-oil]');
        const c = counts.get(r) || 0;
        if (plus && total() < size) counts.set(r, c + 1);
        if (minus && c > 0) counts.set(r, c - 1);
        update();
        if (btn.disabled) {
          // The control the shopper used just disabled itself; keep keyboard focus nearby.
          const next = plus
            ? (submit && !submit.disabled ? submit : $('[data-bundle-minus]', r))
            : $('[data-bundle-plus]', r);
          if (next && !next.disabled) next.focus();
        }
        return;
      }
      if (e.target.closest('[data-bundle-reset]')) {
        rows.forEach((r) => counts.set(r, 0));
        update();
        const first = firstPlus();
        if (first) first.focus();
      }
    });
    if (form) form.addEventListener('submit', async (e) => {
      e.preventDefault();
      if (busy || soldOut || total() !== size || !submit || submit.disabled) return;
      busy = true;
      update();
      submit.textContent = 'Adding…';
      let added = false;
      try {
        const res = await fetch(theme.routes.cartAdd + '.js', { method: 'POST', headers: { Accept: 'application/json', 'X-Requested-With': 'XMLHttpRequest' }, body: new FormData(form) });
        const data = await res.json();
        if (!res.ok) throw cartError(data);
        added = true;
        rows.forEach((r) => counts.set(r, 0));
      } catch (err) {
        toast(err.userFacing ? err.message : 'Could not add your collection. Please check your connection and try again.');
      } finally {
        busy = false;
        submit.innerHTML = label;
        update();
      }
      if (!added) return;
      if (theme.cartType === 'drawer' && document.getElementById('CartDrawer')) await refreshCart(true, firstPlus() || submit);
      else window.location.href = theme.routes.cart;
    });
    update();
  }

  $$('[data-quiz]').forEach(initQuiz);
  $$('[data-bundle]').forEach(initBundle);
  document.addEventListener('shopify:section:load', (e) => {
    $$('[data-quiz]', e.target).forEach(initQuiz);
    $$('[data-bundle]', e.target).forEach(initBundle);
  });

  /* ---------- end ---------- */
  window.theme.formatMoney = formatMoney;
  window.theme.toast = toast;
  window.theme.openDrawer = openDrawer;
  window.theme.refreshCart = refreshCart;
})();
