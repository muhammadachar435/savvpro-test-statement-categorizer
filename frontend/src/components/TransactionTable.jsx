import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import {
  Search, X, AlertTriangle, RotateCcw, CheckCircle2,
  ArrowUpDown, Check, ChevronDown, Loader2, AlertCircle,
} from 'lucide-react';

/* ── Helpers ─────────────────────────────────────────────────────────────── */

function formatAmount(amt, type) {
  const num = parseFloat(amt) || 0;
  const abs = new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 2,
  }).format(Math.abs(num));
  if (type === 'credit' || num > 0) return { text: `+${abs}`, isCredit: true };
  return { text: `-${abs}`, isCredit: false };
}

function ConfidenceBadge({ confidence }) {
  const pct = Math.round((confidence || 0) * 100);
  const cls = pct >= 90 ? 'conf-badge conf-high' : pct > 0 ? 'conf-badge conf-mid' : 'conf-badge conf-low';
  const title =
    pct >= 90
      ? 'Deterministic high-confidence rule match'
      : pct > 0
      ? 'Ambiguous keyword match; verification recommended'
      : 'Unrecognized vendor — routed to Needs Review';
  return <span className={cls} title={title}>{pct}%</span>;
}

/* ── Portal Category Dropdown ────────────────────────────────────────────── */
/**
 * Renders the dropdown in a portal on document.body so it is never clipped
 * by parent overflow:hidden/auto.  Position is calculated from the trigger's
 * bounding rect so it anchors correctly wherever in the page the row sits.
 *
 * Keyboard: ArrowUp/Down navigate items, Enter selects, Escape closes.
 */
function CategoryDropdown({ txId, currentValue, categories, onSelect, disabled }) {
  const [open, setOpen] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  const [focusedIdx, setFocusedIdx] = useState(-1);
  const triggerRef = useRef(null);
  const panelRef = useRef(null);
  const searchRef = useRef(null);
  const [panelStyle, setPanelStyle] = useState({});

  // Categories that match the search query
  const filtered = useMemo(() => {
    const q = searchTerm.toLowerCase();
    return categories.filter((c) => c.toLowerCase().includes(q));
  }, [categories, searchTerm]);

  // Compute panel position from trigger rect
  const openPanel = useCallback(() => {
    if (!triggerRef.current) return;
    const rect = triggerRef.current.getBoundingClientRect();
    const spaceBelow = window.innerHeight - rect.bottom;
    const spaceAbove = rect.top;
    const panelH = 280;

    const openUp = spaceBelow < panelH && spaceAbove > panelH;
    setPanelStyle({
      top: openUp ? rect.top + window.scrollY - panelH - 4 : rect.bottom + window.scrollY + 4,
      left: rect.left + window.scrollX,
      width: Math.max(rect.width, 220),
    });
    setOpen(true);
    setSearchTerm('');
    setFocusedIdx(-1);
    // Focus search after mount
    setTimeout(() => searchRef.current?.focus(), 50);
  }, []);

  // Close on outside click or scroll
  useEffect(() => {
    if (!open) return;
    const handle = (e) => {
      if (
        panelRef.current && !panelRef.current.contains(e.target) &&
        triggerRef.current && !triggerRef.current.contains(e.target)
      ) {
        setOpen(false);
      }
    };
    const handleScroll = () => setOpen(false);
    document.addEventListener('mousedown', handle);
    window.addEventListener('scroll', handleScroll, true);
    return () => {
      document.removeEventListener('mousedown', handle);
      window.removeEventListener('scroll', handleScroll, true);
    };
  }, [open]);

  const handleKeyDown = (e) => {
    if (!open) {
      if (e.key === 'Enter' || e.key === ' ' || e.key === 'ArrowDown') {
        e.preventDefault();
        openPanel();
      }
      return;
    }
    if (e.key === 'Escape') { setOpen(false); triggerRef.current?.focus(); return; }
    if (e.key === 'ArrowDown') { e.preventDefault(); setFocusedIdx((i) => Math.min(i + 1, filtered.length - 1)); }
    if (e.key === 'ArrowUp')   { e.preventDefault(); setFocusedIdx((i) => Math.max(i - 1, 0)); }
    if (e.key === 'Enter' && focusedIdx >= 0) {
      e.preventDefault();
      const cat = filtered[focusedIdx];
      if (cat) { onSelect(txId, cat); setOpen(false); }
    }
  };

  return (
    <div className="category-select-wrapper">
      {/* Trigger button */}
      <button
        ref={triggerRef}
        type="button"
        id={`cat-trigger-${txId}`}
        className={`category-trigger${currentValue === 'Needs Review' ? ' trigger-needs-review' : ''}`}
        onClick={disabled ? undefined : open ? () => setOpen(false) : openPanel}
        onKeyDown={handleKeyDown}
        disabled={disabled}
        aria-haspopup="listbox"
        aria-expanded={open}
        aria-label={`Category for transaction — currently ${currentValue}`}
      >
        <span className="category-trigger-label">{currentValue || 'Select category'}</span>
        <ChevronDown
          size={14}
          strokeWidth={1.75}
          className="category-trigger-chevron"
          aria-hidden="true"
        />
      </button>

      {/* Portal panel */}
      {open && createPortal(
        <div
          ref={panelRef}
          className="category-dropdown-portal"
          style={{
            position: 'absolute',
            top: panelStyle.top,
            left: panelStyle.left,
            width: panelStyle.width,
          }}
          role="listbox"
          aria-label="Tax category options"
          onKeyDown={handleKeyDown}
        >
          {/* Search */}
          <div className="category-dropdown-search">
            <Search size={14} strokeWidth={1.75} style={{ color: 'var(--color-text-muted)', flexShrink: 0 }} />
            <input
              ref={searchRef}
              type="text"
              className="category-dropdown-search-input"
              placeholder="Search categories…"
              value={searchTerm}
              onChange={(e) => { setSearchTerm(e.target.value); setFocusedIdx(-1); }}
              aria-label="Search tax categories"
            />
          </div>

          {/* Options */}
          <div className="category-dropdown-list" role="group">
            {filtered.length === 0 && (
              <div style={{ padding: '12px 12px', fontSize: 13, color: 'var(--color-text-muted)', textAlign: 'center' }}>
                No categories match
              </div>
            )}
            {filtered.map((cat, i) => (
              <button
                key={cat}
                type="button"
                role="option"
                aria-selected={cat === currentValue}
                className={`category-dropdown-item ${cat === currentValue ? 'selected' : ''} ${i === focusedIdx ? 'focused' : ''}`}
                onMouseEnter={() => setFocusedIdx(i)}
                onClick={() => { onSelect(txId, cat); setOpen(false); }}
              >
                {cat}
                {cat === currentValue && (
                  <Check size={14} strokeWidth={1.75} aria-hidden="true" />
                )}
              </button>
            ))}
          </div>
        </div>,
        document.body
      )}
    </div>
  );
}

/* ── TransactionTable ─────────────────────────────────────────────────────── */

/**
 * TransactionTable — interactive transaction ledger with filter tabs, search,
 * inline portal category reclassification, and deterministic audit trails.
 * No emojis. Lucide-react icons only (16px in buttons/inputs/cells, stroke 1.75).
 */
export default function TransactionTable({
  transactions,
  categories,
  onCategoryChange,
  updatingTxId,
}) {
  const [search, setSearch] = useState('');
  const [filterMode, setFilterMode] = useState('all'); // 'all' | 'needs_review'
  const [selectedCategory, setSelectedCategory] = useState('');
  const [selectedType, setSelectedType] = useState('all');

  const needsReviewCount = useMemo(
    () => transactions.filter((t) => t.needs_review).length,
    [transactions]
  );

  const filteredTransactions = useMemo(() => {
    return transactions.filter((tx) => {
      if (filterMode === 'needs_review' && !tx.needs_review) return false;
      if (selectedCategory && tx.category !== selectedCategory) return false;
      if (selectedType !== 'all' && tx.type !== selectedType) return false;
      if (search.trim()) {
        const q = search.toLowerCase();
        const match =
          tx.description.toLowerCase().includes(q) ||
          (tx.reason && tx.reason.toLowerCase().includes(q)) ||
          tx.category.toLowerCase().includes(q);
        if (!match) return false;
      }
      return true;
    });
  }, [transactions, filterMode, selectedCategory, selectedType, search]);

  const resetFilters = () => {
    setSearch('');
    setFilterMode('all');
    setSelectedCategory('');
    setSelectedType('all');
  };

  return (
    <section className="section-card" aria-label="Transaction ledger">
      {/* Toolbar */}
      <div className="ledger-toolbar">
        {/* Filter tabs */}
        <div className="filter-tabs" role="tablist" aria-label="Transaction filter">
          <button
            type="button"
            role="tab"
            aria-selected={filterMode === 'all'}
            className={`tab-btn ${filterMode === 'all' ? 'tab-btn-active' : ''}`}
            onClick={() => setFilterMode('all')}
          >
            All ({transactions.length})
          </button>
          <button
            type="button"
            role="tab"
            aria-selected={filterMode === 'needs_review'}
            className={`tab-btn tab-btn-review ${filterMode === 'needs_review' ? 'tab-btn-active' : ''}`}
            onClick={() => setFilterMode('needs_review')}
          >
            Needs Review
            {needsReviewCount > 0 && (
              <span className="tab-count" aria-label={`${needsReviewCount} items needing review`}>
                {needsReviewCount}
              </span>
            )}
          </button>
        </div>

        {/* Search + selects */}
        <div className="filter-controls">
          {/* Search */}
          <div className="search-wrap">
            <span className="search-icon" aria-hidden="true">
              <Search size={14} strokeWidth={1.75} />
            </span>
            <input
              type="text"
              className="search-input"
              placeholder="Search description, merchant, reason…"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              aria-label="Search transactions"
            />
            {search && (
              <button
                type="button"
                className="search-clear"
                onClick={() => setSearch('')}
                aria-label="Clear search"
              >
                <X size={14} strokeWidth={1.75} />
              </button>
            )}
          </div>

          {/* Category select */}
          <select
            className="select-filter"
            value={selectedCategory}
            onChange={(e) => setSelectedCategory(e.target.value)}
            aria-label="Filter by category"
          >
            <option value="">All Categories</option>
            {categories.map((cat) => (
              <option key={`opt_${cat}`} value={cat}>{cat}</option>
            ))}
          </select>

          {/* Type select */}
          <select
            className="select-filter"
            value={selectedType}
            onChange={(e) => setSelectedType(e.target.value)}
            aria-label="Filter by transaction type"
          >
            <option value="all">All Types</option>
            <option value="debit">Debits (Outflows)</option>
            <option value="credit">Credits (Inflows)</option>
          </select>
        </div>
      </div>

      {/* Table or empty state */}
      {filteredTransactions.length === 0 ? (
        <div className="empty-state">
          <div className="empty-icon" aria-hidden="true">
            <Search size={24} strokeWidth={1.75} />
          </div>
          <h4>No transactions match your filters</h4>
          <p>Try clearing your search query or reset filters to see all statement items.</p>
          <button
            type="button"
            className="btn btn-secondary"
            onClick={resetFilters}
          >
            Reset Filters
          </button>
        </div>
      ) : (
        <div className="table-responsive">
          <table className="ledger-table">
            <thead>
              <tr>
                <th scope="col" className="col-row">#</th>
                <th scope="col" className="col-date">Date</th>
                <th scope="col" className="col-desc">Description &amp; Audit Trail</th>
                <th scope="col" className="col-amount text-right">Amount</th>
                <th scope="col" className="col-category">Tax Category (Reclassify)</th>
                <th scope="col" className="col-conf text-center">Confidence</th>
              </tr>
            </thead>
            <tbody>
              {filteredTransactions.map((tx) => {
                const { text: amtText, isCredit } = formatAmount(tx.amount, tx.type);
                const isUpdating = updatingTxId === tx.id;

                return (
                  <tr
                    key={tx.id}
                    className={[
                      'ledger-row',
                      tx.needs_review ? 'row-needs-review' : '',
                      tx.manually_edited ? 'row-edited' : '',
                    ]
                      .filter(Boolean)
                      .join(' ')}
                  >
                    <td className="col-row">{tx.row_number}</td>
                    <td className="col-date">{tx.date || '—'}</td>

                    {/* Description + badges */}
                    <td className="col-desc">
                      <span className="desc-text">{tx.description}</span>
                      <div className="row-badges">
                        {tx.needs_review && (
                          <span className="badge badge-needs-review">
                            <AlertTriangle size={10} strokeWidth={1.75} aria-hidden="true" />
                            Needs Review
                          </span>
                        )}
                        {tx.is_refund && (
                          <span className="badge badge-refund">
                            <RotateCcw size={10} strokeWidth={1.75} aria-hidden="true" />
                            Refund Offset
                          </span>
                        )}
                        {tx.is_transfer && (
                          <span className="badge badge-transfer">
                            <ArrowUpDown size={10} strokeWidth={1.75} aria-hidden="true" />
                            Transfer
                          </span>
                        )}
                        {tx.manually_edited && (
                          <span className="badge badge-edited">
                            <CheckCircle2 size={10} strokeWidth={1.75} aria-hidden="true" />
                            User Verified
                          </span>
                        )}
                      </div>
                      {tx.reason && (
                        <div className="audit-reason" title={tx.reason}>
                          <span className="reason-label">Brain:</span> {tx.reason}
                        </div>
                      )}
                    </td>

                    {/* Amount */}
                    <td className={`col-amount text-right ${isCredit ? 'amount-credit' : 'amount-debit'}`}>
                      <span className="amount-value">{amtText}</span>
                    </td>

                    {/* Category dropdown — portal-rendered, fixes z-index/clipping */}
                    <td className="col-category">
                      {categories.length > 0 ? (
                        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                          <CategoryDropdown
                            txId={tx.id}
                            currentValue={tx.category}
                            categories={categories}
                            onSelect={onCategoryChange}
                            disabled={isUpdating || !!updatingTxId}
                          />
                          {isUpdating && (
                            <span className="updating-spinner" aria-label="Updating category">
                              <Loader2 size={14} strokeWidth={1.75} className="spin" />
                            </span>
                          )}
                        </div>
                      ) : (
                        <span style={{ display: 'flex', alignItems: 'center', gap: 4, color: 'var(--color-text-muted)', fontSize: 12 }}>
                          <AlertCircle size={14} strokeWidth={1.75} />
                          Categories loading…
                        </span>
                      )}
                    </td>

                    {/* Confidence */}
                    <td className="col-conf text-center">
                      <ConfidenceBadge confidence={tx.confidence} />
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
