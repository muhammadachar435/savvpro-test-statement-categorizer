import { useRef, useState } from 'react';
import { Upload, Loader2, PlayCircle, FolderOpen } from 'lucide-react';

/**
 * StatementUpload — drag-and-drop zone, file selector, and sample demo loader.
 * No emojis. Lucide-react icons (16–20px, stroke 1.75).
 */
export default function StatementUpload({ onFileUpload, onLoadSample, isLoading }) {
  const [isDragging, setIsDragging] = useState(false);
  const fileInputRef = useRef(null);

  const handleDragOver = (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (!isLoading) setIsDragging(true);
  };

  const handleDragLeave = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
    if (isLoading) return;
    const files = e.dataTransfer.files;
    if (files && files.length > 0) {
      const file = files[0];
      if (!file.name.toLowerCase().endsWith('.csv')) {
        alert('Please upload a valid CSV file.');
        return;
      }
      onFileUpload(file);
    }
  };

  const handleFileChange = (e) => {
    const files = e.target.files;
    if (files && files.length > 0) onFileUpload(files[0]);
    if (fileInputRef.current) fileInputRef.current.value = '';
  };

  return (
    <section className="upload-section" aria-label="Statement upload and demo">
      <div style={{ marginBottom: 'var(--space-6)' }}>
        <h2 className="upload-section-title">Upload your bank statement</h2>
        <p className="upload-section-sub">
          Supports bank and credit card CSV exports. Transactions are classified automatically
          using a deterministic zero-LLM engine — nothing leaves your machine.
        </p>
      </div>

      {/* Drop zone */}
      <div
        className={`dropzone ${isDragging ? 'dropzone-active' : ''} ${isLoading ? 'dropzone-loading' : ''}`}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        onClick={() => !isLoading && fileInputRef.current?.click()}
        role="button"
        tabIndex={0}
        onKeyDown={(e) => {
          if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault();
            fileInputRef.current?.click();
          }
        }}
        aria-label="Upload CSV bank statement dropzone"
      >
        <input
          ref={fileInputRef}
          type="file"
          accept=".csv"
          style={{ display: 'none' }}
          onChange={handleFileChange}
          disabled={isLoading}
        />

        <div className="dropzone-content">
          <div className="dropzone-icon-wrap" aria-hidden="true">
            {isLoading
              ? <Loader2 size={24} strokeWidth={1.75} className="spin" />
              : <Upload size={24} strokeWidth={1.75} />}
          </div>
          <div className="dropzone-text">
            <h3>
              {isLoading
                ? 'Processing statement…'
                : 'Drag & drop your CSV file here'}
            </h3>
            <p>Supports bank and credit card CSV exports · Max 5 MB</p>
          </div>
          <button
            type="button"
            className="btn btn-secondary"
            disabled={isLoading}
            onClick={(e) => {
              e.stopPropagation();
              fileInputRef.current?.click();
            }}
          >
            <FolderOpen size={16} strokeWidth={1.75} />
            Browse CSV Files
          </button>
        </div>
      </div>

      {/* Divider */}
      <div className="demo-divider"><span>OR</span></div>

      {/* Sample statement card */}
      <div className="sample-action-card">
        <div className="sample-info">
          <h4>Try the synthetic freelance demo</h4>
          <p>
            Instantly explore 18 realistic transactions — Adobe subscriptions, cloud hosting,
            client revenue, refunds, and flagged "Needs Review" items.
          </p>
        </div>
        <button
          type="button"
          className="btn btn-primary"
          onClick={onLoadSample}
          disabled={isLoading}
        >
          {isLoading
            ? <><Loader2 size={16} strokeWidth={1.75} className="spin" /> Loading…</>
            : <><PlayCircle size={16} strokeWidth={1.75} /> Load Sample Statement</>}
        </button>
      </div>
    </section>
  );
}
