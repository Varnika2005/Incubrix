import React from 'react';
import { Film, Sparkles, History, Cpu, Play, Wand2 } from 'lucide-react';

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
    <header
      className="sticky top-0 z-50 w-full"
      style={{
        background: 'rgba(5, 8, 16, 0.7)',
        backdropFilter: 'blur(20px) saturate(180%)',
        WebkitBackdropFilter: 'blur(20px) saturate(180%)',
        borderBottom: '1px solid rgba(255,255,255,0.06)',
        boxShadow: '0 4px 30px rgba(0,0,0,0.3)',
      }}
    >
      {/* Rainbow Accent Line at top */}
      <div
        className="h-[2px] w-full"
        style={{
          background: 'linear-gradient(90deg, #8B5CF6 0%, #EC4899 25%, #22D3EE 50%, #34D399 75%, #FBBF24 100%)',
          opacity: 0.7,
        }}
      />

      <div className="max-w-7xl mx-auto px-4 sm:px-6 h-16 flex items-center justify-between">
        {/* Brand */}
        <div
          className="flex items-center gap-3 cursor-pointer group"
          onClick={() => onNavigate('landing')}
        >
          <div
            className="w-10 h-10 rounded-xl flex items-center justify-center group-hover:scale-110 transition-transform duration-300"
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
            <p className="text-[11px] text-[#64748B]">Prompt-to-Video Engine</p>
          </div>
        </div>

        {/* Navigation Actions */}
        <div className="flex items-center gap-2.5">
          <button
            onClick={() => onNavigate('studio')}
            className={`btn text-xs py-2 px-3.5 ${activeView === 'studio' ? 'btn-primary' : 'btn-secondary'}`}
          >
            <Sparkles className="w-4 h-4" />
            <span>Studio</span>
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
            <span>{isDemoLoading ? 'Loading...' : '1-Click Demo'}</span>
          </button>

          <button
            onClick={onOpenHistory}
            className="btn btn-secondary text-xs py-2 px-3"
            title="View Persistent Job History"
          >
            <History className="w-4 h-4 text-amber-400" />
            <span className="hidden md:inline">History</span>
          </button>

          <button
            onClick={onOpenCapabilities}
            className="btn btn-secondary text-xs py-2 px-3"
            title="View Real System Capabilities"
          >
            <Cpu className="w-4 h-4 text-emerald-400" />
            <span className="hidden md:inline">Capabilities</span>
          </button>
        </div>
      </div>
    </header>
  );
};
