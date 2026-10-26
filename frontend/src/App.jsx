import { useCallback, useEffect, useState } from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import Header from './components/Header';
import AlertBanner from './components/AlertBanner';
import StatementUpload from './components/StatementUpload';
import SummaryCards from './components/SummaryCards';
import CategoryBreakdown from './components/CategoryBreakdown';
import TransactionTable from './components/TransactionTable';
import ExportToolbar from './components/ExportToolbar';
import ScheduleC from './pages/ScheduleC';
import Settings from './pages/Settings';
import NotFound from './pages/NotFound';
import {
  exportStatement,
  getCategories,
  getSampleStatement,
  reviewTransaction,
  uploadStatement,
} from './services/api';
import './App.css';

export default function App() {
  const [categories, setCategories] = useState([]);
  const [statement, setStatement] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [updatingTxId, setUpdatingTxId] = useState(null);
  const [isExporting, setIsExporting] = useState(false);
  const [error, setError] = useState(null);
  const [successMessage, setSuccessMessage] = useState(null);
  const [parseErrors, setParseErrors] = useState([]);

  // Fetch standard domain categories on component mount
  useEffect(() => {
    let isMounted = true;
    getCategories()
      .then((data) => {
        if (isMounted && data.categories) {
          setCategories(data.categories);
        }
      })
      .catch((err) => {
        if (isMounted) {
          setError(`Unable to connect to backend service: ${err.message}`);
        }
      });

    return () => {
      isMounted = false;
    };
  }, []);

  // Handle uploading CSV bank statement
  const handleFileUpload = useCallback(async (file) => {
    setIsLoading(true);
    setError(null);
    setSuccessMessage(null);
    setParseErrors([]);

    try {
      const data = await uploadStatement(file);
      setStatement(data);
      if (data.errors && data.errors.length > 0) {
        setParseErrors(data.errors);
      }
      setSuccessMessage(`Successfully processed statement "${data.filename}" (${data.total_rows} transactions).`);
    } catch (err) {
      setError(err.message || 'Failed to upload statement.');
    } finally {
      setIsLoading(false);
    }
  }, []);

  // Handle loading synthetic sample statement
  const handleLoadSample = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    setSuccessMessage(null);
    setParseErrors([]);

    try {
      const data = await getSampleStatement();
      setStatement(data);
      if (data.errors && data.errors.length > 0) {
        setParseErrors(data.errors);
      }
      setSuccessMessage('Loaded synthetic Freelance statement (18 transactions). Explore metrics and resolve "Needs Review" items below.');
    } catch (err) {
      setError(err.message || 'Failed to load sample statement.');
    } finally {
      setIsLoading(false);
    }
  }, []);

  // Handle manual review and category reclassification
  const handleCategoryChange = useCallback(async (transactionId, newCategory) => {
    if (!statement || updatingTxId) return;

    const targetTx = statement.transactions.find((t) => t.id === transactionId);
    if (!targetTx || targetTx.category === newCategory) return;

    setUpdatingTxId(transactionId);
    setError(null);

    try {
      const res = await reviewTransaction(transactionId, newCategory, statement.transactions);
      setStatement((prev) => ({
        ...prev,
        transactions: res.transactions,
        summary: res.summary,
      }));
      setSuccessMessage(`Updated "${targetTx.description}" to ${newCategory}. Summary totals recalculated live.`);
    } catch (err) {
      setError(`Failed to update category: ${err.message}`);
    } finally {
      setUpdatingTxId(null);
    }
  }, [statement, updatingTxId]);

  // Handle exporting finalized reviewed statement to CSV
  const handleExport = useCallback(async (filename) => {
    if (!statement || !statement.transactions || statement.transactions.length === 0) {
      setError('No transactions available to export.');
      return;
    }

    setIsExporting(true);
    setError(null);

    try {
      await exportStatement(statement.transactions, filename);
      setSuccessMessage(`Successfully exported statement to ${filename}.`);
    } catch (err) {
      setError(`Export failed: ${err.message}`);
    } finally {
      setIsExporting(false);
    }
  }, [statement]);

  // Handle resetting back to initial upload state
  const handleReset = useCallback(() => {
    setStatement(null);
    setError(null);
    setSuccessMessage(null);
    setParseErrors([]);
  }, []);

  return (
    <BrowserRouter>
      <div className="app-container">
        <Header />

        <main className="main-content">
          <AlertBanner
            error={error}
            parseErrors={parseErrors}
            successMessage={successMessage}
            onDismiss={() => {
              setError(null);
              setSuccessMessage(null);
            }}
          />

          <Routes>
            <Route
              path="/"
              element={
                !statement ? (
                  <StatementUpload
                    onFileUpload={handleFileUpload}
                    onLoadSample={handleLoadSample}
                    isLoading={isLoading}
                  />
                ) : (
                  <div className="statement-dashboard">
                    <ExportToolbar
                      filename={statement.filename}
                      totalRows={statement.total_rows}
                      needsReviewCount={statement.summary?.total_needs_review_count || 0}
                      onExport={handleExport}
                      onReset={handleReset}
                      isExporting={isExporting}
                    />

                    <SummaryCards summary={statement.summary} />

                    <CategoryBreakdown breakdown={statement.summary?.category_breakdown} />

                    <TransactionTable
                      transactions={statement.transactions}
                      categories={categories}
                      onCategoryChange={handleCategoryChange}
                      updatingTxId={updatingTxId}
                    />
                  </div>
                )
              }
            />
            <Route
              path="/schedule-c"
              element={<ScheduleC statement={statement} />}
            />
            <Route
              path="/settings"
              element={<Settings />}
            />
            <Route
              path="*"
              element={<NotFound />}
            />
          </Routes>
        </main>

        <footer className="app-footer">
          <div className="footer-inner">
            <span className="footer-brand">SAVV Pro Solutions</span>
            <div className="footer-meta">
              <span>Freelancer Schedule C Edition</span>
              <span>Deterministic Zero-LLM Architecture</span>
              <span>All processing is local</span>
            </div>
          </div>
        </footer>
      </div>
    </BrowserRouter>
  );
}
