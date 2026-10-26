import { Link } from 'react-router-dom';
import { ArrowLeft, AlertCircle } from 'lucide-react';

/**
 * NotFound — 404 catch-all page to ensure invalid URLs never show a blank screen.
 */
export default function NotFound() {
  return (
    <div className="section-card" style={{ maxWidth: 540, margin: '60px auto', padding: '40px 32px', textAlign: 'center' }}>
      <div style={{ display: 'inline-flex', padding: 12, borderRadius: '50%', background: 'var(--color-bg-muted)', color: 'var(--color-text-muted)', marginBottom: 16 }}>
        <AlertCircle size={32} strokeWidth={1.75} aria-hidden="true" />
      </div>
      <h1 style={{ fontSize: 22, fontWeight: 700, color: 'var(--color-text-primary)', marginBottom: 8 }}>
        404 — Page Not Found
      </h1>
      <p style={{ fontSize: 14, color: 'var(--color-text-muted)', marginBottom: 24, lineHeight: 1.5 }}>
        The link you followed does not exist or has been moved. Use the navigation links above or return to the dashboard.
      </p>
      <div>
        <Link to="/" className="btn btn-primary" style={{ display: 'inline-flex', alignItems: 'center', gap: 8, padding: '8px 18px' }}>
          <ArrowLeft size={16} strokeWidth={1.75} aria-hidden="true" />
          Back to Dashboard
        </Link>
      </div>
    </div>
  );
}
