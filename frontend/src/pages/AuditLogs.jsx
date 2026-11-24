import React, { useState, useEffect } from 'react';
import { API } from '../config';

export default function AuditLogs() {
  const [logs, setLogs] = useState([]);
  const [total, setTotal] = useState(0);
  const [filter, setFilter] = useState('');
  const [loading, setLoading] = useState(false);

  const fetchLogs = async (invoiceFilter = '') => {
    setLoading(true);
    try {
      const params = new URLSearchParams({ limit: '100', offset: '0' });
      if (invoiceFilter) params.set('invoice_doc_number', invoiceFilter);
      const res = await fetch(`${API}/audit-logs?${params}`);
      const data = await res.json();
      setLogs(data.logs || []);
      setTotal(data.total || 0);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchLogs(); }, []);

  const handleFilter = (e) => {
    e.preventDefault();
    fetchLogs(filter);
  };

  const eventColor = (type) => {
    if (type.includes('ERROR')) return 'text-red-600';
    if (type.includes('STARTED')) return 'text-blue-600';
    if (type.includes('COMPLETED')) return 'text-green-600';
    if (type.includes('SLACK')) return 'text-purple-600';
    if (type.includes('APPROVER')) return 'text-orange-600';
    return 'text-gray-600';
  };

  const outcomeColor = (outcome) => {
    switch (outcome?.toLowerCase()) {
      case 'pass': case 'passed': return 'bg-green-100 text-green-800';
      case 'escalate': case 'escalated': return 'bg-yellow-100 text-yellow-800';
      case 'stop': case 'stopped': return 'bg-red-100 text-red-800';
      case 'processing': return 'bg-blue-100 text-blue-800';
      default: return 'bg-gray-100 text-gray-700';
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold">📋 Audit Trail</h2>
        <span className="text-sm text-gray-500">{total} entries</span>
      </div>

      {/* Filter */}
      <form onSubmit={handleFilter} className="flex gap-2">
        <input
          type="text"
          placeholder="Filter by invoice doc number…"
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
          className="flex-1 px-3 py-2 border rounded-lg text-sm focus:ring-2 focus:ring-brand-500 outline-none"
        />
        <button
          type="submit"
          className="px-4 py-2 text-sm bg-brand-600 text-white rounded-lg hover:bg-brand-700"
        >
          🔍 Filter
        </button>
        <button
          type="button"
          onClick={() => { setFilter(''); fetchLogs(); }}
          className="px-4 py-2 text-sm bg-white border rounded-lg hover:bg-gray-50"
        >
          Clear
        </button>
      </form>

      {/* Log Table */}
      <div className="bg-white rounded-lg shadow overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 text-left text-xs uppercase text-gray-500">
            <tr>
              <th className="px-4 py-3 w-12">#</th>
              <th className="px-4 py-3">Timestamp</th>
              <th className="px-4 py-3">Invoice</th>
              <th className="px-4 py-3">Event</th>
              <th className="px-4 py-3">Outcome</th>
              <th className="px-4 py-3">Actor</th>
              <th className="px-4 py-3">Details</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {logs.map((log) => (
              <tr key={log.id} className="hover:bg-gray-50">
                <td className="px-4 py-2 text-gray-400 font-mono text-xs">{log.id}</td>
                <td className="px-4 py-2 text-xs text-gray-500 whitespace-nowrap">
                  {new Date(log.timestamp).toLocaleString()}
                </td>
                <td className="px-4 py-2 font-mono font-medium">{log.invoice_doc_number}</td>
                <td className={`px-4 py-2 font-medium text-xs ${eventColor(log.event_type)}`}>
                  {log.event_type}
                </td>
                <td className="px-4 py-2">
                  {log.outcome && (
                    <span className={`inline-block px-2 py-0.5 text-xs rounded-full font-medium ${outcomeColor(log.outcome)}`}>
                      {log.outcome}
                    </span>
                  )}
                </td>
                <td className="px-4 py-2 text-gray-600">{log.actor}</td>
                <td className="px-4 py-2 text-xs text-gray-500 max-w-xs truncate" title={log.details}>
                  {log.details?.length > 80 ? log.details.slice(0, 80) + '…' : log.details}
                </td>
              </tr>
            ))}
            {logs.length === 0 && !loading && (
              <tr>
                <td colSpan={7} className="px-4 py-8 text-center text-gray-400">
                  No audit logs yet. Process an invoice to see entries here.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
