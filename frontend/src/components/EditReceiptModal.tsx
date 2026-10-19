import React from 'react';
import { EditReceipt } from '../types';
import { FileCheck, Download, X, Clock, CheckCircle2, ShieldCheck, Sparkles, Hash, Cpu } from 'lucide-react';

interface EditReceiptModalProps {
  isOpen: boolean;
  onClose: () => void;
  receipt: EditReceipt | null;
}

export const EditReceiptModal: React.FC<EditReceiptModalProps> = ({
  isOpen,
  onClose,
  receipt,
}) => {
  if (!isOpen || !receipt) return null;

  const downloadJson = () => {
    const dataStr = 'data:text/json;charset=utf-8,' + encodeURIComponent(JSON.stringify(receipt, null, 2));
    const downloadAnchor = document.createElement('a');
    downloadAnchor.setAttribute('href', dataStr);
    downloadAnchor.setAttribute('download', `clippilot_receipt_${receipt.job_id.slice(0, 8)}.json`);
    document.body.appendChild(downloadAnchor);
    downloadAnchor.click();
    downloadAnchor.remove();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-md animate-fade-in">
      <div className="glass-card w-full max-w-xl border-cyan-500/40 p-6 flex flex-col gap-5 shadow-2xl relative overflow-hidden animate-scale-in">
        {/* Top Rainbow Accent Strip */}
        <div
          className="absolute top-0 left-0 right-0 h-1"
          style={{
            background: 'linear-gradient(90deg, #22D3EE 0%, #8B5CF6 33%, #EC4899 66%, #34D399 100%)',
          }}
        />

        {/* Header */}
        <div className="flex items-center justify-between border-b border-[rgba(255,255,255,0.08)] pb-3">
          <div className="flex items-center gap-3">
            <div
              className="w-10 h-10 rounded-xl flex items-center justify-center text-cyan-300"
              style={{
                background: 'linear-gradient(135deg, rgba(34,211,238,0.2) 0%, rgba(139,92,246,0.15) 100%)',
                border: '1px solid rgba(34,211,238,0.35)',
                boxShadow: '0 0 15px rgba(34,211,238,0.2)',
              }}
            >
              <FileCheck className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h3 className="text-base font-bold text-white">ClipPilot Edit Receipt</h3>
                <span className="badge badge-cyan text-[10px] font-semibold">Verified Audit Log</span>
              </div>
              <p className="text-xs text-[#94A3B8]">Cryptographic record of applied media transformations</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-[#94A3B8] hover:text-white hover:bg-[rgba(255,255,255,0.08)] transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Receipt Content */}
        <div className="space-y-4 max-h-[440px] overflow-y-auto pr-1 text-xs">
          {/* Metadata Cards */}
          <div className="grid grid-cols-2 gap-3">
            <div
              className="p-3.5 rounded-xl border border-[rgba(34,211,238,0.2)]"
              style={{ background: 'rgba(34,211,238,0.04)' }}
            >
              <div className="flex items-center gap-1.5 text-[#67E8F9] mb-1 font-semibold text-[10px] uppercase tracking-wider">
                <Hash className="w-3 h-3" />
                <span>Job Identification</span>
              </div>
              <span className="font-mono text-white text-[11px] select-all truncate block">{receipt.job_id}</span>
            </div>
            <div
              className="p-3.5 rounded-xl border border-[rgba(251,191,36,0.2)]"
              style={{ background: 'rgba(251,191,36,0.04)' }}
            >
              <div className="flex items-center gap-1.5 text-amber-400 mb-1 font-semibold text-[10px] uppercase tracking-wider">
                <Clock className="w-3 h-3" />
                <span>Processing Latency</span>
              </div>
              <span className="font-bold text-amber-300 text-sm">
                {receipt.processing_time_seconds.toFixed(2)}s
              </span>
            </div>
          </div>

          {/* User Prompt */}
          <div
            className="p-3.5 rounded-xl border border-[rgba(139,92,246,0.2)]"
            style={{ background: 'rgba(139,92,246,0.04)' }}
          >
            <div className="flex items-center gap-1.5 text-violet-400 mb-1 font-semibold text-[10px] uppercase tracking-wider">
              <Sparkles className="w-3 h-3" />
              <span>Original Prompt Interpretation</span>
            </div>
            <p className="text-white italic text-xs leading-relaxed">"{receipt.user_prompt}"</p>
          </div>

          {/* Applied Operations List */}
          <div>
            <span className="text-[#94A3B8] block mb-2 font-semibold uppercase tracking-wider text-[10px] flex items-center justify-between">
              <span>Verified Applied Operations ({receipt.applied_operations.length})</span>
              <span className="text-emerald-400 font-mono">100% SUCCESS</span>
            </span>
            <div className="space-y-2">
              {receipt.applied_operations.map((op, i) => (
                <div
                  key={i}
                  className="p-3 rounded-xl border border-[rgba(255,255,255,0.06)] bg-[rgba(255,255,255,0.02)] flex items-center justify-between hover:border-cyan-500/30 transition-colors"
                >
                  <div className="flex items-center gap-2.5">
                    <div className="w-6 h-6 rounded-md bg-emerald-500/15 border border-emerald-500/30 flex items-center justify-center text-emerald-400 shrink-0">
                      <CheckCircle2 className="w-3.5 h-3.5" />
                    </div>
                    <span className="font-bold text-white text-xs tracking-wide">{op.type?.toUpperCase()}</span>
                  </div>
                  <span className="text-[#94A3B8] text-[11px] max-w-[65%] text-right truncate">{op.description}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Output vs Input Comparison */}
          {receipt.output_metadata && (
            <div
              className="p-3.5 rounded-xl border border-[rgba(52,211,153,0.2)]"
              style={{ background: 'rgba(52,211,153,0.03)' }}
            >
              <div className="flex items-center gap-1.5 text-emerald-400 mb-2 font-semibold uppercase tracking-wider text-[10px]">
                <Cpu className="w-3 h-3" />
                <span>Output Transformation Specifications</span>
              </div>
              <div className="grid grid-cols-3 gap-2 text-[11px]">
                <div className="p-2 rounded-lg bg-black/40 border border-[rgba(255,255,255,0.05)]">
                  <span className="text-[#64748B] block text-[10px]">Duration:</span>
                  <p className="text-white font-mono font-bold mt-0.5">{receipt.output_metadata.duration.toFixed(1)}s</p>
                </div>
                <div className="p-2 rounded-lg bg-black/40 border border-[rgba(255,255,255,0.05)]">
                  <span className="text-[#64748B] block text-[10px]">Resolution:</span>
                  <p className="text-white font-mono font-bold mt-0.5">{receipt.output_metadata.width}x{receipt.output_metadata.height}</p>
                </div>
                <div className="p-2 rounded-lg bg-black/40 border border-[rgba(255,255,255,0.05)]">
                  <span className="text-[#64748B] block text-[10px]">Aspect Ratio:</span>
                  <p className="text-white font-mono font-bold mt-0.5">{receipt.output_metadata.aspect_ratio}</p>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between pt-3 border-t border-[rgba(255,255,255,0.08)]">
          <div className="flex items-center gap-1.5 text-[#64748B] text-[11px]">
            <ShieldCheck className="w-4 h-4 text-emerald-400" />
            <span className="text-[#94A3B8]">ClipPilot Engine v{receipt.app_version}</span>
          </div>

          <div className="flex items-center gap-2">
            <button onClick={onClose} className="btn btn-secondary text-xs py-2 px-3.5">
              Close
            </button>
            <button
              onClick={downloadJson}
              className="btn btn-accent text-xs py-2 px-4 font-bold shadow-lg"
              style={{
                boxShadow: '0 4px 15px rgba(34,211,238,0.25)',
              }}
            >
              <Download className="w-3.5 h-3.5" />
              <span>Download JSON Receipt</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
