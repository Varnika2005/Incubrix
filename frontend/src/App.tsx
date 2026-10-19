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
    <div className="min-h-screen flex flex-col" style={{ background: 'var(--bg-primary)', color: 'var(--text-main)' }}>
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
      <footer
        className="py-6 px-4 relative overflow-hidden"
        style={{
          background: 'rgba(5,8,16,0.8)',
          backdropFilter: 'blur(12px)',
          borderTop: '1px solid rgba(255,255,255,0.04)',
        }}
      >
        {/* Rainbow line at top of footer */}
        <div
          className="absolute top-0 left-0 right-0 h-[1px]"
          style={{
            background: 'linear-gradient(90deg, #8B5CF6 0%, #EC4899 25%, #22D3EE 50%, #34D399 75%, #FBBF24 100%)',
            opacity: 0.4,
          }}
        />

        <div className="max-w-7xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-4 text-xs text-[#64748B]">
          <div className="flex items-center gap-2.5">
            <span
              className="w-2.5 h-2.5 rounded-full animate-pulse"
              style={{
                background: 'linear-gradient(135deg, #34D399, #22D3EE)',
                boxShadow: '0 0 8px rgba(52,211,153,0.4)',
              }}
            />
            <span
              className="font-bold"
              style={{
                background: 'linear-gradient(90deg, #C4B5FD, #F9A8D4, #67E8F9)',
                WebkitBackgroundClip: 'text',
                WebkitTextFillColor: 'transparent',
              }}
            >
              ClipPilot AI Engine
            </span>
            <span>• IncuBrix Selection PS2</span>
          </div>

          <div className="flex items-center gap-4">
            <button
              onClick={() => setIsCapabilitiesOpen(true)}
              className="hover:text-white transition-colors duration-200"
            >
              Engine Diagnostics
            </button>
            <span style={{ color: 'rgba(139,92,246,0.4)' }}>•</span>
            <button
              onClick={() => setIsHistoryOpen(true)}
              className="hover:text-white transition-colors duration-200"
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
