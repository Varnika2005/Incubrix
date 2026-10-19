import React, { useEffect, useState } from 'react';
import { SystemCapabilities } from '../types';
import { api } from '../services/api';
import { Cpu, CheckCircle2, XCircle, X, Shield, Film, Mic } from 'lucide-react';

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
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-sm animate-in fade-in duration-200">
      <div className="glass-card w-full max-w-xl border-indigo-500/30 p-6 flex flex-col gap-5 shadow-2xl">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-[rgba(255,255,255,0.08)] pb-3">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-indigo-500/15 border border-indigo-500/30 flex items-center justify-center text-indigo-400">
              <Cpu className="w-4 h-4" />
            </div>
            <div>
              <h3 className="text-sm font-bold text-white">System Capabilities & Engines</h3>
              <p className="text-xs text-[#94A3B8]">Live diagnostic of verified system dependencies</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded-lg text-[#94A3B8] hover:text-white hover:bg-[rgba(255,255,255,0.06)]"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Content */}
        {isLoading || !capabilities ? (
          <div className="py-12 text-center text-xs text-[#94A3B8]">
            Probing system capabilities...
          </div>
        ) : (
          <div className="space-y-4 text-xs max-h-[420px] overflow-y-auto pr-1">
            {/* Core Engines */}
            <div className="space-y-2">
              <div className="p-3.5 rounded-xl bg-black/40 border border-[rgba(255,255,255,0.06)] flex items-start gap-3">
                <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
                <div>
                  <div className="flex items-center gap-2">
                    <span className="font-bold text-white">FFmpeg & FFprobe Media Engine</span>
                    <span className="badge badge-emerald text-[9px]">Verified</span>
                  </div>
                  <p className="text-[#94A3B8] text-[11px] mt-0.5 font-mono">
                    {capabilities.ffmpeg_version}
                  </p>
                </div>
              </div>

              <div className="p-3.5 rounded-xl bg-black/40 border border-[rgba(255,255,255,0.06)] flex items-start gap-3">
                <Mic className="w-4 h-4 text-cyan-400 shrink-0 mt-0.5" />
                <div>
                  <div className="flex items-center gap-2">
                    <span className="font-bold text-white">Speech Transcription Engine</span>
                    <span className="badge badge-cyan text-[9px]">
                      {capabilities.whisper_available ? 'Whisper AI' : 'Deterministic SRT'}
                    </span>
                  </div>
                  <p className="text-[#94A3B8] text-[11px] mt-0.5">
                    {capabilities.whisper_details}
                  </p>
                </div>
              </div>

              <div className="p-3.5 rounded-xl bg-black/40 border border-[rgba(255,255,255,0.06)] flex items-start gap-3">
                <Shield className="w-4 h-4 text-indigo-400 shrink-0 mt-0.5" />
                <div>
                  <div className="flex items-center gap-2">
                    <span className="font-bold text-white">Natural Language Interpretation</span>
                    <span className="badge badge-indigo text-[9px]">Offline Guaranteed</span>
                  </div>
                  <p className="text-[#94A3B8] text-[11px] mt-0.5">
                    High-accuracy deterministic regex/rule parser with semantic contradiction checks and prompt repair.
                  </p>
                </div>
              </div>
            </div>

            {/* Media Constraints */}
            <div className="p-3.5 rounded-xl bg-black/40 border border-[rgba(255,255,255,0.06)]">
              <span className="text-[#64748B] block mb-2 font-semibold uppercase tracking-wider text-[10px]">
                Platform Constraints
              </span>
              <div className="grid grid-cols-2 gap-2 text-[11px]">
                <div>
                  <span className="text-[#94A3B8]">Max File Size:</span>
                  <p className="font-semibold text-white">{capabilities.max_file_size_mb} MB</p>
                </div>
                <div>
                  <span className="text-[#94A3B8]">Max Video Length:</span>
                  <p className="font-semibold text-white">{capabilities.max_duration_seconds} seconds</p>
                </div>
                <div className="col-span-2">
                  <span className="text-[#94A3B8]">Supported Formats:</span>
                  <p className="font-mono text-cyan-300 mt-0.5">{capabilities.supported_formats.join(', ')}</p>
                </div>
              </div>
            </div>

            {/* Supported Operations */}
            <div className="p-3.5 rounded-xl bg-black/40 border border-[rgba(255,255,255,0.06)]">
              <span className="text-[#64748B] block mb-2 font-semibold uppercase tracking-wider text-[10px]">
                Implemented Video Transformations
              </span>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-1.5 text-[11px] text-[#CBD5E1]">
                {capabilities.supported_operations.map((op, i) => (
                  <div key={i} className="flex items-center gap-1.5">
                    <span className="w-1.5 h-1.5 rounded-full bg-indigo-400" />
                    <span>{op}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        <div className="flex justify-end pt-2 border-t border-[rgba(255,255,255,0.08)]">
          <button onClick={onClose} className="btn btn-secondary text-xs py-2 px-5">
            Close
          </button>
        </div>
      </div>
    </div>
  );
};
