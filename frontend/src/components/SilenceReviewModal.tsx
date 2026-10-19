import React, { useState } from 'react';
import { SilenceSegment } from '../types';
import { Radio, X, Check, Scissors, AlertCircle, CheckSquare, Square } from 'lucide-react';

interface SilenceReviewModalProps {
  isOpen: boolean;
  onClose: () => void;
  segments: SilenceSegment[];
  onConfirmCuts: (cuts: [number, number][]) => void;
}

export const SilenceReviewModal: React.FC<SilenceReviewModalProps> = ({
  isOpen,
  onClose,
  segments,
  onConfirmCuts,
}) => {
  if (!isOpen) return null;

  // Selected segments indices
  const [selectedIndices, setSelectedIndices] = useState<Set<number>>(
    new Set(segments.map((_, i) => i))
  );

  const toggleIndex = (idx: number) => {
    const next = new Set(selectedIndices);
    if (next.has(idx)) {
      next.delete(idx);
    } else {
      next.add(idx);
    }
    setSelectedIndices(next);
  };

  const selectAll = () => setSelectedIndices(new Set(segments.map((_, i) => i)));
  const deselectAll = () => setSelectedIndices(new Set());

  const totalTimeSaved = segments
    .filter((_, idx) => selectedIndices.has(idx))
    .reduce((acc, curr) => acc + curr.duration, 0);

  const handleApply = () => {
    const approvedCuts: [number, number][] = segments
      .filter((_, idx) => selectedIndices.has(idx))
      .map((s) => [s.start, s.end]);
    onConfirmCuts(approvedCuts);
    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm animate-in fade-in duration-200">
      <div className="glass-card w-full max-w-lg border-indigo-500/30 p-6 flex flex-col gap-5 shadow-2xl">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-[rgba(255,255,255,0.08)] pb-3">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-rose-500/15 border border-rose-500/30 flex items-center justify-center text-rose-400">
              <Radio className="w-4 h-4" />
            </div>
            <div>
              <h3 className="text-sm font-bold text-white">Smart Silence Review</h3>
              <p className="text-xs text-[#94A3B8]">Review candidate silent intervals before cutting</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded-lg text-[#94A3B8] hover:text-white hover:bg-[rgba(255,255,255,0.06)]"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Info banner */}
        <div className="p-3 rounded-xl bg-indigo-500/10 border border-indigo-500/20 text-xs text-indigo-200 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Scissors className="w-4 h-4 text-indigo-400" />
            <span>
              Total Silence Selected: <strong>{totalTimeSaved.toFixed(2)}s</strong>
            </span>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={selectAll}
              className="text-[11px] underline hover:text-white"
            >
              Select All
            </button>
            <span>•</span>
            <button
              onClick={deselectAll}
              className="text-[11px] underline hover:text-white"
            >
              Clear
            </button>
          </div>
        </div>

        {/* Segments List */}
        <div className="max-h-60 overflow-y-auto space-y-2 pr-1">
          {segments.length === 0 ? (
            <div className="text-center py-8 text-xs text-[#64748B]">
              No silent intervals detected under threshold (&lt; -30dB, &ge; 0.5s).
            </div>
          ) : (
            segments.map((seg, idx) => {
              const isSelected = selectedIndices.has(idx);
              return (
                <div
                  key={idx}
                  onClick={() => toggleIndex(idx)}
                  className={`p-3 rounded-xl border cursor-pointer flex items-center justify-between transition-all ${
                    isSelected
                      ? 'border-indigo-500/40 bg-indigo-500/15 text-white'
                      : 'border-[rgba(255,255,255,0.06)] bg-black/20 text-[#94A3B8] hover:border-[rgba(255,255,255,0.12)]'
                  }`}
                >
                  <div className="flex items-center gap-3">
                    {isSelected ? (
                      <CheckSquare className="w-4 h-4 text-indigo-400" />
                    ) : (
                      <Square className="w-4 h-4 text-[#64748B]" />
                    )}
                    <div className="text-xs">
                      <span className="font-semibold">Pause #{idx + 1}</span>
                      <p className="text-[11px] text-[#94A3B8]">
                        From {seg.start.toFixed(2)}s to {seg.end.toFixed(2)}s
                      </p>
                    </div>
                  </div>

                  <span className="badge badge-rose text-[10px]">
                    -{seg.duration.toFixed(2)}s
                  </span>
                </div>
              );
            })
          )}
        </div>

        {/* Action Buttons */}
        <div className="flex items-center justify-end gap-3 pt-3 border-t border-[rgba(255,255,255,0.08)]">
          <button onClick={onClose} className="btn btn-secondary text-xs py-2 px-4">
            Cancel
          </button>
          <button
            onClick={handleApply}
            className="btn btn-primary text-xs py-2 px-5 font-bold"
          >
            <Check className="w-3.5 h-3.5" />
            <span>Apply Silence Cuts</span>
          </button>
        </div>
      </div>
    </div>
  );
};
