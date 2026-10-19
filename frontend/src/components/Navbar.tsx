import React, { useState, useRef, useEffect } from 'react';
import {
  Film,
  Sparkles,
  FileVideo,
  Cpu,
  Play,
  LogOut,
  User,
  Plus,
  Menu,
  X,
  ChevronDown,
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';

interface NavbarProps {
  activeView: 'landing' | 'studio' | 'projects' | 'login' | 'signup';
  onNavigate: (view: 'landing' | 'studio' | 'projects' | 'login' | 'signup') => void;
  onOpenCapabilities: () => void;
  onStartDemo: () => void;
  onNewProject: () => void;
  isDemoLoading: boolean;
}

export const Navbar: React.FC<NavbarProps> = ({
  activeView,
  onNavigate,
  onOpenCapabilities,
  onStartDemo,
  onNewProject,
  isDemoLoading,
}) => {
  const { user, isAuthenticated, logout } = useAuth();
  const [isUserMenuOpen, setIsUserMenuOpen] = useState(false);
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const userMenuRef = useRef<HTMLDivElement>(null);

  // Close user dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (userMenuRef.current && !userMenuRef.current.contains(e.target as Node)) {
        setIsUserMenuOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const getInitials = (name?: string) => {
    if (!name) return 'CP';
    const parts = name.trim().split(' ');
    if (parts.length >= 2) {
      return `${parts[0][0]}${parts[1][0]}`.toUpperCase();
    }
    return name.slice(0, 2).toUpperCase();
  };

  const handleLogout = async () => {
    setIsUserMenuOpen(false);
    setIsMobileMenuOpen(false);
    await logout();
    onNavigate('landing');
  };

  return (
    <header className="sticky top-0 z-50 w-full border-b border-[#E6E2F0] bg-white/95 backdrop-blur-md shadow-xs">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        {/* Brand Logo (from blueprint) */}
        <div
          className="flex items-center gap-3 cursor-pointer group select-none"
          onClick={() => onNavigate('landing')}
        >
          <div className="w-10 h-10 rounded-2xl bg-[#6654F0] flex items-center justify-center text-white shadow-md shadow-[#6654F0]/25 group-hover:scale-105 transition-transform">
            <Film className="w-5 h-5" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="font-extrabold text-lg tracking-tight text-[#191832]">ClipPilot AI</span>
              <span className="hidden sm:inline-flex text-[10px] uppercase font-bold tracking-wider px-2 py-0.5 rounded-md bg-[#EFEDF8] text-[#6654F0]">
                PROMPT-TO-VIDEO STUDIO
              </span>
            </div>
            <p className="text-[11px] text-[#66627B]">Prompt-to-Video Engine</p>
          </div>
        </div>

        {/* Desktop Primary Navigation Links */}
        <nav className="hidden md:flex items-center gap-1.5">
          <button
            onClick={() => onNavigate('studio')}
            className={`btn ${
              activeView === 'studio' ? 'btn-primary' : 'btn-ghost'
            } text-xs py-2 px-4 rounded-xl`}
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
            onClick={() => onNavigate('projects')}
            className={`btn ${
              activeView === 'projects' ? 'btn-primary' : 'btn-ghost'
            } text-xs py-2 px-4 rounded-xl`}
          >
            <FileVideo className="w-4 h-4" />
            <span>Projects</span>
          </button>

          <button
            onClick={onOpenCapabilities}
            className="btn btn-ghost text-xs py-2 px-4 rounded-xl"
            title="Inspect Genuine FFmpeg Engine Capabilities"
          >
            <Cpu className="w-4 h-4" />
            <span>Capabilities</span>
          </button>
        </nav>

        {/* Desktop Actions */}
        <div className="hidden md:flex items-center gap-3">
          {/* 1-Click Demo Shortcut */}
          <button
            onClick={onStartDemo}
            disabled={isDemoLoading}
            className="btn btn-secondary text-xs py-2 px-3.5 rounded-xl border-[#E6E2F0]"
            title="Load Bundled Synthetic Video Demo Project"
          >
            <Play className={`w-3.5 h-3.5 text-[#15B8C9] ${isDemoLoading ? 'animate-spin' : ''}`} />
            <span>{isDemoLoading ? 'Loading...' : '1-Click Demo'}</span>
          </button>

          {isAuthenticated ? (
            <div className="flex items-center gap-3">
              {/* New Project CTA */}
              <button
                onClick={onNewProject}
                className="btn btn-accent text-xs py-2 px-3.5 font-bold shadow-sm"
              >
                <Plus className="w-3.5 h-3.5" />
                <span>New Video</span>
              </button>

              {/* User Avatar Dropdown */}
              <div className="relative" ref={userMenuRef}>
                <button
                  type="button"
                  onClick={() => setIsUserMenuOpen(!isUserMenuOpen)}
                  className="flex items-center gap-2 p-1.5 rounded-xl hover:bg-[#F1F5F9] border border-transparent hover:border-[#E2E8F0] transition-colors"
                >
                  <div className="w-8 h-8 rounded-lg bg-gradient-to-tr from-indigo-600 to-indigo-800 text-white font-bold text-xs flex items-center justify-center shadow-sm">
                    {getInitials(user?.full_name)}
                  </div>
                  <span className="text-xs font-semibold text-[#0F172A] max-w-[120px] truncate">
                    {user?.full_name.split(' ')[0]}
                  </span>
                  <ChevronDown className="w-3.5 h-3.5 text-[#94A3B8]" />
                </button>

                {isUserMenuOpen && (
                  <div className="absolute right-0 mt-2 w-56 bg-white border border-[#E2E8F0] rounded-xl shadow-xl py-2 z-50 animation-scaleUp">
                    <div className="px-4 py-2 border-b border-[#F1F5F9]">
                      <p className="text-xs font-bold text-[#0F172A] truncate">{user?.full_name}</p>
                      <p className="text-[11px] text-[#64748B] truncate">{user?.email}</p>
                    </div>

                    <div className="py-1">
                      <button
                        onClick={() => {
                          setIsUserMenuOpen(false);
                          onNavigate('studio');
                        }}
                        className="w-full text-left px-4 py-2 text-xs text-[#334155] hover:bg-[#F8FAFC] flex items-center gap-2 font-medium"
                      >
                        <Sparkles className="w-3.5 h-3.5 text-indigo-600" />
                        <span>Studio Workspace</span>
                      </button>

                      <button
                        onClick={() => {
                          setIsUserMenuOpen(false);
                          onNavigate('projects');
                        }}
                        className="w-full text-left px-4 py-2 text-xs text-[#334155] hover:bg-[#F8FAFC] flex items-center gap-2 font-medium"
                      >
                        <FileVideo className="w-3.5 h-3.5 text-cyan-600" />
                        <span>My Projects</span>
                      </button>

                      <button
                        onClick={() => {
                          setIsUserMenuOpen(false);
                          onOpenCapabilities();
                        }}
                        className="w-full text-left px-4 py-2 text-xs text-[#334155] hover:bg-[#F8FAFC] flex items-center gap-2 font-medium"
                      >
                        <Cpu className="w-3.5 h-3.5 text-[#64748B]" />
                        <span>System Diagnostics</span>
                      </button>
                    </div>

                    <div className="pt-1 border-t border-[#F1F5F9]">
                      <button
                        onClick={handleLogout}
                        className="w-full text-left px-4 py-2 text-xs text-rose-600 hover:bg-rose-50 flex items-center gap-2 font-medium"
                      >
                        <LogOut className="w-3.5 h-3.5" />
                        <span>Sign Out</span>
                      </button>
                    </div>
                  </div>
                )}
              </div>
            </div>
          ) : (
            <div className="flex items-center gap-2.5">
              <button
                onClick={() => onNavigate('login')}
                className="btn btn-secondary text-xs py-2 px-3.5 font-semibold rounded-xl border-[#E6E2F0]"
              >
                <span>Sign in</span>
              </button>

              <button
                onClick={() => onNavigate('signup')}
                className="btn btn-primary text-xs py-2 px-4.5 font-bold rounded-xl shadow-md shadow-[#6654F0]/25"
              >
                <span>Start creating</span>
              </button>
            </div>
          )}
        </div>

        {/* Mobile Hamburger Toggle */}
        <div className="flex md:hidden items-center gap-2">
          <button
            onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
            className="p-2 rounded-lg text-[#475569] hover:bg-[#F1F5F9]"
            aria-label="Toggle menu"
          >
            {isMobileMenuOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
          </button>
        </div>
      </div>

      {/* Mobile Drawer Menu */}
      {isMobileMenuOpen && (
        <div className="md:hidden border-t border-[#E2E8F0] bg-white px-4 py-4 flex flex-col gap-3 shadow-lg">
          {isAuthenticated && user && (
            <div className="p-3 bg-[#F8FAFC] border border-[#E2E8F0] rounded-xl flex items-center gap-3">
              <div className="w-9 h-9 rounded-lg bg-indigo-600 text-white font-bold text-xs flex items-center justify-center">
                {getInitials(user.full_name)}
              </div>
              <div className="min-w-0 flex-1">
                <p className="text-xs font-bold text-[#0F172A] truncate">{user.full_name}</p>
                <p className="text-[11px] text-[#64748B] truncate">{user.email}</p>
              </div>
            </div>
          )}

          <div className="flex flex-col gap-1">
            <button
              onClick={() => {
                setIsMobileMenuOpen(false);
                onNavigate('studio');
              }}
              className={`w-full text-left px-3 py-2.5 rounded-lg text-xs font-semibold flex items-center gap-2.5 ${
                activeView === 'studio' ? 'bg-indigo-50 text-indigo-700' : 'text-[#334155]'
              }`}
            >
              <Sparkles className="w-4 h-4 text-indigo-600" />
              <span>Studio Workspace</span>
            </button>

            <button
              onClick={() => {
                setIsMobileMenuOpen(false);
                onNavigate('projects');
              }}
              className={`w-full text-left px-3 py-2.5 rounded-lg text-xs font-semibold flex items-center gap-2.5 ${
                activeView === 'projects' ? 'bg-indigo-50 text-indigo-700' : 'text-[#334155]'
              }`}
            >
              <FileVideo className="w-4 h-4 text-cyan-600" />
              <span>Projects & History</span>
            </button>

            <button
              onClick={() => {
                setIsMobileMenuOpen(false);
                onOpenCapabilities();
              }}
              className="w-full text-left px-3 py-2.5 rounded-lg text-xs font-semibold text-[#334155] flex items-center gap-2.5"
            >
              <Cpu className="w-4 h-4 text-slate-500" />
              <span>System Capabilities</span>
            </button>
          </div>

          <div className="pt-2 border-t border-[#F1F5F9] flex flex-col gap-2">
            <button
              onClick={() => {
                setIsMobileMenuOpen(false);
                onStartDemo();
              }}
              disabled={isDemoLoading}
              className="btn btn-secondary text-xs w-full py-2.5"
            >
              <Play className="w-3.5 h-3.5 text-cyan-600" />
              <span>{isDemoLoading ? 'Loading Demo...' : '1-Click Demo'}</span>
            </button>

            {isAuthenticated ? (
              <button
                onClick={handleLogout}
                className="btn btn-danger text-xs w-full py-2.5"
              >
                <LogOut className="w-3.5 h-3.5" />
                <span>Sign Out</span>
              </button>
            ) : (
              <div className="grid grid-cols-2 gap-2 pt-1">
                <button
                  onClick={() => {
                    setIsMobileMenuOpen(false);
                    onNavigate('login');
                  }}
                  className="btn btn-secondary text-xs py-2.5"
                >
                  <span>Sign In</span>
                </button>
                <button
                  onClick={() => {
                    setIsMobileMenuOpen(false);
                    onNavigate('signup');
                  }}
                  className="btn btn-primary text-xs py-2.5"
                >
                  <span>Sign Up</span>
                </button>
              </div>
            )}
          </div>
        </div>
      )}
    </header>
  );
};
