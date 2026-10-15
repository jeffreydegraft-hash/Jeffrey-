/* ==========================================================================
   Olivet — cart.js
   cart-drawer, cart-items, cart-remove-button, cart-note, free-shipping-bar,
   product-form. Vanilla, no dependencies. Every DOM lookup is guarded so a
   missing element never throws. Nothing leaks except the custom elements.
   ========================================================================== */
(() => {
  const Olivet = (window.Olivet = window.Olivet || {});
  const routes = Olivet.routes || {};
  const strings = Olivet.strings || {};
  const config = Olivet.config || {};
  const EVENTS = Olivet.EVENTS || {
    cartUpdated: 'cart:updated',
    cartError: 'cart:error',
    variantChanged: 'variant:changed',
    drawerOpened: 'drawer:opened',
    drawerClosed: 'drawer:closed',
  };
  const DrawerBase = typeof Olivet.Drawer === 'function' ? Olivet.Drawer : HTMLElement;

  const BUMP_MS = 300; // feedback: the count ticks up
  const LABEL_SWAP_MS = 120; // state: Add → Added crossfade
  const LABEL_HOLD_MS = 1600;
  const DEBOUNCE_MS = 300; // quantity changes and note saves
  const GENERIC_ERROR = 'There was an error while updating your cart. Please try again.';

  /* ---------- helpers ---------- */
  const publish = (name, data) =>
    Olivet.pubsub && typeof Olivet.pubsub.publish === 'function' ? Olivet.pubsub.publish(name, data) : Promise.resolve();

  const fetchConfig = (type = 'json') =>
    typeof Olivet.fetchConfig === 'function'
      ? Olivet.fetchConfig(type)
      : { method: 'POST', headers: { 'Content-Type': 'application/json', Accept: `application/${type}` } };

  const debounce =
    typeof Olivet.debounce === 'function'
      ? Olivet.debounce
      : (fn, wait = 200) => {
          let t;
          return (...args) => {
            clearTimeout(t);
            t = setTimeout(() => fn(...args), wait);
          };
        };

  const reducedMotion = () =>
    typeof Olivet.prefersReducedMotion === 'function'
      ? Olivet.prefersReducedMotion()
      : window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  const parseHTML = (html) => new DOMParser().parseFromString(html || '', 'text/html');

  const errorMessage = (data) => {
    if (!data) return strings.cartError || GENERIC_ERROR;
    const raw = data.errors || data.description || data.message;
    if (Array.isArray(raw)) return raw.join(' ');
    if (raw && typeof raw === 'object') return Object.values(raw).flat().join(' ');
    return raw || strings.cartError || GENERIC_ERROR;
  };

  const focusElement = (el, container) => {
    if (!el || typeof el.focus !== 'function') return;
    if (container && typeof Olivet.trapFocus === 'function') Olivet.trapFocus(container, el);
    else el.focus({ preventScroll: true });
  };

  /* The header bubble: swap its inner markup, then bump the count. */
  let bumpTimer;
  const updateCartBubble = (html, bump = true) => {
    const bubble = document.getElementById('cart-icon-bubble');
    if (!bubble || !html) return;
    const doc = parseHTML(html);
    const wrapper = doc.getElementById('shopify-section-cart-icon-bubble') || doc.body;
    bubble.innerHTML = wrapper.innerHTML;
    if (!bump) return;
    clearTimeout(bumpTimer);
    bubble.classList.remove('is-bumping');
    bubble.getBoundingClientRect(); // restart the transition if it is mid-flight
    bubble.classList.add('is-bumping');
    bumpTimer = setTimeout(() => bubble.classList.remove('is-bumping'), BUMP_MS);
  };

  /* The cart page: swap #MainCart-Inner from its own section's HTML. */
  const renderMainCart = (sections) => {
    const main = document.getElementById('MainCart-Inner');
    if (!main || !sections) return false;
    const id = main.dataset.sectionId;
    if (!id || !sections[id]) return false;
    const next = parseHTML(sections[id]).getElementById('MainCart-Inner');
    if (!next) return false;
    main.innerHTML = next.innerHTML;
    main.className = next.className;
    return true;
  };

  /* Every cart surface on the page, so one request keeps them all in sync. */
  const getCartSections = () => {
    const list = [];
    const drawer = document.querySelector('cart-drawer');
    if (drawer && typeof drawer.getSectionsToRender === 'function') list.push(...drawer.getSectionsToRender());
    const main = document.getElementById('MainCart-Inner');
    if (main && main.dataset.sectionId) list.push(main.dataset.sectionId);
    list.push('cart-icon-bubble');
    return Array.from(new Set(list));
  };

  /* ---------- cart-drawer ---------- */
  if (!customElements.get('cart-drawer')) {
    customElements.define(
      'cart-drawer',
      class CartDrawer extends DrawerBase {
        connectedCallback() {
          if (typeof super.connectedCallback === 'function') super.connectedCallback();
          this.panel = this.panel || this.querySelector('[data-drawer-panel]') || this;
          // #CartDrawer-Inner (and its close button) is replaced on every render, so delegate.
          this.addEventListener('click', (event) => {
            const btn = event.target.closest('[data-drawer-close]');
            if (btn && this.contains(btn) && typeof this.close === 'function') this.close();
          });
          // Scroll edges: hairlines under the header / above the footer only while
          // content is underneath them (apple-design §12). Scroll doesn't bubble: capture.
          this.addEventListener(
            'scroll',
            (event) => {
              if (event.target && event.target.hasAttribute && event.target.hasAttribute('data-cart-scroll')) this.scheduleEdges();
            },
            true
          );
          // The note accordion changes the content height when it opens or closes
          this.addEventListener('transitionend', () => this.scheduleEdges());
          window.addEventListener('resize', debounce(() => this.updateScrollEdges(), 150));
          this.updateScrollEdges();
        }

        open(trigger) {
          if (typeof super.open === 'function') super.open(trigger);
          this.scheduleEdges();
        }

        scheduleEdges() {
          if (this.edgeFrame) return;
          this.edgeFrame = requestAnimationFrame(() => {
            this.edgeFrame = null;
            this.updateScrollEdges();
          });
        }

        updateScrollEdges() {
          const body = this.querySelector('.cart-drawer__body[data-cart-scroll]');
          const main = this.querySelector('.cart-drawer__main');
          const scrolled = [body, main].some((el) => el && el.scrollTop > 1);
          const more = !!body && body.scrollHeight - body.clientHeight - body.scrollTop > 1;
          this.classList.toggle('is-scrolled', scrolled);
          this.classList.toggle('has-more', more);
        }

        getSectionsToRender() {
          return ['cart-drawer', 'cart-icon-bubble'];
        }

        /**
         * @param {Object} parsedState  JSON from /cart/add.js or /cart/change.js with `sections`
         * @param {Element} [trigger]   element to return focus to on close
         * @param {Object} [options]    { open: true, bump: true, focus: true }
         */
        renderContents(parsedState, trigger, options = {}) {
          const sections = (parsedState && parsedState.sections) || {};
          if (sections['cart-drawer']) {
            const doc = parseHTML(sections['cart-drawer']);
            const next = doc.getElementById('CartDrawer-Inner');
            const current = this.querySelector('#CartDrawer-Inner');
            if (next && current) current.innerHTML = next.innerHTML;
            const nextRoot = doc.querySelector('cart-drawer');
            if (nextRoot) this.classList.toggle('is-empty', nextRoot.classList.contains('is-empty'));
            this.scheduleEdges();
          }
          updateCartBubble(sections['cart-icon-bubble'], options.bump !== false);

          if (this.isOpen) {
            // The focus trap holds references to replaced nodes: re-arm it.
            if (options.focus !== false) this.refocus();
            return;
          }
          if (options.open !== false && typeof this.open === 'function') this.open(trigger);
        }

        refocus(target) {
          const el = target || this.querySelector('[data-drawer-focus]') || this.panel;
          focusElement(el, this.panel);
        }
      }
    );
  }

  /* ---------- cart-items ---------- */
  if (!customElements.get('cart-items')) {
    customElements.define(
      'cart-items',
      class CartItems extends HTMLElement {
        constructor() {
          super();
          this.onQuantityChange = debounce(this.onQuantityChange.bind(this), DEBOUNCE_MS);
        }

        connectedCallback() {
          this.context = this.dataset.context || 'page';
          this.addEventListener('change', (event) => {
            const input = event.target;
            if (!(input instanceof HTMLInputElement) || !input.classList.contains('quantity__input')) return;
            this.onQuantityChange(input);
          });
        }

        onQuantityChange(input) {
          if (!input || !input.isConnected) return;
          const line = parseInt(input.dataset.index, 10);
          if (!line) return;
          const quantity = parseInt(input.value, 10);
          if (Number.isNaN(quantity)) {
            this.resetInput(input);
            return;
          }
          const current = parseInt(input.getAttribute('value'), 10);
          if (quantity === current) return;
          this.updateQuantity(line, Math.max(0, quantity), input.id, input.dataset.quantityVariantId);
        }

        getSectionsToRender() {
          return getCartSections();
        }

        updateQuantity(line, quantity, focusId, variantId) {
          line = parseInt(line, 10);
          quantity = parseInt(quantity, 10);
          if (!line || Number.isNaN(quantity)) return Promise.resolve();
          this.setLoading(true);
          this.hideError(line);
          const body = JSON.stringify({
            line,
            quantity,
            sections: this.getSectionsToRender(),
            sections_url: window.location.pathname,
          });
          return fetch(routes.cart_change_url || '/cart/change', { ...fetchConfig(), body })
            .then((response) => response.json())
            .then((data) => {
              if (!data || data.errors || data.status) {
                const message = errorMessage(data);
                this.fail(line, message, focusId);
                publish(EVENTS.cartError, { source: 'cart-items', message, line, quantity, errors: data && data.errors });
                return;
              }
              this.render(data, focusId, line);
              publish(EVENTS.cartUpdated, { source: 'cart-items', cartData: data, variantId, line, quantity });
            })
            .catch(() => {
              const message = strings.cartError || GENERIC_ERROR;
              this.fail(line, message, focusId);
              publish(EVENTS.cartError, { source: 'cart-items', message, line, quantity });
            })
            .finally(() => this.setLoading(false));
        }

        render(data, focusId, line) {
          const sections = data.sections || {};
          const drawer = document.querySelector('cart-drawer');
          if (drawer && typeof drawer.renderContents === 'function' && sections['cart-drawer']) {
            drawer.renderContents(data, null, { open: false, bump: false, focus: false });
          } else {
            updateCartBubble(sections['cart-icon-bubble'], false);
          }
          renderMainCart(sections);

          // Restore focus to the equivalent input, the previous line, or the heading.
          const context = this.context;
          const target =
            (focusId && document.getElementById(focusId)) ||
            document.getElementById(`Quantity-${context}-${line - 1}`) ||
            (context === 'drawer' ? document.querySelector('cart-drawer [data-drawer-focus]') : document.getElementById('MainCart-Title'));
          const container = context === 'drawer' && drawer && drawer.isOpen ? drawer.panel : null;
          focusElement(target, container);
        }

        fail(line, message, focusId) {
          const input = focusId ? document.getElementById(focusId) : null;
          if (input) this.resetInput(input);
          this.showError(line, message);
          if (input) input.focus({ preventScroll: true });
        }

        resetInput(input) {
          if (!input) return;
          const previous = input.getAttribute('value');
          if (previous != null) input.value = previous;
          const stepper = input.closest('quantity-input');
          if (stepper && typeof stepper.validate === 'function') stepper.validate();
        }

        errorSlot(line) {
          return document.getElementById(`Line-error-${this.context}-${line}`);
        }

        showError(line, message) {
          const slot = this.errorSlot(line);
          if (!slot) return;
          slot.textContent = message;
          slot.hidden = false;
        }

        hideError(line) {
          const slot = this.errorSlot(line);
          if (!slot) return;
          slot.hidden = true;
          slot.textContent = '';
        }

        setLoading(on) {
          this.classList.toggle('is-loading', !!on);
          if (on) this.setAttribute('aria-busy', 'true');
          else this.removeAttribute('aria-busy');
        }
      }
    );
  }

  /* ---------- cart-remove-button ---------- */
  if (!customElements.get('cart-remove-button')) {
    customElements.define(
      'cart-remove-button',
      class CartRemoveButton extends HTMLElement {
        connectedCallback() {
          this.addEventListener('click', (event) => {
            event.preventDefault();
            const items = this.closest('cart-items');
            const line = parseInt(this.dataset.index, 10);
            if (!items || !line || typeof items.updateQuantity !== 'function') return;
            const input = items.querySelector(`input[data-index="${line}"]`);
            items.updateQuantity(line, 0, input ? input.id : null, input ? input.dataset.quantityVariantId : null);
          });
        }
      }
    );
  }

  /* ---------- cart-note ---------- */
  if (!customElements.get('cart-note')) {
    customElements.define(
      'cart-note',
      class CartNote extends HTMLElement {
        connectedCallback() {
          this.textarea = this.querySelector('textarea');
          this.status = this.querySelector('.cart-note__status');
          if (!this.textarea) return;
          this.lastSaved = this.textarea.value;
          this.textarea.addEventListener('change', debounce(() => this.save(), DEBOUNCE_MS));
        }

        save() {
          if (!this.textarea) return;
          const note = this.textarea.value;
          if (note === this.lastSaved) return;
          fetch(routes.cart_update_url || '/cart/update', { ...fetchConfig(), body: JSON.stringify({ note }) })
            .then((response) => {
              if (!response.ok) throw new Error('note');
              this.lastSaved = note;
              this.flash(this.dataset.savedText || '');
            })
            .catch(() => this.flash(this.dataset.errorText || strings.cartError || GENERIC_ERROR, true));
        }

        flash(text, isError = false) {
          if (!this.status) return;
          clearTimeout(this.flashTimer);
          this.status.textContent = text;
          this.status.classList.toggle('is-error', isError);
          this.status.classList.toggle('is-visible', !!text);
          if (!isError) this.flashTimer = setTimeout(() => this.status.classList.remove('is-visible'), 2000);
        }
      }
    );
  }

  /* ---------- free-shipping-bar ----------
     Fill animates on transform: scaleX(var(--progress)). A fresh element
     starts from the previous progress of its surface (drawer or page) so the
     fill grows instead of popping. */
  const progressMemo = {};
  if (!customElements.get('free-shipping-bar')) {
    customElements.define(
      'free-shipping-bar',
      class FreeShippingBar extends HTMLElement {
        connectedCallback() {
          const total = parseFloat(this.dataset.total);
          const threshold = parseFloat(this.dataset.threshold);
          if (!threshold || threshold <= 0 || Number.isNaN(total)) return;
          const progress = Math.min(1, Math.max(0, total / threshold));
          const key = this.closest('cart-drawer') ? 'drawer' : 'page';
          const from = key in progressMemo ? progressMemo[key] : null;
          progressMemo[key] = progress;
          if (from !== null && from !== progress && !reducedMotion()) {
            this.style.setProperty('--progress', from);
            this.getBoundingClientRect();
            requestAnimationFrame(() => this.style.setProperty('--progress', progress));
          } else {
            this.style.setProperty('--progress', progress);
          }
          this.classList.toggle('is-reached', progress >= 1);
          const track = this.querySelector('[role="progressbar"]');
          if (track) track.setAttribute('aria-valuenow', Math.round(progress * 100));
        }
      }
    );
  }

  /* ---------- product-form ---------- */
  if (!customElements.get('product-form')) {
    customElements.define(
      'product-form',
      class ProductForm extends HTMLElement {
        connectedCallback() {
          this.form = this.querySelector('form');
          if (!this.form) return;
          const idInput = this.form.querySelector('[name="id"]');
          if (idInput) idInput.disabled = false;
          this.submitButton = this.form.querySelector('[type="submit"]') || this.querySelector('[type="submit"]');
          this.timers = [];
          this.form.addEventListener('submit', this.onSubmit.bind(this));
        }

        get errorElement() {
          let el = this.querySelector('.product-form__error');
          if (!el && this.form) {
            el = document.createElement('p');
            el.className = 'product-form__error form-status form-status--error';
            el.setAttribute('role', 'alert');
            el.hidden = true;
            this.form.insertAdjacentElement('afterend', el);
          }
          return el;
        }

        showError(message) {
          const el = this.errorElement;
          if (!el) return;
          el.textContent = message;
          el.hidden = false;
        }

        hideError() {
          const el = this.querySelector('.product-form__error');
          if (!el) return;
          el.hidden = true;
          el.textContent = '';
        }

        onSubmit(event) {
          event.preventDefault();
          const button = this.submitButton;
          if (!button || button.disabled || button.getAttribute('aria-disabled') === 'true') return;
          this.hideError();
          button.setAttribute('aria-disabled', 'true');
          button.classList.add('is-loading');

          const drawer = document.querySelector('cart-drawer');
          const wantsDrawer = config.cartType ? config.cartType === 'drawer' : true;
          const useDrawer = wantsDrawer && drawer && typeof drawer.renderContents === 'function';
          const sections = useDrawer && typeof drawer.getSectionsToRender === 'function' ? drawer.getSectionsToRender() : ['cart-icon-bubble'];

          const formData = new FormData(this.form);
          formData.append('sections', sections.join(','));
          formData.append('sections_url', window.location.pathname);

          const init = fetchConfig('javascript');
          delete init.headers['Content-Type'];
          init.headers['X-Requested-With'] = 'XMLHttpRequest';
          init.body = formData;

          fetch(routes.cart_add_url || '/cart/add', init)
            .then((response) => response.json())
            .then((response) => {
              if (!response || response.status) {
                const message = errorMessage(response);
                this.showError(message);
                publish(EVENTS.cartError, { source: 'product-form', message, errors: response && response.errors });
                return;
              }
              if (!useDrawer) {
                window.location = routes.cart_url || '/cart';
                return;
              }
              drawer.renderContents(response, button);
              publish(EVENTS.cartUpdated, { source: 'product-form', productVariantId: response.variant_id, cartData: response });
              this.flashAdded();
            })
            .catch(() => {
              const message = strings.cartError || GENERIC_ERROR;
              this.showError(message);
              publish(EVENTS.cartError, { source: 'product-form', message });
            })
            .finally(() => {
              button.classList.remove('is-loading');
              button.removeAttribute('aria-disabled');
            });
        }

        /* Add to cart → Added, blur crossfade, back after 1.6s. */
        flashAdded() {
          const button = this.submitButton;
          if (!button || !strings.added) return;
          let label = button.querySelector('[data-add-to-cart-text]') || button.querySelector('.btn__text') || button.querySelector('.btn__content') || button;
          if (label.children.length) {
            const plain = Array.from(label.querySelectorAll('span')).find((s) => !s.children.length && s.textContent.trim());
            if (plain) label = plain;
          }
          this.timers.forEach(clearTimeout);
          this.timers = [];
          if (this.originalLabel == null) this.originalLabel = label.textContent;
          const swap = (text, then) => {
            button.classList.add('is-transitioning');
            this.timers.push(
              setTimeout(() => {
                label.textContent = text;
                button.classList.remove('is-transitioning');
                if (then) then();
              }, LABEL_SWAP_MS)
            );
          };
          swap(strings.added, () => {
            this.timers.push(
              setTimeout(() => {
                swap(this.originalLabel, () => {
                  this.originalLabel = null;
                });
              }, LABEL_HOLD_MS)
            );
          });
        }
      }
    );
  }

  /* ---------- header cart link ----------
     theme.js already turns [data-drawer-open] clicks into drawer toggles. This
     only adds the guarantee: with a drawer present the link never navigates;
     without one it stays a plain link to the cart page. */
  document.addEventListener('click', (event) => {
    const link = event.target.closest('#cart-icon-bubble');
    if (!link) return;
    const drawer = document.querySelector('cart-drawer');
    if (!drawer || typeof drawer.open !== 'function') return;
    event.preventDefault();
    if (!link.hasAttribute('data-drawer-open')) drawer.open(link);
  });
})();
