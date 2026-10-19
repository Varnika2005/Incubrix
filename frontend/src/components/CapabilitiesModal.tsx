import React, { useEffect, useState } from 'react';
import { SystemCapabilities } from '../types';
import { api } from '../services/api';
import { Cpu, CheckCircle2, X, Shield, Mic } from 'lucide-react';

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
    <div className="modal-overlay">
      <div className="modal-content p-6 flex flex-col gap-5 max-w-xl">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-[#F1F5F9] pb-3">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-indigo-50 border border-indigo-200 flex items-center justify-center text-indigo-600">
              <Cpu className="w-4 h-4" />
            </div>
            <div>
              <h3 className="text-sm font-bold text-[#0F172A]">System Capabilities & Engines</h3>
              <p className="text-xs text-[#64748B]">Live diagnostic of verified system dependencies</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-[#94A3B8] hover:text-[#0F172A] hover:bg-[#F1F5F9]"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Content */}
        {isLoading || !capabilities ? (
          <div className="py-12 text-center text-xs text-[#64748B] flex flex-col items-center gap-2">
            <div className="w-5 h-5 border-2 border-indigo-600 border-t-transparent rounded-full animate-spin" />
            <span>Probing system capabilities...</span>
          </div>
        ) : (
          <div className="space-y-4 text-xs max-h-[440px] overflow-y-auto pr-1">
            {/* Core Engines */}
            <div className="space-y-2">
              <div className="p-3.5 rounded-xl bg-[#F8FAFC] border border-[#E2E8F0] flex items-start gap-3">
                <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0 mt-0.5" />
                <div>
                  <div className="flex items-center gap-2">
                    <span className="font-bold text-[#0F172A]">FFmpeg & FFprobe Media Engine</span>
                    <span className="badge badge-emerald text-[9px]">Verified</span>
                  </div>
                  <p className="text-[#475569] text-[11px] mt-0.5 font-mono">
                    {capabilities.ffmpeg_version}
                  </p>
                </div>
              </div>

              <div className="p-3.5 rounded-xl bg-[#F8FAFC] border border-[#E2E8F0] flex items-start gap-3">
                <Mic className="w-4 h-4 text-cyan-600 shrink-0 mt-0.5" />
                <div>
                  <div className="flex items-center gap-2">
                    <span className="font-bold text-[#0F172A]">Speech & Subtitle Generator</span>
                    <span className="badge badge-cyan text-[9px]">
                      {capabilities.whisper_available ? 'Whisper AI' : 'Deterministic SRT'}
                    </span>
                  </div>
                  <p className="text-[#64748B] text-[11px] mt-0.5">
                    {capabilities.whisper_details}
                  </p>
                </div>
              </div>

              <div className="p-3.5 rounded-xl bg-[#F8FAFC] border border-[#E2E8F0] flex items-start gap-3">
                <Shield className="w-4 h-4 text-indigo-600 shrink-0 mt-0.5" />
                <div>
                  <div className="flex items-center gap-2">
                    <span className="font-bold text-[#0F172A]">Natural Language Interpretation</span>
                    <span className="badge badge-indigo text-[9px]">Offline Guaranteed</span>
                  </div>
                  <p className="text-[#64748B] text-[11px] mt-0.5">
                    High-accuracy deterministic regex/rule parser with semantic contradiction checks and prompt repair.
                  </p>
                </div>
              </div>
            </div>

            {/* Media Constraints */}
            <div className="p-3.5 rounded-xl bg-[#F8FAFC] border border-[#E2E8F0]">
              <span className="text-[#64748B] block mb-2 font-bold uppercase tracking-wider text-[10px]">
                Platform Constraints
              </span>
              <div className="grid grid-cols-2 gap-2 text-[11px]">
                <div>
                  <span className="text-[#64748B]">Max File Size:</span>
                  <p className="font-bold text-[#0F172A]">{capabilities.max_file_size_mb} MB</p>
                </div>
                <div>
                  <span className="text-[#64748B]">Max Video Length:</span>
                  <p className="font-bold text-[#0F172A]">{capabilities.max_duration_seconds} seconds</p>
                </div>
                <div className="col-span-2">
                  <span className="text-[#64748B]">Supported Formats:</span>
                  <p className="font-mono text-cyan-700 font-semibold mt-0.5">{capabilities.supported_formats.join(', ')}</p>
                </div>
              </div>
            </div>

            {/* Supported Operations */}
            <div className="p-3.5 rounded-xl bg-[#F8FAFC] border border-[#E2E8F0]">
              <span className="text-[#64748B] block mb-2 font-bold uppercase tracking-wider text-[10px]">
                Implemented Video Transformations
              </span>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-1.5 text-[11px] text-[#334155]">
                {capabilities.supported_operations.map((op, i) => (
                  <div key={i} className="flex items-center gap-1.5">
                    <span className="w-1.5 h-1.5 rounded-full bg-indigo-500" />
                    <span>{op}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        <div className="flex justify-end pt-2 border-t border-[#F1F5F9]">
          <button onClick={onClose} className="btn btn-secondary text-xs py-2 px-5">
            Close
          </button>
        </div>
      </div>
    </div>
  );
};
