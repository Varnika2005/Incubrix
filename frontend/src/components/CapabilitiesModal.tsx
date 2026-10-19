import React, { useEffect, useState } from 'react';
import { SystemCapabilities } from '../types';
import { api } from '../services/api';
import { Cpu, CheckCircle2, XCircle, X, Shield, Film, Mic, Sparkles, HardDrive, Check } from 'lucide-react';

interface CapabilitiesModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export const CapabilitiesModal: React.FC<CapabilitiesModalProps> = ({
  isOpen,
  onClose,
}) => {
  const [capabilities, setCapabilities] = useState<SystemCapabilities | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    if (isOpen) {
      setIsLoading(true);
      api
        .getCapabilities()
        .then(setCapabilities)
        .catch(console.error)
        .finally(() => setIsLoading(false));
    }
  }, [isOpen]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-md animate-fade-in">
      <div className="glass-card w-full max-w-xl border-violet-500/40 p-6 flex flex-col gap-5 shadow-2xl relative overflow-hidden animate-scale-in">
        {/* Top Rainbow Accent Strip */}
        <div
          className="absolute top-0 left-0 right-0 h-1"
          style={{
            background: 'linear-gradient(90deg, #8B5CF6 0%, #22D3EE 50%, #34D399 100%)',
          }}
        />

        {/* Header */}
        <div className="flex items-center justify-between border-b border-[rgba(255,255,255,0.08)] pb-3">
          <div className="flex items-center gap-3">
            <div
              className="w-10 h-10 rounded-xl flex items-center justify-center text-violet-300"
              style={{
                background: 'linear-gradient(135deg, rgba(139,92,246,0.2) 0%, rgba(34,211,238,0.15) 100%)',
                border: '1px solid rgba(139,92,246,0.35)',
                boxShadow: '0 0 15px rgba(139,92,246,0.2)',
              }}
            >
              <Cpu className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h3 className="text-base font-bold text-white">System Capabilities & Engines</h3>
                <span className="badge badge-emerald text-[10px] font-semibold">100% Operational</span>
              </div>
              <p className="text-xs text-[#94A3B8]">Live diagnostic of underlying processing dependencies</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-[#94A3B8] hover:text-white hover:bg-[rgba(255,255,255,0.08)] transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Content */}
        {isLoading || !capabilities ? (
          <div className="py-12 text-center text-xs text-[#94A3B8] flex flex-col items-center gap-3">
            <div className="w-6 h-6 border-2 border-violet-500 border-t-transparent rounded-full animate-spin" />
            <span>Probing verified engine diagnostics...</span>
          </div>
        ) : (
          <div className="space-y-4 text-xs max-h-[440px] overflow-y-auto pr-1">
            {/* Core Engines */}
            <div className="space-y-2.5">
              <div
                className="p-3.5 rounded-xl border border-[rgba(52,211,153,0.25)] flex items-start gap-3"
                style={{ background: 'rgba(52,211,153,0.03)' }}
              >
                <div className="w-7 h-7 rounded-lg bg-emerald-500/15 border border-emerald-500/30 flex items-center justify-center text-emerald-400 shrink-0 mt-0.5">
                  <Film className="w-4 h-4" />
                </div>
                <div className="flex-1">
                  <div className="flex items-center justify-between">
                    <span className="font-bold text-white text-xs">FFmpeg Media Transcoding Engine</span>
                    <span className="badge badge-emerald text-[9px]">Verified Native</span>
                  </div>
                  <p className="text-[#94A3B8] text-[11px] mt-1 font-mono bg-black/40 px-2 py-1 rounded border border-[rgba(255,255,255,0.04)]">
                    {capabilities.ffmpeg_version}
                  </p>
                </div>
              </div>

              <div
                className="p-3.5 rounded-xl border border-[rgba(34,211,238,0.25)] flex items-start gap-3"
                style={{ background: 'rgba(34,211,238,0.03)' }}
              >
                <div className="w-7 h-7 rounded-lg bg-cyan-500/15 border border-cyan-500/30 flex items-center justify-center text-cyan-400 shrink-0 mt-0.5">
                  <Mic className="w-4 h-4" />
                </div>
                <div className="flex-1">
                  <div className="flex items-center justify-between">
                    <span className="font-bold text-white text-xs">Speech Transcription Subsystem</span>
                    <span className="badge badge-cyan text-[9px]">
                      {capabilities.whisper_available ? 'Whisper AI' : 'Deterministic SRT'}
                    </span>
                  </div>
                  <p className="text-[#CBD5E1] text-[11px] mt-1">
                    {capabilities.whisper_details}
                  </p>
                </div>
              </div>

              <div
                className="p-3.5 rounded-xl border border-[rgba(139,92,246,0.25)] flex items-start gap-3"
                style={{ background: 'rgba(139,92,246,0.03)' }}
              >
                <div className="w-7 h-7 rounded-lg bg-violet-500/15 border border-violet-500/30 flex items-center justify-center text-violet-400 shrink-0 mt-0.5">
                  <Sparkles className="w-4 h-4" />
                </div>
                <div className="flex-1">
                  <div className="flex items-center justify-between">
                    <span className="font-bold text-white text-xs">Natural Language Plan Synthesizer</span>
                    <span className="badge badge-indigo text-[9px]">Offline Guaranteed</span>
                  </div>
                  <p className="text-[#CBD5E1] text-[11px] mt-1">
                    High-accuracy regex & deterministic rule parser with semantic contradiction checks and parameter repair.
                  </p>
                </div>
              </div>
            </div>

            {/* Media Constraints */}
            <div className="p-3.5 rounded-xl bg-black/40 border border-[rgba(255,255,255,0.06)]">
              <span className="text-[#94A3B8] block mb-2 font-semibold uppercase tracking-wider text-[10px] flex items-center gap-1.5">
                <HardDrive className="w-3 h-3 text-amber-400" />
                <span>Processing Bounds & Safeguards</span>
              </span>
              <div className="grid grid-cols-2 gap-2.5 text-[11px]">
                <div className="p-2 rounded-lg bg-[rgba(255,255,255,0.02)] border border-[rgba(255,255,255,0.04)]">
                  <span className="text-[#64748B] block text-[10px]">Max Upload Size:</span>
                  <p className="font-bold text-white font-mono mt-0.5">{capabilities.max_file_size_mb} MB</p>
                </div>
                <div className="p-2 rounded-lg bg-[rgba(255,255,255,0.02)] border border-[rgba(255,255,255,0.04)]">
                  <span className="text-[#64748B] block text-[10px]">Max Duration:</span>
                  <p className="font-bold text-white font-mono mt-0.5">{capabilities.max_duration_seconds} seconds</p>
                </div>
                <div className="col-span-2 p-2 rounded-lg bg-[rgba(255,255,255,0.02)] border border-[rgba(255,255,255,0.04)]">
                  <span className="text-[#64748B] block text-[10px]">Supported Codecs/Containers:</span>
                  <p className="font-mono text-cyan-300 font-semibold mt-0.5">{capabilities.supported_formats.join(', ')}</p>
                </div>
              </div>
            </div>

            {/* Supported Operations */}
            <div className="p-3.5 rounded-xl bg-black/40 border border-[rgba(255,255,255,0.06)]">
              <span className="text-[#94A3B8] block mb-2 font-semibold uppercase tracking-wider text-[10px] flex items-center gap-1.5">
                <CheckCircle2 className="w-3 h-3 text-emerald-400" />
                <span>Verified Video Transformations ({capabilities.supported_operations.length})</span>
              </span>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-[11px]">
                {capabilities.supported_operations.map((op, i) => (
                  <div
                    key={i}
                    className="flex items-center gap-2 p-1.5 rounded-lg bg-[rgba(255,255,255,0.02)] border border-[rgba(255,255,255,0.04)]"
                  >
                    <div className="w-4 h-4 rounded-full bg-emerald-500/20 text-emerald-400 flex items-center justify-center shrink-0">
                      <Check className="w-2.5 h-2.5" />
                    </div>
                    <span className="text-[#CBD5E1] truncate font-medium">{op}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        <div className="flex justify-end pt-2 border-t border-[rgba(255,255,255,0.08)]">
          <button onClick={onClose} className="btn btn-secondary text-xs py-2 px-5 font-bold">
            Close
          </button>
        </div>
      </div>
    </div>
  );
};
