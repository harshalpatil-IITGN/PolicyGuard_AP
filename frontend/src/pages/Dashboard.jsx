import React, { useState, useEffect, useMemo } from 'react';
import { API } from '../config';

export default function Dashboard({ onNavigateToUpload }) {
  const [invoices, setInvoices] = useState([]);
  const [loading, setLoading] = useState(false);
  const [processing, setProcessing] = useState(null);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [batchRunning, setBatchRunning] = useState(false);
  const [batchResults, setBatchResults] = useState(null);
  const [resettingAll, setResettingAll] = useState(false);

  // Search & Filter state
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState('ALL');

  // Inspection Modal state
  const [inspectModalOpen, setInspectModalOpen] = useState(false);
  const [inspectData, setInspectData] = useState(null);
  const [inspectLoading, setInspectLoading] = useState(false);

  // Fetch all invoices from backend
  const fetchInvoices = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${API}/invoices`);
      if (!res.ok) throw new Error(await res.text());
      const data = await res.json();
      setInvoices(data.invoices || []);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchInvoices(); }, []);

  // Compute unique statuses present in data
  const uniqueStatuses = useMemo(() => {
    const statuses = new Set(invoices.map(inv => inv.status).filter(Boolean));
    const standard = ['Parked', 'Processing', 'Passed', 'Escalated', 'Stopped'];
    const ordered = standard.filter(s => statuses.has(s));
    statuses.forEach(s => {
      if (!ordered.includes(s)) ordered.push(s);
    });
    return ordered;
  }, [invoices]);

  // Executive KPI summary calculations
  const stats = useMemo(() => {
    const total = invoices.length;
    const passed = invoices.filter(i => i.status === 'Passed').length;
    const escalated = invoices.filter(i => i.status === 'Escalated').length;
    const stopped = invoices.filter(i => i.status === 'Stopped').length;
    const parked = invoices.filter(i => i.status === 'Parked').length;
    return { total, passed, escalated, stopped, parked };
  }, [invoices]);

  // Filter invoices based on Search Term across (Doc Number, Vendor, Vendor Invoice, PO(s), Gross Amount) and Status filter
  const filteredInvoices = useMemo(() => {
    const term = searchTerm.trim().toLowerCase();

    return invoices.filter(inv => {
      if (statusFilter !== 'ALL' && inv.status?.toLowerCase() !== statusFilter.toLowerCase()) {
        return false;
      }
      if (!term) return true;

      const docNum = (inv.invoice_doc_number || '').toLowerCase();
      const vendor = (inv.vendor_name || '').toLowerCase();
      const vendorInv = (inv.vendor_invoice_number || '').toLowerCase();
      const pos = (inv.po_numbers_quoted || '').toLowerCase();
      const amount = (inv.gross_amount || '').toString().toLowerCase();

      return (
        docNum.includes(term) ||
        vendor.includes(term) ||
        vendorInv.includes(term) ||
        pos.includes(term) ||
        amount.includes(term)
      );
    });
  }, [invoices, searchTerm, statusFilter]);

  // Process single invoice
  const processInvoice = async (docNum) => {
    setProcessing(docNum);
    setResult(null);
    setError(null);
    try {
      const res = await fetch(`${API}/invoices/process/${docNum}`, { method: 'POST' });
      if (!res.ok) throw new Error(await res.text());
      const data = await res.json();
      setResult(data);
      fetchInvoices();
    } catch (e) {
      setError(e.message);
    } finally {
      setProcessing(null);
    }
  };

  // Inspect invoice evidence (read-only modal)
  const openInspectModal = async (docNum) => {
    setInspectLoading(true);
    setInspectModalOpen(true);
    setInspectData(null);
    try {
      const res = await fetch(`${API}/invoices/${docNum}/inspect`);
      if (!res.ok) throw new Error(await res.text());
      const data = await res.json();
      setInspectData(data);
    } catch (e) {
      setError(e.message);
    } finally {
      setInspectLoading(false);
    }
  };

  // Process all parked
  const processAll = async () => {
    setBatchRunning(true);
    setBatchResults(null);
    setError(null);
    try {
      const res = await fetch(`${API}/invoices/process-all`, { method: 'POST' });
      if (!res.ok) throw new Error(await res.text());
      const data = await res.json();
      setBatchResults(data);
      fetchInvoices();
    } catch (e) {
      setError(e.message);
    } finally {
      setBatchRunning(false);
    }
  };

  // Reset invoice status back to Parked (or any status)
  const resetStatus = async (docNum, newStatus = 'Parked') => {
    try {
      const res = await fetch(`${API}/invoices/${docNum}/status`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ status: newStatus }),
      });
      if (!res.ok) throw new Error(await res.text());
      fetchInvoices();
    } catch (e) {
      setError(e.message);
    }
  };

  // Reset ALL invoices back to Parked
  const resetAllInvoices = async () => {
    if (!window.confirm("Are you sure you want to reset ALL invoices back to 'Parked'?")) {
      return;
    }
    setResettingAll(true);
    setError(null);
    try {
      const res = await fetch(`${API}/invoices/reset-all`, { method: 'POST' });
      if (!res.ok) throw new Error(await res.text());
      await fetchInvoices();
    } catch (e) {
      setError(e.message);
    } finally {
      setResettingAll(false);
    }
  };

  // Release stopped invoice under Policy APR-1 (Financial Controller Override)
  const releaseStop = async (docNum) => {
    const reason = window.prompt(
      'Enter reason for releasing this stopped invoice (Clause APR-1):',
      'PO amendment / approved override by Financial Controller Kruti Jadeja'
    );
    if (!reason) return;
    try {
      const res = await fetch(`${API}/invoices/${docNum}/release`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ reason }),
      });
      if (!res.ok) throw new Error(await res.text());
      fetchInvoices();
    } catch (e) {
      setError(e.message);
    }
  };

  const outcomeColor = (outcome) => {
    switch (outcome?.toLowerCase()) {
      case 'pass': case 'passed': return 'bg-emerald-100 text-emerald-800 border-emerald-200';
      case 'escalate': case 'escalated': return 'bg-amber-100 text-amber-800 border-amber-200';
      case 'stop': case 'stopped': return 'bg-rose-100 text-rose-800 border-rose-200';
      case 'processing': return 'bg-blue-100 text-blue-800 border-blue-200';
      case 'parked': return 'bg-slate-100 text-slate-800 border-slate-200';
      default: return 'bg-gray-100 text-gray-800 border-gray-200';
    }
  };

  // Curated demo storylines for presenting to clients
  const DEMO_STORIES = [
    {
      id: 'story-1',
      docNum: '5105600001',
      title: 'Story 1: Autonomous Auto-Pass (Straight-Through Processing)',
      subtitle: 'Zero human touch required',
      badge: 'STP Auto-Pass',
      badgeColor: 'bg-emerald-100 text-emerald-800 border-emerald-300',
      vendor: 'Pinnacle Quality Labs LLP',
      amount: '₹1,28,856.00',
      description: 'Vendor invoice matches agreed PO rate and site service entries to the exact rupee. Clean autonomous clearing.',
    },
    {
      id: 'story-2',
      docNum: '5105600035',
      title: 'Story 2: Marginal Variance & Slack Mobile Escalation',
      subtitle: 'Human-in-the-Loop decision routing',
      badge: 'Escalation to Manager',
      badgeColor: 'bg-amber-100 text-amber-800 border-amber-300',
      vendor: 'Orbit Stone Crusher & Co',
      amount: '₹1,73,528.85',
      description: '1.20% weighbridge bulk aggregate variance. Automatically dispatches interactive Block Kit card to Procurement Head on Slack.',
    },
    {
      id: 'story-3',
      docNum: '5105600103',
      title: 'Story 3: Hard Stop & Leakage Prevention (Policy CL-1)',
      subtitle: 'Automated fraud / closed-PO defense',
      badge: 'Auto-Stop & Halt',
      badgeColor: 'bg-rose-100 text-rose-800 border-rose-300',
      vendor: 'Chitra Switchgear & Co',
      amount: '₹5,63,568.00',
      description: 'Vendor billed against deleted/closed PO line (LOEKZ=L). System halts payment instantly under HOLD-1 with Controller override.',
    },
    {
      id: 'story-4',
      docNum: 'PDF',
      title: 'Story 4: Multimodal PDF & Scanned Invoice Ingestion',
      subtitle: 'AI sensory perception + deterministic match',
      badge: 'Gemini AI Vision',
      badgeColor: 'bg-indigo-100 text-indigo-800 border-indigo-300',
      vendor: 'Sankalp Electric Co Ltd (PDF)',
      amount: '₹5,63,249.40',
      description: 'Vendor submits raw PDF invoice. Gemini AI parses multi-line billing data and PolicyGuard AP reconciles it live.',
      isPdf: true,
    },
  ];

  return (
    <div className="space-y-8">
      {/* ── Executive KPI Metrics Bar ── */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
        <div className="bg-white p-4 rounded-xl shadow-sm border border-gray-200">
          <div className="text-xs font-semibold uppercase tracking-wider text-gray-500">Total Invoice Queue</div>
          <div className="text-2xl font-bold text-gray-900 mt-1">{stats.total}</div>
          <div className="text-xs text-gray-400 mt-0.5">{stats.parked} currently waiting</div>
        </div>
        <div className="bg-white p-4 rounded-xl shadow-sm border border-emerald-100 bg-emerald-50/20">
          <div className="text-xs font-semibold uppercase tracking-wider text-emerald-700">Autonomous Passed</div>
          <div className="text-2xl font-bold text-emerald-700 mt-1">{stats.passed}</div>
          <div className="text-xs text-emerald-600 mt-0.5">Straight-Through (&lt; 1.2s)</div>
        </div>
        <div className="bg-white p-4 rounded-xl shadow-sm border border-amber-100 bg-amber-50/20">
          <div className="text-xs font-semibold uppercase tracking-wider text-amber-700">Slack Escalations</div>
          <div className="text-2xl font-bold text-amber-700 mt-1">{stats.escalated}</div>
          <div className="text-xs text-amber-600 mt-0.5">Routed to authorized approver</div>
        </div>
        <div className="bg-white p-4 rounded-xl shadow-sm border border-rose-100 bg-rose-50/20">
          <div className="text-xs font-semibold uppercase tracking-wider text-rose-700">Auto-Stopped & Held</div>
          <div className="text-2xl font-bold text-rose-700 mt-1">{stats.stopped}</div>
          <div className="text-xs text-rose-600 mt-0.5">Leakage / violations halted</div>
        </div>
        <div className="bg-white p-4 rounded-xl shadow-sm border border-blue-100 bg-blue-50/20 col-span-2 md:col-span-1">
          <div className="text-xs font-semibold uppercase tracking-wider text-brand-700">Reconciliation Speed</div>
          <div className="text-2xl font-bold text-brand-700 mt-1">&lt; 1.5s</div>
          <div className="text-xs text-brand-600 mt-0.5">vs. 15-20 min manual work</div>
        </div>
      </div>

      {/* ── Client Presentation Mode: Guided Story Showcase ── */}
      <div className="bg-gradient-to-br from-slate-900 to-brand-900 text-white rounded-2xl p-6 shadow-xl border border-blue-900 space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-white/10 pb-4">
          <div>
            <span className="px-2.5 py-0.5 text-xs font-bold uppercase tracking-wider bg-blue-500/30 text-blue-200 rounded-full border border-blue-400/30">
              Client Demo Mode
            </span>
            <h2 className="text-xl font-bold mt-1 text-white">Curated Executive Walkthrough (4 Key Stories)</h2>
            <p className="text-xs text-blue-200">
              Run through these 4 real-world business scenarios to showcase the end-to-end power of PolicyGuard AP.
            </p>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 pt-2">
          {DEMO_STORIES.map((story) => {
            const currentInv = invoices.find(i => i.invoice_doc_number === story.docNum);
            const status = currentInv?.status || (story.isPdf ? 'Ready' : 'Parked');

            return (
              <div
                key={story.id}
                className="bg-white/10 backdrop-blur-md rounded-xl p-4 border border-white/15 flex flex-col justify-between hover:bg-white/15 transition-all shadow-sm"
              >
                <div className="space-y-2">
                  <div className="flex items-center justify-between gap-1">
                    <span className={`px-2 py-0.5 text-[10px] font-bold rounded-md border ${story.badgeColor}`}>
                      {story.badge}
                    </span>
                    {!story.isPdf && (
                      <span className={`px-2 py-0.5 text-[10px] rounded-full font-medium ${outcomeColor(status)}`}>
                        {status}
                      </span>
                    )}
                  </div>
                  <h3 className="text-sm font-bold text-white leading-snug">{story.title}</h3>
                  <div className="text-xs text-blue-100 font-medium">{story.vendor} • {story.amount}</div>
                  <p className="text-xs text-blue-200/80 leading-relaxed">{story.description}</p>
                </div>

                <div className="pt-4 border-t border-white/10 mt-3 flex items-center justify-between gap-2">
                  {story.isPdf ? (
                    <button
                      onClick={() => onNavigateToUpload?.()}
                      className="w-full py-1.5 px-3 bg-white text-slate-900 rounded-lg text-xs font-bold hover:bg-blue-50 transition-colors shadow-sm flex items-center justify-center gap-1.5"
                    >
                      <span>📄 Ingest PDF Sample</span>
                    </button>
                  ) : (
                    <>
                      <button
                        onClick={() => processInvoice(story.docNum)}
                        disabled={processing === story.docNum || status !== 'Parked'}
                        className={`flex-1 py-1.5 px-2 rounded-lg text-xs font-bold transition-all flex items-center justify-center gap-1 shadow-sm ${
                          status === 'Parked'
                            ? 'bg-blue-500 hover:bg-blue-400 text-white'
                            : 'bg-white/10 text-white/40 cursor-not-allowed'
                        }`}
                      >
                        {processing === story.docNum ? '⏳ Matching...' : status === 'Parked' ? '▶️ Execute Match' : status}
                      </button>

                      <button
                        onClick={() => openInspectModal(story.docNum)}
                        className="py-1.5 px-2.5 bg-white/10 hover:bg-white/20 text-blue-100 rounded-lg text-xs font-medium border border-white/20 transition-colors"
                        title="View 3-way match calculation breakdown and audit evidence"
                      >
                        🔍 Evidence
                      </button>

                      {status !== 'Parked' && (
                        <button
                          onClick={() => resetStatus(story.docNum, 'Parked')}
                          className="py-1.5 px-2 bg-white/10 hover:bg-white/20 text-blue-200 rounded-lg text-xs transition-colors"
                          title="Reset status back to Parked"
                        >
                          ↺
                        </button>
                      )}
                    </>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* ── Search & Filter Controls ── */}
      <div className="space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <h3 className="text-lg font-bold text-gray-900">Enterprise Invoices Repository</h3>
            <p className="text-xs text-gray-500">
              Showing {filteredInvoices.length} of {invoices.length} total invoice records
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <button
              onClick={fetchInvoices}
              disabled={loading}
              className="px-3.5 py-1.5 text-xs bg-white border border-gray-300 rounded-lg font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50 transition-colors shadow-sm"
            >
              {loading ? '⏳' : '🔄'} Refresh
            </button>
            <button
              onClick={resetAllInvoices}
              disabled={resettingAll || loading}
              className="px-3.5 py-1.5 text-xs bg-white border border-rose-300 text-rose-700 hover:bg-rose-50 rounded-lg font-medium transition-colors shadow-sm"
              title="Reset all invoice statuses back to Parked"
            >
              {resettingAll ? '⏳ Resetting...' : '↺ Reset All to Parked'}
            </button>
            <button
              onClick={processAll}
              disabled={batchRunning || invoices.filter(i => i.status === 'Parked').length === 0}
              className="px-3.5 py-1.5 text-xs bg-brand-600 text-white rounded-lg font-semibold hover:bg-brand-700 disabled:opacity-50 transition-colors shadow-sm"
              title="Batch processes all parked invoices"
            >
              {batchRunning ? '⏳ Processing Batch...' : '▶️ Sweep & Match All Parked'}
            </button>
          </div>
        </div>

        <div className="bg-white p-3.5 rounded-xl shadow-sm border border-gray-200 flex flex-col md:flex-row gap-3 items-stretch md:items-center">
          <div className="relative flex-1">
            <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-gray-400">
              🔍
            </div>
            <input
              type="text"
              placeholder="Search by Doc Number, Vendor, Vendor Invoice, PO, or Amount..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full pl-9 pr-8 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-brand-500 focus:border-brand-500 outline-none transition-all"
            />
            {searchTerm && (
              <button
                onClick={() => setSearchTerm('')}
                className="absolute inset-y-0 right-0 pr-3 flex items-center text-xs text-gray-400 hover:text-gray-600"
              >
                ✕
              </button>
            )}
          </div>

          <div className="flex items-center gap-2">
            <label htmlFor="status-select" className="text-xs font-semibold text-gray-500 uppercase tracking-wider whitespace-nowrap">
              Filter Status:
            </label>
            <select
              id="status-select"
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="px-3 py-2 text-sm border border-gray-300 rounded-lg bg-white text-gray-700 focus:ring-2 focus:ring-brand-500 focus:border-brand-500 outline-none font-medium"
            >
              <option value="ALL">All Statuses ({invoices.length})</option>
              {uniqueStatuses.map((st) => (
                <option key={st} value={st}>
                  {st} ({invoices.filter(i => i.status === st).length})
                </option>
              ))}
            </select>

            {(searchTerm || statusFilter !== 'ALL') && (
              <button
                onClick={() => { setSearchTerm(''); setStatusFilter('ALL'); }}
                className="px-3 py-2 text-xs font-medium text-gray-600 hover:text-gray-900 bg-gray-100 hover:bg-gray-200 rounded-lg transition-colors whitespace-nowrap"
              >
                Reset
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Result Card */}
      {result && (
        <div className={`border p-4 rounded-xl text-sm shadow-sm flex items-center justify-between ${outcomeColor(result.outcome)}`}>
          <div>
            <strong>Match Result:</strong> Invoice <span className="font-mono font-bold">{result.invoice_doc_number}</span> → <strong>{result.outcome}</strong>
            <span className="ml-2 text-gray-700">{result.message}</span>
          </div>
          <button
            onClick={() => openInspectModal(result.invoice_doc_number)}
            className="px-3 py-1 bg-white border rounded text-xs font-bold shadow-sm hover:bg-gray-50 text-gray-800"
          >
            🔍 Inspect Evidence
          </button>
        </div>
      )}

      {/* ── Invoices Data Table ── */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b border-gray-200 text-left text-xs uppercase font-semibold text-gray-500 tracking-wider">
              <tr>
                <th className="px-4 py-3">Doc Number</th>
                <th className="px-4 py-3">Vendor</th>
                <th className="px-4 py-3">Vendor Invoice</th>
                <th className="px-4 py-3">PO(s)</th>
                <th className="px-4 py-3">Gross Amount</th>
                <th className="px-4 py-3">Status</th>
                <th className="px-4 py-3 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {filteredInvoices.map((inv) => (
                <tr key={inv.invoice_doc_number} className="hover:bg-blue-50/40 transition-colors">
                  <td className="px-4 py-3 font-mono font-bold text-gray-900">{inv.invoice_doc_number}</td>
                  <td className="px-4 py-3 font-medium text-gray-800">{inv.vendor_name}</td>
                  <td className="px-4 py-3 text-gray-600 font-mono text-xs">{inv.vendor_invoice_number}</td>
                  <td className="px-4 py-3 font-mono text-xs text-brand-700">{inv.po_numbers_quoted}</td>
                  <td className="px-4 py-3 font-semibold text-gray-900">₹{inv.gross_amount}</td>
                  <td className="px-4 py-3">
                    <span className={`inline-block px-2.5 py-0.5 text-xs rounded-full font-medium border ${outcomeColor(inv.status)}`}>
                      {inv.status}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-right">
                    <div className="flex items-center justify-end gap-1.5">
                      <button
                        onClick={() => processInvoice(inv.invoice_doc_number)}
                        disabled={processing === inv.invoice_doc_number || inv.status !== 'Parked'}
                        className={`px-2.5 py-1 text-xs font-semibold rounded-md shadow-sm transition-all ${
                          inv.status === 'Parked'
                            ? 'bg-brand-600 text-white hover:bg-brand-700 active:scale-95'
                            : 'bg-gray-100 text-gray-400 cursor-not-allowed border border-gray-200'
                        }`}
                        title={inv.status === 'Parked' ? 'Run 3-way match' : `Invoice is already ${inv.status}`}
                      >
                        {processing === inv.invoice_doc_number ? '⏳' : '▶️ Match'}
                      </button>

                      <button
                        onClick={() => openInspectModal(inv.invoice_doc_number)}
                        className="px-2 py-1 text-xs font-medium text-gray-600 hover:text-brand-700 hover:bg-brand-50 rounded border border-gray-200 transition-colors"
                        title="Inspect 3-way match reconciliation details"
                      >
                        🔍
                      </button>

                      {inv.status === 'Stopped' && (
                        <button
                          onClick={() => releaseStop(inv.invoice_doc_number)}
                          className="px-2 py-1 text-xs font-semibold text-emerald-700 bg-emerald-50 hover:bg-emerald-100 rounded border border-emerald-300 transition-colors"
                          title="Release stopped invoice under policy APR-1 (Financial Controller)"
                        >
                          🔓 Release
                        </button>
                      )}

                      {inv.status !== 'Parked' && (
                        <button
                          onClick={() => resetStatus(inv.invoice_doc_number, 'Parked')}
                          className="px-2 py-1 text-xs font-medium text-gray-500 hover:text-brand-600 hover:bg-gray-100 rounded border border-gray-200 transition-colors"
                          title="Reset status back to 'Parked' to test matching again"
                        >
                          ↺
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* ── 3-Way Reconciliation Evidence Modal ── */}
      {inspectModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4 overflow-y-auto">
          <div className="bg-white rounded-2xl shadow-2xl max-w-3xl w-full max-h-[90vh] flex flex-col overflow-hidden border border-gray-200">
            {/* Modal Header */}
            <div className="bg-slate-900 text-white p-5 flex items-center justify-between">
              <div>
                <span className="text-xs uppercase tracking-wider text-blue-300 font-bold">Three-Way Match Evidence Inspector</span>
                <h3 className="text-lg font-bold text-white flex items-center gap-2 mt-0.5">
                  <span>Reconciliation for Invoice</span>
                  <span className="font-mono text-blue-300">{inspectData?.invoice_doc_number}</span>
                </h3>
              </div>
              <button
                onClick={() => setInspectModalOpen(false)}
                className="text-gray-400 hover:text-white text-xl px-2 py-1 rounded-lg hover:bg-white/10 transition-colors"
              >
                ✕
              </button>
            </div>

            {/* Modal Content */}
            <div className="p-6 overflow-y-auto space-y-6">
              {inspectLoading && (
                <div className="py-12 text-center text-gray-500 space-y-2">
                  <div className="text-2xl animate-spin">⏳</div>
                  <div className="text-sm">Calculating three-way reconciliation math...</div>
                </div>
              )}

              {inspectData?.details && (
                <div className="space-y-6">
                  {/* Status Banner */}
                  <div className="flex items-center justify-between p-4 bg-gray-50 rounded-xl border border-gray-200">
                    <div>
                      <div className="text-xs text-gray-500 uppercase font-semibold">Vendor</div>
                      <div className="text-sm font-bold text-gray-900">{inspectData.details.vendor_name}</div>
                      <div className="text-xs text-gray-500 font-mono">Invoice #{inspectData.details.vendor_invoice_number}</div>
                    </div>
                    <div className="text-right">
                      <div className="text-xs text-gray-500 uppercase font-semibold">Calculated Outcome</div>
                      <span className={`inline-block mt-1 px-3 py-1 text-xs font-bold rounded-full border ${outcomeColor(inspectData.calculated_outcome)}`}>
                        {inspectData.calculated_outcome?.toUpperCase()}
                      </span>
                    </div>
                  </div>

                  {/* Summary of Reasons / Policy Violations */}
                  {inspectData.details.overall_reasons?.length > 0 && (
                    <div className="p-4 bg-amber-50/60 rounded-xl border border-amber-200 text-xs space-y-1.5">
                      <div className="font-bold text-amber-900 uppercase">Policy Rules & Audit Rationale:</div>
                      {inspectData.details.overall_reasons.map((r, idx) => (
                        <div key={idx} className="text-amber-800 flex items-start gap-1.5">
                          <span>•</span> <span>{r}</span>
                        </div>
                      ))}
                    </div>
                  )}

                  {/* Assigned Approver if Escalated */}
                  {inspectData.details.final_approver_name && (
                    <div className="p-3.5 bg-blue-50 rounded-xl border border-blue-200 flex items-center justify-between text-xs">
                      <div>
                        <span className="font-bold text-brand-900">Designated Approver (Clause ESC-3): </span>
                        <span className="text-brand-800">{inspectData.details.final_approver_name} ({inspectData.details.final_approver_role})</span>
                      </div>
                      <span className="text-brand-600 font-mono">{inspectData.details.final_approver_email}</span>
                    </div>
                  )}

                  {/* Line Item Reconciliations */}
                  <div className="space-y-3">
                    <h4 className="text-xs font-bold text-gray-700 uppercase tracking-wider">
                      Itemized Line Reconciliations ({inspectData.details.line_results?.length || 0})
                    </h4>

                    {inspectData.details.line_results?.map((lr) => (
                      <div key={lr.invoice_line_number} className="border border-gray-200 rounded-xl p-4 space-y-3 bg-white shadow-sm">
                        <div className="flex items-center justify-between border-b pb-2">
                          <span className="font-bold text-sm text-gray-900">
                            Line {lr.invoice_line_number} — Material {lr.material_id} ({lr.category})
                          </span>
                          <span className={`px-2 py-0.5 text-xs font-bold rounded border ${outcomeColor(lr.outcome)}`}>
                            {lr.outcome}
                          </span>
                        </div>

                        {/* Math Comparison Grid */}
                        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
                          <div className="bg-gray-50 p-2.5 rounded-lg border">
                            <span className="text-gray-500 block">Billed Net Amount</span>
                            <span className="font-bold text-gray-900">₹{lr.invoice_line_net_amount?.toLocaleString()}</span>
                          </div>
                          <div className="bg-gray-50 p-2.5 rounded-lg border">
                            <span className="text-gray-500 block">Value at PO Price</span>
                            <span className="font-bold text-gray-900">₹{lr.value_at_po_price?.toLocaleString()}</span>
                          </div>
                          <div className="bg-gray-50 p-2.5 rounded-lg border">
                            <span className="text-gray-500 block">Price Variance</span>
                            <span className={`font-bold ${lr.price_variance_inr > 0 ? 'text-amber-700' : 'text-gray-900'}`}>
                              ₹{lr.price_variance_inr} ({lr.price_variance_pct}%)
                            </span>
                          </div>
                          <div className="bg-gray-50 p-2.5 rounded-lg border">
                            <span className="text-gray-500 block">Qty Variance</span>
                            <span className={`font-bold ${lr.qty_variance_qty > 0 ? 'text-amber-700' : 'text-gray-900'}`}>
                              {lr.qty_variance_qty} {lr.po_order_unit} ({lr.qty_variance_pct}%)
                            </span>
                          </div>
                        </div>

                        {/* UoM & Receipt Breakdown */}
                        <div className="text-xs text-gray-600 space-y-1 bg-slate-50 p-2.5 rounded-lg border border-slate-200">
                          <div>• <strong>PO Line:</strong> #{lr.po_number} Item {lr.po_items_matched?.join(', ')} (Unit Price: ₹{lr.po_price_per_unit}/{lr.po_order_unit})</div>
                          <div>• <strong>UoM Conversion:</strong> {lr.uom_conversion_used || 'Direct 1:1 match'}</div>
                          <div>• <strong>Net Goods Received:</strong> {lr.net_received_qty} {lr.po_order_unit} | Available Qty: {lr.available_qty} {lr.po_order_unit} (Prior Invoiced: {lr.prior_invoiced_qty} {lr.po_order_unit})</div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>

            {/* Modal Footer */}
            <div className="p-4 bg-gray-50 border-t border-gray-200 flex items-center justify-between text-xs text-gray-500">
              <span>PolicyGuard AP Deterministic Verification Engine • SOX/Audit Compliant</span>
              <button
                onClick={() => setInspectModalOpen(false)}
                className="px-4 py-2 bg-slate-900 text-white rounded-lg font-semibold hover:bg-slate-800 transition-colors"
              >
                Close Inspector
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
