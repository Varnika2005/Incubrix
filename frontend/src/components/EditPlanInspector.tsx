import React from 'react';
import { EditPlan } from '../types';
import {
  CheckCircle2,
  Scissors,
  Maximize2,
  Volume2,
  Sparkles,
  Captions,
  Radio,
  Clock,
  RotateCcw,
  Sliders,
  AlertCircle,
} from 'lucide-react';

interface EditPlanInspectorProps {
  plan: EditPlan;
  onPlanChange: (updatedPlan: EditPlan) => void;
  onApproveAndProcess: () => void;
  onOpenSilenceReview?: () => void;
  onReset: () => void;
  isProcessing: boolean;
  hasSilenceDetections: boolean;
}

export const EditPlanInspector: React.FC<EditPlanInspectorProps> = ({
  plan,
  onPlanChange,
  onApproveAndProcess,
  onOpenSilenceReview,
  onReset,
  isProcessing,
  hasSilenceDetections,
}) => {
  const getOpIcon = (type: string) => {
    switch (type) {
      case 'trim_start':
      case 'trim_end':
      case 'time_slice':
      case 'target_duration':
        return <Scissors className="w-4 h-4 text-indigo-600" />;
      case 'aspect_ratio':
      case 'resolution':
        return <Maximize2 className="w-4 h-4 text-cyan-600" />;
      case 'audio_volume':
        return <Volume2 className="w-4 h-4 text-emerald-600" />;
      case 'color_adjust':
        return <Sparkles className="w-4 h-4 text-amber-600" />;
      case 'silence_removal':
        return <Radio className="w-4 h-4 text-rose-600" />;
      case 'subtitles':
        return <Captions className="w-4 h-4 text-indigo-600" />;
      default:
        return <Sliders className="w-4 h-4 text-indigo-600" />;
    }
  };

  const handleUpdateOpParam = (index: number, key: string, value: any) => {
    const updatedOps = [...plan.operations];
    updatedOps[index] = {
      ...updatedOps[index],
      [key]: value,
    };
    onPlanChange({
      ...plan,
      operations: updatedOps,
    });
  };

  return (
    <div className="card p-6 flex flex-col gap-5 border-indigo-200 shadow-sm">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-[#F1F5F9] pb-4">
        <div>
          <div className="flex items-center gap-2">
            <span className="badge badge-indigo text-[10px]">Verified Plan</span>
            <h3 className="text-base font-bold text-[#0F172A]">Explainable Edit Plan</h3>
          </div>
          <p className="text-xs text-[#64748B] mt-0.5">
            Inspect and tweak interpreted operations before execution
          </p>
        </div>

        {plan.estimated_duration && (
          <div className="badge badge-neutral text-xs py-1 px-3 self-start sm:self-auto font-mono">
            <Clock className="w-3.5 h-3.5 text-indigo-600" />
            <span>Est. Output: <strong>{plan.estimated_duration.toFixed(1)}s</strong></span>
          </div>
        )}
      </div>

      {/* Warnings List */}
      {plan.warnings.length > 0 && (
        <div className="p-3.5 rounded-xl border border-amber-200 bg-amber-50 flex flex-col gap-1.5 text-xs text-amber-800">
          <div className="flex items-center gap-2 font-bold text-amber-900">
            <AlertCircle className="w-4 h-4 shrink-0 text-amber-600" />
            <span>Plan Considerations:</span>
          </div>
          <ul className="list-disc list-inside space-y-0.5 text-amber-800 pl-1">
            {plan.warnings.map((w, i) => (
              <li key={i}>{w}</li>
            ))}
          </ul>
        </div>
      )}

      {/* Step by Step Operations */}
      <div className="flex flex-col gap-3">
        <span className="text-xs font-bold text-[#64748B] uppercase tracking-wider">
          Sequence of Operations ({plan.operations.length})
        </span>

        {plan.operations.map((op, idx) => (
          <div
            key={idx}
            className="p-3.5 rounded-xl border border-[#E2E8F0] bg-[#F8FAFC] flex flex-col gap-2.5 transition-all hover:border-[#CBD5E1]"
          >
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2.5">
                <div className="w-7 h-7 rounded-lg bg-white border border-[#E2E8F0] flex items-center justify-center shadow-xs">
                  {getOpIcon(op.type)}
                </div>
                <div>
                  <span className="text-xs font-bold text-[#0F172A]">
                    Step {idx + 1}: {op.type.toUpperCase().replace('_', ' ')}
                  </span>
                  <p className="text-xs text-[#64748B]">{op.description}</p>
                </div>
              </div>
            </div>

            {/* Interactive parameter adjustments */}
            <div className="pl-9.5 flex flex-wrap items-center gap-3 text-xs pt-2 border-t border-[#E2E8F0]">
              {op.type === 'trim_start' && (
                <div className="flex items-center gap-2">
                  <span className="text-[#64748B]">Seconds to trim:</span>
                  <input
                    type="number"
                    min="0"
                    step="0.5"
                    value={op.seconds ?? 0}
                    onChange={(e) => handleUpdateOpParam(idx, 'seconds', parseFloat(e.target.value) || 0)}
                    className="w-20 px-2 py-1 rounded-lg bg-white border border-[#CBD5E1] text-[#0F172A] text-xs font-mono font-medium outline-none focus:border-indigo-500"
                  />
                </div>
              )}

              {op.type === 'time_slice' && (
                <div className="flex items-center gap-3">
                  <div className="flex items-center gap-1.5">
                    <span className="text-[#64748B]">Start (s):</span>
                    <input
                      type="number"
                      min="0"
                      step="0.5"
                      value={op.start_time ?? 0}
                      onChange={(e) => handleUpdateOpParam(idx, 'start_time', parseFloat(e.target.value) || 0)}
                      className="w-16 px-2 py-1 rounded-lg bg-white border border-[#CBD5E1] text-[#0F172A] text-xs font-mono font-medium outline-none focus:border-indigo-500"
                    />
                  </div>
                  <div className="flex items-center gap-1.5">
                    <span className="text-[#64748B]">End (s):</span>
                    <input
                      type="number"
                      min="0"
                      step="0.5"
                      value={op.end_time ?? 0}
                      onChange={(e) => handleUpdateOpParam(idx, 'end_time', parseFloat(e.target.value) || 0)}
                      className="w-16 px-2 py-1 rounded-lg bg-white border border-[#CBD5E1] text-[#0F172A] text-xs font-mono font-medium outline-none focus:border-indigo-500"
                    />
                  </div>
                </div>
              )}

              {op.type === 'aspect_ratio' && (
                <div className="flex items-center gap-3">
                  <div className="flex items-center gap-1.5">
                    <span className="text-[#64748B]">Ratio:</span>
                    <select
                      value={op.ratio}
                      onChange={(e) => handleUpdateOpParam(idx, 'ratio', e.target.value)}
                      className="px-2 py-1 rounded-lg bg-white border border-[#CBD5E1] text-[#0F172A] text-xs font-medium outline-none focus:border-indigo-500"
                    >
                      <option value="16:9">16:9 Landscape</option>
                      <option value="9:16">9:16 Vertical Reel</option>
                      <option value="1:1">1:1 Square</option>
                    </select>
                  </div>
                  <div className="flex items-center gap-1.5">
                    <span className="text-[#64748B]">Fit Mode:</span>
                    <select
                      value={op.mode}
                      onChange={(e) => handleUpdateOpParam(idx, 'mode', e.target.value)}
                      className="px-2 py-1 rounded-lg bg-white border border-[#CBD5E1] text-[#0F172A] text-xs font-medium outline-none focus:border-indigo-500"
                    >
                      <option value="crop">Crop (Fill Frame)</option>
                      <option value="pad">Pad (Black Bars)</option>
                    </select>
                  </div>
                </div>
              )}

              {op.type === 'audio_volume' && (
                <div className="flex items-center gap-3 w-full max-w-xs">
                  <span className="text-[#64748B]">Volume:</span>
                  <input
                    type="range"
                    min="0"
                    max="200"
                    step="10"
                    value={op.mute ? 0 : (op.volume_percent ?? 100)}
                    onChange={(e) => {
                      const val = parseFloat(e.target.value);
                      handleUpdateOpParam(idx, 'volume_percent', val);
                      handleUpdateOpParam(idx, 'mute', val === 0);
                    }}
                    className="w-full accent-indigo-600"
                  />
                  <span className="font-mono text-[#0F172A] font-semibold w-12 text-right">
                    {op.mute ? 'Mute' : `${op.volume_percent ?? 100}%`}
                  </span>
                </div>
              )}

              {op.type === 'silence_removal' && hasSilenceDetections && onOpenSilenceReview && (
                <button
                  onClick={onOpenSilenceReview}
                  className="btn btn-secondary text-[11px] py-1 px-2.5"
                >
                  <Radio className="w-3 h-3 text-rose-600" />
                  <span>Review Detected Cuts</span>
                </button>
              )}
            </div>
          </div>
        ))}
      </div>

      {/* Action Bar */}
      <div className="flex flex-col sm:flex-row items-center justify-between gap-3 pt-3 border-t border-[#F1F5F9]">
        <button
          onClick={onReset}
          disabled={isProcessing}
          className="btn btn-secondary text-xs py-2 px-3 w-full sm:w-auto"
        >
          <RotateCcw className="w-3.5 h-3.5" />
          <span>Reset Plan</span>
        </button>

        <button
          onClick={onApproveAndProcess}
          disabled={isProcessing}
          className="btn btn-primary text-sm py-2.5 px-6 w-full sm:w-auto font-bold tracking-wide shadow-md shadow-indigo-500/20"
        >
          {isProcessing ? (
            <div className="flex items-center gap-2">
              <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
              <span>Processing Media Pipeline...</span>
            </div>
          ) : (
            <>
              <CheckCircle2 className="w-4 h-4" />
              <span>Approve & Process Video</span>
            </>
          )}
        </button>
      </div>
    </div>
  );
};
