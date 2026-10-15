/* ==========================================================================
   Olivet — customer.js
   Classic customer accounts: the login / recover switch and the address
   book (add / edit panels, delete confirmation, country → province
   selects). Loaded with defer after shopify_common.js, which supplies
   Shopify.CountryProvinceSelector and Shopify.postLink. Vanilla, no deps.
   ========================================================================== */
(() => {
  const FIELD_SELECTOR =
    'input:not([type="hidden"]):not([disabled]), select:not([disabled]), textarea:not([disabled])';

  const focusFirstField = (panel) => {
    const field = panel.querySelector(FIELD_SELECTOR);
    if (field) field.focus({ preventScroll: true });
  };

  /* ---------- login / recover ----------
     The URL hash is the source of truth: #recover shows the reset panel
     (Shopify itself redirects there after a failed recover post). CSS
     :target paints the right panel before this runs; here we mirror it
     with classes for browsers without :has(), keep aria-expanded honest
     and move focus into the panel that just appeared. */
  const recoverRequested = () => window.location.hash === '#recover';

  const syncLogin = (root, moveFocus) => {
    const login = root.querySelector('[data-login-panel="login"]');
    const recover = root.querySelector('[data-login-panel="recover"]');
    if (!login || !recover) return;
    const showRecover = recoverRequested();
    recover.classList.toggle('is-open', showRecover);
    login.classList.toggle('is-hidden', showRecover);
    root
      .querySelectorAll('[data-login-toggle="recover"]')
      .forEach((toggle) => toggle.setAttribute('aria-expanded', String(showRecover)));
    if (!moveFocus) return;
    const target = showRecover ? recover : login;
    const errors = target.querySelector('[data-form-errors]');
    if (errors) errors.focus({ preventScroll: true });
    else focusFirstField(target);
  };

  let hashListenerBound = false;

  const initLogin = () => {
    const root = document.querySelector('[data-login]');
    if (!root || root.dataset.olivetInit) return;
    root.dataset.olivetInit = 'true';
    syncLogin(root, false);

    root.addEventListener('click', (event) => {
      const toggle = event.target.closest('[data-login-toggle]');
      if (!toggle) return;
      // Navigating to the hash already in the URL fires no hashchange, so
      // resync by hand (e.g. "Back to log in" when the hash is #login).
      if (toggle.getAttribute('href') === window.location.hash) {
        event.preventDefault();
        syncLogin(root, true);
      }
    });

    if (!hashListenerBound) {
      hashListenerBound = true;
      window.addEventListener('hashchange', () => {
        const current = document.querySelector('[data-login]');
        if (current) syncLogin(current, true);
      });
    }
  };

  /* ---------- address book ---------- */
  const togglesFor = (root, panel) => root.querySelectorAll(`[data-address-toggle="#${panel.id}"]`);

  const setExpanded = (root, panel, expanded) => {
    togglesFor(root, panel).forEach((toggle) => toggle.setAttribute('aria-expanded', String(expanded)));
  };

  const closePanel = (root, panel, returnFocus) => {
    if (!panel.classList.contains('is-open')) return;
    panel.classList.remove('is-open');
    setExpanded(root, panel, false);
    if (!returnFocus) return;
    const toggle = togglesFor(root, panel)[0];
    if (toggle) toggle.focus({ preventScroll: true });
  };

  const openPanel = (root, panel) => {
    // One surface at a time: close any other open panel first.
    root
      .querySelectorAll('[data-address-form].is-open')
      .forEach((other) => other !== panel && closePanel(root, other, false));
    panel.classList.add('is-open');
    setExpanded(root, panel, true);
    const errors = panel.querySelector('[data-form-errors]');
    if (errors) errors.focus({ preventScroll: true });
    else focusFirstField(panel);
  };

  const deleteAddress = (url) => {
    if (!url) return;
    if (window.Shopify && typeof window.Shopify.postLink === 'function') {
      window.Shopify.postLink(url, { parameters: { _method: 'delete' } });
      return;
    }
    // shopify_common.js missing: post the same request by hand.
    const form = document.createElement('form');
    form.method = 'post';
    form.action = url;
    const method = document.createElement('input');
    method.type = 'hidden';
    method.name = '_method';
    method.value = 'delete';
    form.appendChild(method);
    document.body.appendChild(form);
    form.submit();
  };

  const initCountrySelects = (root) => {
    if (typeof Shopify === 'undefined' || !Shopify.CountryProvinceSelector) return;
    root.querySelectorAll('[data-address-country-select]').forEach((select) => {
      if (select.dataset.olivetInit) return;
      select.dataset.olivetInit = 'true';
      const suffix = select.dataset.suffix || '';
      new Shopify.CountryProvinceSelector(`AddressForm${suffix}-country`, `AddressForm${suffix}-province`, {
        hideElement: `AddressForm${suffix}-province-container`,
      });
    });
  };

  const initAddresses = () => {
    const root = document.querySelector('[data-customer-addresses]');
    if (!root || root.dataset.olivetInit) return;
    root.dataset.olivetInit = 'true';

    initCountrySelects(root);

    // A form that came back with errors stays open. The marker attribute is
    // dropped once the class is set so Cancel can hide the panel again.
    root.querySelectorAll('[data-address-form]').forEach((panel) => {
      const errors = panel.querySelector('[data-form-errors]');
      if (!errors) return;
      panel.classList.add('is-open');
      setExpanded(root, panel, true);
      errors.removeAttribute('data-form-errors');
    });

    root.addEventListener('click', (event) => {
      const toggle = event.target.closest('[data-address-toggle]');
      if (toggle) {
        const panel = root.querySelector(toggle.getAttribute('data-address-toggle'));
        if (!panel) return;
        if (panel.classList.contains('is-open')) closePanel(root, panel, true);
        else openPanel(root, panel);
        return;
      }

      const cancel = event.target.closest('[data-address-cancel]');
      if (cancel) {
        const panel = cancel.closest('[data-address-form]');
        if (panel) closePanel(root, panel, true);
        return;
      }

      const remove = event.target.closest('[data-address-delete]');
      if (remove) {
        const message = remove.getAttribute('data-confirm-message') || '';
        if (!message || window.confirm(message)) deleteAddress(remove.getAttribute('data-address-delete'));
      }
    });

    root.addEventListener('keydown', (event) => {
      if (event.key !== 'Escape') return;
      const panel = event.target.closest('[data-address-form]');
      if (!panel || !panel.classList.contains('is-open')) return;
      event.preventDefault();
      closePanel(root, panel, true);
    });
  };

  /* ---------- init ---------- */
  const init = () => {
    initLogin();
    initAddresses();
  };

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init);
  else init();

  // Theme editor re-renders the section: the new root has no init flag yet.
  document.addEventListener('shopify:section:load', init);
})();
