import { useState } from 'react';
import { ChevronUp, ChevronDown } from 'lucide-react';

function formatMoney(val) {
  if (val === undefined || val === null || val === '') return '$0.00';
  const num = typeof val === 'number' ? val : parseFloat(val);
  if (isNaN(num)) return '$0.00';
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 2,
  }).format(num);
}

/**
 * CategoryBreakdown — IRS Schedule C tax breakdown table.
 * Collapsible. No emojis. Lucide-react only.
 */
export default function CategoryBreakdown({ breakdown }) {
  const [isOpen, setIsOpen] = useState(true);

  if (!breakdown || breakdown.length === 0) return null;

  const toggle = () => setIsOpen((o) => !o);

  return (
    <section className="section-card" aria-label="Tax category breakdown">
      {/* Header */}
      <div className="section-card-header">
        <h3
          className="section-card-title"
          onClick={toggle}
          role="button"
          tabIndex={0}
          aria-expanded={isOpen}
          onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') toggle(); }}
        >
          IRS Schedule C — Tax Category Breakdown
        </h3>
        <button
          type="button"
          className="btn-collapse"
          onClick={toggle}
          aria-expanded={isOpen}
          aria-label={isOpen ? 'Collapse breakdown' : 'Expand breakdown'}
        >
          {isOpen
            ? <><ChevronUp size={14} strokeWidth={1.75} /> Collapse</>
            : <><ChevronDown size={14} strokeWidth={1.75} /> Expand</>}
        </button>
      </div>

      {/* Table */}
      {isOpen && (
        <div className="table-responsive">
          <table className="breakdown-table">
            <thead>
              <tr>
                <th scope="col">Domain Tax Category</th>
                <th scope="col" className="text-center">Count</th>
                <th scope="col" className="text-right">Net Category Amount</th>
                <th scope="col" className="text-center">IRS Deductibility</th>
                <th scope="col" className="text-right">Estimated Deduction</th>
              </tr>
            </thead>
            <tbody>
              {breakdown.map((item) => {
                const isNeedsReview = item.category === 'Needs Review';
                const pillClass =
                  item.deductible_percentage === '100%'
                    ? 'pct-pill pill-100'
                    : item.deductible_percentage === '50%'
                    ? 'pct-pill pill-50'
                    : 'pct-pill pill-0';

                return (
                  <tr
                    key={item.category}
                    className={isNeedsReview && item.count > 0 ? 'row-needs-review-highlight' : ''}
                  >
                    <td>
                      <span className="cat-name">{item.category}</span>
                      {isNeedsReview && item.count > 0 && (
                        <span className="badge-pending" aria-label="Pending review">
                          Pending Review
                        </span>
                      )}
                    </td>
                    <td className="text-center count-cell">{item.count}</td>
                    <td className="text-right amount-cell">{formatMoney(item.total_amount)}</td>
                    <td className="text-center">
                      <span className={pillClass}>{item.deductible_percentage}</span>
                    </td>
                    <td className="text-right deductible-cell">
                      {formatMoney(item.deductible_estimate)}
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
