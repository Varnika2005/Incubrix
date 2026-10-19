import React from 'react';
import { EditPlan, EditOperation } from '../types';
import {
  CheckCircle2,
  Scissors,
  Maximize2,
  Volume2,
  Sparkles,
  Captions,
  Radio,
  Clock,
  Play,
  RotateCcw,
  Sliders,
  AlertCircle,
  FileText
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
        return <Scissors className="w-4 h-4 text-indigo-400" />;
      case 'aspect_ratio':
      case 'resolution':
        return <Maximize2 className="w-4 h-4 text-cyan-400" />;
      case 'audio_volume':
        return <Volume2 className="w-4 h-4 text-emerald-400" />;
      case 'color_adjust':
        return <Sparkles className="w-4 h-4 text-amber-400" />;
      case 'silence_removal':
        return <Radio className="w-4 h-4 text-rose-400" />;
      case 'subtitles':
        return <Captions className="w-4 h-4 text-purple-400" />;
      default:
        return <Sliders className="w-4 h-4 text-indigo-400" />;
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
    <div className="glass-card p-5 flex flex-col gap-5 border-indigo-500/25">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-[rgba(255,255,255,0.06)] pb-4">
        <div>
          <div className="flex items-center gap-2">
            <span className="badge badge-indigo text-[10px]">Verified Plan</span>
            <h3 className="text-base font-semibold text-white">Explainable Edit Plan</h3>
          </div>
          <p className="text-xs text-[#94A3B8] mt-0.5">
            Inspect and tweak interpreted operations before execution
          </p>
        </div>

        {plan.estimated_duration && (
          <div className="metadata-pill text-xs py-1 px-3 self-start sm:self-auto">
            <Clock className="w-3.5 h-3.5 text-indigo-400" />
            <span>Est. Output Duration: <strong>{plan.estimated_duration.toFixed(1)}s</strong></span>
          </div>
        )}
      </div>

      {/* Warnings List */}
      {plan.warnings.length > 0 && (
        <div className="p-3.5 rounded-xl border border-amber-500/30 bg-amber-500/10 flex flex-col gap-1.5 text-xs">
          <div className="flex items-center gap-2 font-semibold text-amber-300">
            <AlertCircle className="w-4 h-4 shrink-0" />
            <span>Plan Considerations:</span>
          </div>
          <ul className="list-disc list-inside space-y-0.5 text-amber-200/90 pl-1">
            {plan.warnings.map((w, i) => (
              <li key={i}>{w}</li>
            ))}
          </ul>
        </div>
      )}

      {/* Step by Step Operations */}
      <div className="flex flex-col gap-3">
        <span className="text-xs font-semibold text-[#94A3B8] uppercase tracking-wider">
          Sequence of Operations ({plan.operations.length})
        </span>

        {plan.operations.map((op, idx) => (
          <div
            key={idx}
            className="p-3.5 rounded-xl border border-[rgba(255,255,255,0.06)] bg-[rgba(10,14,24,0.5)] flex flex-col gap-2.5 transition-all hover:border-[rgba(255,255,255,0.12)]"
          >
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2.5">
                <div className="w-7 h-7 rounded-lg bg-[rgba(255,255,255,0.05)] flex items-center justify-center">
                  {getOpIcon(op.type)}
                </div>
                <div>
                  <span className="text-xs font-semibold text-white">
                    Step {idx + 1}: {op.type.toUpperCase().replace('_', ' ')}
                  </span>
                  <p className="text-xs text-[#94A3B8]">{op.description}</p>
                </div>
              </div>
            </div>

            {/* Interactive parameter adjustments */}
            <div className="pl-9.5 flex flex-wrap items-center gap-3 text-xs pt-1 border-t border-[rgba(255,255,255,0.04)]">
              {op.type === 'trim_start' && (
                <div className="flex items-center gap-2">
                  <span className="text-[#94A3B8]">Seconds to trim:</span>
                  <input
                    type="number"
                    min="0"
                    step="0.5"
                    value={op.seconds ?? 0}
                    onChange={(e) => handleUpdateOpParam(idx, 'seconds', parseFloat(e.target.value) || 0)}
                    className="w-20 px-2 py-1 rounded bg-black/40 border border-[rgba(255,255,255,0.1)] text-white text-xs"
                  />
                </div>
              )}

              {op.type === 'time_slice' && (
                <div className="flex items-center gap-3">
                  <div className="flex items-center gap-1.5">
                    <span className="text-[#94A3B8]">Start (s):</span>
                    <input
                      type="number"
                      min="0"
                      step="0.5"
                      value={op.start_time ?? 0}
                      onChange={(e) => handleUpdateOpParam(idx, 'start_time', parseFloat(e.target.value) || 0)}
                      className="w-16 px-2 py-1 rounded bg-black/40 border border-[rgba(255,255,255,0.1)] text-white text-xs"
                    />
                  </div>
                  <div className="flex items-center gap-1.5">
                    <span className="text-[#94A3B8]">End (s):</span>
                    <input
                      type="number"
                      min="0"
                      step="0.5"
                      value={op.end_time ?? 0}
                      onChange={(e) => handleUpdateOpParam(idx, 'end_time', parseFloat(e.target.value) || 0)}
                      className="w-16 px-2 py-1 rounded bg-black/40 border border-[rgba(255,255,255,0.1)] text-white text-xs"
                    />
                  </div>
                </div>
              )}

              {op.type === 'aspect_ratio' && (
                <div className="flex items-center gap-3">
                  <div className="flex items-center gap-1.5">
                    <span className="text-[#94A3B8]">Ratio:</span>
                    <select
                      value={op.ratio}
                      onChange={(e) => handleUpdateOpParam(idx, 'ratio', e.target.value)}
                      className="px-2 py-1 rounded bg-black/40 border border-[rgba(255,255,255,0.1)] text-white text-xs"
                    >
                      <option value="16:9">16:9 Landscape</option>
                      <option value="9:16">9:16 Vertical Reel</option>
                      <option value="1:1">1:1 Square</option>
                    </select>
                  </div>
                  <div className="flex items-center gap-1.5">
                    <span className="text-[#94A3B8]">Fit Mode:</span>
                    <select
                      value={op.mode}
                      onChange={(e) => handleUpdateOpParam(idx, 'mode', e.target.value)}
                      className="px-2 py-1 rounded bg-black/40 border border-[rgba(255,255,255,0.1)] text-white text-xs"
                    >
                      <option value="crop">Crop (Fill Frame)</option>
                      <option value="pad">Pad (Black Bars)</option>
                    </select>
                  </div>
                </div>
              )}

              {op.type === 'audio_volume' && (
                <div className="flex items-center gap-3 w-full max-w-xs">
                  <span className="text-[#94A3B8]">Volume:</span>
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
                    className="w-full accent-indigo-500"
                  />
                  <span className="font-mono text-white w-12 text-right">
                    {op.mute ? 'Mute' : `${op.volume_percent ?? 100}%`}
                  </span>
                </div>
              )}

              {op.type === 'silence_removal' && hasSilenceDetections && onOpenSilenceReview && (
                <button
                  onClick={onOpenSilenceReview}
                  className="btn btn-secondary text-[11px] py-1 px-2.5"
                >
                  <Radio className="w-3 h-3 text-rose-400" />
                  <span>Review Detected Cuts</span>
                </button>
              )}
            </div>
          </div>
        ))}
      </div>

      {/* Action Bar */}
      <div className="flex flex-col sm:flex-row items-center justify-between gap-3 pt-3 border-t border-[rgba(255,255,255,0.06)]">
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
          className="btn btn-primary text-sm py-2.5 px-6 w-full sm:w-auto font-bold tracking-wide"
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
