import React, { useState, useEffect } from 'react';
import { AuthProvider, useAuth } from './context/AuthContext';
import { Navbar } from './components/Navbar';
import { LandingPage } from './pages/LandingPage';
import { StudioPage } from './pages/StudioPage';
import { ProjectsPage } from './pages/ProjectsPage';
import { LoginPage } from './pages/LoginPage';
import { SignupPage } from './pages/SignupPage';
import { CapabilitiesModal } from './components/CapabilitiesModal';
import { JobResponse } from './types';
import { api } from './services/api';

type AppView = 'landing' | 'studio' | 'projects' | 'login' | 'signup';

function MainApp() {
  const { isAuthenticated, isLoading: isAuthLoading } = useAuth();
  const [activeView, setActiveView] = useState<AppView>('landing');
  const [selectedJob, setSelectedJob] = useState<JobResponse | null>(null);
  const [redirectTarget, setRedirectTarget] = useState<AppView | null>(null);

  // Modals & Demo states
  const [isCapabilitiesOpen, setIsCapabilitiesOpen] = useState(false);
  const [isDemoLoading, setIsDemoLoading] = useState(false);

  // Hash-based routing synchronization
  useEffect(() => {
    const handleHashChange = () => {
      const hash = window.location.hash.replace('#', '').replace('/', '');
      if (['landing', 'studio', 'projects', 'login', 'signup'].includes(hash)) {
        setActiveView(hash as AppView);
      } else if (!hash) {
        setActiveView('landing');
      }
    };

    handleHashChange();
    window.addEventListener('hashchange', handleHashChange);
    return () => window.removeEventListener('hashchange', handleHashChange);
  }, []);

  // Update hash when activeView changes
  const navigateTo = (view: AppView) => {
    // Route guard: if trying to open projects while unauthenticated
    if (view === 'projects' && !isAuthenticated) {
      setRedirectTarget('projects');
      window.location.hash = '#login';
      return;
    }

    // If trying to open studio without an active demo and unauthenticated
    if (view === 'studio' && !isAuthenticated && !selectedJob) {
      setRedirectTarget('studio');
      window.location.hash = '#login';
      return;
    }

    window.location.hash = `#${view}`;
  };

  const handleAuthSuccess = () => {
    const target = redirectTarget || 'studio';
    setRedirectTarget(null);
    navigateTo(target);
  };

  const handleStartDemo = async () => {
    setIsDemoLoading(true);
    try {
      const demoJob = await api.createDemoJob();
      setSelectedJob(demoJob);
      navigateTo('studio');
    } catch (err) {
      console.error('Failed to trigger demo', err);
    } finally {
      setIsDemoLoading(false);
    }
  };

  const handleNewProject = () => {
    setSelectedJob(null);
    navigateTo('studio');
  };

  if (isAuthLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-[var(--bg-primary)]">
        <div className="flex flex-col items-center gap-3">
          <div className="w-8 h-8 border-3 border-indigo-600 border-t-transparent rounded-full animate-spin" />
          <span className="text-xs font-semibold text-[#64748B]">Initializing ClipPilot Studio...</span>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex flex-col bg-[var(--bg-primary)] text-[var(--text-main)]">
      {/* Top Application Shell Navbar */}
      <Navbar
        activeView={activeView}
        onNavigate={navigateTo}
        onOpenCapabilities={() => setIsCapabilitiesOpen(true)}
        onStartDemo={handleStartDemo}
        onNewProject={handleNewProject}
        isDemoLoading={isDemoLoading}
      />

      {/* Main Dynamic View Area */}
      <main className="flex-1">
        {activeView === 'landing' && (
          <LandingPage
            onStartEditing={() => navigateTo('studio')}
            onStartDemo={handleStartDemo}
            onNavigateToSignup={() => navigateTo('signup')}
            isDemoLoading={isDemoLoading}
          />
        )}

        {activeView === 'studio' && (
          <StudioPage
            initialJob={selectedJob}
            onClearJob={() => setSelectedJob(null)}
          />
        )}

        {activeView === 'projects' && (
          <ProjectsPage
            onSelectJob={(job) => {
              setSelectedJob(job);
              navigateTo('studio');
            }}
            onNewProject={handleNewProject}
            onNavigateToLogin={() => navigateTo('login')}
          />
        )}

        {activeView === 'login' && (
          <LoginPage
            onNavigateToSignup={() => navigateTo('signup')}
            onNavigateToDemo={handleStartDemo}
            onSuccess={handleAuthSuccess}
          />
        )}

        {activeView === 'signup' && (
          <SignupPage
            onNavigateToLogin={() => navigateTo('login')}
            onNavigateToDemo={handleStartDemo}
            onSuccess={handleAuthSuccess}
          />
        )}
      </main>

      {/* System Capabilities Modal */}
      <CapabilitiesModal
        isOpen={isCapabilitiesOpen}
        onClose={() => setIsCapabilitiesOpen(false)}
      />

      {/* Global Application Footer */}
      <footer className="border-t border-[#E2E8F0] py-6 px-4 bg-white/80 mt-12">
        <div className="max-w-7xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-4 text-xs text-[#64748B]">
          <div className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
            <span className="text-[#0F172A] font-bold">ClipPilot AI Engine</span>
            <span>• IncuBrix Selection PS2 Submission</span>
          </div>

          <div className="flex items-center gap-4">
            <button
              onClick={() => setIsCapabilitiesOpen(true)}
              className="hover:text-indigo-600 transition-colors font-medium"
            >
              Engine Diagnostics
            </button>
            <span style={{ color: 'rgba(139,92,246,0.4)' }}>•</span>
            <button
              onClick={() => navigateTo('projects')}
              className="hover:text-indigo-600 transition-colors font-medium"
            >
              Projects & History
            </button>
            <span>•</span>
            <a
              href="http://127.0.0.1:8000/docs"
              target="_blank"
              rel="noopener noreferrer"
              className="hover:text-indigo-600 transition-colors font-medium"
            >
              FastAPI Swagger Docs
            </a>
          </div>
        </div>
      </footer>
    </div>
  );
}

export function App() {
  return (
    <AuthProvider>
      <MainApp />
    </AuthProvider>
  );
}

export default App;
