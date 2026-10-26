import { AlertCircle, CheckCircle2, AlertTriangle, X } from 'lucide-react';

/**
 * AlertBanner — error / success / parse-warning banners.
 * No emojis. Uses lucide-react icons (16px, stroke 1.75).
 */
export default function AlertBanner({ error, parseErrors, successMessage, onDismiss }) {
  if (!error && (!parseErrors || parseErrors.length === 0) && !successMessage) {
    return null;
  }

  return (
    <aside className="alert-container" aria-live="polite">
      {error && (
        <div className="alert-card alert-error" role="alert">
          <div className="alert-icon-wrap" aria-hidden="true">
            <AlertCircle size={16} strokeWidth={1.75} />
          </div>
          <div className="alert-body">
            <strong>Error:</strong> {error}
          </div>
          {onDismiss && (
            <button
              type="button"
              className="alert-dismiss"
              onClick={onDismiss}
              aria-label="Dismiss error"
            >
              <X size={16} strokeWidth={1.75} />
            </button>
          )}
        </div>
      )}

      {successMessage && (
        <div className="alert-card alert-success" role="status">
          <div className="alert-icon-wrap" aria-hidden="true">
            <CheckCircle2 size={16} strokeWidth={1.75} />
          </div>
          <div className="alert-body">{successMessage}</div>
          {onDismiss && (
            <button
              type="button"
              className="alert-dismiss"
              onClick={onDismiss}
              aria-label="Dismiss message"
            >
              <X size={16} strokeWidth={1.75} />
            </button>
          )}
        </div>
      )}

      {parseErrors && parseErrors.length > 0 && (
        <div className="alert-card alert-warning" role="alert">
          <div className="alert-icon-wrap" aria-hidden="true">
            <AlertTriangle size={16} strokeWidth={1.75} />
          </div>
          <div className="alert-body">
            <strong>Statement Parse Warnings ({parseErrors.length}):</strong>
            <p style={{ marginTop: 4, marginBottom: 6 }}>
              Valid transactions were processed, but {parseErrors.length} row(s) had errors:
            </p>
            <ul className="parse-errors-list">
              {parseErrors.slice(0, 5).map((err, idx) => (
                <li key={`err_${idx}`}>
                  Row {err.row_number || 'Header'}: {err.message}
                </li>
              ))}
              {parseErrors.length > 5 && (
                <li>…and {parseErrors.length - 5} more row warnings</li>
              )}
            </ul>
          </div>
        </div>
      )}
    </aside>
  );
}
