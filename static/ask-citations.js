/* ═══════════════════════════════════════════════════════════════════════════
   ASK PAGE — Q&A CITATIONS RENDERER
   Displays verified Q&A answers from the api response, prioritized above
   raw article citations. Integrates with the existing answer display flow.
═══════════════════════════════════════════════════════════════════════════ */

/**
 * Render citations (both Q&A and law articles) from API response
 * Q&A citations are displayed first as they are pre-verified answers
 */
function displayCitations(citations) {
  const citationsContainer = document.getElementById('answer-citations');
  if (!citationsContainer) return;
  
  citationsContainer.innerHTML = '';
  
  // Display Q&A citations FIRST (higher priority)
  if (citations.qa && citations.qa.length > 0) {
    const qaSection = document.createElement('div');
    qaSection.className = 'citations-section qa-section';
    qaSection.innerHTML = `
      <div class="citations-section-header">
        <h4 class="citations-section-title">✓ Verified Q&A</h4>
        <span class="citations-section-count">${citations.qa.length}</span>
      </div>
    `;
    
    citations.qa.forEach((item, idx) => {
      const qaCard = document.createElement('div');
      qaCard.className = 'citation-card qa-citation-card';
      qaCard.innerHTML = `
        <div class="qa-citation-law">${escapeHtml(item.law || '')}</div>
        <div class="qa-citation-question">${escapeHtml(item.question || '')}</div>
        ${item.ref ? `<div class="qa-citation-ref">Ref: ${escapeHtml(item.ref)}</div>` : ''}
      `;
      qaSection.appendChild(qaCard);
    });
    
    citationsContainer.appendChild(qaSection);
  }
  
  // Display law article citations
  if (citations.laws && citations.laws.length > 0) {
    const lawSection = document.createElement('div');
    lawSection.className = 'citations-section law-section';
    lawSection.innerHTML = `
      <div class="citations-section-header">
        <h4 class="citations-section-title">📜 Law Articles</h4>
        <span class="citations-section-count">${citations.laws.length}</span>
      </div>
    `;
    
    citations.laws.forEach((item, idx) => {
      const lawCard = document.createElement('div');
      lawCard.className = 'citation-card law-citation-card';
      lawCard.innerHTML = `
        <div class="law-citation-name">${escapeHtml(item.law || '')}</div>
        <div class="law-citation-article">Art. ${escapeHtml(item.article || '')}</div>
        ${item.title ? `<div class="law-citation-title">${escapeHtml(item.title)}</div>` : ''}
      `;
      lawSection.appendChild(lawCard);
    });
    
    citationsContainer.appendChild(lawSection);
  }
  
  // Show empty state if no citations
  if ((!citations.qa || citations.qa.length === 0) && 
      (!citations.laws || citations.laws.length === 0)) {
    citationsContainer.innerHTML = '<div class="citations-empty">No citations found</div>';
  }
}

/**
 * Escape HTML to prevent XSS
 */
function escapeHtml(text) {
  const map = {
    '&': '&amp;',
    '<': '&lt;',
    '>': '&gt;',
    '"': '&quot;',
    "'": '&#039;'
  };
  return text.replace(/[&<>"']/g, m => map[m]);
}
