/* ==========================================================================
   Olivet — theme.js
   Core helpers (pubsub, focus, drawers, reveal, sticky header, accordions,
   quantity inputs, image load state). Vanilla, no dependencies.
   ========================================================================== */
(() => {
  const Olivet = (window.Olivet = window.Olivet || {});
  const config = Olivet.config || { routes: {}, strings: {} };
  Olivet.routes = config.routes || {};
  Olivet.strings = config.strings || {};

  /* ---------- utilities ---------- */
  Olivet.prefersReducedMotion = () =>
    window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  Olivet.debounce = (fn, wait = 200) => {
    let t;
    return (...args) => {
      clearTimeout(t);
      t = setTimeout(() => fn.apply(this, args), wait);
    };
  };

  Olivet.fetchConfig = (type = 'json') => ({
    method: 'POST',
    headers: { 'Content-Type': 'application/json', Accept: `application/${type}` },
  });

  Olivet.getFocusable = (container) =>
    Array.from(
      container.querySelectorAll(
        "summary, a[href], button:not([disabled]), [tabindex]:not([tabindex^='-']), input:not([type=hidden]):not([disabled]), select:not([disabled]), textarea:not([disabled]), [contenteditable]"
      )
    ).filter((el) => el.offsetParent !== null || el === document.activeElement);

  /* ---------- pubsub ---------- */
  const subscribers = {};
  Olivet.pubsub = {
    subscribe(name, cb) {
      (subscribers[name] = subscribers[name] || []).push(cb);
      return () => {
        subscribers[name] = (subscribers[name] || []).filter((fn) => fn !== cb);
      };
    },
    publish(name, data) {
      return Promise.all((subscribers[name] || []).map((cb) => cb(data)));
    },
  };
  Olivet.EVENTS = {
    cartUpdated: 'cart:updated',
    cartError: 'cart:error',
    variantChanged: 'variant:changed',
    drawerOpened: 'drawer:opened',
    drawerClosed: 'drawer:closed',
  };

  /* ---------- money ---------- */
  Olivet.formatMoney = (cents, format) => {
    if (typeof cents === 'string') cents = cents.replace('.', '');
    const fmt = format || config.moneyFormat || '${{amount}}';
    const placeholderRegex = /\{\{\s*(\w+)\s*\}\}/;
    const formatWithDelimiters = (number, precision = 2, thousands = ',', decimal = '.') => {
      if (isNaN(number) || number == null) return '0';
      number = (number / 100.0).toFixed(precision);
      const parts = number.split('.');
      const dollars = parts[0].replace(/(\d)(?=(\d\d\d)+(?!\d))/g, `$1${thousands}`);
      const centsPart = parts[1] ? decimal + parts[1] : '';
      return dollars + centsPart;
    };
    let value = '';
    const match = fmt.match(placeholderRegex);
    switch (match ? match[1] : 'amount') {
      case 'amount_no_decimals':
        value = formatWithDelimiters(cents, 0);
        break;
      case 'amount_with_comma_separator':
        value = formatWithDelimiters(cents, 2, '.', ',');
        break;
      case 'amount_no_decimals_with_comma_separator':
        value = formatWithDelimiters(cents, 0, '.', ',');
        break;
      case 'amount_with_apostrophe_separator':
        value = formatWithDelimiters(cents, 2, "'", '.');
        break;
      case 'amount_no_decimals_with_space_separator':
        value = formatWithDelimiters(cents, 0, ' ', '');
        break;
      case 'amount_with_space_separator':
        value = formatWithDelimiters(cents, 2, ' ', ',');
        break;
      case 'amount_with_period_and_space_separator':
        value = formatWithDelimiters(cents, 2, ' ', '.');
        break;
      default:
        value = formatWithDelimiters(cents, 2);
    }
    return fmt.replace(placeholderRegex, value);
  };

  /* ---------- focus trap ---------- */
  const trap = {};
  Olivet.trapFocus = (container, elementToFocus = container) => {
    const elements = Olivet.getFocusable(container);
    const first = elements[0];
    const last = elements[elements.length - 1];
    Olivet.releaseFocus();

    trap.focusin = (event) => {
      if (event.target !== container && event.target !== last && event.target !== first) return;
      document.addEventListener('keydown', trap.keydown);
    };
    trap.focusout = () => document.removeEventListener('keydown', trap.keydown);
    trap.keydown = (event) => {
      if (event.code !== 'Tab') return;
      if (event.target === last && !event.shiftKey) {
        event.preventDefault();
        first && first.focus();
      }
      if ((event.target === container || event.target === first) && event.shiftKey) {
        event.preventDefault();
        last && last.focus();
      }
    };
    document.addEventListener('focusout', trap.focusout);
    document.addEventListener('focusin', trap.focusin);
    if (elementToFocus) {
      elementToFocus.focus({ preventScroll: true });
      if (elementToFocus.tagName === 'INPUT' && ['search', 'text', 'email', 'url'].includes(elementToFocus.type) && elementToFocus.value) {
        elementToFocus.setSelectionRange(0, elementToFocus.value.length);
      }
    }
  };
  Olivet.releaseFocus = () => {
    document.removeEventListener('focusin', trap.focusin);
    document.removeEventListener('focusout', trap.focusout);
    document.removeEventListener('keydown', trap.keydown);
  };

  /* ---------- Drawer base ----------
     Contract: element has .is-open when open; body gets .drawer-open.
     Panel animates on transform (var(--ease-drawer)), backdrop on opacity.
     Enter 400ms, exit 260ms — exits are faster. Escape closes. */
  class Drawer extends HTMLElement {
    constructor() {
      super();
      this.onKeydown = this.onKeydown.bind(this);
      this.onTransitionEnd = this.onTransitionEnd.bind(this);
    }

    connectedCallback() {
      this.panel = this.querySelector('[data-drawer-panel]') || this;
      this.backdrop = this.querySelector('[data-drawer-backdrop]');
      this.closeButtons = this.querySelectorAll('[data-drawer-close]');
      this.closeButtons.forEach((btn) => btn.addEventListener('click', () => this.close()));
      if (this.backdrop) this.backdrop.addEventListener('click', () => this.close());
      // The panel is the fallback focus target, so it must accept programmatic focus
      if (this.panel !== this && !this.panel.hasAttribute('tabindex')) this.panel.setAttribute('tabindex', '-1');
      this.setAttribute('aria-hidden', 'true');
    }

    get isOpen() {
      return this.classList.contains('is-open');
    }

    open(trigger) {
      if (this.isOpen) return;
      // Interrupting a close: cancel its pending cleanup so it can't mark this
      // drawer inert or pull focus back after it has reopened.
      this.cancelPendingClose();
      this.trigger = trigger || document.activeElement;
      // Close any other open drawer first (spatial consistency: one surface at a time)
      document.querySelectorAll('[data-drawer].is-open').forEach((d) => d !== this && d.close(true));
      this.removeAttribute('inert');
      this.setAttribute('aria-hidden', 'false');
      // Force a frame so the transition runs from the closed state
      this.getBoundingClientRect();
      this.classList.add('is-open');
      document.body.classList.add('drawer-open');
      document.addEventListener('keydown', this.onKeydown);
      const focusTarget = this.querySelector('[data-drawer-focus]') || this.panel;
      Olivet.trapFocus(this.panel, focusTarget);
      if (this.trigger && this.trigger.setAttribute) this.trigger.setAttribute('aria-expanded', 'true');
      Olivet.pubsub.publish(Olivet.EVENTS.drawerOpened, { drawer: this });
    }

    close(silent = false) {
      if (!this.isOpen) return;
      this.classList.remove('is-open');
      document.removeEventListener('keydown', this.onKeydown);
      Olivet.releaseFocus();
      if (!document.querySelector('[data-drawer].is-open')) document.body.classList.remove('drawer-open');
      if (this.trigger && this.trigger.setAttribute) this.trigger.setAttribute('aria-expanded', 'false');
      const trigger = this.trigger;
      this.trigger = null;
      const finish = () => {
        this.cancelPendingClose();
        this.setAttribute('aria-hidden', 'true');
        this.setAttribute('inert', '');
        // Return focus only if nothing else took over (another drawer opened meanwhile)
        const focusFree = !document.querySelector('[data-drawer].is-open') && (document.activeElement === document.body || this.contains(document.activeElement));
        if (!silent && focusFree && trigger && trigger.focus) trigger.focus({ preventScroll: true });
      };
      this.cancelPendingClose();
      if (Olivet.prefersReducedMotion()) {
        finish();
      } else {
        // Not { once: true }: child transitions (fading links) bubble here first
        // and would consume a one-shot listener before the panel's own event.
        this.finish = finish;
        this.panel.addEventListener('transitionend', this.onTransitionEnd);
        this.closeTimeout = setTimeout(finish, 500); // safety if no transition fires
      }
      Olivet.pubsub.publish(Olivet.EVENTS.drawerClosed, { drawer: this });
    }

    cancelPendingClose() {
      clearTimeout(this.closeTimeout);
      this.closeTimeout = null;
      this.panel.removeEventListener('transitionend', this.onTransitionEnd);
      this.finish = null;
    }

    onTransitionEnd(event) {
      if (event.target !== this.panel || event.propertyName !== 'transform' && event.propertyName !== 'opacity') return;
      if (this.finish) this.finish();
    }

    onKeydown(event) {
      if (event.key === 'Escape') {
        event.preventDefault();
        this.close();
      }
    }

    toggle(trigger) {
      this.isOpen ? this.close() : this.open(trigger);
    }
  }
  Olivet.Drawer = Drawer;

  /* Generic drawer triggers: <button data-drawer-open="#id"> */
  document.addEventListener('click', (event) => {
    const trigger = event.target.closest('[data-drawer-open]');
    if (!trigger) return;
    const target = document.querySelector(trigger.getAttribute('data-drawer-open'));
    if (!target || typeof target.open !== 'function') return;
    event.preventDefault();
    target.toggle ? target.toggle(trigger) : target.open(trigger);
  });

  /* menu-drawer: the mobile navigation */
  if (!customElements.get('menu-drawer')) {
    customElements.define(
      'menu-drawer',
      class MenuDrawer extends Drawer {
        connectedCallback() {
          super.connectedCallback();
          // Submenus: slide-in panels
          this.querySelectorAll('[data-submenu-open]').forEach((btn) => {
            btn.addEventListener('click', () => {
              const panel = this.querySelector(btn.getAttribute('data-submenu-open'));
              if (!panel) return;
              panel.classList.add('is-open');
              panel.removeAttribute('inert');
              btn.setAttribute('aria-expanded', 'true');
              const back = panel.querySelector('[data-submenu-back]');
              Olivet.trapFocus(panel, back || panel);
            });
          });
          this.querySelectorAll('[data-submenu-back]').forEach((btn) => {
            btn.addEventListener('click', () => {
              const panel = btn.closest('[data-submenu]');
              if (!panel) return;
              panel.classList.remove('is-open');
              panel.setAttribute('inert', '');
              const opener = this.querySelector(`[data-submenu-open="#${panel.id}"]`);
              if (opener) opener.setAttribute('aria-expanded', 'false');
              Olivet.trapFocus(this.panel, opener || this.panel);
            });
          });
        }
        close(silent) {
          super.close(silent);
          this.querySelectorAll('[data-submenu].is-open').forEach((p) => {
            p.classList.remove('is-open');
            p.setAttribute('inert', '');
          });
        }
      }
    );
  }

  /* search-drawer: the search overlay from the header (origin: top) */
  if (!customElements.get('search-drawer')) {
    customElements.define(
      'search-drawer',
      class SearchDrawer extends Drawer {
        connectedCallback() {
          super.connectedCallback();
          this.input = this.querySelector('input[type="search"]');
          const reset = this.querySelector('[data-search-reset]');
          if (reset && this.input) {
            reset.addEventListener('click', () => {
              this.input.value = '';
              this.input.focus();
              this.input.dispatchEvent(new Event('input', { bubbles: true }));
            });
          }
        }
      }
    );
  }

  /* ---------- sticky header ----------
     Hides on scroll down, returns on scroll up. Transform only. */
  if (!customElements.get('sticky-header')) {
    customElements.define(
      'sticky-header',
      class StickyHeader extends HTMLElement {
        connectedCallback() {
          this.header = this.querySelector('.header') || this;
          this.lastY = window.scrollY;
          this.ticking = false;
          this.threshold = 12;
          this.onScroll = this.onScroll.bind(this);
          window.addEventListener('scroll', this.onScroll, { passive: true });
          this.measure();
          window.addEventListener('resize', Olivet.debounce(() => this.measure(), 150));
          this.onScroll();
        }
        disconnectedCallback() {
          window.removeEventListener('scroll', this.onScroll);
        }
        measure() {
          const h = this.getBoundingClientRect().height;
          document.documentElement.style.setProperty('--header-height', `${Math.round(h)}px`);
        }
        onScroll() {
          if (this.ticking) return;
          this.ticking = true;
          requestAnimationFrame(() => {
            const y = window.scrollY;
            const delta = y - this.lastY;
            this.classList.toggle('is-scrolled', y > 8);
            if (document.body.classList.contains('drawer-open')) {
              this.ticking = false;
              return;
            }
            if (y <= 0) {
              this.classList.remove('is-hidden');
            } else if (delta > this.threshold && y > this.offsetHeight * 1.5) {
              this.classList.add('is-hidden');
              this.lastY = y;
            } else if (delta < -this.threshold) {
              this.classList.remove('is-hidden');
              this.lastY = y;
            }
            if (Math.abs(delta) > this.threshold) this.lastY = y;
            this.ticking = false;
          });
        }
      }
    );
  }

  /* ---------- scroll reveal ---------- */
  const initReveal = () => {
    const nodes = document.querySelectorAll('[data-reveal]');
    if (!nodes.length) return;
    if (config.revealOnScroll === false || !('IntersectionObserver' in window)) {
      document.documentElement.classList.add('no-reveal');
      return;
    }
    const io = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (!entry.isIntersecting) return;
          entry.target.classList.add('is-visible');
          io.unobserve(entry.target);
        });
      },
      { rootMargin: '0px 0px -8% 0px', threshold: 0.05 }
    );
    nodes.forEach((n) => {
      // Elements already in view at load reveal immediately (no waiting for scroll)
      const r = n.getBoundingClientRect();
      if (r.top < window.innerHeight * 0.9) n.classList.add('is-visible');
      else io.observe(n);
    });
    // Theme editor: reveal anything added later
    Olivet.observeReveal = (root) => root.querySelectorAll('[data-reveal]').forEach((n) => io.observe(n));
  };

  /* ---------- image load state ---------- */
  const markLoaded = (img) => img.classList.add('is-loaded');
  document.addEventListener(
    'load',
    (event) => {
      if (event.target.tagName === 'IMG' && event.target.classList.contains('media__img')) markLoaded(event.target);
    },
    true
  );
  const initImages = () => {
    document.querySelectorAll('img.media__img').forEach((img) => {
      if (img.complete && img.naturalWidth > 0) markLoaded(img);
    });
  };

  /* ---------- accordion (details) ----------
     Animates grid-template-rows 0fr → 1fr. The one tolerated layout
     animation, because there is no transform equivalent for an accordion. */
  if (!customElements.get('olivet-accordion')) {
    customElements.define(
      'olivet-accordion',
      class Accordion extends HTMLElement {
        connectedCallback() {
          this.details = this.querySelector('details');
          this.summary = this.querySelector('summary');
          this.content = this.querySelector('[data-accordion-content]');
          if (!this.details || !this.summary || !this.content) return;
          this.summary.setAttribute('role', 'button');
          this.summary.setAttribute('aria-expanded', this.details.open ? 'true' : 'false');
          if (this.details.open) this.details.classList.add('is-open');
          this.summary.addEventListener('click', (e) => {
            e.preventDefault();
            this.details.classList.contains('is-open') ? this.close() : this.open();
          });
        }
        open() {
          // A click mid-close retargets the transition back to 1fr instead of being swallowed
          this._cancelClose();
          this.details.open = true;
          this.summary.setAttribute('aria-expanded', 'true');
          // next frame so the 0fr → 1fr transition runs
          requestAnimationFrame(() => this.details.classList.add('is-open'));
        }
        close() {
          this.details.classList.remove('is-open');
          this.summary.setAttribute('aria-expanded', 'false');
          this._cancelClose();
          if (Olivet.prefersReducedMotion()) {
            this.details.open = false;
            return;
          }
          this._onEnd = (event) => {
            if (event.target !== this.content) return;
            this._finishClose();
          };
          this.content.addEventListener('transitionend', this._onEnd);
          this._closeTimer = setTimeout(() => this._finishClose(), 320);
        }
        _cancelClose() {
          clearTimeout(this._closeTimer);
          if (this._onEnd) this.content.removeEventListener('transitionend', this._onEnd);
          this._onEnd = null;
        }
        _finishClose() {
          this._cancelClose();
          this.details.open = false;
        }
      }
    );
  }

  /* ---------- quantity input ---------- */
  if (!customElements.get('quantity-input')) {
    customElements.define(
      'quantity-input',
      class QuantityInput extends HTMLElement {
        connectedCallback() {
          this.input = this.querySelector('input');
          this.changeEvent = new Event('change', { bubbles: true });
          this.querySelectorAll('button').forEach((btn) =>
            btn.addEventListener('click', (e) => {
              e.preventDefault();
              const prev = this.input.value;
              btn.name === 'plus' ? this.input.stepUp() : this.input.stepDown();
              if (prev !== this.input.value) this.input.dispatchEvent(this.changeEvent);
              this.validate();
            })
          );
          this.input.addEventListener('change', () => this.validate());
          this.validate();
        }
        validate() {
          const min = parseInt(this.input.min || '1', 10);
          const max = this.input.max ? parseInt(this.input.max, 10) : Infinity;
          const value = parseInt(this.input.value, 10);
          const minus = this.querySelector('[name="minus"]');
          const plus = this.querySelector('[name="plus"]');
          if (minus) minus.toggleAttribute('disabled', !(value > min));
          if (plus) plus.toggleAttribute('disabled', !(value < max));
        }
      }
    );
  }

  /* ---------- localization form (country / language) ---------- */
  if (!customElements.get('localization-form')) {
    customElements.define(
      'localization-form',
      class LocalizationForm extends HTMLElement {
        connectedCallback() {
          this.form = this.querySelector('form');
          this.querySelectorAll('select').forEach((select) => {
            select.addEventListener('change', (e) => {
              const input = this.querySelector(`input[name="${e.target.dataset.target}"]`);
              if (input) input.value = e.target.value;
              this.form && this.form.submit();
            });
          });
        }
      }
    );
  }

  /* ---------- details-disclosure (header dropdowns): close on outside click / Escape ---------- */
  if (!customElements.get('details-disclosure')) {
    customElements.define(
      'details-disclosure',
      class DetailsDisclosure extends HTMLElement {
        connectedCallback() {
          this.details = this.querySelector('details');
          this.summary = this.querySelector('summary');
          if (!this.details) return;
          this.onFocusOut = this.onFocusOut.bind(this);
          this.onKeyup = this.onKeyup.bind(this);
          this.details.addEventListener('focusout', this.onFocusOut);
          this.details.addEventListener('keyup', this.onKeyup);
          this.summary.addEventListener('click', () => {
            requestAnimationFrame(() => this.summary.setAttribute('aria-expanded', this.details.open ? 'true' : 'false'));
          });
          document.addEventListener('click', (e) => {
            if (this.details.open && !this.details.contains(e.target)) this.closeMenu();
          });
        }
        onFocusOut(e) {
          if (e.relatedTarget && !this.details.contains(e.relatedTarget)) this.closeMenu();
        }
        onKeyup(e) {
          if (e.key === 'Escape' && this.details.open) {
            this.closeMenu();
            this.summary.focus();
          }
        }
        closeMenu() {
          this.details.removeAttribute('open');
          this.summary.setAttribute('aria-expanded', 'false');
        }
      }
    );
  }

  /* ---------- share button ---------- */
  if (!customElements.get('share-button')) {
    customElements.define(
      'share-button',
      class ShareButton extends HTMLElement {
        connectedCallback() {
          this.button = this.querySelector('button');
          this.url = this.dataset.url || window.location.href;
          this.shareTitle = this.dataset.title || document.title;
          if (!this.button) return;
          this.button.addEventListener('click', async () => {
            try {
              if (navigator.share) {
                await navigator.share({ title: this.shareTitle, url: this.url });
              } else if (navigator.clipboard) {
                await navigator.clipboard.writeText(this.url);
                this.flash(this.dataset.copied || 'Link copied');
              }
            } catch (e) {
              /* user cancelled */
            }
          });
        }
        flash(text) {
          const label = this.button.querySelector('[data-share-label]');
          if (!label) return;
          const prev = label.textContent;
          this.button.classList.add('is-transitioning');
          setTimeout(() => {
            label.textContent = text;
            this.button.classList.remove('is-transitioning');
          }, 120);
          setTimeout(() => {
            this.button.classList.add('is-transitioning');
            setTimeout(() => {
              label.textContent = prev;
              this.button.classList.remove('is-transitioning');
            }, 120);
          }, 1800);
        }
      }
    );
  }

  /* ---------- init ---------- */
  const init = () => {
    initReveal();
    initImages();
  };
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init);
  else init();

  // Theme editor hooks
  document.addEventListener('shopify:section:load', (e) => {
    initImages();
    if (Olivet.observeReveal) Olivet.observeReveal(e.target);
    e.target.querySelectorAll('[data-reveal]').forEach((n) => n.classList.add('is-visible'));
  });
})();
