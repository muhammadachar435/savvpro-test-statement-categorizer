import { Link } from 'react-router-dom';
import { FileText, ArrowRight, CheckCircle2 } from 'lucide-react';

/**
 * Schedule C Page Component
 * IRS Schedule C (Form 1040) tax classification overview and deductions breakdown.
 */
export default function ScheduleC({ statement }) {
  const summary = statement?.summary;
  const breakdown = summary?.category_breakdown;
  const hasStatement = Boolean(statement && summary);

  const scheduleCLines = [
    { line: 'Line 8', category: 'Advertising', desc: 'Marketing campaigns, Google/Meta ads, promotional domain expenses.' },
    { line: 'Line 9', category: 'Car & Truck Expenses', desc: 'Business mileage, parking fees, tolls, vehicle maintenance.' },
    { line: 'Line 11', category: 'Contract Labor', desc: 'Subcontractors, external design or engineering freelancers.' },
    { line: 'Line 17', category: 'Legal & Professional Services', desc: 'Accounting fees, CPA consults, legal compliance retainers.' },
    { line: 'Line 18', category: 'Office Expenses', desc: 'Stationery, office supplies, postage, non-capitalized equipment.' },
    { line: 'Line 22', category: 'Supplies', desc: 'Hardware components, cables, incidental materials consumed.' },
    { line: 'Line 24a', category: 'Travel', desc: 'Airfare, lodging, rideshare for business client trips.' },
    { line: 'Line 24b', category: 'Deductible Meals (50%)', desc: 'Qualifying business meals subject to 50% statutory limitation.' },
    { line: 'Line 25', category: 'Utilities', desc: 'Business Internet, dedicated phone lines, utilities allocation.' },
    { line: 'Line 27a', category: 'Other Expenses (Software/SaaS/Cloud)', desc: 'Cloud infrastructure (AWS/GCP), GitHub, Figma, SaaS subscriptions.' },
  ];

  return (
    <div className="schedule-c-page" style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-6)' }}>
      {/* Page Header */}
      <div className="page-header" style={{ marginBottom: 0 }}>
        <h1 className="page-title">IRS Schedule C Deductions</h1>
        <p className="page-subtitle">
          Form 1040 Profit or Loss From Business (Sole Proprietorship) expense classifications.
        </p>
      </div>

      {/* Statement Status Banner */}
      {hasStatement ? (
        <div
          className="section-card"
          style={{
            padding: 'var(--space-5) var(--space-6)',
            background: 'var(--color-bg)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            flexWrap: 'wrap',
            gap: 'var(--space-4)',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-3)' }}>
            <div style={{ color: 'var(--color-success)', display: 'flex' }}>
              <CheckCircle2 size={20} strokeWidth={1.75} aria-hidden="true" />
            </div>
            <div>
              <div style={{ fontSize: '14px', fontWeight: 600, color: 'var(--color-text-primary)' }}>
                Active Statement: <span style={{ fontFamily: 'var(--font-mono)' }}>{statement.filename}</span>
              </div>
              <div style={{ fontSize: '12px', color: 'var(--color-text-muted)' }}>
                Total Deductible Expenses Calculated:{' '}
                <strong style={{ color: 'var(--color-deductible)', fontFamily: 'var(--font-mono)' }}>
                  ${(summary.total_deductible || 0).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                </strong>
              </div>
            </div>
          </div>
          <Link to="/" className="btn btn-secondary btn-sm" style={{ display: 'inline-flex', alignItems: 'center', gap: '6px' }}>
            <span>View Full Table on Dashboard</span>
            <ArrowRight size={14} strokeWidth={1.75} aria-hidden="true" />
          </Link>
        </div>
      ) : (
        <div
          className="section-card"
          style={{
            padding: 'var(--space-5) var(--space-6)',
            background: 'var(--color-bg-subtle)',
            borderLeft: '4px solid var(--color-brand)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            flexWrap: 'wrap',
            gap: 'var(--space-4)',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-3)' }}>
            <div style={{ color: 'var(--color-brand)', display: 'flex' }}>
              <FileText size={20} strokeWidth={1.75} aria-hidden="true" />
            </div>
            <div>
              <div style={{ fontSize: '14px', fontWeight: 600, color: 'var(--color-text-primary)' }}>
                No Bank Statement Loaded Yet
              </div>
              <div style={{ fontSize: '12px', color: 'var(--color-text-muted)' }}>
                Upload a CSV bank statement on the Dashboard or load the sample file to see live Schedule C totals.
              </div>
            </div>
          </div>
          <Link to="/" className="btn btn-primary btn-sm" style={{ display: 'inline-flex', alignItems: 'center', gap: '6px' }}>
            <span>Go to Dashboard</span>
            <ArrowRight size={14} strokeWidth={1.75} aria-hidden="true" />
          </Link>
        </div>
      )}

      {/* Schedule C Tax Classification Map Card */}
      <div className="section-card">
        <div className="section-card-header">
          <span className="section-card-title">
            <FileText size={18} strokeWidth={1.75} aria-hidden="true" />
            Schedule C Part II Expense Mapping Rules
          </span>
          <span style={{ fontSize: '12px', color: 'var(--color-text-muted)' }}>
            Deterministic Categorization
          </span>
        </div>

        <div style={{ overflowX: 'auto' }}>
          <table className="ledger-table" style={{ width: '100%' }}>
            <thead>
              <tr>
                <th style={{ width: '120px' }}>IRS Line</th>
                <th style={{ width: '220px' }}>Category Name</th>
                <th>Standard Freelancer Description</th>
                {hasStatement && <th className="text-right" style={{ width: '150px' }}>Current Total</th>}
              </tr>
            </thead>
            <tbody>
              {scheduleCLines.map((item) => {
                const matchedBreakdown = breakdown?.[item.category];
                return (
                  <tr key={item.line}>
                    <td style={{ fontWeight: 600, color: 'var(--color-brand)', fontFamily: 'var(--font-mono)' }}>
                      {item.line}
                    </td>
                    <td style={{ fontWeight: 600, color: 'var(--color-text-primary)' }}>
                      {item.category}
                    </td>
                    <td style={{ color: 'var(--color-text-secondary)', fontSize: '13px' }}>
                      {item.desc}
                    </td>
                    {hasStatement && (
                      <td className="text-right" style={{ fontFamily: 'var(--font-mono)', fontWeight: 600 }}>
                        {matchedBreakdown ? (
                          <span style={{ color: 'var(--color-deductible)' }}>
                            ${matchedBreakdown.total_amount.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                          </span>
                        ) : (
                          <span style={{ color: 'var(--color-text-disabled)' }}>$0.00</span>
                        )}
                      </td>
                    )}
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
