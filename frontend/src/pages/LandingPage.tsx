import React from 'react';
import {
  Sparkles,
  ArrowRight,
  Play,
  Film,
  Scissors,
  Smartphone,
  Captions,
  Radio,
  CheckCircle2,
  Shield,
  Zap,
} from 'lucide-react';

interface LandingPageProps {
  onStartEditing: () => void;
  onStartDemo: () => void;
  isDemoLoading: boolean;
}

export const LandingPage: React.FC<LandingPageProps> = ({
  onStartEditing,
  onStartDemo,
  isDemoLoading,
}) => {
  return (
    <div className="flex flex-col gap-20 py-12 px-4 max-w-6xl mx-auto">
      {/* Hero Section */}
      <div className="text-center flex flex-col items-center gap-6 pt-6">
        <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-indigo-500/10 border border-indigo-500/20 text-indigo-300 text-xs font-semibold">
          <Sparkles className="w-3.5 h-3.5" />
          <span>IncuBrix PS2 Submission — Prompt-Based Video Editing Studio</span>
        </div>

        <h1 className="text-4xl sm:text-6xl font-extrabold tracking-tight text-white max-w-4xl leading-[1.15]">
          Your idea. Your prompt.{' '}
          <span className="bg-clip-text text-transparent bg-gradient-to-r from-indigo-400 via-cyan-300 to-indigo-300">
            Your finished video.
          </span>
        </h1>

        <p className="text-base sm:text-lg text-[#94A3B8] max-w-2xl leading-relaxed">
          ClipPilot AI transforms natural-language prompts into verified, explainable editing plans
          and transcodes your real videos with deterministic accuracy.
        </p>

        {/* CTA Buttons */}
        <div className="flex flex-wrap items-center justify-center gap-4 pt-2">
          <button
            onClick={onStartEditing}
            className="btn btn-primary text-sm py-3 px-7 font-bold shadow-xl shadow-indigo-500/25"
          >
            <span>Start Editing Studio</span>
            <ArrowRight className="w-4 h-4" />
          </button>

          <button
            onClick={onStartDemo}
            disabled={isDemoLoading}
            className="btn btn-accent text-sm py-3 px-6 font-bold"
          >
            <Play className={`w-4 h-4 ${isDemoLoading ? 'animate-spin' : ''}`} />
            <span>{isDemoLoading ? 'Booting Demo...' : '1-Click Interactive Demo'}</span>
          </button>
        </div>

        {/* Confidence badges */}
        <div className="flex flex-wrap items-center justify-center gap-6 pt-4 text-xs text-[#64748B]">
          <span className="flex items-center gap-1.5">
            <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
            100% Real Video Processing (FFmpeg 9.0)
          </span>
          <span className="flex items-center gap-1.5">
            <CheckCircle2 className="w-3.5 h-3.5 text-cyan-400" />
            Deterministic Prompt Understanding
          </span>
          <span className="flex items-center gap-1.5">
            <CheckCircle2 className="w-3.5 h-3.5 text-indigo-400" />
            Zero Paid API Dependencies Required
          </span>
        </div>
      </div>

      {/* 3-Step Workflow Section */}
      <div className="flex flex-col gap-8">
        <div className="text-center">
          <h2 className="text-2xl font-bold text-white">How ClipPilot AI Works</h2>
          <p className="text-xs text-[#94A3B8] mt-1">From raw instruction to verified export in seconds</p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="glass-card p-6 flex flex-col gap-3 border-[rgba(255,255,255,0.06)]">
            <div className="w-10 h-10 rounded-xl bg-indigo-500/15 border border-indigo-500/30 flex items-center justify-center text-indigo-400 font-bold">
              1
            </div>
            <h3 className="text-base font-bold text-white">Upload or Pick Sample</h3>
            <p className="text-xs text-[#94A3B8] leading-relaxed">
              Drop any MP4, MOV, or WEBM video or instantly boot our bundled talking-head demo project with one click.
            </p>
          </div>

          <div className="glass-card p-6 flex flex-col gap-3 border-indigo-500/30 bg-gradient-to-b from-indigo-950/20 to-transparent">
            <div className="w-10 h-10 rounded-xl bg-cyan-500/15 border border-cyan-500/30 flex items-center justify-center text-cyan-400 font-bold">
              2
            </div>
            <h3 className="text-base font-bold text-white">Type Your Instruction</h3>
            <p className="text-xs text-[#94A3B8] leading-relaxed">
              State what to trim, crop, resize, mute, adjust, or caption. The engine interprets your words into an explainable, step-by-step edit plan.
            </p>
          </div>

          <div className="glass-card p-6 flex flex-col gap-3 border-[rgba(255,255,255,0.06)]">
            <div className="w-10 h-10 rounded-xl bg-emerald-500/15 border border-emerald-500/30 flex items-center justify-center text-emerald-400 font-bold">
              3
            </div>
            <h3 className="text-base font-bold text-white">Approve & Download</h3>
            <p className="text-xs text-[#94A3B8] leading-relaxed">
              Tweak parameters, review detected silence cuts, approve the pipeline, and download your finished video with a cryptographic audit receipt.
            </p>
          </div>
        </div>
      </div>

      {/* Feature Showcase Grid */}
      <div className="flex flex-col gap-8">
        <div className="text-center">
          <h2 className="text-2xl font-bold text-white">Core Innovations & Capabilities</h2>
          <p className="text-xs text-[#94A3B8] mt-1">Built specifically for judges seeking real technical substance</p>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <div className="glass-card p-5 flex flex-col gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-indigo-500/15 flex items-center justify-center text-indigo-400">
              <Scissors className="w-4 h-4" />
            </div>
            <h4 className="text-sm font-bold text-white">Precise Trimming & Slicing</h4>
            <p className="text-xs text-[#94A3B8]">
              Millisecond-accurate boundary extraction, duration limiting, and negative timestamp rejection.
            </p>
          </div>

          <div className="glass-card p-5 flex flex-col gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-cyan-500/15 flex items-center justify-center text-cyan-400">
              <Smartphone className="w-4 h-4" />
            </div>
            <h4 className="text-sm font-bold text-white">Smart Aspect Ratio</h4>
            <p className="text-xs text-[#94A3B8]">
              Transform between 16:9 Landscape, 9:16 Vertical Shorts, and 1:1 Square without accidental distortion.
            </p>
          </div>

          <div className="glass-card p-5 flex flex-col gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-rose-500/15 flex items-center justify-center text-rose-400">
              <Radio className="w-4 h-4" />
            </div>
            <h4 className="text-sm font-bold text-white">Silence Review & Cut</h4>
            <p className="text-xs text-[#94A3B8]">
              Automated pause detection with interactive candidate cut inspection before removal.
            </p>
          </div>

          <div className="glass-card p-5 flex flex-col gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-purple-500/15 flex items-center justify-center text-purple-400">
              <Captions className="w-4 h-4" />
            </div>
            <h4 className="text-sm font-bold text-white">Subtitle Generator & Burner</h4>
            <p className="text-xs text-[#94A3B8]">
              Timestamped SRT creation burned directly into the output video with stylized formatting.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};
