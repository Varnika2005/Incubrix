import React from 'react';
import { EditReceipt } from '../types';
import { FileCheck, Download, X, Clock, CheckCircle2, ShieldCheck } from 'lucide-react';

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
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm animate-in fade-in duration-200">
      <div className="glass-card w-full max-w-xl border-cyan-500/30 p-6 flex flex-col gap-5 shadow-2xl">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-[rgba(255,255,255,0.08)] pb-3">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-cyan-500/15 border border-cyan-500/30 flex items-center justify-center text-cyan-400">
              <FileCheck className="w-4 h-4" />
            </div>
            <div>
              <h3 className="text-sm font-bold text-white">ClipPilot Edit Receipt</h3>
              <p className="text-xs text-[#94A3B8]">Cryptographic & Audit Log of Applied Media Transforms</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded-lg text-[#94A3B8] hover:text-white hover:bg-[rgba(255,255,255,0.06)]"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Receipt Content */}
        <div className="space-y-4 max-h-[420px] overflow-y-auto pr-1 text-xs">
          {/* Metadata Cards */}
          <div className="grid grid-cols-2 gap-3">
            <div className="p-3 rounded-xl bg-black/40 border border-[rgba(255,255,255,0.06)]">
              <span className="text-[#64748B] block mb-1">Job ID</span>
              <span className="font-mono text-white text-[11px] select-all">{receipt.job_id}</span>
            </div>
            <div className="p-3 rounded-xl bg-black/40 border border-[rgba(255,255,255,0.06)]">
              <span className="text-[#64748B] block mb-1">Processing Time</span>
              <span className="font-bold text-amber-300">{receipt.processing_time_seconds.toFixed(2)} seconds</span>
            </div>
          </div>

          {/* User Prompt */}
          <div className="p-3 rounded-xl bg-black/40 border border-[rgba(255,255,255,0.06)]">
            <span className="text-[#64748B] block mb-1">Original User Prompt</span>
            <p className="text-white italic">"{receipt.user_prompt}"</p>
          </div>

          {/* Applied Operations List */}
          <div>
            <span className="text-[#64748B] block mb-2 font-semibold uppercase tracking-wider text-[10px]">
              Verified Applied Operations ({receipt.applied_operations.length})
            </span>
            <div className="space-y-1.5">
              {receipt.applied_operations.map((op, i) => (
                <div
                  key={i}
                  className="p-2.5 rounded-lg bg-[rgba(255,255,255,0.03)] border border-[rgba(255,255,255,0.05)] flex items-center justify-between"
                >
                  <div className="flex items-center gap-2">
                    <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
                    <span className="font-semibold text-white">{op.type?.toUpperCase()}</span>
                  </div>
                  <span className="text-[#94A3B8] text-[11px]">{op.description}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Output vs Input Comparison */}
          {receipt.output_metadata && (
            <div className="p-3 rounded-xl bg-black/40 border border-[rgba(255,255,255,0.06)]">
              <span className="text-[#64748B] block mb-2 font-semibold uppercase tracking-wider text-[10px]">
                Output Transformation Specs
              </span>
              <div className="grid grid-cols-3 gap-2 text-[11px]">
                <div>
                  <span className="text-[#64748B]">Duration:</span>
                  <p className="text-white font-mono">{receipt.output_metadata.duration.toFixed(1)}s</p>
                </div>
                <div>
                  <span className="text-[#64748B]">Resolution:</span>
                  <p className="text-white font-mono">{receipt.output_metadata.width}x{receipt.output_metadata.height}</p>
                </div>
                <div>
                  <span className="text-[#64748B]">Aspect Ratio:</span>
                  <p className="text-white font-mono">{receipt.output_metadata.aspect_ratio}</p>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between pt-3 border-t border-[rgba(255,255,255,0.08)]">
          <div className="flex items-center gap-1.5 text-[#64748B] text-[11px]">
            <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
            <span>ClipPilot Engine v{receipt.app_version}</span>
          </div>

          <div className="flex items-center gap-2">
            <button onClick={onClose} className="btn btn-secondary text-xs py-2 px-3">
              Close
            </button>
            <button
              onClick={downloadJson}
              className="btn btn-accent text-xs py-2 px-4 font-bold"
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
