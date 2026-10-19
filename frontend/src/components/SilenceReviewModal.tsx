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
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 modal-overlay">
      <div
        className="glass-card w-full max-w-lg p-6 flex flex-col gap-5 shadow-2xl animate-fade-in-up"
        style={{
          borderColor: 'rgba(236,72,153,0.25)',
          background: 'linear-gradient(160deg, rgba(236,72,153,0.04) 0%, var(--bg-card) 30%), var(--bg-card)',
          boxShadow: '0 25px 80px -15px rgba(236,72,153,0.2), 0 10px 40px -10px rgba(0,0,0,0.6)',
        }}
      >
        {/* Header */}
        <div className="flex items-center justify-between border-b border-[rgba(255,255,255,0.06)] pb-3">
          <div className="flex items-center gap-2.5">
            <div
              className="w-9 h-9 rounded-xl flex items-center justify-center"
              style={{
                background: 'linear-gradient(135deg, rgba(236,72,153,0.2), rgba(251,113,133,0.1))',
                border: '1.5px solid rgba(236,72,153,0.35)',
                boxShadow: '0 0 15px rgba(236,72,153,0.12)',
              }}
            >
              <Radio className="w-4 h-4 text-pink-400" />
            </div>
            <div>
              <h3 className="text-sm font-bold text-white">Smart Silence Review</h3>
              <p className="text-xs text-[#64748B]">Review candidate silent intervals before cutting</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-[#94A3B8] hover:text-white hover:bg-[rgba(255,255,255,0.06)] transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Info banner */}
        <div
          className="p-3.5 rounded-2xl text-xs flex items-center justify-between"
          style={{
            background: 'linear-gradient(135deg, rgba(139,92,246,0.08), rgba(236,72,153,0.05))',
            border: '1px solid rgba(139,92,246,0.2)',
            color: '#C4B5FD',
          }}
        >
          <div className="flex items-center gap-2">
            <Scissors className="w-4 h-4 text-violet-400" />
            <span>
              Total Silence Selected: <strong>{totalTimeSaved.toFixed(2)}s</strong>
            </span>
          </div>
          <div className="flex items-center gap-2">
            <button onClick={selectAll} className="text-[11px] underline hover:text-white transition-colors">
              Select All
            </button>
            <span style={{ color: 'rgba(139,92,246,0.4)' }}>•</span>
            <button onClick={deselectAll} className="text-[11px] underline hover:text-white transition-colors">
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
                  className="p-3.5 rounded-xl border cursor-pointer flex items-center justify-between transition-all"
                  style={{
                    borderColor: isSelected ? 'rgba(139,92,246,0.35)' : 'rgba(255,255,255,0.06)',
                    background: isSelected
                      ? 'linear-gradient(135deg, rgba(139,92,246,0.12), rgba(236,72,153,0.06))'
                      : 'rgba(0,0,0,0.2)',
                    color: isSelected ? '#fff' : '#94A3B8',
                  }}
                >
                  <div className="flex items-center gap-3">
                    {isSelected ? (
                      <CheckSquare className="w-4 h-4 text-violet-400" />
                    ) : (
                      <Square className="w-4 h-4 text-[#64748B]" />
                    )}
                    <div className="text-xs">
                      <span className="font-bold">Pause #{idx + 1}</span>
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
        <div className="flex items-center justify-end gap-3 pt-3 border-t border-[rgba(255,255,255,0.06)]">
          <button onClick={onClose} className="btn btn-secondary text-xs py-2 px-4">
            Cancel
          </button>
          <button
            onClick={handleApply}
            className="btn text-xs py-2 px-5 font-bold"
            style={{
              background: 'linear-gradient(135deg, #EC4899 0%, #8B5CF6 100%)',
              color: '#fff',
              boxShadow: '0 4px 16px rgba(236,72,153,0.3)',
            }}
          >
            <Check className="w-3.5 h-3.5" />
            <span>Apply Silence Cuts</span>
          </button>
        </div>
      </div>
    </div>
  );
};
