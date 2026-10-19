import React, { useState } from 'react';
import { Navbar } from './components/Navbar';
import { LandingPage } from './pages/LandingPage';
import { StudioPage } from './pages/StudioPage';
import { JobHistory } from './components/JobHistory';
import { CapabilitiesModal } from './components/CapabilitiesModal';
import { JobResponse } from './types';
import { api } from './services/api';

export function App() {
  const [activeView, setActiveView] = useState<'studio' | 'landing'>('studio');
  const [selectedJob, setSelectedJob] = useState<JobResponse | null>(null);
  
  // Navigation Modals
  const [isHistoryOpen, setIsHistoryOpen] = useState(false);
  const [isCapabilitiesOpen, setIsCapabilitiesOpen] = useState(false);
  const [isDemoLoading, setIsDemoLoading] = useState(false);

  const handleStartDemo = async () => {
    setIsDemoLoading(true);
    try {
      const demoJob = await api.createDemoJob();
      setSelectedJob(demoJob);
      setActiveView('studio');
    } catch (err) {
      console.error('Failed to trigger demo', err);
    } finally {
      setIsDemoLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex flex-col bg-[var(--bg-primary)] text-[var(--text-main)]">
      {/* Top Navbar */}
      <Navbar
        activeView={activeView}
        onNavigate={setActiveView}
        onOpenHistory={() => setIsHistoryOpen(true)}
        onOpenCapabilities={() => setIsCapabilitiesOpen(true)}
        onStartDemo={handleStartDemo}
        isDemoLoading={isDemoLoading}
      />

      {/* Main Content Area */}
      <main className="flex-1">
        {activeView === 'landing' ? (
          <LandingPage
            onStartEditing={() => setActiveView('studio')}
            onStartDemo={handleStartDemo}
            isDemoLoading={isDemoLoading}
          />
        ) : (
          <StudioPage
            initialJob={selectedJob}
            onClearJob={() => setSelectedJob(null)}
          />
        )}
      </main>

      {/* Persistent Job History Modal */}
      <JobHistory
        isOpen={isHistoryOpen}
        onClose={() => setIsHistoryOpen(false)}
        onSelectJob={(job) => {
          setSelectedJob(job);
          setActiveView('studio');
        }}
      />

      {/* System Capabilities Modal */}
      <CapabilitiesModal
        isOpen={isCapabilitiesOpen}
        onClose={() => setIsCapabilitiesOpen(false)}
      />

      {/* Global Footer */}
      <footer className="border-t border-[rgba(255,255,255,0.06)] py-6 px-4 bg-black/30">
        <div className="max-w-7xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-4 text-xs text-[#64748B]">
          <div className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
            <span className="text-white font-semibold">ClipPilot AI Engine</span>
            <span>• IncuBrix Selection PS2</span>
          </div>

          <div className="flex items-center gap-4">
            <button
              onClick={() => setIsCapabilitiesOpen(true)}
              className="hover:text-white transition-colors"
            >
              Engine Diagnostics
            </button>
            <span>•</span>
            <button
              onClick={() => setIsHistoryOpen(true)}
              className="hover:text-white transition-colors"
            >
              SQLite Audit Store
            </button>
          </div>
        </div>
      </footer>
    </div>
  );
}

export default App;
