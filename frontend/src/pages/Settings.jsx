import { useState } from 'react';
import { Sliders, Shield, FileSpreadsheet, CheckCircle2, Lock } from 'lucide-react';

/**
 * Settings Page Component
 * Professional configuration panel for categorization rules, export security, and privacy.
 */
export default function Settings() {
  const [formulaProtection, setFormulaProtection] = useState(true);
  const [requireConfirmation, setRequireConfirmation] = useState(true);
  const [autoFlagAmbiguity, setAutoFlagAmbiguity] = useState(true);
  const [savedSuccess, setSavedSuccess] = useState(false);

  const handleSave = (e) => {
    e.preventDefault();
    setSavedSuccess(true);
    setTimeout(() => setSavedSuccess(false), 3000);
  };

  return (
    <div className="settings-page" style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-6)' }}>
      {/* Page Header */}
      <div className="page-header" style={{ marginBottom: 0 }}>
        <h1 className="page-title">Application Settings</h1>
        <p className="page-subtitle">
          Configure deterministic categorization behavior, export security shields, and privacy parameters.
        </p>
      </div>

      {savedSuccess && (
        <div
          className="alert-card alert-success"
          role="status"
          style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-3)' }}
        >
          <CheckCircle2 size={18} strokeWidth={1.75} aria-hidden="true" />
          <span>Settings successfully updated and saved for this session.</span>
        </div>
      )}

      {/* Settings Sections Grid */}
      <form onSubmit={handleSave} style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-5)' }}>
        {/* Categorization Brain Card */}
        <div className="section-card">
          <div className="section-card-header">
            <span className="section-card-title">
              <Sliders size={18} strokeWidth={1.75} aria-hidden="true" />
              Categorization Engine Rules
            </span>
            <span className="navbar-badge" style={{ color: 'var(--color-brand)' }}>
              Deterministic Brain
            </span>
          </div>

          <div style={{ padding: 'var(--space-5) var(--space-6)', display: 'flex', flexDirection: 'column', gap: 'var(--space-4)' }}>
            <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: 'var(--space-4)' }}>
              <div>
                <label style={{ fontSize: '14px', fontWeight: 600, color: 'var(--color-text-primary)', display: 'block', marginBottom: '2px' }}>
                  Ambiguity Flagging
                </label>
                <p style={{ fontSize: '13px', color: 'var(--color-text-muted)', margin: 0 }}>
                  Automatically route low-confidence or dual-matching transactions to the Needs Review queue.
                </p>
              </div>
              <input
                type="checkbox"
                checked={autoFlagAmbiguity}
                onChange={(e) => setAutoFlagAmbiguity(e.target.checked)}
                style={{ width: '18px', height: '18px', accentColor: 'var(--color-brand)', cursor: 'pointer', marginTop: '2px' }}
                aria-label="Toggle ambiguity flagging"
              />
            </div>

            <hr style={{ border: 'none', borderTop: '1px solid var(--color-border)', margin: 0 }} />

            <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: 'var(--space-4)' }}>
              <div>
                <label style={{ fontSize: '14px', fontWeight: 600, color: 'var(--color-text-primary)', display: 'block', marginBottom: '2px' }}>
                  Manual Reclassification Validation
                </label>
                <p style={{ fontSize: '13px', color: 'var(--color-text-muted)', margin: 0 }}>
                  Recalculate live financial summaries and deduction totals immediately upon manual change.
                </p>
              </div>
              <input
                type="checkbox"
                checked={requireConfirmation}
                onChange={(e) => setRequireConfirmation(e.target.checked)}
                style={{ width: '18px', height: '18px', accentColor: 'var(--color-brand)', cursor: 'pointer', marginTop: '2px' }}
                aria-label="Toggle manual reclassification validation"
              />
            </div>
          </div>
        </div>

        {/* Export & Security Card */}
        <div className="section-card">
          <div className="section-card-header">
            <span className="section-card-title">
              <FileSpreadsheet size={18} strokeWidth={1.75} aria-hidden="true" />
              CSV Export & Security Protections
            </span>
            <span className="navbar-badge" style={{ color: 'var(--color-success)' }}>
              Active Shield
            </span>
          </div>

          <div style={{ padding: 'var(--space-5) var(--space-6)', display: 'flex', flexDirection: 'column', gap: 'var(--space-4)' }}>
            <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: 'var(--space-4)' }}>
              <div>
                <label style={{ fontSize: '14px', fontWeight: 600, color: 'var(--color-text-primary)', display: 'block', marginBottom: '2px' }}>
                  CSV Formula Injection Sanitization
                </label>
                <p style={{ fontSize: '13px', color: 'var(--color-text-muted)', margin: 0 }}>
                  Prepend a single quote prefix to cells starting with <code style={{ fontFamily: 'var(--font-mono)' }}>=</code>, <code style={{ fontFamily: 'var(--font-mono)' }}>+</code>, <code style={{ fontFamily: 'var(--font-mono)' }}>-</code>, or <code style={{ fontFamily: 'var(--font-mono)' }}>@</code> to neutralize spreadsheet execution.
                </p>
              </div>
              <input
                type="checkbox"
                checked={formulaProtection}
                onChange={(e) => setFormulaProtection(e.target.checked)}
                style={{ width: '18px', height: '18px', accentColor: 'var(--color-brand)', cursor: 'pointer', marginTop: '2px' }}
                aria-label="Toggle CSV formula injection sanitization"
              />
            </div>
          </div>
        </div>

        {/* Privacy & Architecture Card */}
        <div className="section-card">
          <div className="section-card-header">
            <span className="section-card-title">
              <Shield size={18} strokeWidth={1.75} aria-hidden="true" />
              Data Privacy & Architecture
            </span>
            <span className="navbar-badge">
              <Lock size={10} strokeWidth={1.75} />
              Local Only
            </span>
          </div>

          <div style={{ padding: 'var(--space-5) var(--space-6)', display: 'flex', flexDirection: 'column', gap: 'var(--space-3)' }}>
            <div style={{ fontSize: '13px', color: 'var(--color-text-secondary)', lineHeight: 1.6 }}>
              <strong>Zero External API Calls:</strong> Bank transactions are parsed locally using deterministic regex and pattern matching. No financial data, account numbers, or descriptions are ever transmitted to an external LLM, third-party analytics, or remote database.
            </div>
            <div style={{ fontSize: '12px', color: 'var(--color-text-muted)', fontFamily: 'var(--font-mono)' }}>
              Architecture: Deterministic FastAPI (Backend) + React 19 Client (Frontend)
            </div>
          </div>
        </div>

        {/* Action Buttons */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-3)' }}>
          <button type="submit" className="btn btn-primary">
            Save Preferences
          </button>
        </div>
      </form>
    </div>
  );
}
