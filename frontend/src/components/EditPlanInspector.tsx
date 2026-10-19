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
  FileText,
  Zap,
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

const opColorMap: Record<string, { icon: string; bg: string; border: string; shadow: string }> = {
  trim_start:      { icon: '#A78BFA', bg: 'rgba(139,92,246,0.1)',  border: 'rgba(139,92,246,0.25)', shadow: 'rgba(139,92,246,0.08)' },
  trim_end:        { icon: '#A78BFA', bg: 'rgba(139,92,246,0.1)',  border: 'rgba(139,92,246,0.25)', shadow: 'rgba(139,92,246,0.08)' },
  time_slice:      { icon: '#C4B5FD', bg: 'rgba(167,139,250,0.1)', border: 'rgba(167,139,250,0.25)', shadow: 'rgba(167,139,250,0.08)' },
  target_duration: { icon: '#C4B5FD', bg: 'rgba(167,139,250,0.1)', border: 'rgba(167,139,250,0.25)', shadow: 'rgba(167,139,250,0.08)' },
  aspect_ratio:    { icon: '#67E8F9', bg: 'rgba(34,211,238,0.1)',  border: 'rgba(34,211,238,0.25)', shadow: 'rgba(34,211,238,0.08)' },
  resolution:      { icon: '#67E8F9', bg: 'rgba(34,211,238,0.1)',  border: 'rgba(34,211,238,0.25)', shadow: 'rgba(34,211,238,0.08)' },
  audio_volume:    { icon: '#6EE7B7', bg: 'rgba(52,211,153,0.1)',  border: 'rgba(52,211,153,0.25)', shadow: 'rgba(52,211,153,0.08)' },
  color_adjust:    { icon: '#FCD34D', bg: 'rgba(251,191,36,0.1)',  border: 'rgba(251,191,36,0.25)', shadow: 'rgba(251,191,36,0.08)' },
  silence_removal: { icon: '#F9A8D4', bg: 'rgba(236,72,153,0.1)', border: 'rgba(236,72,153,0.25)', shadow: 'rgba(236,72,153,0.08)' },
  subtitles:       { icon: '#FDBA74', bg: 'rgba(251,146,60,0.1)', border: 'rgba(251,146,60,0.25)', shadow: 'rgba(251,146,60,0.08)' },
};

const defaultColors = { icon: '#A78BFA', bg: 'rgba(139,92,246,0.1)', border: 'rgba(139,92,246,0.25)', shadow: 'rgba(139,92,246,0.08)' };

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
        return <Scissors className="w-4 h-4" />;
      case 'aspect_ratio':
      case 'resolution':
        return <Maximize2 className="w-4 h-4" />;
      case 'audio_volume':
        return <Volume2 className="w-4 h-4" />;
      case 'color_adjust':
        return <Sparkles className="w-4 h-4" />;
      case 'silence_removal':
        return <Radio className="w-4 h-4" />;
      case 'subtitles':
        return <Captions className="w-4 h-4" />;
      default:
        return <Sliders className="w-4 h-4" />;
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
    <div
      className="glass-card p-6 flex flex-col gap-5 animate-fade-in-up"
      style={{
        borderColor: 'rgba(139,92,246,0.2)',
        background: 'linear-gradient(160deg, rgba(139,92,246,0.03) 0%, var(--bg-card) 40%), var(--bg-card)',
      }}
    >
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-[rgba(255,255,255,0.06)] pb-4">
        <div>
          <div className="flex items-center gap-2.5">
            <span className="badge badge-indigo text-[10px]">Verified Plan</span>
            <h3 className="text-base font-bold text-white">Explainable Edit Plan</h3>
          </div>
          <p className="text-xs text-[#64748B] mt-1">
            Inspect and tweak interpreted operations before execution
          </p>
        </div>

        {plan.estimated_duration && (
          <div className="metadata-pill text-xs py-1.5 px-3.5 self-start sm:self-auto">
            <Clock className="w-3.5 h-3.5 text-violet-400" />
            <span>Est. Output Duration: <strong>{plan.estimated_duration.toFixed(1)}s</strong></span>
          </div>
        )}
      </div>

      {/* Warnings List */}
      {plan.warnings.length > 0 && (
        <div
          className="p-4 rounded-2xl flex flex-col gap-2 text-xs animate-fade-in-up"
          style={{
            background: 'linear-gradient(135deg, rgba(251,191,36,0.08) 0%, rgba(251,146,60,0.05) 100%)',
            border: '1px solid rgba(251,191,36,0.25)',
          }}
        >
          <div className="flex items-center gap-2 font-bold text-amber-300">
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
        <span className="text-xs font-bold text-[#64748B] uppercase tracking-wider flex items-center gap-2">
          <Zap className="w-3.5 h-3.5 text-violet-400" />
          Sequence of Operations ({plan.operations.length})
        </span>

        {plan.operations.map((op, idx) => {
          const colors = opColorMap[op.type] || defaultColors;
          return (
            <div
              key={idx}
              className="p-4 rounded-2xl flex flex-col gap-3 transition-all hover:scale-[1.005] animate-slide-in"
              style={{
                background: colors.bg,
                border: `1px solid ${colors.border}`,
                boxShadow: `0 4px 16px ${colors.shadow}`,
                animationDelay: `${idx * 60}ms`,
              }}
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div
                    className="w-8 h-8 rounded-lg flex items-center justify-center"
                    style={{
                      background: `${colors.bg}`,
                      border: `1px solid ${colors.border}`,
                      color: colors.icon,
                    }}
                  >
                    {getOpIcon(op.type)}
                  </div>
                  <div>
                    <span className="text-xs font-bold text-white">
                      Step {idx + 1}: {op.type.toUpperCase().replace('_', ' ')}
                    </span>
                    <p className="text-xs text-[#94A3B8]">{op.description}</p>
                  </div>
                </div>
              </div>

              {/* Interactive parameter adjustments */}
              <div className="pl-11 flex flex-wrap items-center gap-3 text-xs pt-1 border-t" style={{ borderColor: `${colors.border}` }}>
                {op.type === 'trim_start' && (
                  <div className="flex items-center gap-2">
                    <span className="text-[#94A3B8]">Seconds to trim:</span>
                    <input
                      type="number"
                      min="0"
                      step="0.5"
                      value={op.seconds ?? 0}
                      onChange={(e) => handleUpdateOpParam(idx, 'seconds', parseFloat(e.target.value) || 0)}
                      className="w-20 px-2.5 py-1.5 rounded-lg bg-black/40 border border-[rgba(255,255,255,0.1)] text-white text-xs focus:border-violet-500 focus:outline-none transition-colors"
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
                        className="w-16 px-2.5 py-1.5 rounded-lg bg-black/40 border border-[rgba(255,255,255,0.1)] text-white text-xs focus:border-violet-500 focus:outline-none transition-colors"
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
                        className="w-16 px-2.5 py-1.5 rounded-lg bg-black/40 border border-[rgba(255,255,255,0.1)] text-white text-xs focus:border-violet-500 focus:outline-none transition-colors"
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
                        className="px-2.5 py-1.5 rounded-lg bg-black/40 border border-[rgba(255,255,255,0.1)] text-white text-xs focus:border-cyan-500 focus:outline-none transition-colors"
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
                        className="px-2.5 py-1.5 rounded-lg bg-black/40 border border-[rgba(255,255,255,0.1)] text-white text-xs focus:border-cyan-500 focus:outline-none transition-colors"
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
                      className="w-full"
                      style={{ accentColor: '#34D399' }}
                    />
                    <span className="font-mono text-white w-12 text-right font-bold">
                      {op.mute ? 'Mute' : `${op.volume_percent ?? 100}%`}
                    </span>
                  </div>
                )}

                {op.type === 'silence_removal' && hasSilenceDetections && onOpenSilenceReview && (
                  <button
                    onClick={onOpenSilenceReview}
                    className="btn btn-secondary text-[11px] py-1.5 px-3"
                    style={{ borderColor: 'rgba(236,72,153,0.3)' }}
                  >
                    <Radio className="w-3 h-3 text-pink-400" />
                    <span>Review Detected Cuts</span>
                  </button>
                )}
              </div>
            </div>
          );
        })}
      </div>

      {/* Action Bar */}
      <div className="flex flex-col sm:flex-row items-center justify-between gap-3 pt-4 border-t border-[rgba(255,255,255,0.06)]">
        <button
          onClick={onReset}
          disabled={isProcessing}
          className="btn btn-secondary text-xs py-2 px-4 w-full sm:w-auto"
        >
          <RotateCcw className="w-3.5 h-3.5" />
          <span>Reset Plan</span>
        </button>

        <button
          onClick={onApproveAndProcess}
          disabled={isProcessing}
          className="btn text-sm py-3 px-7 w-full sm:w-auto font-bold tracking-wide"
          style={{
            background: isProcessing
              ? 'rgba(255,255,255,0.05)'
              : 'linear-gradient(135deg, #8B5CF6 0%, #EC4899 50%, #22D3EE 100%)',
            backgroundSize: '200% 200%',
            animation: isProcessing ? 'none' : 'gradient-x 4s ease infinite',
            color: '#fff',
            boxShadow: isProcessing ? 'none' : '0 6px 24px rgba(139,92,246,0.35)',
          }}
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
