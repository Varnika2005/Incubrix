import React from 'react';
import { Film, Sparkles, History, Cpu, Play } from 'lucide-react';

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
  return (
    <header className="sticky top-0 z-50 w-full border-b border-[rgba(255,255,255,0.08)] bg-[rgba(8,11,17,0.85)] backdrop-blur-md">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 h-16 flex items-center justify-between">
        {/* Brand */}
        <div
          className="flex items-center gap-3 cursor-pointer group"
          onClick={() => onNavigate('landing')}
        >
          <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-indigo-500 to-cyan-400 flex items-center justify-center shadow-lg shadow-indigo-500/20 group-hover:scale-105 transition-transform">
            <Film className="w-5 h-5 text-white" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="font-bold text-lg tracking-tight text-white">ClipPilot</span>
              <span className="badge badge-cyan text-[10px] px-1.5 py-0.5">AI Studio</span>
            </div>
            <p className="text-[11px] text-[#94A3B8]">Prompt-to-Video Engine</p>
          </div>
        </div>

        {/* Navigation Actions */}
        <div className="flex items-center gap-3">
          <button
            onClick={() => onNavigate('studio')}
            className={`btn ${activeView === 'studio' ? 'btn-primary' : 'btn-secondary'} text-xs py-2 px-3.5`}
          >
            <Sparkles className="w-4 h-4" />
            <span>Studio</span>
          </button>

          <button
            onClick={onStartDemo}
            disabled={isDemoLoading}
            className="btn btn-accent text-xs py-2 px-3.5 hidden sm:inline-flex"
            title="Load 1-Click Interactive Demo with Bundled Synthetic Video"
          >
            <Play className={`w-3.5 h-3.5 ${isDemoLoading ? 'animate-spin' : ''}`} />
            <span>{isDemoLoading ? 'Loading Demo...' : '1-Click Demo'}</span>
          </button>

          <button
            onClick={onOpenHistory}
            className="btn btn-secondary text-xs py-2 px-3"
            title="View Persistent Job History"
          >
            <History className="w-4 h-4" />
            <span className="hidden md:inline">History</span>
          </button>

          <button
            onClick={onOpenCapabilities}
            className="btn btn-secondary text-xs py-2 px-3"
            title="View Real System Capabilities"
          >
            <Cpu className="w-4 h-4" />
            <span className="hidden md:inline">Capabilities</span>
          </button>
        </div>
      </div>
    </header>
  );
};
