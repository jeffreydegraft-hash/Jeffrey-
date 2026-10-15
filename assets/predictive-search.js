/* ==========================================================================
   Olivet — predictive-search.js
   <predictive-search> wraps the search form in the search drawer.
   - 250ms debounce, previous request aborted (AbortController)
   - .is-loading on the element (skeleton row), .has-results when open
   - results HTML comes from the `predictive-search` section via
     routes.predictive_search_url, parsed with DOMParser
   - Arrow keys move aria-selected through [role=option], Enter follows the
     selected link, Escape clears the input or closes the drawer
   ========================================================================== */
(() => {
  if (customElements.get('predictive-search')) return;

  const Olivet = window.Olivet || {};
  const routes = Olivet.routes || {};
  const strings = Olivet.strings || {};

  const debounce = (fn, wait) => {
    let t;
    return (...args) => {
      clearTimeout(t);
      t = setTimeout(() => fn(...args), wait);
    };
  };

  class PredictiveSearch extends HTMLElement {
    constructor() {
      super();
      this.cache = new Map();
      this.controller = null;
      this.onInput = this.onInput.bind(this);
      this.onKeydown = this.onKeydown.bind(this);
      this.onSubmit = this.onSubmit.bind(this);
      this.onFocus = this.onFocus.bind(this);
      this.onResultsClick = this.onResultsClick.bind(this);
      this.search = debounce(() => this.onChange(), 250);
    }

    connectedCallback() {
      this.input = this.querySelector('input[type="search"]');
      this.form = this.querySelector('form');
      this.results = this.querySelector('#predictive-search-results');
      this.status = this.querySelector('[data-predictive-search-status]');
      this.popular = (this.closest('[data-drawer]') || document).querySelector('[data-search-popular]');
      if (!this.input || !this.results) return;

      this.input.addEventListener('input', this.onInput);
      this.input.addEventListener('focus', this.onFocus);
      this.addEventListener('keydown', this.onKeydown);
      if (this.form) this.form.addEventListener('submit', this.onSubmit);
      this.results.addEventListener('click', this.onResultsClick);
    }

    disconnectedCallback() {
      if (this.controller) this.controller.abort();
    }

    /* ---------- state ---------- */
    get query() {
      return this.input.value.trim();
    }

    get isOpen() {
      return this.results.classList.contains('is-open');
    }

    get options() {
      return Array.from(this.results.querySelectorAll('[role="option"]'));
    }

    get selected() {
      return this.results.querySelector('[role="option"][aria-selected="true"]');
    }

    setLoading(loading) {
      this.classList.toggle('is-loading', loading);
      this.input.setAttribute('aria-busy', loading ? 'true' : 'false');
      if (loading) this.setStatus(this.dataset.loadingText || strings.searchLoading || '');
    }

    setStatus(text) {
      if (this.status) this.status.textContent = text || '';
    }

    togglePopular() {
      if (this.popular) this.popular.hidden = this.query.length > 0;
    }

    /* ---------- events ---------- */
    onInput() {
      this.togglePopular();
      this.search();
    }

    onFocus() {
      // Re-open cached results when focus returns to a non-empty input
      if (!this.isOpen && this.query.length && this.cache.has(this.query.toLowerCase())) {
        this.render(this.cache.get(this.query.toLowerCase()));
      }
    }

    onChange() {
      const q = this.query;
      if (!q.length) {
        this.close(true);
        return;
      }
      this.fetchResults(q);
    }

    onSubmit(event) {
      const selected = this.selected;
      const link = selected && selected.querySelector('a[href]');
      if (link) {
        event.preventDefault();
        window.location.href = link.href;
        return;
      }
      if (!this.query.length) event.preventDefault();
    }

    onResultsClick(event) {
      const option = event.target.closest('[role="option"]');
      if (option) this.select(option, false);
    }

    onKeydown(event) {
      switch (event.key) {
        case 'ArrowDown':
          event.preventDefault();
          this.move(1);
          break;
        case 'ArrowUp':
          event.preventDefault();
          this.move(-1);
          break;
        case 'Enter': {
          const selected = this.selected;
          const link = selected && selected.querySelector('a[href]');
          if (link) {
            event.preventDefault();
            window.location.href = link.href;
          }
          break;
        }
        case 'Escape': {
          event.preventDefault();
          event.stopPropagation();
          if (this.query.length) {
            this.input.value = '';
            this.togglePopular();
            this.close(true);
            this.input.focus();
          } else {
            const drawer = this.closest('[data-drawer]') || document.querySelector('#SearchDrawer');
            if (drawer && typeof drawer.close === 'function') drawer.close();
          }
          break;
        }
        default:
          break;
      }
    }

    /* ---------- keyboard selection ---------- */
    move(delta) {
      const options = this.options;
      if (!this.isOpen || !options.length) return;
      const current = this.selected;
      let index = current ? options.indexOf(current) + delta : delta > 0 ? 0 : options.length - 1;
      if (index < 0) index = options.length - 1;
      if (index >= options.length) index = 0;
      this.select(options[index]);
    }

    select(option, scroll = true) {
      this.options.forEach((el) => el.setAttribute('aria-selected', el === option ? 'true' : 'false'));
      if (option) {
        this.input.setAttribute('aria-activedescendant', option.id || '');
        if (scroll) option.scrollIntoView({ block: 'nearest' });
      } else {
        this.input.removeAttribute('aria-activedescendant');
      }
    }

    /* ---------- fetching ---------- */
    async fetchResults(q) {
      const key = q.toLowerCase();
      if (this.cache.has(key)) {
        this.render(this.cache.get(key));
        return;
      }
      if (this.controller) this.controller.abort();
      const controller = new AbortController();
      this.controller = controller;
      this.setLoading(true);

      const base = routes.predictive_search_url || '/search/suggest';
      const params = new URLSearchParams({
        q,
        'resources[type]': 'product,collection,page,article',
        'resources[limit]': '4',
        'resources[options][fields]': 'title,product_type,variants.title,vendor',
        section_id: 'predictive-search',
      });

      try {
        const response = await fetch(`${base}?${params.toString()}`, { signal: controller.signal });
        if (!response.ok) throw new Error(`Predictive search failed (${response.status})`);
        const text = await response.text();
        const doc = new DOMParser().parseFromString(text, 'text/html');
        const container = doc.querySelector('#predictive-search-results');
        const html = container ? container.innerHTML : '';
        this.cache.set(key, html);
        if (this.query.toLowerCase() !== key) return; // stale: a newer query is in flight
        this.render(html);
      } catch (error) {
        if (error.name === 'AbortError') return;
        this.close(true);
        this.setStatus(this.dataset.errorText || strings.searchError || '');
      } finally {
        if (this.controller === controller) {
          this.controller = null;
          this.setLoading(false);
        }
      }
    }

    render(html) {
      this.results.innerHTML = html;
      this.setLoading(false);
      const live = this.results.querySelector('[data-predictive-search-live]');
      this.setStatus(live ? live.textContent.trim() : '');
      this.open();
    }

    open() {
      this.results.classList.add('is-open');
      this.classList.add('has-results');
      this.input.setAttribute('aria-expanded', 'true');
      this.select(null);
    }

    close(clear = false) {
      if (this.controller) {
        this.controller.abort();
        this.controller = null;
        this.setLoading(false);
      }
      this.results.classList.remove('is-open');
      this.classList.remove('has-results');
      this.input.setAttribute('aria-expanded', 'false');
      this.select(null);
      if (clear) {
        this.results.innerHTML = '';
        this.setStatus('');
      }
    }
  }

  customElements.define('predictive-search', PredictiveSearch);
})();
