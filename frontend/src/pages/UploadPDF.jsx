import React, { useState } from 'react';
import { API } from '../config';

export default function UploadPDF() {
  const [file, setFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [showRaw, setShowRaw] = useState(false);

  const handleUpload = async (e) => {
    e.preventDefault();
    if (!file) return;
    setUploading(true);
    setResult(null);
    setError(null);

    const formData = new FormData();
    formData.append('file', file);

    try {
      const res = await fetch(`${API}/invoices/upload-pdf`, {
        method: 'POST',
        body: formData,
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || `Upload failed with HTTP ${res.status}`);
      }
      const data = await res.json();
      setResult(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setUploading(false);
    }
  };

  const outcomeBadge = (outcome) => {
    switch (outcome?.toLowerCase()) {
      case 'pass': case 'passed':
        return <span className="px-2.5 py-1 text-xs font-bold rounded-full bg-green-100 text-green-800 border border-green-200">✅ PASSED</span>;
      case 'escalate': case 'escalated':
        return <span className="px-2.5 py-1 text-xs font-bold rounded-full bg-yellow-100 text-yellow-800 border border-yellow-200">🔶 ESCALATED</span>;
      case 'stop': case 'stopped':
        return <span className="px-2.5 py-1 text-xs font-bold rounded-full bg-red-100 text-red-800 border border-red-200">🔴 STOPPED</span>;
      default:
        return <span className="px-2.5 py-1 text-xs font-bold rounded-full bg-gray-100 text-gray-800 border border-gray-200">{outcome}</span>;
    }
  };

  const header = result?.extracted_data?.header;
  const lines = result?.extracted_data?.lines || [];
  const match = result?.match_result;

  return (
    <div className="max-w-4xl space-y-6">
      <div>
        <h2 className="text-xl font-bold text-gray-900 tracking-tight">📄 Native PDF Invoice Ingestion</h2>
        <p className="text-sm text-gray-500 mt-1">
          Upload digital or scanned vendor invoices. Gemini multimodal AI extracts header metadata and itemized billing rows,
          then PolicyGuard AP performs a live Three-Way Match against ERP PO and Goods Receipt records.
        </p>
      </div>

      <form onSubmit={handleUpload} className="space-y-4">
        <div className="border-2 border-dashed border-gray-300 rounded-xl p-8 text-center bg-white hover:border-brand-500 transition-colors cursor-pointer shadow-sm">
          <input
            type="file"
            accept=".pdf"
            onChange={(e) => setFile(e.target.files[0])}
            className="block mx-auto text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:text-sm file:font-semibold file:bg-brand-50 file:text-brand-700 hover:file:bg-brand-100 cursor-pointer"
          />
          {file && (
            <p className="mt-3 text-sm text-gray-700 font-medium">
              Selected: <span className="font-mono text-brand-600">{file.name}</span> ({(file.size / 1024).toFixed(1)} KB)
            </p>
          )}
        </div>

        <button
          type="submit"
          disabled={!file || uploading}
          className="w-full px-4 py-3 bg-brand-600 text-white rounded-lg font-semibold hover:bg-brand-700 disabled:opacity-50 transition-all shadow-sm flex items-center justify-center gap-2"
        >
          {uploading ? (
            <>
              <span className="animate-spin">⏳</span>
              <span>Extracting Document & Running 3-Way Match...</span>
            </>
          ) : (
            <>
              <span>🚀</span>
              <span>Upload, Ingest & Match</span>
            </>
          )}
        </button>
      </form>

      {/* Error */}
      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-sm flex items-center gap-2">
          <span>❌</span> <span>{error}</span>
        </div>
      )}

      {/* Result Presentation */}
      {result && (
        <div className="space-y-6">
          <div className="bg-emerald-50 border border-emerald-200 px-4 py-3 rounded-lg text-sm text-emerald-800 font-medium flex items-center justify-between">
            <span>✅ {result.message}</span>
            <button
              onClick={() => setShowRaw(!showRaw)}
              className="text-xs text-brand-600 hover:underline font-semibold"
            >
              {showRaw ? 'Hide Raw JSON' : 'Inspect Raw JSON'}
            </button>
          </div>

          {/* Structured Extracted Invoice Summary */}
          {header && (
            <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-5 space-y-4">
              <h3 className="text-sm font-bold text-gray-900 uppercase tracking-wider border-b pb-2">
                📋 Extracted Document Metadata
              </h3>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                <div>
                  <span className="text-xs text-gray-500 uppercase font-semibold">Vendor</span>
                  <div className="font-semibold text-gray-900">{header.vendor_name || 'N/A'}</div>
                </div>
                <div>
                  <span className="text-xs text-gray-500 uppercase font-semibold">Invoice No</span>
                  <div className="font-mono font-bold text-brand-700">{header.vendor_invoice_number || 'N/A'}</div>
                </div>
                <div>
                  <span className="text-xs text-gray-500 uppercase font-semibold">PO Quoted</span>
                  <div className="font-mono font-medium text-gray-800">{header.po_number || 'N/A'}</div>
                </div>
                <div>
                  <span className="text-xs text-gray-500 uppercase font-semibold">Gross Amount</span>
                  <div className="font-bold text-gray-900">₹{header.gross_amount?.toLocaleString?.() || header.gross_amount}</div>
                </div>
              </div>

              {/* Extracted Line Items Table */}
              {lines.length > 0 && (
                <div className="mt-4">
                  <h4 className="text-xs font-bold text-gray-500 uppercase mb-2">Itemized Lines ({lines.length})</h4>
                  <div className="overflow-x-auto border border-gray-100 rounded-lg">
                    <table className="w-full text-xs text-left">
                      <thead className="bg-gray-50 font-semibold text-gray-600 border-b">
                        <tr>
                          <th className="p-2">#</th>
                          <th className="p-2">Description</th>
                          <th className="p-2">HSN/SAC</th>
                          <th className="p-2">Qty</th>
                          <th className="p-2">Unit</th>
                          <th className="p-2">Rate</th>
                          <th className="p-2 text-right">Net Amount</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-gray-100">
                        {lines.map((l, i) => (
                          <tr key={i} className="hover:bg-gray-50">
                            <td className="p-2 font-mono">{l.line_number || i + 1}</td>
                            <td className="p-2 font-medium text-gray-800">{l.material_description}</td>
                            <td className="p-2 font-mono text-gray-500">{l.hsn_sac_code || '—'}</td>
                            <td className="p-2 font-mono">{l.quantity}</td>
                            <td className="p-2 font-semibold text-gray-700">{l.unit}</td>
                            <td className="p-2 font-mono">₹{l.unit_price}</td>
                            <td className="p-2 font-mono font-semibold text-right">₹{l.line_net_amount?.toLocaleString?.() || l.line_net_amount}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Live 3-Way Match Result */}
          {match && (
            <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-5 space-y-4">
              <div className="flex items-center justify-between border-b pb-3">
                <div>
                  <h3 className="text-sm font-bold text-gray-900 uppercase tracking-wider">
                    ⚡ Live 3-Way Match Outcome
                  </h3>
                  <p className="text-xs text-gray-500">
                    Reconciled against ERP Document <span className="font-mono font-bold text-brand-700">{match.invoice_doc_number}</span>
                  </p>
                </div>
                <div>{outcomeBadge(match.overall_outcome)}</div>
              </div>

              {/* Reasons if any */}
              {match.overall_reasons?.length > 0 && (
                <div className="bg-gray-50 p-3 rounded-lg border text-xs space-y-1">
                  <div className="font-bold text-gray-700">Audit & Policy Notes:</div>
                  {match.overall_reasons.map((r, idx) => (
                    <div key={idx} className="text-gray-600 flex items-start gap-1.5">
                      <span>•</span> <span>{r}</span>
                    </div>
                  ))}
                </div>
              )}

              {/* Line variance breakdowns */}
              {match.line_results?.length > 0 && (
                <div className="space-y-3">
                  <h4 className="text-xs font-bold text-gray-500 uppercase">Line Variance Reconciliations</h4>
                  {match.line_results.map((lr) => (
                    <div key={lr.invoice_line_number} className="border rounded-lg p-3 text-xs space-y-2 bg-gray-50/50">
                      <div className="flex items-center justify-between font-semibold">
                        <span>Line {lr.invoice_line_number} — {lr.category?.toUpperCase()} ({lr.value_band})</span>
                        <span>{outcomeBadge(lr.outcome)}</span>
                      </div>
                      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-gray-600">
                        <div>Billed Qty: <strong className="text-gray-900">{lr.billed_qty_converted} {lr.po_order_unit}</strong></div>
                        <div>Available Qty: <strong className="text-gray-900">{lr.available_qty} {lr.po_order_unit}</strong></div>
                        <div>Price Var: <strong className={lr.price_variance_inr > 0 ? 'text-amber-700' : 'text-gray-900'}>₹{lr.price_variance_inr} ({lr.price_variance_pct}%)</strong></div>
                        <div>Qty Var: <strong className={lr.qty_variance_qty > 0 ? 'text-amber-700' : 'text-gray-900'}>{lr.qty_variance_qty} ({lr.qty_variance_pct}%)</strong></div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* Raw JSON Debug (Toggleable) */}
          {showRaw && (
            <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4">
              <h3 className="text-xs font-bold text-gray-500 uppercase mb-2">Raw API Payload</h3>
              <pre className="text-xs bg-gray-900 text-emerald-400 p-4 rounded-lg overflow-auto max-h-96 font-mono">
                {JSON.stringify(result, null, 2)}
              </pre>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
