import React, { useState } from 'react';
import { SilenceSegment } from '../types';
import { Radio, X, Check, Scissors, CheckSquare, Square } from 'lucide-react';

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
    <div className="modal-overlay">
      <div className="modal-content p-6 flex flex-col gap-5 max-w-lg">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-[#F1F5F9] pb-3">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-rose-50 border border-rose-200 flex items-center justify-center text-rose-600">
              <Radio className="w-4 h-4" />
            </div>
            <div>
              <h3 className="text-sm font-bold text-[#0F172A]">Smart Silence Review</h3>
              <p className="text-xs text-[#64748B]">Review candidate silent intervals before cutting</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-[#94A3B8] hover:text-[#0F172A] hover:bg-[#F1F5F9]"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Info banner */}
        <div className="p-3 rounded-xl bg-indigo-50 border border-indigo-200 text-xs text-indigo-900 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Scissors className="w-4 h-4 text-indigo-600" />
            <span>
              Total Silence Selected: <strong>{totalTimeSaved.toFixed(2)}s</strong>
            </span>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={selectAll}
              className="text-[11px] underline font-semibold text-indigo-700 hover:text-indigo-900"
            >
              Select All
            </button>
            <span>•</span>
            <button
              onClick={deselectAll}
              className="text-[11px] underline font-semibold text-indigo-700 hover:text-indigo-900"
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
                      ? 'border-indigo-300 bg-indigo-50/60 text-[#0F172A]'
                      : 'border-[#E2E8F0] bg-white text-[#64748B] hover:border-[#CBD5E1]'
                  }`}
                >
                  <div className="flex items-center gap-3">
                    {isSelected ? (
                      <CheckSquare className="w-4 h-4 text-indigo-600" />
                    ) : (
                      <Square className="w-4 h-4 text-[#94A3B8]" />
                    )}
                    <div className="text-xs">
                      <span className="font-bold text-[#0F172A]">Pause #{idx + 1}</span>
                      <p className="text-[11px] text-[#64748B]">
                        From {seg.start.toFixed(2)}s to {seg.end.toFixed(2)}s
                      </p>
                    </div>
                  </div>

                  <span className="badge badge-coral text-[10px]">
                    -{seg.duration.toFixed(2)}s
                  </span>
                </div>
              );
            })
          )}
        </div>

        {/* Action Buttons */}
        <div className="flex items-center justify-end gap-3 pt-3 border-t border-[#F1F5F9]">
          <button onClick={onClose} className="btn btn-secondary text-xs py-2 px-4">
            Cancel
          </button>
          <button
            onClick={handleApply}
            className="btn btn-primary text-xs py-2 px-5 font-bold shadow-sm"
          >
            <Check className="w-3.5 h-3.5" />
            <span>Apply Silence Cuts</span>
          </button>
        </div>
      </div>
    </div>
  );
};
