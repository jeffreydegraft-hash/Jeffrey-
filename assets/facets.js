/* ==========================================================================
   Olivet — facets.js
   Filtering and sorting through the Section Rendering API, plus the
   mobile <facets-drawer> and the search page's clear button.

   Contract (sections/main-collection-product-grid + snippets/facets):
   - <facet-filters-form> wraps <form data-section="…">
       #FacetFiltersForm (sidebar) / #FacetFiltersFormMobile (drawer)
   - #SortBy toolbar pill (every breakpoint) is form-associated; the sheet
     form carries sort_by as a hidden [data-sort-select] kept in sync
   - #ProductGridContainer is replaced; #ProductCount, #ProductCountDrawer,
     #ActiveFacets, #ActiveFacetsBadge are swapped by id
   - per filter group: [data-facet-group] > [data-facet-selected], [data-facet-values]
   - [data-facet-remove] links (chips, "Clear all") fetch instead of navigating

   Motion: the only thing that moves is the grid's opacity while a request is
   in flight (state). Filtered results do not replay the scroll reveal.
   ========================================================================== */
(() => {
  if (window.__olivetFacets) return;
  window.__olivetFacets = true;

  const Olivet = (window.Olivet = window.Olivet || {});
  const GRID_ID = 'ProductGridContainer';
  const SWAP_IDS = ['ProductCount', 'ProductCountDrawer', 'ActiveFacets', 'ActiveFacetsBadge'];
  const cache = new Map();
  let controller = null;
  let currentQuery = null;

  const debounce =
    Olivet.debounce ||
    ((fn, wait) => {
      let t;
      return (...args) => {
        clearTimeout(t);
        t = setTimeout(() => fn(...args), wait);
      };
    });

  const esc = (s) => (window.CSS && CSS.escape ? CSS.escape(s) : String(s).replace(/["\\]/g, '\\$&'));
  const forms = () => Array.from(document.querySelectorAll('facet-filters-form form[data-section]'));
  const primaryForm = () => document.getElementById('FacetFiltersForm') || document.getElementById('FacetFiltersFormMobile');
  const sectionId = () => {
    const form = primaryForm();
    if (form && form.dataset.section) return form.dataset.section;
    const section = document.querySelector('.collection-grid[data-section-id]');
    return section ? section.dataset.sectionId : null;
  };
  const urlFor = (query) => `${window.location.pathname}${query ? `?${query}` : ''}`;

  /* Form → query string. Empty values are dropped; sort_by is deduped
     (the toolbar select and the sheet's sort value can share a form owner). */
  const buildQuery = (form) => {
    const params = new URLSearchParams();
    new FormData(form).forEach((value, key) => {
      const v = String(value).trim();
      if (v === '') return;
      if (key === 'sort_by') params.set(key, v);
      else params.append(key, v);
    });
    return params.toString();
  };

  const syncSort = (value, except) => {
    document.querySelectorAll('#SortBy, facet-filters-form [name="sort_by"]').forEach((el) => {
      if (el !== except) el.value = value;
    });
    fitSort();
  };

  /* The sort pill hugs the current order ("Featured ⌄"). CSS field-sizing
     does this where supported; elsewhere a hidden twin measures the label. */
  const FIELD_SIZING = !!(window.CSS && CSS.supports && CSS.supports('field-sizing', 'content'));
  function fitSort() {
    const select = document.getElementById('SortBy');
    if (FIELD_SIZING || !select || !select.isConnected) return;
    const option = select.options[select.selectedIndex];
    if (!option) return;
    const cs = getComputedStyle(select);
    const probe = document.createElement('span');
    probe.textContent = option.text;
    Object.assign(probe.style, {
      position: 'absolute',
      visibility: 'hidden',
      whiteSpace: 'pre',
      fontFamily: cs.fontFamily,
      fontSize: cs.fontSize,
      fontWeight: cs.fontWeight,
      letterSpacing: cs.letterSpacing,
    });
    document.body.appendChild(probe);
    const text = probe.getBoundingClientRect().width;
    probe.remove();
    const pad = parseFloat(cs.paddingLeft) + parseFloat(cs.paddingRight);
    select.style.width = `${Math.ceil(text + pad) + 2}px`;
  }

  const setLoading = (on) => {
    const grid = document.getElementById(GRID_ID);
    if (!grid) return;
    grid.classList.toggle('is-loading', on);
    grid.setAttribute('aria-busy', on ? 'true' : 'false');
  };

  const fetchSection = (query) => {
    const id = sectionId();
    if (!id) return Promise.reject(new Error('facets: no section id'));
    if (cache.has(query)) return Promise.resolve(cache.get(query));
    if (controller) controller.abort();
    controller = new AbortController();
    const url = `${window.location.pathname}?${query ? `${query}&` : ''}section_id=${encodeURIComponent(id)}`;
    return fetch(url, { signal: controller.signal })
      .then((res) => {
        if (!res.ok) throw new Error(`facets: ${res.status}`);
        return res.text();
      })
      .then((html) => {
        cache.set(query, html);
        return html;
      });
  };

  /* ---------- rendering ---------- */
  const renderGrid = (doc) => {
    const grid = document.getElementById(GRID_ID);
    const next = doc.getElementById(GRID_ID);
    if (!grid || !next) return;
    grid.innerHTML = next.innerHTML;
    if (Olivet.observeReveal) Olivet.observeReveal(grid);
    // Same task as the insert: no style recalc in between, so no reveal replays.
    grid.querySelectorAll('[data-reveal]').forEach((n) => n.classList.add('is-visible'));
    grid.querySelectorAll('img.media__img').forEach((img) => {
      if (img.complete && img.naturalWidth > 0) img.classList.add('is-loaded');
    });
  };

  const renderSwaps = (doc) => {
    SWAP_IDS.forEach((id) => {
      const cur = document.getElementById(id);
      const next = doc.getElementById(id);
      if (!cur || !next) return;
      cur.innerHTML = next.innerHTML;
      cur.className = next.className;
    });
  };

  /* Update counts in place for the group the user is touching (keeps focus
     and checked state); replace every other group's values wholesale so the
     sidebar and the drawer always mirror each other. */
  const renderGroup = (group, nextGroup, keepFocus) => {
    const selected = group.querySelector('[data-facet-selected]');
    const nextSelected = nextGroup.querySelector('[data-facet-selected]');
    if (selected && nextSelected) {
      selected.innerHTML = nextSelected.innerHTML;
      selected.className = nextSelected.className;
    }
    const values = group.querySelector('[data-facet-values]');
    const nextValues = nextGroup.querySelector('[data-facet-values]');
    if (!values || !nextValues) return;
    if (!keepFocus) {
      values.innerHTML = nextValues.innerHTML;
      return;
    }
    nextValues.querySelectorAll('input[type="checkbox"]').forEach((nextInput) => {
      const input = values.querySelector(`input[name="${esc(nextInput.name)}"][value="${esc(nextInput.value)}"]`);
      if (!input) return;
      input.disabled = nextInput.disabled;
      const label = input.closest('label');
      const nextLabel = nextInput.closest('label');
      const count = label && label.querySelector('[data-facet-count]');
      const nextCount = nextLabel && nextLabel.querySelector('[data-facet-count]');
      if (count && nextCount) count.textContent = nextCount.textContent;
      if (label) label.classList.toggle('is-disabled', nextInput.disabled);
    });
  };

  const renderForms = (doc, source, target) => {
    forms().forEach((form) => {
      const nextForm = doc.getElementById(form.id);
      if (!nextForm) return;
      form.querySelectorAll('[data-facet-group]').forEach((group) => {
        const nextGroup = nextForm.querySelector(`[data-facet-group="${esc(group.dataset.facetGroup)}"]`);
        if (!nextGroup) return;
        const keepFocus = form === source && !!target && group.contains(target);
        renderGroup(group, nextGroup, keepFocus);
      });
      const select = form.querySelector('[data-sort-select]');
      const nextSelect = nextForm.querySelector('[data-sort-select]');
      if (select && nextSelect && select !== target) select.value = nextSelect.value;
    });
    const sortBy = document.getElementById('SortBy');
    const nextSortBy = doc.getElementById('SortBy');
    if (sortBy && nextSortBy && sortBy !== target) sortBy.value = nextSortBy.value;
    fitSort();
  };

  const render = (query, options = {}) => {
    const { source = null, target = null, push = true } = options;
    currentQuery = query;
    setLoading(true);
    return fetchSection(query)
      .then((html) => {
        if (query !== currentQuery) return;
        const doc = new DOMParser().parseFromString(html, 'text/html');
        renderGrid(doc);
        renderSwaps(doc);
        renderForms(doc, source, target);
        // The request is the source of truth for the order: a cached or
        // stale response must not reset the sheet's sort value.
        const sort = new URLSearchParams(query).get('sort_by');
        if (sort) syncSort(sort, null);
        if (push && window.location.search.replace(/^\?/, '') !== query) {
          history.pushState({ olivetFacets: query }, '', urlFor(query));
        }
      })
      .catch((err) => {
        if (err && err.name === 'AbortError') return;
        // Degrade to a full navigation so the visitor still gets results.
        window.location.href = urlFor(query);
      })
      .finally(() => {
        if (query === currentQuery) setLoading(false);
      });
  };

  /* ---------- <facet-filters-form> ---------- */
  if (!customElements.get('facet-filters-form')) {
    customElements.define(
      'facet-filters-form',
      class FacetFiltersForm extends HTMLElement {
        connectedCallback() {
          this.form = this.querySelector('form');
          if (!this.form) return;
          this.debounced = debounce((target) => this.update(target), 300);
          this.form.addEventListener('input', (e) => this.onChange(e));
          this.form.addEventListener('change', (e) => this.onChange(e));
          this.form.addEventListener('submit', (e) => {
            e.preventDefault();
            // Enter inside a price field: apply now, keep the field focused.
            const active = document.activeElement;
            this.update(this.form.contains(active) ? active : null);
          });
        }
        onChange(event) {
          const target = event.target;
          if (!target || !target.matches('input, select')) return;
          if (target.matches('[data-sort-select]')) syncSort(target.value, target);
          this.debounced(target);
        }
        update(target) {
          render(buildQuery(this.form), { source: this.form, target });
        }
      }
    );
  }

  /* ---------- <facets-drawer> ---------- */
  const defineDrawer = () => {
    if (!Olivet.Drawer || customElements.get('facets-drawer')) return;
    customElements.define(
      'facets-drawer',
      class FacetsDrawer extends Olivet.Drawer {
        connectedCallback() {
          super.connectedCallback();
          // One filter surface at a time: the sidebar takes over at 990px.
          this.mq = window.matchMedia('(min-width: 990px)');
          this.onMq = (e) => {
            if (e.matches && this.isOpen) this.close(true);
          };
          if (this.mq.addEventListener) this.mq.addEventListener('change', this.onMq);
          else this.mq.addListener(this.onMq);
        }
        disconnectedCallback() {
          if (!this.mq) return;
          if (this.mq.removeEventListener) this.mq.removeEventListener('change', this.onMq);
          else this.mq.removeListener(this.onMq);
        }
      }
    );
  };
  if (Olivet.Drawer) defineDrawer();
  else document.addEventListener('DOMContentLoaded', defineDrawer);

  /* ---------- document-level wiring ---------- */
  // Sort pill width (no-op where field-sizing is supported): now, once the
  // font settles, and when touch input changes the pill's type size.
  fitSort();
  if (document.fonts && document.fonts.ready) document.fonts.ready.then(fitSort);
  const coarse = window.matchMedia('(pointer: coarse)');
  if (coarse.addEventListener) coarse.addEventListener('change', fitSort);

  // Toolbar sort (form-associated through form="", so its events never reach the form element)
  document.addEventListener('change', (event) => {
    const select = event.target;
    if (!select || select.id !== 'SortBy') return;
    syncSort(select.value, select);
    const form = select.form || primaryForm();
    if (form) render(buildQuery(form), { source: form, target: select });
  });

  // Active-filter chips, "Clear all" links
  document.addEventListener('click', (event) => {
    const link = event.target.closest('a[data-facet-remove]');
    if (!link || !primaryForm()) return;
    let url;
    try {
      url = new URL(link.href, window.location.origin);
    } catch (e) {
      return;
    }
    if (url.pathname !== window.location.pathname) return;
    event.preventDefault();
    render(url.searchParams.toString());
  });

  // Back / forward
  window.addEventListener('popstate', () => {
    if (!primaryForm()) return;
    render(window.location.search.replace(/^\?/, ''), { push: false });
  });

  // Search page: clear the big field (the header's search-drawer handles its own)
  document.addEventListener('click', (event) => {
    const button = event.target.closest('[data-search-reset]');
    if (!button || button.closest('search-drawer')) return;
    const form = button.closest('form');
    const input = form && form.querySelector('input[type="search"]');
    if (!input) return;
    input.value = '';
    input.focus();
    input.dispatchEvent(new Event('input', { bubbles: true }));
  });
})();
