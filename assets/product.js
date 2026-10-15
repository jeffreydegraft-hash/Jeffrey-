/* ==========================================================================
   Olivet — product.js
   <variant-picker>, <media-gallery> (+ lightbox), <sticky-buy-bar>,
   <product-recommendations>.
   Vanilla, no dependencies beyond window.Olivet (assets/theme.js) and
   Olivet.motion (assets/motion.js) for springs. Every lookup is guarded:
   a missing element is a no-op, never a throw.
   ========================================================================== */
(() => {
  const Olivet = (window.Olivet = window.Olivet || {});
  const strings = Olivet.strings || {};
  const config = Olivet.config || {};
  const EVENTS = Olivet.EVENTS || { variantChanged: 'variant:changed' };
  const publish = (name, data) => {
    if (Olivet.pubsub && typeof Olivet.pubsub.publish === 'function') Olivet.pubsub.publish(name, data);
  };
  const subscribe = (name, cb) =>
    Olivet.pubsub && typeof Olivet.pubsub.subscribe === 'function' ? Olivet.pubsub.subscribe(name, cb) : () => {};
  const reducedMotion = () =>
    typeof Olivet.prefersReducedMotion === 'function'
      ? Olivet.prefersReducedMotion()
      : window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  const motion = () => (Olivet.motion && typeof Olivet.motion.animate === 'function' ? Olivet.motion : null);

  /* Money in the shop's format; with currency codes when the theme shows them. */
  const formatPrice = (cents) => {
    if (typeof Olivet.formatMoney !== 'function') return null;
    const format = config.currencyCodeEnabled ? config.moneyWithCurrencyFormat : config.moneyFormat;
    return Olivet.formatMoney(cents, format || undefined);
  };

  const readJson = (root, selector) => {
    const el = root && root.querySelector(selector);
    if (!el) return null;
    try {
      return JSON.parse(el.textContent);
    } catch (e) {
      return null;
    }
  };

  /* Label morph for Add → Sold out: blur-crossfade via .btn.is-transitioning */
  const swapLabel = (button, text) => {
    if (!button) return;
    const label = button.querySelector('[data-add-label]');
    if (!label || label.textContent.trim() === text) return;
    if (reducedMotion()) {
      label.textContent = text;
      return;
    }
    button.classList.add('is-transitioning');
    setTimeout(() => {
      label.textContent = text;
      button.classList.remove('is-transitioning');
    }, 120);
  };

  /* ---------- variant-picker ---------- */
  if (!customElements.get('variant-picker')) {
    customElements.define(
      'variant-picker',
      class VariantPicker extends HTMLElement {
        connectedCallback() {
          this.sectionId = this.dataset.section || '';
          this.url = this.dataset.url || window.location.pathname;
          this.updateUrl = this.dataset.updateUrl !== 'false';
          this.variants = readJson(this, '[data-variants]') || [];
          this.currentVariant = readJson(this, '[data-selected-variant]');
          this.groups = Array.from(this.querySelectorAll('fieldset'));
          this.onChange = this.onChange.bind(this);
          this.addEventListener('change', this.onChange);
          this.markAvailability();
        }

        disconnectedCallback() {
          this.removeEventListener('change', this.onChange);
          if (this.controller) this.controller.abort();
        }

        get form() {
          const input = this.querySelector('input[form], select[form]');
          const id = input && input.getAttribute('form');
          return id ? document.getElementById(id) : this.closest('form');
        }

        get selectedOptions() {
          return this.groups.map((group) => {
            const checked = group.querySelector('input[type="radio"]:checked');
            if (checked) return checked.value;
            const select = group.querySelector('select');
            return select ? select.value : null;
          });
        }

        get submitButton() {
          return document.getElementById(`ProductSubmitButton-${this.sectionId}`);
        }

        findVariant(options) {
          return this.variants.find((v) => Array.isArray(v.options) && v.options.every((opt, i) => opt === options[i])) || null;
        }

        onChange(event) {
          if (event && event.target && !event.target.matches('input[type="radio"], select')) return;
          const options = this.selectedOptions;
          this.updateSelectedLabels();
          this.markAvailability();
          const variant = this.findVariant(options);
          this.currentVariant = variant;
          this.updateVariantInput(variant);
          this.setButtonState(variant);
          this.updateURL(variant);
          this.updateMedia(variant);
          if (!variant) {
            publish(EVENTS.variantChanged, { variant: null, sectionId: this.sectionId });
            return;
          }
          this.renderSection(variant);
          publish(EVENTS.variantChanged, { variant, sectionId: this.sectionId });
        }

        updateSelectedLabels() {
          this.groups.forEach((group) => {
            const checked = group.querySelector('input[type="radio"]:checked');
            const select = group.querySelector('select');
            const label = group.querySelector('[data-selected-value]');
            const value = checked ? checked.value : select ? select.value : '';
            if (label) label.textContent = value;
            group.querySelectorAll('input[type="radio"]').forEach((input) => {
              const card = group.querySelector(`label[for="${input.id}"]`);
              if (card) card.classList.toggle('is-selected', input.checked);
            });
          });
        }

        /* Each card shows the variant it leads to with the other current
           selections: its price, and a struck-through name when that variant
           can't be bought. Purely visual; the radios stay selectable. */
        markAvailability() {
          if (!this.variants.length) return;
          const selected = this.selectedOptions;
          this.groups.forEach((group, index) => {
            group.querySelectorAll('input[type="radio"]').forEach((input) => {
              const card = group.querySelector(`label[for="${input.id}"]`);
              if (!card) return;
              const match = this.variants.find(
                (v) => Array.isArray(v.options) && v.options.every((opt, i) => (i === index ? opt === input.value : opt === selected[i]))
              );
              const available = !!(match && match.available);
              card.classList.toggle('is-unavailable', !available);
              const note = card.querySelector('[data-option-unavailable]');
              if (note) note.hidden = available;
              const price = card.querySelector('[data-option-price]');
              if (price) {
                const text = match ? formatPrice(match.price) : '';
                if (text !== null) {
                  price.textContent = text;
                  price.hidden = !text;
                }
              }
            });
          });
        }

        updateVariantInput(variant) {
          const form = this.form;
          if (!form) return;
          const input = form.querySelector('input[name="id"]');
          if (!input) return;
          if (variant) {
            input.value = variant.id;
            input.disabled = !variant.available;
          } else {
            input.disabled = true;
          }
        }

        setButtonState(variant) {
          const button = this.submitButton;
          if (!button) return;
          if (!variant) {
            button.disabled = true;
            swapLabel(button, strings.unavailable || 'Unavailable');
          } else if (!variant.available) {
            button.disabled = true;
            swapLabel(button, strings.soldOut || 'Sold out');
          } else {
            button.disabled = false;
            swapLabel(button, strings.addToCart || 'Add to Bag');
          }
        }

        updateURL(variant) {
          if (!variant || !this.updateUrl || !window.history || !window.history.replaceState) return;
          try {
            const url = new URL(this.url, window.location.origin);
            url.searchParams.set('variant', variant.id);
            window.history.replaceState({}, '', `${url.pathname}${url.search}`);
          } catch (e) {
            /* ignore malformed urls */
          }
        }

        updateMedia(variant) {
          if (!variant || !variant.featured_media || !variant.featured_media.id) return;
          const gallery = document.getElementById(`MediaGallery-${this.sectionId}`);
          if (gallery && typeof gallery.setActive === 'function') gallery.setActive(variant.featured_media.id, { scroll: true });
        }

        renderSection(variant) {
          if (this.controller) this.controller.abort();
          this.controller = new AbortController();
          const sep = this.url.includes('?') ? '&' : '?';
          const url = `${this.url}${sep}variant=${variant.id}&section_id=${encodeURIComponent(this.sectionId)}`;
          const price = document.getElementById(`price-${this.sectionId}`);
          if (price) price.classList.add('is-loading');
          fetch(url, { signal: this.controller.signal })
            .then((res) => (res.ok ? res.text() : Promise.reject(new Error(String(res.status)))))
            .then((html) => {
              const doc = new DOMParser().parseFromString(html, 'text/html');
              this.swap(doc, `price-${this.sectionId}`);
              this.swap(doc, `Sku-${this.sectionId}`, true);
              this.swap(doc, `Inventory-${this.sectionId}`, true);
              this.syncButton(doc);
              this.syncQuantity(doc);
            })
            .catch(() => {
              /* aborted or offline: the JSON-derived state above still holds */
            })
            .finally(() => {
              if (price) price.classList.remove('is-loading');
            });
        }

        swap(doc, id, copyHidden) {
          const next = doc.getElementById(id);
          const current = document.getElementById(id);
          if (!next || !current) return;
          current.innerHTML = next.innerHTML;
          if (copyHidden) current.toggleAttribute('hidden', next.hasAttribute('hidden'));
        }

        syncButton(doc) {
          const next = doc.getElementById(`ProductSubmitButton-${this.sectionId}`);
          const button = this.submitButton;
          if (!next || !button) return;
          button.disabled = next.hasAttribute('disabled');
          const label = next.querySelector('[data-add-label]');
          if (label) swapLabel(button, label.textContent.trim());
        }

        syncQuantity(doc) {
          const next = doc.getElementById(`Quantity-${this.sectionId}`);
          const current = document.getElementById(`Quantity-${this.sectionId}`);
          if (!next || !current) return;
          ['min', 'max', 'step'].forEach((attr) => {
            if (next.hasAttribute(attr)) current.setAttribute(attr, next.getAttribute(attr));
            else current.removeAttribute(attr);
          });
          const min = parseInt(current.min || '1', 10);
          const max = current.max ? parseInt(current.max, 10) : Infinity;
          const value = parseInt(current.value, 10) || min;
          current.value = Math.min(Math.max(value, min), max);
          const wrapper = current.closest('quantity-input');
          if (wrapper && typeof wrapper.validate === 'function') wrapper.validate();
        }
      }
    );
  }

  /* ---------- media-gallery ---------- */
  if (!customElements.get('media-gallery')) {
    customElements.define(
      'media-gallery',
      class MediaGallery extends HTMLElement {
        connectedCallback() {
          this.track = this.querySelector('[data-track]');
          this.slides = Array.from(this.querySelectorAll('[data-slide]'));
          this.thumbs = Array.from(this.querySelectorAll('[data-thumb]'));
          this.dots = Array.from(this.querySelectorAll('[data-dot]'));
          this.lightbox = this.querySelector('[data-lightbox]');
          this.layout = this.dataset.layout || 'thumbnails';
          this.desktop = window.matchMedia('(min-width: 990px)');
          this.phone = window.matchMedia('(max-width: 749px)');
          this.onClick = this.onClick.bind(this);
          this.onThumbKeydown = this.onThumbKeydown.bind(this);
          this.addEventListener('click', this.onClick);
          this.thumbs.forEach((thumb) => thumb.addEventListener('keydown', this.onThumbKeydown));
          this.observeSlides();
          this.bindLightbox();
          // Deep link to a variant whose media is not first: line the carousel up without motion.
          const active = this.activeSlide;
          if (active && this.slides.indexOf(active) > 0 && !this.desktop.matches) this.scrollToSlide(active, 'auto');
        }

        disconnectedCallback() {
          this.removeEventListener('click', this.onClick);
          if (this.io) this.io.disconnect();
          this.endDrag();
        }

        get activeSlide() {
          return this.slides.find((slide) => slide.classList.contains('is-active')) || this.slides[0] || null;
        }

        get activeId() {
          const slide = this.activeSlide;
          return slide ? slide.dataset.mediaId : null;
        }

        onClick(event) {
          const thumb = event.target.closest('[data-thumb]');
          if (thumb && this.contains(thumb)) {
            this.setActive(thumb.dataset.mediaId, { scroll: true });
            return;
          }
          const dot = event.target.closest('[data-dot]');
          if (dot && this.contains(dot)) {
            this.setActive(dot.dataset.mediaId, { scroll: true });
            return;
          }
          const opener = event.target.closest('[data-lightbox-open]');
          if (opener && this.contains(opener)) {
            event.preventDefault();
            this.openLightbox(opener);
            return;
          }
          if (event.target.closest('[data-lightbox-close]')) this.closeLightbox();
        }

        /* Public: called by <variant-picker> with the variant's featured media id. */
        setActive(mediaId, options = {}) {
          const id = String(mediaId);
          const slide = this.slides.find((s) => s.dataset.mediaId === id);
          if (!slide) return;
          this.slides.forEach((s) => {
            const active = s === slide;
            s.classList.toggle('is-active', active);
            if (!active) s.querySelectorAll('video').forEach((video) => video.pause && video.pause());
          });
          this.thumbs.forEach((t) => t.setAttribute('aria-pressed', String(t.dataset.mediaId === id)));
          this.dots.forEach((d) => d.setAttribute('aria-current', d.dataset.mediaId === id ? 'true' : 'false'));
          if (options.fromScroll) return;
          if (!this.desktop.matches) {
            this.scrollToSlide(slide, reducedMotion() ? 'auto' : 'smooth');
          } else if (this.layout === 'stacked' && options.scroll) {
            slide.scrollIntoView({ block: 'nearest', behavior: reducedMotion() ? 'auto' : 'smooth' });
          }
        }

        scrollToSlide(slide, behavior) {
          if (!this.track || !slide) return;
          const left = slide.offsetLeft - this.track.offsetLeft;
          if (typeof this.track.scrollTo === 'function') this.track.scrollTo({ left, behavior: behavior || 'smooth' });
          else this.track.scrollLeft = left;
        }

        /* Mobile carousel → dots follow the slide in view. */
        observeSlides() {
          if (!this.track || !('IntersectionObserver' in window) || this.slides.length < 2) return;
          this.io = new IntersectionObserver(
            (entries) => {
              if (this.desktop.matches) return; // desktop stage/stack is not a scroll container
              entries.forEach((entry) => {
                if (entry.isIntersecting && entry.intersectionRatio >= 0.6) {
                  this.setActive(entry.target.dataset.mediaId, { fromScroll: true });
                }
              });
            },
            { root: this.track, threshold: [0.6] }
          );
          this.slides.forEach((slide) => this.io.observe(slide));
        }

        onThumbKeydown(event) {
          const index = this.thumbs.indexOf(event.currentTarget);
          if (index < 0) return;
          let next = null;
          switch (event.key) {
            case 'ArrowDown':
            case 'ArrowRight':
              next = Math.min(index + 1, this.thumbs.length - 1);
              break;
            case 'ArrowUp':
            case 'ArrowLeft':
              next = Math.max(index - 1, 0);
              break;
            case 'Home':
              next = 0;
              break;
            case 'End':
              next = this.thumbs.length - 1;
              break;
            default:
              return;
          }
          event.preventDefault();
          const thumb = this.thumbs[next];
          if (!thumb) return;
          thumb.focus();
          this.setActive(thumb.dataset.mediaId, { scroll: true });
        }

        /* ---- lightbox (native <dialog>) ----
           Large screens: a centred modal; it scales .96 → 1 from its centre on
           a spring (Lightbox preset: 0.4s, no bounce) while it fades in.
           Phones: full screen. The image follows the finger 1:1 when dragged
           down, rubber-bands upward, and on release either springs home with
           the finger's velocity or, if the projected landing point passes 30%
           of the screen (or the flick is fast), carries on off screen and
           closes (apple-design §2, §5, §6, §9). */
        bindLightbox() {
          if (!this.lightbox || typeof this.lightbox.showModal !== 'function') return;
          this.lbPanel = this.lightbox.querySelector('[data-lightbox-panel]');
          this.lbBody = this.lightbox.querySelector('[data-lightbox-body]');
          this.lbScrim = this.lightbox.querySelector('[data-lightbox-scrim]');
          this.lightbox.addEventListener('click', (event) => {
            // Outside the centred panel (the scrim or the dialog's own box) closes
            if (event.target === this.lightbox || event.target === this.lbScrim) this.closeLightbox();
          });
          this.lightbox.addEventListener('cancel', (event) => {
            event.preventDefault(); // Escape: run the exit motion first
            this.closeLightbox();
          });
          this.lightbox.addEventListener('close', () => this.resetLightbox());
          this.onDragDown = this.onDragDown.bind(this);
          this.onDragMove = this.onDragMove.bind(this);
          this.onDragUp = this.onDragUp.bind(this);
          this.onViewport = this.onViewport.bind(this);
          if (this.lbBody) this.lbBody.addEventListener('pointerdown', this.onDragDown);
        }

        lightboxRest() {
          // Where the panel enters from and leaves to: centred scale on large screens, a short rise on phones
          return this.phone.matches ? 'translateY(48px)' : 'scale(0.96)';
        }

        openLightbox(opener) {
          if (!this.lightbox || typeof this.lightbox.showModal !== 'function' || this.lightbox.open) return;
          const body = this.lbBody;
          if (!body || !opener.dataset.zoomSrc) return;
          body.innerHTML = '';
          const img = document.createElement('img');
          img.className = 'lightbox__img';
          img.alt = opener.dataset.zoomAlt || '';
          img.decoding = 'async';
          img.draggable = false;
          const w = parseInt(opener.dataset.zoomWidth, 10);
          const h = parseInt(opener.dataset.zoomHeight, 10);
          if (w > 0 && h > 0) {
            img.width = w;
            img.height = h;
          }
          // Show the already-loaded stage image at once, then the 2000px source replaces it.
          const current = opener.querySelector('img');
          if (current && current.currentSrc) img.src = current.currentSrc;
          const full = new Image();
          full.onload = () => {
            img.src = opener.dataset.zoomSrc;
            img.classList.add('is-loaded');
          };
          full.src = opener.dataset.zoomSrc;
          body.appendChild(img);

          this.lightboxTrigger = opener;
          this.lbClosing = false;
          clearTimeout(this.closeTimer);
          this.lightbox.classList.remove('is-closing', 'is-open', 'is-dismissing');
          this.lightbox.showModal();
          // Commit the closed style (opacity 0) before .is-open so the fade runs
          void this.lightbox.offsetWidth;
          this.lightbox.classList.add('is-open');
          const m = motion();
          if (m && !reducedMotion() && this.lbPanel) {
            m.animate(this.lbPanel, { from: this.lightboxRest(), to: 'none' }, { duration: 0.4, bounce: 0 });
          }
          if (window.visualViewport) window.visualViewport.addEventListener('resize', this.onViewport);
          const close = this.lightbox.querySelector('[data-lightbox-close]');
          if (close) close.focus({ preventScroll: true });
        }

        /**
         * @param {{velocity:number, offset:number, height:number}} [gesture] release state of a drag-dismiss
         */
        closeLightbox(gesture) {
          if (!this.lightbox || !this.lightbox.open || this.lbClosing) return;
          this.lbClosing = true;
          this.endDrag();
          const trigger = this.lightboxTrigger;
          const finish = () => {
            if (!this.lbClosing) return;
            this.lbClosing = false;
            clearTimeout(this.closeTimer);
            if (this.lightbox.open) this.lightbox.close();
            this.resetLightbox();
            if (trigger && typeof trigger.focus === 'function') trigger.focus({ preventScroll: true });
            this.lightboxTrigger = null;
          };
          this.lightbox.classList.remove('is-open', 'is-dragging');
          this.lightbox.classList.add('is-closing');
          if (gesture) this.lightbox.classList.add('is-dismissing');
          if (this.lbScrim) this.lbScrim.style.opacity = '';
          this.lightbox.style.removeProperty('--lb-progress');

          const m = motion();
          if (!m || reducedMotion()) {
            this.closeTimer = setTimeout(finish, 180); // opacity fade only (CSS)
            return;
          }
          if (gesture && this.lbBody) {
            // Keep going the way the finger threw it, from where it is, at its speed
            const remaining = Math.max(1, gesture.height - gesture.offset);
            m.animate(
              this.lbBody,
              { to: `translateY(${Math.round(gesture.height)}px) scale(0.88)` },
              { duration: 0.35, bounce: 0, velocity: Math.max(0, gesture.velocity) / remaining }
            );
            this.closeTimer = setTimeout(finish, 280);
          } else if (this.lbPanel) {
            // Exit along the entrance path, faster than the entrance (the fade ends it)
            m.animate(this.lbPanel, { to: this.lightboxRest() }, { duration: 0.35, bounce: 0 });
            this.closeTimer = setTimeout(finish, 200);
          } else {
            this.closeTimer = setTimeout(finish, 200);
          }
        }

        resetLightbox() {
          if (!this.lightbox) return;
          this.endDrag();
          this.lbClosing = false;
          this.lightbox.classList.remove('is-open', 'is-closing', 'is-dismissing', 'is-dragging', 'is-zoomed');
          this.lightbox.style.removeProperty('--lb-progress');
          const m = Olivet.motion;
          [this.lbPanel, this.lbBody].forEach((el) => {
            if (!el) return;
            if (m && typeof m.stop === 'function') m.stop(el);
            el.style.transform = '';
          });
          if (this.lbScrim) this.lbScrim.style.opacity = '';
          if (this.lbBody) this.lbBody.innerHTML = '';
          if (window.visualViewport) window.visualViewport.removeEventListener('resize', this.onViewport);
        }

        /* Pinch-zoomed in: hand one-finger pans back to the browser (CSS touch-action) */
        onViewport() {
          const zoomed = !!(window.visualViewport && window.visualViewport.scale > 1.01);
          if (this.lightbox) this.lightbox.classList.toggle('is-zoomed', zoomed);
        }

        /* ---- phone: drag down to dismiss ---- */
        onDragDown(event) {
          if (!this.lightbox || !this.lightbox.open || this.lbClosing || !this.phone.matches) return;
          if (this.drag) {
            // A second finger: this is a pinch, not a dismiss. Put the image back.
            this.settleDrag(0);
            this.endDrag();
            return;
          }
          if (event.pointerType === 'mouse' && event.button !== 0) return;
          if (window.visualViewport && window.visualViewport.scale > 1.01) return;
          this.drag = {
            id: event.pointerId,
            x0: event.clientX,
            y0: event.clientY,
            state: 'pending',
            offset: 0,
            samples: [{ t: event.timeStamp, y: event.clientY }],
          };
          window.addEventListener('pointermove', this.onDragMove, { passive: true });
          window.addEventListener('pointerup', this.onDragUp);
          window.addEventListener('pointercancel', this.onDragUp);
        }

        onDragMove(event) {
          const d = this.drag;
          if (!d || event.pointerId !== d.id) return;
          const dx = event.clientX - d.x0;
          const dy = event.clientY - d.y0;
          const m = Olivet.motion;
          if (d.state === 'pending') {
            if (Math.abs(dx) < 10 && Math.abs(dy) < 10) return; // hysteresis
            if (Math.abs(dx) > Math.abs(dy)) {
              this.endDrag(); // sideways: not ours
              return;
            }
            d.state = 'dragging';
            try {
              this.lbBody.setPointerCapture(d.id);
            } catch (e) {
              /* capture is best effort */
            }
            if (m && typeof m.stop === 'function') m.stop(this.lbBody);
            d.height = window.innerHeight || this.lightbox.clientHeight || 800;
            // Grab mid-settle: continue from where the image is on screen
            const matrix = new DOMMatrixReadOnly(getComputedStyle(this.lbBody).transform);
            d.base = matrix.m42 || 0;
            this.lightbox.classList.add('is-dragging');
          }
          if (d.state !== 'dragging') return;
          const raw = d.base + dy; // 1:1 from the grab point
          const rubber = m && typeof m.rubberband === 'function' ? m.rubberband : (o) => o * 0.3;
          const offset = raw < 0 ? -rubber(-raw, d.height) : raw;
          d.offset = offset;
          this.applyDrag(offset, d.height);
          d.samples.push({ t: event.timeStamp, y: event.clientY });
          while (d.samples.length > 2 && event.timeStamp - d.samples[0].t > 80) d.samples.shift();
        }

        applyDrag(offset, height) {
          const progress = Math.max(0, Math.min(1, offset / (height * 0.5)));
          // Hint toward the outcome: the image shrinks a little as it leaves
          this.lbBody.style.transform = `translateY(${offset}px) scale(${1 - 0.12 * progress})`;
          if (this.lbScrim) this.lbScrim.style.opacity = String(1 - progress);
          this.lightbox.style.setProperty('--lb-progress', progress.toFixed(3));
        }

        onDragUp(event) {
          const d = this.drag;
          if (!d || event.pointerId !== d.id) return;
          if (d.state === 'dragging') {
            const first = d.samples[0];
            const last = d.samples[d.samples.length - 1];
            const dt = Math.max(1, last.t - first.t);
            const velocity = ((last.y - first.y) / dt) * 1000; // px/s, + = down
            const project = Olivet.motion && Olivet.motion.project ? Olivet.motion.project : (v) => v * 0.5;
            const projected = d.offset + project(velocity);
            const cancelled = event.type === 'pointercancel';
            const dismiss = !cancelled && (projected > d.height * 0.3 || velocity > 700) && velocity > -200;
            this.lightbox.classList.remove('is-dragging');
            if (dismiss) {
              const gesture = { velocity, offset: d.offset, height: d.height };
              this.endDrag();
              this.closeLightbox(gesture);
              return;
            }
            this.settleDrag(cancelled ? 0 : velocity);
          }
          this.endDrag();
        }

        /* Spring home from the on-screen value, carrying the release velocity */
        settleDrag(velocity) {
          const d = this.drag;
          if (!d || d.state !== 'dragging' || !this.lbBody) return;
          this.lightbox.classList.remove('is-dragging');
          if (this.lbScrim) this.lbScrim.style.opacity = '';
          this.lightbox.style.removeProperty('--lb-progress');
          const m = motion();
          const from = this.lbBody.style.transform;
          if (!m || reducedMotion()) {
            this.lbBody.style.transform = '';
            return;
          }
          const distance = Math.abs(d.offset) || 1;
          const momentum = Math.abs(velocity) > 300;
          m.animate(this.lbBody, { from, to: 'none' }, { duration: 0.4, bounce: momentum ? 0.15 : 0, velocity: -velocity / distance });
        }

        endDrag() {
          window.removeEventListener('pointermove', this.onDragMove);
          window.removeEventListener('pointerup', this.onDragUp);
          window.removeEventListener('pointercancel', this.onDragUp);
          const d = this.drag;
          if (d && this.lbBody) {
            try {
              this.lbBody.releasePointerCapture(d.id);
            } catch (e) {
              /* already released */
            }
          }
          this.drag = null;
        }
      }
    );
  }

  /* ---------- sticky-buy-bar ----------
     Phones and tablets: a translucent bar with the title, price and an
     "Add to Bag" pill. It rises (transform + opacity, CSS) once the main
     submit button has scrolled above the viewport, and steps aside while
     the footer is in view. Its button submits the same product form through
     the form attribute; it mirrors the main button's disabled, loading and
     "Added" states so the feedback shows where the user tapped. */
  if (!customElements.get('sticky-buy-bar')) {
    customElements.define(
      'sticky-buy-bar',
      class StickyBuyBar extends HTMLElement {
        connectedCallback() {
          this.sectionId = this.dataset.section || '';
          this.main = document.getElementById(this.dataset.button || `ProductSubmitButton-${this.sectionId}`);
          this.button = this.querySelector('[data-sticky-button]');
          this.label = this.querySelector('[data-sticky-label]');
          this.price = this.querySelector('[data-sticky-price]');
          if (!this.main || !this.button || !('IntersectionObserver' in window)) return;
          this.mq = window.matchMedia('(max-width: 989px)');
          this.past = false;
          this.footerInView = false;
          this.update = this.update.bind(this);

          // The root reaches far below the viewport, so the button counts as
          // "intersecting" anywhere from the viewport down. It stops only once
          // it has scrolled above the top, and a jump straight from below to
          // above (anchor link, scroll restoration) still crosses that edge.
          this.io = new IntersectionObserver(
            ([entry]) => {
              this.past = !entry.isIntersecting && entry.boundingClientRect.height > 0;
              this.update();
            },
            { rootMargin: '0px 0px 100000px 0px' }
          );
          this.io.observe(this.main);
          this.footer = document.querySelector('[role="contentinfo"], footer');
          if (this.footer) {
            this.footerIo = new IntersectionObserver(([entry]) => {
              this.footerInView = entry.isIntersecting;
              this.update();
            });
            this.footerIo.observe(this.footer);
          }
          if (this.mq.addEventListener) this.mq.addEventListener('change', this.update);

          this.mirror = new MutationObserver(() => this.sync());
          this.mirror.observe(this.main, { attributes: true, attributeFilter: ['disabled', 'class', 'aria-disabled'], childList: true, subtree: true, characterData: true });
          this.sync();

          this.unsubscribe = subscribe(EVENTS.variantChanged, (data) => {
            if (!data || data.sectionId !== this.sectionId || !data.variant || !this.price) return;
            const text = formatPrice(data.variant.price);
            if (text) this.price.textContent = text;
          });
        }

        disconnectedCallback() {
          if (this.io) this.io.disconnect();
          if (this.footerIo) this.footerIo.disconnect();
          if (this.mirror) this.mirror.disconnect();
          if (this.unsubscribe) this.unsubscribe();
          if (this.mq && this.mq.removeEventListener) this.mq.removeEventListener('change', this.update);
        }

        update() {
          const show = this.past && !this.footerInView && this.mq.matches;
          if (show === this.classList.contains('is-visible')) return;
          this.classList.toggle('is-visible', show);
          this.toggleAttribute('inert', !show);
          // Never strand focus inside a bar that is leaving
          if (!show && this.contains(document.activeElement) && typeof this.main.focus === 'function') this.main.focus({ preventScroll: true });
        }

        sync() {
          const main = this.main;
          const button = this.button;
          button.disabled = main.disabled;
          ['is-loading', 'is-transitioning'].forEach((cls) => button.classList.toggle(cls, main.classList.contains(cls)));
          if (main.hasAttribute('aria-disabled')) button.setAttribute('aria-disabled', main.getAttribute('aria-disabled'));
          else button.removeAttribute('aria-disabled');
          const source = main.querySelector('[data-add-label]');
          const text = source ? source.textContent.trim() : '';
          if (this.label && text && this.label.textContent !== text) this.label.textContent = text;
        }
      }
    );
  }

  /* ---------- product-recommendations ---------- */
  if (!customElements.get('product-recommendations')) {
    customElements.define(
      'product-recommendations',
      class ProductRecommendations extends HTMLElement {
        connectedCallback() {
          const url = this.dataset.url;
          if (!url) return;
          const load = () => {
            fetch(url)
              .then((res) => (res.ok ? res.text() : Promise.reject(new Error(String(res.status)))))
              .then((html) => {
                const doc = new DOMParser().parseFromString(html, 'text/html');
                const fresh = doc.querySelector('product-recommendations');
                if (fresh && fresh.querySelector('.product-recommendations__inner')) {
                  this.innerHTML = fresh.innerHTML;
                  this.reveal();
                } else {
                  this.empty();
                }
              })
              .catch(() => this.empty());
          };
          if ('IntersectionObserver' in window) {
            const io = new IntersectionObserver(
              (entries) => {
                if (!entries.some((entry) => entry.isIntersecting)) return;
                io.disconnect();
                load();
              },
              { rootMargin: '600px 0px' }
            );
            io.observe(this);
          } else {
            load();
          }
        }

        empty() {
          const designMode = window.Shopify && window.Shopify.designMode;
          if (designMode && this.dataset.emptyText) {
            this.innerHTML = `<div class="page-width section--tight"><p class="caption text-center">${this.dataset.emptyText}</p></div>`;
            return;
          }
          this.remove();
        }

        reveal() {
          const nodes = this.querySelectorAll('[data-reveal]');
          if (!nodes.length) return;
          // Force a style pass so the injected cards start from their hidden state and fade in staggered.
          nodes[0].getBoundingClientRect();
          if (typeof Olivet.observeReveal === 'function') {
            Olivet.observeReveal(this);
          } else {
            requestAnimationFrame(() => nodes.forEach((node) => node.classList.add('is-visible')));
          }
          this.querySelectorAll('img.media__img').forEach((img) => {
            if (img.complete && img.naturalWidth > 0) img.classList.add('is-loaded');
          });
        }
      }
    );
  }

  /* ---------- theme editor: open a tab when its block is selected ---------- */
  document.addEventListener('shopify:block:select', (event) => {
    const accordion = event.target && event.target.querySelector && event.target.querySelector('olivet-accordion');
    if (accordion && typeof accordion.open === 'function' && accordion.details && !accordion.details.open) accordion.open();
  });
})();
