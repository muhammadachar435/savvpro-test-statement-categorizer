import {
  TrendingUp, CreditCard, Receipt, RotateCcw, ArrowLeftRight, AlertTriangle,
} from 'lucide-react';

/** Currency formatter */
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
 * SummaryCards — six financial KPI cards with gradient corner glow.
 * No emojis; lucide-react icons (20px, stroke 1.75) in card headers only.
 */
export default function SummaryCards({ summary }) {
  if (!summary) return null;

  const totalDeductible =
    summary.category_breakdown?.reduce((acc, cat) => {
      const val = parseFloat(cat.deductible_estimate) || 0;
      return acc + val;
    }, 0) || 0;

  const needsReviewCount = summary.total_needs_review_count || 0;

  const cards = [
    {
      label: 'Gross Client Revenue',
      value: formatMoney(summary.total_income),
      caption: 'Taxable gross business inflows',
      cls: 'metric-income',
    },
    {
      label: 'Net Operating Expenses',
      value: formatMoney(summary.total_expenses),
      caption: 'Net business costs (refunds offset)',
      cls: 'metric-expense',
    },
    {
      label: 'Tax Deductible Estimate',
      value: formatMoney(totalDeductible),
      caption: 'Schedule C eligible deductions',
      cls: 'metric-deduction',
    },
    {
      label: 'Expense Refunds Offset',
      value: formatMoney(summary.total_refunds),
      caption: 'Credited back against categories',
      cls: 'metric-refund',
    },
    {
      label: 'Transfers & Card Payoffs',
      value: formatMoney(summary.total_transfers),
      caption: 'Non-deductible balance movements',
      cls: 'metric-transfer',
    },
    {
      label: 'Needs User Review',
      value: needsReviewCount,
      subtext: `item${needsReviewCount === 1 ? '' : 's'}`,
      caption: needsReviewCount > 0
        ? 'Requires classification before filing'
        : 'All transactions categorized',
      cls: `metric-review ${needsReviewCount > 0 ? 'metric-review-active' : ''}`,
      isCount: true,
    },
  ];

  return (
    <section className="summary-grid" aria-label="Statement financial totals">
      {cards.map((card) => (
        <div key={card.label} className={`metric-card ${card.cls}`}>
          <span className="metric-label">{card.label}</span>
          <div className="metric-value">
            {card.value}
            {card.subtext && (
              <span className="metric-subtext">{card.subtext}</span>
            )}
          </div>
          <p className="metric-caption">{card.caption}</p>
        </div>
      ))}
    </section>
  );
}
