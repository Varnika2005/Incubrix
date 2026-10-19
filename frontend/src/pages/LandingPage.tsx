import React, { useState } from 'react';
import {
  Sparkles,
  ArrowRight,
  Play,
  Film,
  Scissors,
  Smartphone,
  Captions,
  FileCheck,
  CheckCircle2,
  ShieldCheck,
  Zap,
  Sliders,
  Cpu,
  MessageSquare,
  Volume2,
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';

interface LandingPageProps {
  onStartEditing: () => void;
  onStartDemo: () => void;
  onNavigateToSignup: () => void;
  isDemoLoading: boolean;
}

// Interactive Prompt Sandbox Simulation Data
const SANDBOX_PROMPTS = [
  {
    title: 'Shorts Reframe + Subtitles',
    prompt: 'Convert to 9:16 vertical shorts and burn stylized subtitles',
    operations: [
      { type: 'aspect_ratio', target: '9:16', desc: 'Crop 16:9 to vertical 1080x1920 with centered focus' },
      { type: 'subtitles', engine: 'whisper_ai', desc: 'Generate timestamped SRT and burn into video frame' },
    ],
    ffmpeg: 'ffmpeg -i input.mp4 -vf "crop=ih*(9/16):ih,subtitles=transcription.srt" -c:a copy output.mp4',
    benefit: 'Ready for TikTok, YouTube Shorts, and Instagram Reels in 1 pass',
  },
  {
    title: 'Silence Cut + Speed Up',
    prompt: 'Cut all silent pauses and speed up video to 1.25x',
    operations: [
      { type: 'silence_removal', threshold: '-30dB', desc: 'Scan audio for pauses >0.5s and produce human-reviewable cut list' },
      { type: 'playback_speed', factor: 1.25, desc: 'Set video PTS to 0.8 and audio atempo filter to 1.25' },
    ],
    ffmpeg: 'ffmpeg -i input.mp4 -filter_complex "[0:v]setpts=0.8*PTS[v];[0:a]atempo=1.25[a]" -map "[v]" -map "[a]" output.mp4',
    benefit: 'Compresses long talking-head footage into high-retention content',
  },
  {
    title: 'Trim Intro + Background Mute',
    prompt: 'Trim first 3 seconds, keep 10 seconds, and mute audio',
    operations: [
      { type: 'trim', start: '3.0s', end: '13.0s', desc: 'Millisecond keyframe boundary slice between 00:00:03 and 00:00:13' },
      { type: 'audio_mute', desc: 'Strip audio stream completely for silent background loop' },
    ],
    ffmpeg: 'ffmpeg -ss 00:00:03 -i input.mp4 -t 10 -an -c:v libx264 output.mp4',
    benefit: 'Clean B-roll extraction with zero background microphone noise',
  },
  {
    title: 'Square Feed + Audio Boost',
    prompt: 'Crop to 1:1 square for Instagram and boost speech volume by 1.5x',
    operations: [
      { type: 'aspect_ratio', target: '1:1', desc: 'Center-crop to square 1080x1080' },
      { type: 'volume_adjustment', factor: 1.5, desc: 'Apply volume=1.5 filter with audio peak limiter' },
    ],
    ffmpeg: 'ffmpeg -i input.mp4 -vf "crop=min(iw\\,ih):min(iw\\,ih)" -af "volume=1.5" output.mp4',
    benefit: 'Square social grid optimization with clear broadcast audio levels',
  },
];

export const LandingPage: React.FC<LandingPageProps> = ({
  onStartEditing,
  onStartDemo,
  onNavigateToSignup,
  isDemoLoading,
}) => {
  const { isAuthenticated, user } = useAuth();

  return (
    <div className="flex flex-col gap-20 sm:gap-28 py-8 sm:py-12 px-4 sm:px-6 lg:px-8 max-w-7xl mx-auto w-full">
      {/* 1. Palette Dots Indicator (from user blueprint) */}
      <div className="flex items-center gap-2 text-xs font-medium text-[#66627B] select-none">
        <div className="flex items-center gap-1.5">
          <span className="w-2.5 h-2.5 rounded-full bg-[#6654F0]" title="Electric Violet" />
          <span className="w-2.5 h-2.5 rounded-full bg-[#15B8C9]" title="Cyan" />
          <span className="w-2.5 h-2.5 rounded-full bg-[#FF8B70]" title="Coral" />
          <span className="w-2.5 h-2.5 rounded-full bg-[#BDEFD8]" title="Mint" />
          <span className="w-2.5 h-2.5 rounded-full bg-[#EFEDF8] border border-[#E6E2F0]" title="Soft Lavender" />
        </div>
        <span className="text-[11px] text-[#8E8A9F] ml-1">
          Violet · Cyan · Coral · Mint · Soft lavender
        </span>
      </div>

      {/* 2. Hero Section: Split Layout on Desktop */}
      <section className="grid grid-cols-1 lg:grid-cols-12 gap-10 lg:gap-12 items-center">
        {/* Left Column: Headline, Copy, Actions, Highlights */}
        <div className="lg:col-span-6 flex flex-col gap-6 text-left">
          {/* Badge */}
          <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-[#EFEDF8] border border-[#E6E2F0] text-[#6654F0] text-xs font-semibold w-fit shadow-xs">
            <Sparkles className="w-3.5 h-3.5 text-[#6654F0]" />
            <span>ClipPilot AI — Creative Studio</span>
          </div>

          {/* Headline */}
          <h1 className="text-4xl sm:text-5xl lg:text-6xl font-extrabold tracking-tight text-[#191832] leading-[1.12]">
            Your words. Your vision.<br />
            <span className="text-[#6654F0]">
              Your finished video.
            </span>
          </h1>

          {/* Subtitle */}
          <p className="text-base sm:text-lg text-[#66627B] max-w-xl leading-relaxed">
            Turn natural-language instructions into polished video edits with an AI-powered creative studio. Explainable plans, genuine FFmpeg processing, and instant exports.
          </p>

          {/* Action Buttons */}
          <div className="flex flex-wrap items-center gap-3 pt-2">
            {isAuthenticated ? (
              <button
                onClick={onStartEditing}
                className="btn btn-primary text-sm sm:text-base py-3 px-7 font-bold rounded-xl shadow-lg shadow-[#6654F0]/25 transition-all hover:scale-[1.02]"
              >
                <span>Launch Studio ({user?.full_name?.split(' ')[0] || 'Creator'})</span>
                <ArrowRight className="w-4 h-4 ml-1" />
              </button>
            ) : (
              <button
                onClick={onNavigateToSignup}
                className="btn btn-primary text-sm sm:text-base py-3 px-7 font-bold rounded-xl shadow-lg shadow-[#6654F0]/25 transition-all hover:scale-[1.02]"
              >
                <span>Start creating</span>
                <ArrowRight className="w-4 h-4 ml-1" />
              </button>
            )}

            <button
              onClick={onStartDemo}
              disabled={isDemoLoading}
              className="btn btn-secondary text-sm sm:text-base py-3 px-6 font-semibold rounded-xl bg-white border border-[#E6E2F0] hover:bg-[#EFEDF8] text-[#191832] transition-all"
            >
              <Play className={`w-4 h-4 text-[#15B8C9] ${isDemoLoading ? 'animate-spin' : ''}`} />
              <span>{isDemoLoading ? 'Booting Demo...' : 'Explore demo'}</span>
            </button>
          </div>

          {/* Three Compact Feature Highlights */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 pt-4 border-t border-[#E6E2F0]">
            <div className="flex items-center gap-2 text-xs font-semibold text-[#191832]">
              <CheckCircle2 className="w-4 h-4 text-[#15B8C9] shrink-0" />
              <span>Real video processing</span>
            </div>
            <div className="flex items-center gap-2 text-xs font-semibold text-[#191832]">
              <CheckCircle2 className="w-4 h-4 text-[#6654F0] shrink-0" />
              <span>Editable edit plans</span>
            </div>
            <div className="flex items-center gap-2 text-xs font-semibold text-[#191832]">
              <CheckCircle2 className="w-4 h-4 text-[#FF8B70] shrink-0" />
              <span>Creator-ready exports</span>
            </div>
          </div>
        </div>

        {/* Right Column: Genuine Product Blueprint Card */}
        <div className="lg:col-span-6 w-full">
          <div className="card p-6 sm:p-7 border border-[#E6E2F0] bg-white rounded-3xl shadow-xl flex flex-col gap-5 relative overflow-hidden">
            {/* Blueprint Header */}
            <div className="flex items-center justify-between border-b border-[#EFEDF8] pb-4">
              <div className="flex items-center gap-2 text-[#6654F0] font-bold text-sm">
                <Sparkles className="w-4 h-4" />
                <span>Your editing workspace</span>
              </div>
              <span className="badge badge-emerald text-[10px]">
                FFmpeg 9.0 Core
              </span>
            </div>

            {/* Describe Your Edit Card */}
            <div className="bg-[#EFEDF8] border border-[#E6E2F0] rounded-2xl p-4 flex flex-col gap-2">
              <div className="flex items-center gap-2 text-xs font-semibold text-[#66627B]">
                <MessageSquare className="w-4 h-4 text-[#6654F0]" />
                <span>Describe your edit</span>
              </div>
              <p className="text-sm font-semibold text-[#191832] bg-white/70 p-3 rounded-xl border border-[#E6E2F0] shadow-xs">
                "Make a vertical reel, add subtitles and improve the audio."
              </p>
            </div>

            {/* Split Operations: Review Plan & Export Video Cards */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3.5">
              {/* Review edit plan card (soft lavender) */}
              <div className="bg-[#EFEDF8] border border-[#E6E2F0] rounded-2xl p-4 flex flex-col gap-1 transition-all hover:border-[#6654F0]">
                <div className="flex items-center gap-2 text-xs font-bold text-[#6654F0]">
                  <Sliders className="w-4 h-4" />
                  <span>Review edit plan</span>
                </div>
                <p className="text-xs text-[#66627B]">Inspect each operation</p>
              </div>

              {/* Export video card (soft mint) */}
              <div className="bg-[#EBFBF3] border border-[#BDEFD8] rounded-2xl p-4 flex flex-col gap-1 transition-all hover:border-[#15B8C9]">
                <div className="flex items-center gap-2 text-xs font-bold text-[#0E6B47]">
                  <Film className="w-4 h-4 text-[#15B8C9]" />
                  <span>Export video</span>
                </div>
                <p className="text-xs text-[#0E6B47]">Preview and download</p>
              </div>
            </div>

            {/* 4 Discrete Inspectable Execution Steps */}
            <div className="pt-2 flex flex-col gap-2">
              <span className="text-[11px] font-bold uppercase tracking-wider text-[#8E8A9F]">
                Generated Pipeline Steps
              </span>
              <div className="grid grid-cols-2 gap-2 text-xs">
                <div className="p-2.5 rounded-xl bg-[#F7F6FC] border border-[#E6E2F0] flex items-center justify-between">
                  <span className="font-semibold text-[#191832]">1. Trim Opening</span>
                  <span className="text-[11px] font-mono text-[#6654F0]">0.0s - 3.0s</span>
                </div>
                <div className="p-2.5 rounded-xl bg-[#F7F6FC] border border-[#E6E2F0] flex items-center justify-between">
                  <span className="font-semibold text-[#191832]">2. 9:16 Vertical</span>
                  <span className="text-[11px] font-mono text-[#15B8C9]">1080x1920</span>
                </div>
                <div className="p-2.5 rounded-xl bg-[#F7F6FC] border border-[#E6E2F0] flex items-center justify-between">
                  <span className="font-semibold text-[#191832]">3. Audio Boost</span>
                  <span className="text-[11px] font-mono text-[#FF8B70]">+50% Vol</span>
                </div>
                <div className="p-2.5 rounded-xl bg-[#F7F6FC] border border-[#E6E2F0] flex items-center justify-between">
                  <span className="font-semibold text-[#191832]">4. Burn Subtitles</span>
                  <span className="text-[11px] font-mono text-[#0E6B47]">SRT Captions</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* 3. The 4-Step Production Pipeline (Phase 3 Requirement) */}
      <section className="flex flex-col gap-10 pt-8">
        <div className="text-center max-w-2xl mx-auto">
          <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-[#EFEDF8] text-[#6654F0] text-xs font-bold mb-3">
            <span>Deterministic Workflow</span>
          </div>
          <h2 className="text-3xl sm:text-4xl font-extrabold text-[#191832] tracking-tight">
            How Prompt-Based Editing Works
          </h2>
          <p className="text-sm text-[#66627B] mt-2.5 leading-relaxed">
            No complex timelines or opaque cloud credits. From your natural-language idea to a verified, exported video in four transparent steps.
          </p>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
          <div className="card p-6 flex flex-col gap-3 border border-[#E6E2F0] hover:border-[#6654F0] transition-all">
            <div className="w-10 h-10 rounded-xl bg-[#EFEDF8] border border-[#E6E2F0] flex items-center justify-center text-[#6654F0] font-extrabold text-sm">
              1
            </div>
            <h3 className="text-base font-bold text-[#191832]">Describe your edit</h3>
            <p className="text-xs text-[#66627B] leading-relaxed">
              Upload your video and type plain-English instructions. Specify cut durations, social aspect ratios, captions, or volume changes.
            </p>
          </div>

          <div className="card p-6 flex flex-col gap-3 border border-[#E6E2F0] hover:border-[#15B8C9] transition-all">
            <div className="w-10 h-10 rounded-xl bg-[#E7F9FA] border border-[#15B8C9]/30 flex items-center justify-center text-[#15B8C9] font-extrabold text-sm">
              2
            </div>
            <h3 className="text-base font-bold text-[#191832]">Review the edit plan</h3>
            <p className="text-xs text-[#66627B] leading-relaxed">
              The NLP engine compiles your request into an inspectable, structured step sequence with editable parameters and bounds checking.
            </p>
          </div>

          <div className="card p-6 flex flex-col gap-3 border border-[#E6E2F0] hover:border-[#FF8B70] transition-all">
            <div className="w-10 h-10 rounded-xl bg-[#FFF2EF] border border-[#FF8B70]/30 flex items-center justify-center text-[#FF8B70] font-extrabold text-sm">
              3
            </div>
            <h3 className="text-base font-bold text-[#191832]">Process the video</h3>
            <p className="text-xs text-[#66627B] leading-relaxed">
              Approve with one click. The backend executes genuine FFmpeg filtergraphs with millisecond trimming accuracy and audio normalization.
            </p>
          </div>

          <div className="card p-6 flex flex-col gap-3 border border-[#E6E2F0] hover:border-[#0E6B47] transition-all">
            <div className="w-10 h-10 rounded-xl bg-[#EBFBF3] border border-[#BDEFD8] flex items-center justify-center text-[#0E6B47] font-extrabold text-sm">
              4
            </div>
            <h3 className="text-base font-bold text-[#191832]">Preview and export</h3>
            <p className="text-xs text-[#66627B] leading-relaxed">
              Compare original and edited videos synchronized side-by-side, inspect cryptographic edit receipts, and download your finalized MP4.
            </p>
          </div>
        </div>
      </section>

      {/* 4. Feature Section (4 Distinct Cards - Phase 3 Requirement) */}
      <section className="flex flex-col gap-10">
        <div className="text-center max-w-2xl mx-auto">
          <h2 className="text-3xl sm:text-4xl font-extrabold text-[#191832] tracking-tight">
            Creator Capabilities
          </h2>
          <p className="text-sm text-[#66627B] mt-2.5 leading-relaxed">
            Engineered for modern video production with dependable, battle-tested media processing.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Card 1: Natural-language editing */}
          <div className="card p-7 flex flex-col gap-3.5 border border-[#E6E2F0]">
            <div className="w-11 h-11 rounded-2xl bg-[#EFEDF8] border border-[#E6E2F0] flex items-center justify-center text-[#6654F0]">
              <Scissors className="w-5 h-5" />
            </div>
            <h4 className="text-lg font-bold text-[#191832]">Natural-Language Editing</h4>
            <p className="text-sm text-[#66627B] leading-relaxed">
              Instruct the engine using conversational language like "Cut the first 3s", "Keep from 0:10 to 0:45", or "Mute audio". Fast keyframe seeking ensures instant, millisecond-accurate cuts.
            </p>
          </div>

          {/* Card 2: Smart subtitle workflow */}
          <div className="card p-7 flex flex-col gap-3.5 border border-[#E6E2F0]">
            <div className="w-11 h-11 rounded-2xl bg-[#E7F9FA] border border-[#15B8C9]/30 flex items-center justify-center text-[#15B8C9]">
              <Captions className="w-5 h-5" />
            </div>
            <h4 className="text-lg font-bold text-[#191832]">Smart Subtitle Workflow</h4>
            <p className="text-sm text-[#66627B] leading-relaxed">
              Automatically builds timestamped SRT captions with high-contrast outlines and burns them into your video so they display flawlessly on mobile devices without external subtitle files.
            </p>
          </div>

          {/* Card 3: Creator-ready aspect ratios */}
          <div className="card p-7 flex flex-col gap-3.5 border border-[#E6E2F0]">
            <div className="w-11 h-11 rounded-2xl bg-[#FFF2EF] border border-[#FF8B70]/30 flex items-center justify-center text-[#FF8B70]">
              <Smartphone className="w-5 h-5" />
            </div>
            <h4 className="text-lg font-bold text-[#191832]">Creator-Ready Aspect Ratios</h4>
            <p className="text-sm text-[#66627B] leading-relaxed">
              Convert any widescreen footage to 9:16 vertical for TikTok and Reels, 1:1 square for Instagram posts, or standard 16:9 1080p for YouTube using smart center crop and scaling filters.
            </p>
          </div>

          {/* Card 4: Transparent, editable processing plans */}
          <div className="card p-7 flex flex-col gap-3.5 border border-[#E6E2F0]">
            <div className="w-11 h-11 rounded-2xl bg-[#EBFBF3] border border-[#BDEFD8] flex items-center justify-center text-[#0E6B47]">
              <FileCheck className="w-5 h-5" />
            </div>
            <h4 className="text-lg font-bold text-[#191832]">Transparent, Editable Processing Plans</h4>
            <p className="text-sm text-[#66627B] leading-relaxed">
              Never blindly trust AI edits. ClipPilot generates an explainable plan showing every planned operation. Review, adjust values, and approve before a single frame is transcoded.
            </p>
          </div>
        </div>
      </section>

      {/* 5. Differentiators Section */}
      <section className="bg-white border border-[#E6E2F0] rounded-3xl p-8 sm:p-12 shadow-sm">
        <div className="max-w-4xl mx-auto flex flex-col gap-8 text-center">
          <div>
            <h2 className="text-2xl sm:text-3xl font-extrabold text-[#191832]">
              Why ClipPilot AI Stands Out
            </h2>
            <p className="text-sm text-[#66627B] mt-2">
              Engineered with technical rigor for the IncuBrix selection evaluation.
            </p>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-left">
            <div className="p-4 rounded-2xl bg-[#F7F6FC] border border-[#E6E2F0] flex items-start gap-3">
              <Cpu className="w-5 h-5 text-[#6654F0] shrink-0 mt-0.5" />
              <div>
                <h4 className="text-sm font-bold text-[#191832]">Real Processing, No Cloud Credits</h4>
                <p className="text-xs text-[#66627B] mt-1 leading-relaxed">
                  Processes media locally with genuine FFmpeg 9.0 executables. Zero credit burn, zero rate limits, and 100% deterministic outputs.
                </p>
              </div>
            </div>

            <div className="p-4 rounded-2xl bg-[#F7F6FC] border border-[#E6E2F0] flex items-start gap-3">
              <ShieldCheck className="w-5 h-5 text-[#0E6B47] shrink-0 mt-0.5" />
              <div>
                <h4 className="text-sm font-bold text-[#191832]">Owner-Isolated Storage</h4>
                <p className="text-xs text-[#66627B] mt-1 leading-relaxed">
                  SQLite database with strict user authorization ensures no creator can access, view, or download another user's project files.
                </p>
              </div>
            </div>

            <div className="p-4 rounded-2xl bg-[#F7F6FC] border border-[#E6E2F0] flex items-start gap-3">
              <Sparkles className="w-5 h-5 text-[#15B8C9] shrink-0 mt-0.5" />
              <div>
                <h4 className="text-sm font-bold text-[#191832]">Explainable Verification</h4>
                <p className="text-xs text-[#66627B] mt-1 leading-relaxed">
                  Never guess what will happen to your footage. The explainable plan inspector lets you adjust seconds and parameters before processing.
                </p>
              </div>
            </div>

            <div className="p-4 rounded-2xl bg-[#F7F6FC] border border-[#E6E2F0] flex items-start gap-3">
              <Zap className="w-5 h-5 text-[#FF8B70] shrink-0 mt-0.5" />
              <div>
                <h4 className="text-sm font-bold text-[#191832]">Instant 1-Click Onboarding</h4>
                <p className="text-xs text-[#66627B] mt-1 leading-relaxed">
                  Bundled synthetic test assets enable evaluators and creators to test full audio/video pipelines immediately with zero upload wait.
                </p>
              </div>
            </div>
          </div>

          <div className="pt-2 flex items-center justify-center gap-4">
            {isAuthenticated ? (
              <button
                onClick={onStartEditing}
                className="btn btn-primary text-sm py-3 px-8 font-bold rounded-xl shadow-md shadow-[#6654F0]/20"
              >
                <span>Enter ClipPilot Studio</span>
                <ArrowRight className="w-4 h-4 ml-1" />
              </button>
            ) : (
              <button
                onClick={onNavigateToSignup}
                className="btn btn-primary text-sm py-3 px-8 font-bold rounded-xl shadow-md shadow-[#6654F0]/20"
              >
                <span>Create Your Account</span>
                <ArrowRight className="w-4 h-4 ml-1" />
              </button>
            )}
          </div>
        </div>
      </section>
    </div>
  );
};
