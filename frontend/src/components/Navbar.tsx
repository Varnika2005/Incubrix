import React from 'react';
import { Film, Sparkles, History, Cpu, Play, Wand2, Layers, CheckSquare, HelpCircle, BookOpen } from 'lucide-react';

interface NavbarProps {
  activeView: 'studio' | 'landing';
  onNavigate: (view: 'studio' | 'landing') => void;
  onOpenHistory: () => void;
  onOpenCapabilities: () => void;
  onStartDemo: () => void;
  isDemoLoading: boolean;
}

export const Navbar: React.FC<NavbarProps> = ({
  activeView,
  onNavigate,
  onOpenHistory,
  onOpenCapabilities,
  onStartDemo,
  isDemoLoading,
}) => {
  const handleNavAnchor = (anchorId: string) => {
    if (activeView !== 'landing') {
      onNavigate('landing');
      setTimeout(() => {
        const el = document.getElementById(anchorId);
        if (el) el.scrollIntoView({ behavior: 'smooth' });
      }, 100);
    } else {
      const el = document.getElementById(anchorId);
      if (el) el.scrollIntoView({ behavior: 'smooth' });
    }
  };

  return (
    <header
      className="sticky top-0 z-50 w-full"
      style={{
        background: 'rgba(5, 8, 16, 0.85)',
        backdropFilter: 'blur(24px) saturate(180%)',
        WebkitBackdropFilter: 'blur(24px) saturate(180%)',
        borderBottom: '1px solid rgba(255,255,255,0.08)',
        boxShadow: '0 4px 30px rgba(0,0,0,0.4)',
      }}
    >
      {/* Rainbow Accent Line at top */}
      <div
        className="h-[2.5px] w-full"
        style={{
          background: 'linear-gradient(90deg, #8B5CF6 0%, #EC4899 25%, #22D3EE 50%, #34D399 75%, #FBBF24 100%)',
        }}
      />

      <div className="max-w-7xl mx-auto px-4 sm:px-6 h-16 flex items-center justify-between gap-4">
        {/* Brand */}
        <div
          className="flex items-center gap-3 cursor-pointer group shrink-0"
          onClick={() => onNavigate('landing')}
        >
          <div
            className="w-10 h-10 rounded-xl flex items-center justify-center group-hover:scale-105 transition-transform duration-300"
            style={{
              background: 'linear-gradient(135deg, #8B5CF6 0%, #EC4899 50%, #22D3EE 100%)',
              boxShadow: '0 4px 20px rgba(139,92,246,0.35), 0 0 40px -10px rgba(236,72,153,0.25)',
            }}
          >
            <Film className="w-5 h-5 text-white" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="font-extrabold text-lg tracking-tight text-white">ClipPilot</span>
              <span
                className="text-[10px] font-bold px-2 py-0.5 rounded-full"
                style={{
                  background: 'linear-gradient(135deg, rgba(139,92,246,0.2), rgba(236,72,153,0.15))',
                  border: '1px solid rgba(139,92,246,0.3)',
                  color: '#C4B5FD',
                }}
              >
                AI Studio
              </span>
            </div>
            <p className="text-[11px] text-[#64748B]">PS2 Prompt Video Editor</p>
          </div>
        </div>

        {/* Structured Anchor Navigation Links */}
        <nav className="hidden lg:flex items-center gap-1 text-xs font-semibold text-[#94A3B8]">
          <button
            onClick={() => handleNavAnchor('workflow')}
            className="px-3 py-1.5 rounded-lg hover:text-white hover:bg-[rgba(255,255,255,0.05)] transition-colors"
          >
            Workflow
          </button>
          <button
            onClick={() => handleNavAnchor('features')}
            className="px-3 py-1.5 rounded-lg hover:text-white hover:bg-[rgba(255,255,255,0.05)] transition-colors"
          >
            Capabilities
          </button>
          <button
            onClick={() => handleNavAnchor('architecture')}
            className="px-3 py-1.5 rounded-lg hover:text-white hover:bg-[rgba(255,255,255,0.05)] transition-colors"
          >
            Architecture
          </button>
          <button
            onClick={() => handleNavAnchor('ps2-rubric')}
            className="px-3 py-1.5 rounded-lg hover:text-white hover:bg-[rgba(255,255,255,0.05)] transition-colors flex items-center gap-1.5"
          >
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
            <span>PS2 Rubric</span>
          </button>
          <button
            onClick={() => handleNavAnchor('faq')}
            className="px-3 py-1.5 rounded-lg hover:text-white hover:bg-[rgba(255,255,255,0.05)] transition-colors"
          >
            FAQ
          </button>
        </nav>

        {/* Action Controls */}
        <div className="flex items-center gap-2">
          <button
            onClick={() => onNavigate(activeView === 'studio' ? 'landing' : 'studio')}
            className={`btn text-xs py-2 px-3.5 font-bold ${
              activeView === 'studio' ? 'btn-primary' : 'btn-secondary'
            }`}
          >
            <Wand2 className="w-4 h-4" />
            <span>{activeView === 'studio' ? 'Overview' : 'Studio'}</span>
          </button>

          <button
            onClick={onStartDemo}
            disabled={isDemoLoading}
            className="btn text-xs py-2 px-3.5 hidden sm:inline-flex font-bold"
            style={{
              background: isDemoLoading
                ? 'rgba(255,255,255,0.05)'
                : 'linear-gradient(135deg, #22D3EE 0%, #06B6D4 100%)',
              color: '#fff',
              boxShadow: isDemoLoading ? 'none' : '0 4px 16px rgba(34,211,238,0.3)',
            }}
            title="Load 1-Click Interactive Demo with Bundled Synthetic Video"
          >
            <Play className={`w-3.5 h-3.5 ${isDemoLoading ? 'animate-spin' : ''}`} />
            <span>{isDemoLoading ? 'Booting...' : '1-Click Demo'}</span>
          </button>

          <button
            onClick={onOpenHistory}
            className="btn btn-secondary text-xs py-2 px-3"
            title="View Persistent Job History (SQLite)"
          >
            <History className="w-4 h-4 text-amber-400" />
            <span className="hidden md:inline">History</span>
          </button>

          <button
            onClick={onOpenCapabilities}
            className="btn btn-secondary text-xs py-2 px-3"
            title="View Real System Capabilities (FFmpeg Diagnostics)"
          >
            <Cpu className="w-4 h-4 text-emerald-400" />
            <span className="hidden md:inline">Engines</span>
          </button>
        </div>
      </div>
    </header>
  );
};
