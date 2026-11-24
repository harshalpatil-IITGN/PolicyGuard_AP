import React, { useState } from 'react';
import Dashboard from './pages/Dashboard';
import AuditLogs from './pages/AuditLogs';
import UploadPDF from './pages/UploadPDF';

const TABS = [
  { id: 'dashboard', label: '📊 Dashboard', icon: '📊' },
  { id: 'upload',    label: '📄 Upload PDF', icon: '📄' },
  { id: 'audit',     label: '📋 Audit Trail', icon: '📋' },
];

export default function App() {
  const [activeTab, setActiveTab] = useState('dashboard');

  return (
    <div className="min-h-screen flex flex-col">
      {/* Header */}
      <header className="bg-brand-900 text-white shadow-lg">
        <div className="max-w-7xl mx-auto px-4 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <span className="text-2xl">🛡️</span>
            <div>
              <h1 className="text-xl font-bold tracking-tight">PolicyGuard AP</h1>
              <p className="text-xs text-blue-200">Agentic AI • Three-Way Match Engine</p>
            </div>
          </div>
          <div className="text-sm text-blue-200">
            Ashvaka Industries Group • FIN-AP-07 v3.2
          </div>
        </div>
      </header>

      {/* Tab Navigation */}
      <nav className="bg-white border-b shadow-sm">
        <div className="max-w-7xl mx-auto px-4 flex gap-1">
          {TABS.map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`px-4 py-3 text-sm font-medium border-b-2 transition-colors ${
                activeTab === tab.id
                  ? 'border-brand-600 text-brand-700 bg-blue-50'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>
      </nav>

      {/* Content */}
      <main className="flex-1 max-w-7xl mx-auto w-full px-4 py-6">
        {activeTab === 'dashboard' && <Dashboard />}
        {activeTab === 'upload' && <UploadPDF />}
        {activeTab === 'audit' && <AuditLogs />}
      </main>

      {/* Footer */}
      <footer className="bg-gray-100 border-t text-center py-3 text-xs text-gray-500">
        PolicyGuard AP v1.0 • Business Date: 09 Oct 2026 18:00 IST • Zero LLM Math
      </footer>
    </div>
  );
}
