/* ==========================================================================
   Olivet — product.js
   <variant-picker>, <media-gallery>, <product-recommendations>.
   Vanilla, no dependencies beyond window.Olivet (assets/theme.js).
   Every lookup is guarded: a missing element is a no-op, never a throw.
   ========================================================================== */
(() => {
  const Olivet = (window.Olivet = window.Olivet || {});
  const strings = Olivet.strings || {};
  const EVENTS = Olivet.EVENTS || { variantChanged: 'variant:changed' };
  const publish = (name, data) => {
    if (Olivet.pubsub && typeof Olivet.pubsub.publish === 'function') Olivet.pubsub.publish(name, data);
  };
  const reducedMotion = () =>
    typeof Olivet.prefersReducedMotion === 'function'
      ? Olivet.prefersReducedMotion()
      : window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;

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
              const pill = group.querySelector(`label[for="${input.id}"]`);
              if (pill) pill.classList.toggle('is-selected', input.checked);
            });
          });
        }

        /* Strike through values that have no purchasable variant with the other
           current selections. Purely visual; the radios stay selectable. */
        markAvailability() {
          if (!this.variants.length) return;
          const selected = this.selectedOptions;
          this.groups.forEach((group, index) => {
            group.querySelectorAll('input[type="radio"]').forEach((input) => {
              const pill = group.querySelector(`label[for="${input.id}"]`);
              if (!pill) return;
              const exists = this.variants.some(
                (v) =>
                  Array.isArray(v.options) &&
                  v.available &&
                  v.options.every((opt, i) => (i === index ? opt === input.value : opt === selected[i]))
              );
              pill.classList.toggle('is-unavailable', !exists);
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
            swapLabel(button, strings.addToCart || 'Add to cart');
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

        /* Mobile carousel → dots/thumbs follow the slide in view. */
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

        /* ---- lightbox (native <dialog>) ---- */
        bindLightbox() {
          if (!this.lightbox || typeof this.lightbox.showModal !== 'function') return;
          this.lightbox.addEventListener('click', (event) => {
            if (event.target === this.lightbox) this.closeLightbox(); // backdrop / padding click
          });
          this.lightbox.addEventListener('cancel', (event) => {
            event.preventDefault(); // Escape: run the exit transition first
            this.closeLightbox();
          });
          this.lightbox.addEventListener('close', () => {
            this.lightbox.classList.remove('is-closing');
            const body = this.lightbox.querySelector('[data-lightbox-body]');
            if (body) body.innerHTML = '';
          });
        }

        openLightbox(opener) {
          if (!this.lightbox || typeof this.lightbox.showModal !== 'function' || this.lightbox.open) return;
          const body = this.lightbox.querySelector('[data-lightbox-body]');
          if (!body || !opener.dataset.zoomSrc) return;
          body.innerHTML = '';
          const img = document.createElement('img');
          img.className = 'lightbox__img';
          img.alt = opener.dataset.zoomAlt || '';
          img.decoding = 'async';
          const w = parseInt(opener.dataset.zoomWidth, 10);
          const h = parseInt(opener.dataset.zoomHeight, 10);
          if (w > 0 && h > 0) {
            img.width = w;
            img.height = h;
            img.style.aspectRatio = `${w} / ${h}`;
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
          this.lightbox.classList.remove('is-closing');
          this.lightbox.showModal();
          const close = this.lightbox.querySelector('[data-lightbox-close]');
          if (close) close.focus({ preventScroll: true });
        }

        closeLightbox() {
          if (!this.lightbox || !this.lightbox.open) return;
          const trigger = this.lightboxTrigger;
          const finish = () => {
            clearTimeout(this.closeTimer);
            if (this.lightbox.open) this.lightbox.close();
            this.lightbox.classList.remove('is-closing');
            if (trigger && typeof trigger.focus === 'function') trigger.focus({ preventScroll: true });
            this.lightboxTrigger = null;
          };
          if (reducedMotion()) {
            finish();
            return;
          }
          this.lightbox.classList.add('is-closing');
          const onEnd = (event) => {
            if (event.target !== this.lightbox) return;
            this.lightbox.removeEventListener('transitionend', onEnd);
            finish();
          };
          this.lightbox.addEventListener('transitionend', onEnd);
          this.closeTimer = setTimeout(() => {
            this.lightbox.removeEventListener('transitionend', onEnd);
            finish();
          }, 260);
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
