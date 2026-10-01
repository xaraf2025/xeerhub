# PHASE 1 IMPLEMENTATION STRATEGY

## Executive Summary
This document outlines the surgical changes needed to restructure XeerHub's navigation and add new pages while preserving all existing functionality.

## Key Principle: Preserve → Refactor → Enhance

Do NOT rewrite the entire file. Make targeted changes to:
1. Navigation HTML
2. JavaScript router
3. Page HTML sections
4. CSS for new sections

---

## PART 1: EXISTING JAVASCRIPT ARCHITECTURE ANALYSIS

### Current Router Pattern (Need to Identify)
The existing index.html appears to use:
- Hash-based routing (`#home`, `#library`, `#ask`, etc.)
- Page visibility controlled by `.page.active` class
- Likely event listeners on navigation links

**Files to inspect:**
- Navigation link click handlers
- Page activation logic
- Existing route mappings

### Existing Functionality to Preserve
✅ Ask AI API calls (Railway endpoint)
✅ Legal Library search/filter/display
✅ Mailchimp newsletter subscription
✅ Google Analytics/Tag Manager
✅ Supabase auth (if used)
✅ Email signup modal
✅ All existing page content

---

## PART 2: NAVIGATION RESTRUCTURING

### HTML Changes

**OLD STRUCTURE:**
```html
<nav class="nav-links">
  <button class="nav-link" data-page="home">Home</button>
  <button class="nav-link" data-page="library">Library</button>
  <button class="nav-link" data-page="ask">Ask</button>
  <button class="nav-link" data-page="pricing">Pricing</button>
  <button class="nav-link" data-page="about">About</button>
  <button class="nav-link" data-page="blog">Blog</button>
  <button class="nav-link" data-page="contact">Contact</button>
</nav>
<button class="nav-cta">Ask AI</button>
```

**NEW STRUCTURE:**
```html
<nav class="nav-links">
  <!-- Product Dropdown -->
  <div class="nav-group">
    <button class="nav-link nav-product-btn">
      Product
      <svg>...</svg>
    </button>
    <div class="nav-dropdown nav-product-menu">
      <a href="#library" class="nav-dropdown-item">Legal Library</a>
      <a href="#ask" class="nav-dropdown-item">Ask AI</a>
    </div>
  </div>
  
  <!-- Main nav items -->
  <button class="nav-link" data-page="solutions">Solutions</button>
  <button class="nav-link" data-page="insights">Insights</button>
  <button class="nav-link" data-page="about">About</button>
  <button class="nav-link" data-page="pricing">Pricing</button>
</nav>

<!-- Primary CTA -->
<button class="nav-cta" data-page="ask">Ask AI</button>
```

### JavaScript Changes

**New Router Function:**
```javascript
// Centralized route mapping
const PAGE_ROUTES = {
  '': 'page-home',
  'home': 'page-home',
  'library': 'page-library',
  'ask': 'page-ask',
  'solutions': 'page-solutions',     // NEW
  'insights': 'page-insights',       // NEW (replaces blog)
  'blog': 'page-insights',           // BACKWARDS COMPAT: redirect to insights
  'about': 'page-about',
  'pricing': 'page-pricing',
  'contact': 'page-contact',
  'dashboard': 'page-dashboard'
};

function routeToPage(pageKey) {
  // Normalize the key
  const normalizedKey = pageKey.toLowerCase().trim();
  
  // Get target page ID
  const pageId = PAGE_ROUTES[normalizedKey] || PAGE_ROUTES[''];
  
  // Hide all pages
  document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
  
  // Show target page
  const targetPage = document.getElementById(pageId);
  if (targetPage) {
    targetPage.classList.add('active');
  }
  
  // Update navigation active state
  updateNavigation(normalizedKey);
}

// Listen for hash changes
window.addEventListener('hashchange', () => {
  const hash = window.location.hash.slice(1).split('/')[0];
  routeToPage(hash);
});

// Initial route on load
routeToPage(window.location.hash.slice(1) || 'home');
```

**Product Dropdown Logic:**
```javascript
function initProductDropdown() {
  const productBtn = document.querySelector('.nav-product-btn');
  const productMenu = document.querySelector('.nav-product-menu');
  
  if (!productBtn || !productMenu) return;
  
  // Toggle on click
  productBtn.addEventListener('click', (e) => {
    e.stopPropagation();
    productMenu.classList.toggle('open');
  });
  
  // Close when clicking outside
  document.addEventListener('click', () => {
    productMenu.classList.remove('open');
  });
  
  // Close when item is clicked
  productMenu.querySelectorAll('a').forEach(link => {
    link.addEventListener('click', () => {
      productMenu.classList.remove('open');
    });
  });
  
  // Keyboard: ESC to close, Tab to navigate
  productBtn.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
      productMenu.classList.remove('open');
      productBtn.focus();
    }
  });
}
```

---

## PART 3: NEW PAGES

### Page 1: Solutions (`#solutions`)

**HTML Structure:**
```html
<section id="page-solutions" class="page">
  <div class="solutions-hero">
    <h1>Legal intelligence for people doing business in Somalia.</h1>
    <p>Accelerate your legal research, compliance, and decision-making.</p>
  </div>
  
  <div class="solutions-grid">
    <!-- 4 solution cards -->
  </div>
  
  <div class="solutions-cta">
    <h2>Ready to get started?</h2>
    <a href="#contact" class="btn btn-gold">Get in touch</a>
  </div>
</section>
```

### Page 2: Insights (`#insights`, backwards compat: `#blog`)

**Key Points:**
- Rename conceptually from "Blog" to "Insights"
- Reuse existing 6 hardcoded articles
- Keep `#blog/...` routes working
- Add category filtering if practical

---

## PART 4: CSS ADDITIONS

New CSS classes for:
- `.nav-group` - wrapper for dropdown
- `.nav-dropdown` - dropdown menu
- `.nav-product-btn` - toggle button with chevron
- `.nav-dropdown-item` - menu item
- `.solutions-*` - solutions page sections
- `.insights-*` - insights page sections (rename from blog)

---

## PART 5: BACKWARDS COMPATIBILITY

### Existing URLs to Preserve:
- `/#library` ✓ (no change)
- `/#ask` ✓ (no change)
- `/#pricing` ✓ (no change)
- `/#about` ✓ (no change)
- `/#contact` ✓ (no change)
- `/#dashboard` ✓ (no change)
- `/#blog` → `#insights` (alias, redirects)
- `/#blog/income-tax-2025` → `#insights/income-tax-2025` (alias)

### Implementation:
Route handler checks if key === 'blog' and maps to PAGE_ROUTES['insights']

---

## PART 6: TESTING CHECKLIST

- [ ] Hash routing works for all 8 pages
- [ ] `#blog` redirects to `#insights`
- [ ] Product dropdown opens/closes on click
- [ ] Product dropdown closes when item selected
- [ ] Product dropdown closes when clicking outside
- [ ] Keyboard navigation works (Tab, ESC)
- [ ] Mobile hamburger menu works
- [ ] All existing functionality preserved:
  - [ ] Ask AI form and API calls
  - [ ] Legal Library search/filters
  - [ ] Email signup
  - [ ] Mailchimp subscription
  - [ ] Analytics tracking
  - [ ] Dashboard access
- [ ] Navigation active state updates correctly
- [ ] All links/buttons functional

---

## PART 7: FILE MODIFICATIONS SUMMARY

### Files to Edit:
1. **index.html** - Navigation restructure + new page sections
2. **app.py** - Add routes to SPA_PATHS
3. **sitemap.xml** - Rename blog to insights, add solutions

### Commit Strategy:
- Commit 1: Navigation restructure + routing
- Commit 2: New page sections (Solutions, Insights)
- Commit 3: CSS updates
- Commit 4: app.py + sitemap.xml

---

## Next Steps

1. Identify exact existing router implementation in index.html
2. Create surgical edits to navigation HTML
3. Add new router function
4. Add product dropdown JavaScript
5. Add page HTML sections
6. Add CSS
7. Test all routes and functionality
8. Commit to feature branch
9. Request review

