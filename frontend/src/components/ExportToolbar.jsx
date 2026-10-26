import { useState } from 'react';
import { FileText, CheckCircle2, AlertTriangle, Download, RefreshCw, Loader2 } from 'lucide-react';

/**
 * ExportToolbar — file metadata, export filename input, and action buttons.
 * No emojis. Lucide-react icons (16px, stroke 1.75).
 */
export default function ExportToolbar({
  filename,
  totalRows,
  needsReviewCount,
  onExport,
  onReset,
  isExporting,
}) {
  const defaultExportName = filename
    ? `categorized_${filename.replace(/\.csv$/i, '')}.csv`
    : 'categorized_statement.csv';

  const [exportFilename, setExportFilename] = useState(defaultExportName);

  const handleExportClick = () => {
    onExport(exportFilename || defaultExportName);
  };

  return (
    <section className="export-toolbar-card" aria-label="Statement export and management">
      {/* Left: file metadata */}
      <div className="toolbar-info">
        <div className="statement-meta">
          <div className="file-icon-wrap" aria-hidden="true">
            <FileText size={16} strokeWidth={1.75} />
          </div>
          <div>
            <div className="active-filename">{filename || 'Statement'}</div>
            <div className="meta-stats">
              {totalRows} transaction{totalRows === 1 ? '' : 's'} ·{' '}
              {needsReviewCount === 0 ? (
                <span className="status-all-clean">
                  <CheckCircle2
                    size={12}
                    strokeWidth={1.75}
                    style={{ display: 'inline', verticalAlign: 'middle', marginRight: 3 }}
                    aria-hidden="true"
                  />
                  All items reviewed & ready
                </span>
              ) : (
                <span className="status-pending-warning">
                  <AlertTriangle
                    size={12}
                    strokeWidth={1.75}
                    style={{ display: 'inline', verticalAlign: 'middle', marginRight: 3 }}
                    aria-hidden="true"
                  />
                  {needsReviewCount} item{needsReviewCount === 1 ? '' : 's'} pending review
                </span>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Right: actions */}
      <div className="toolbar-actions">
        <label htmlFor="export-filename-input" className="sr-only">
          Export CSV filename
        </label>
        <input
          id="export-filename-input"
          type="text"
          className="input-filename"
          placeholder="export_filename.csv"
          value={exportFilename}
          onChange={(e) => setExportFilename(e.target.value)}
          disabled={isExporting}
        />

        <button
          type="button"
          className="btn btn-primary"
          onClick={handleExportClick}
          disabled={isExporting}
          aria-label="Export reviewed CSV"
        >
          {isExporting
            ? <><Loader2 size={16} strokeWidth={1.75} className="spin" /> Exporting…</>
            : <><Download size={16} strokeWidth={1.75} /> Export CSV</>}
        </button>

        <button
          type="button"
          className="btn btn-secondary"
          onClick={onReset}
          disabled={isExporting}
          title="Upload or load another statement"
          aria-label="Load new statement"
        >
          <RefreshCw size={16} strokeWidth={1.75} />
          New Statement
        </button>
      </div>
    </section>
  );
}
