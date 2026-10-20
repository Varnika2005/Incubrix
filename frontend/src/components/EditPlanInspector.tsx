import React, { useState, useEffect } from 'react';
import { EditPlan, TransformedTimelineEffect, InstructionOutcome, InstructionStatus } from '../types';
import { api } from '../services/api';
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
  Undo2,
  Redo2,
  ShieldCheck,
  Trash2,
  Gauge,
  ArrowUpDown,
  VolumeX,
  Layers,
  Wand2,
  Bell,
  Calculator,
  Tag,
  HelpCircle,
  XCircle,
  Send,
  Terminal,
  History,
  AlertTriangle,
  CornerDownRight,
} from 'lucide-react';

interface EditPlanInspectorProps {
  plan: EditPlan;
  jobId?: string;
  onPlanChange: (updatedPlan: EditPlan) => void;
  onApproveAndProcess: () => void;
  onOpenSilenceReview?: () => void;
  onReset: () => void;
  isProcessing: boolean;
  hasSilenceDetections: boolean;
  originalHash?: string | null;
  onUndo?: () => void;
  onRedo?: () => void;
  canUndo?: boolean;
  canRedo?: boolean;
}

export const EditPlanInspector: React.FC<EditPlanInspectorProps> = ({
  plan,
  jobId,
  onPlanChange,
  onApproveAndProcess,
  onOpenSilenceReview,
  onReset,
  isProcessing,
  hasSilenceDetections,
  originalHash,
  onUndo,
  onRedo,
  canUndo = false,
  canRedo = false,
}) => {
  const [testSourceTime, setTestSourceTime] = useState<number>(1.0);
  const [testTimelineTime, setTestTimelineTime] = useState<number>(1.0);
  const [showCoordinateMapper, setShowCoordinateMapper] = useState<boolean>(false);

  // Must-have 3: Strict 3-Way Instruction Processing State
  const [instructionInput, setInstructionInput] = useState<string>('');
  const [isExecutingInstruction, setIsExecutingInstruction] = useState<boolean>(false);
  const [simulateMidwayFailure, setSimulateMidwayFailure] = useState<boolean>(false);
  const [latestOutcome, setLatestOutcome] = useState<InstructionOutcome | null>(null);
  const [instructionError, setInstructionError] = useState<string | null>(null);
  const [instructionHistory, setInstructionHistory] = useState<InstructionOutcome[]>(() => {
    return (plan.instruction_outcomes as InstructionOutcome[]) || [];
  });
  const [showHistoryAudit, setShowHistoryAudit] = useState<boolean>(true);

  // Sync instruction history when plan updates
  useEffect(() => {
    if (plan.instruction_outcomes && plan.instruction_outcomes.length > 0) {
      setInstructionHistory((prev) => {
        const existingIds = new Set(prev.map((p) => p.operationId));
        const newItems = (plan.instruction_outcomes as InstructionOutcome[]).filter(
          (item) => !existingIds.has(item.operationId)
        );
        return [...newItems, ...prev];
      });
    }
  }, [plan.instruction_outcomes]);

  const handleExecuteInstruction = async (textToExecute?: string) => {
    const text = (textToExecute !== undefined ? textToExecute : instructionInput).trim();
    if (!text) return;
    if (!jobId) {
      setInstructionError('No active job ID found. Upload or select a video first.');
      return;
    }
    setIsExecutingInstruction(true);
    setInstructionError(null);
    try {
      const outcome = await api.processInstruction(jobId, text, undefined, simulateMidwayFailure);
      setLatestOutcome(outcome);
      setInstructionHistory((prev) => [outcome, ...prev]);

      if (outcome.status === 'APPLIED') {
        const freshJob = await api.getJob(jobId);
        if (freshJob.edit_plan) {
          onPlanChange(freshJob.edit_plan);
        }
      }
    } catch (err: any) {
      setInstructionError(err.message || 'Instruction execution failed');
    } finally {
      setIsExecutingInstruction(false);
    }
  };

  const getOpIcon = (type: string) => {
    switch (type) {
      case 'trim_start':
      case 'trim_end':
      case 'time_slice':
      case 'target_duration':
      case 'cut':
        return <Scissors className="w-4 h-4 text-indigo-600" />;
      case 'speed':
        return <Gauge className="w-4 h-4 text-amber-600" />;
      case 'reorder':
        return <ArrowUpDown className="w-4 h-4 text-blue-600" />;
      case 'aspect_ratio':
      case 'resolution':
        return <Maximize2 className="w-4 h-4 text-cyan-600" />;
      case 'audio_volume':
        return <Volume2 className="w-4 h-4 text-emerald-600" />;
      case 'mute_range':
        return <VolumeX className="w-4 h-4 text-rose-600" />;
      case 'beep':
        return <Bell className="w-4 h-4 text-amber-600" />;
      case 'visual_effect':
        return <Wand2 className="w-4 h-4 text-purple-600" />;
      case 'color_adjust':
        return <Sparkles className="w-4 h-4 text-amber-600" />;
      case 'silence_removal':
        return <Radio className="w-4 h-4 text-rose-600" />;
      case 'subtitles':
      case 'caption':
        return <Captions className="w-4 h-4 text-indigo-600" />;
      case 'timeline':
        return <Layers className="w-4 h-4 text-indigo-600" />;
      default:
        return <Sliders className="w-4 h-4 text-indigo-600" />;
    }
  };

  // Deterministic client-side coordinate mapping helper
  const mapSourceToTimeline = (sourceTime: number) => {
    if (!plan.timeline || !plan.timeline.segments || plan.timeline.segments.length === 0) {
      return { found: true, timelineTime: sourceTime, segmentId: 'default', speed: 1.0 };
    }
    for (const seg of plan.timeline.segments) {
      if (sourceTime >= seg.source_start - 0.0001 && sourceTime <= seg.source_end + 0.0001) {
        const offsetInSeg = (sourceTime - seg.source_start) / seg.speed;
        return {
          found: true,
          timelineTime: seg.timeline_start + offsetInSeg,
          segmentId: seg.clip_id,
          speed: seg.speed,
        };
      }
    }
    return { found: false, timelineTime: null, segmentId: null, speed: 1.0 };
  };

  const mapTimelineToSource = (timelineTime: number) => {
    if (!plan.timeline || !plan.timeline.segments || plan.timeline.segments.length === 0) {
      return { found: true, sourceTime: timelineTime, segmentId: 'default', speed: 1.0 };
    }
    for (const seg of plan.timeline.segments) {
      if (timelineTime >= seg.timeline_start - 0.0001 && timelineTime <= seg.timeline_end + 0.0001) {
        const offsetInSeg = (timelineTime - seg.timeline_start) * seg.speed;
        return {
          found: true,
          sourceTime: seg.source_start + offsetInSeg,
          segmentId: seg.clip_id,
          speed: seg.speed,
        };
      }
    }
    return { found: false, sourceTime: null, segmentId: null, speed: 1.0 };
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

  const handleRemoveOp = (index: number) => {
    const updatedOps = plan.operations.filter((_, i) => i !== index);
    onPlanChange({
      ...plan,
      operations: updatedOps,
    });
  };

  return (
    <div className="card p-6 flex flex-col gap-5 border-indigo-200 shadow-sm">
      {/* Header with Undo / Redo & Est Duration */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-[#F1F5F9] pb-4">
        <div>
          <div className="flex items-center gap-2">
            <span className="badge badge-indigo text-[10px]">Verified EDL</span>
            <h3 className="text-base font-bold text-[#0F172A]">Explainable Edit Plan</h3>
          </div>
          <p className="text-xs text-[#64748B] mt-0.5">
            Non-destructive timeline operations applied over immutable source video
          </p>
        </div>

        <div className="flex items-center gap-2">
          {/* Undo / Redo Controls */}
          <div className="flex items-center gap-1 bg-slate-100 border border-slate-200 rounded-lg p-1">
            <button
              onClick={onUndo}
              disabled={!canUndo || isProcessing}
              className="px-2.5 py-1 rounded flex items-center gap-1.5 text-xs font-bold text-slate-700 hover:text-slate-900 hover:bg-white disabled:opacity-35 disabled:hover:bg-transparent disabled:cursor-not-allowed transition-all shadow-xs"
              title="Undo last edit (Ctrl+Z)"
            >
              <Undo2 className="w-3.5 h-3.5 text-indigo-600" />
              <span>Undo</span>
            </button>
            <button
              onClick={onRedo}
              disabled={!canRedo || isProcessing}
              className="px-2.5 py-1 rounded flex items-center gap-1.5 text-xs font-bold text-slate-700 hover:text-slate-900 hover:bg-white disabled:opacity-35 disabled:hover:bg-transparent disabled:cursor-not-allowed transition-all shadow-xs"
              title="Redo edit (Ctrl+Y)"
            >
              <Redo2 className="w-3.5 h-3.5 text-indigo-600" />
              <span>Redo</span>
            </button>
          </div>

          {plan.estimated_duration && (
            <div className="badge badge-neutral text-xs py-1 px-3 font-mono">
              <Clock className="w-3.5 h-3.5 text-indigo-600" />
              <span>Est. Output: <strong>{plan.estimated_duration.toFixed(1)}s</strong></span>
            </div>
          )}
        </div>
      </div>

      {/* Non-Destructive Source Guarantee Banner */}
      <div className="p-3 bg-indigo-50/70 border border-indigo-200 rounded-xl flex flex-col sm:flex-row sm:items-center justify-between gap-2.5 text-xs text-indigo-950">
        <div className="flex items-center gap-2">
          <ShieldCheck className="w-4 h-4 text-indigo-600 shrink-0" />
          <span>
            <strong>Non-Destructive Editing:</strong> Source video is immutable and never overwritten.
          </span>
        </div>
        {originalHash && (
          <div className="flex items-center gap-1.5 self-start sm:self-auto font-mono text-[10px] text-indigo-700 bg-white/90 px-2 py-0.5 rounded border border-indigo-200" title={`Verified Source SHA-256: ${originalHash}`}>
            <span className="font-sans font-medium text-slate-500">SHA-256:</span>
            <span>{originalHash.slice(0, 10)}…{originalHash.slice(-6)}</span>
          </div>
        )}
      </div>

      {/* Warnings List */}
      {plan.warnings && plan.warnings.length > 0 && (
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

      {/* Must-have 3: Strict Three-Way Response Instruction Processor */}
      <div className="rounded-xl border border-indigo-200 bg-gradient-to-br from-indigo-50/40 via-white to-slate-50 p-4 space-y-4 shadow-xs">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-indigo-100 pb-3">
          <div>
            <div className="flex items-center gap-2">
              <span className="badge badge-indigo text-[10px] font-bold">Must-have 3 Protocol</span>
              <h4 className="text-sm font-bold text-slate-900 flex items-center gap-1.5">
                <Terminal className="w-4 h-4 text-indigo-600" />
                <span>Strict Three-Way Instruction Processor</span>
              </h4>
            </div>
            <p className="text-[11px] text-slate-600 mt-0.5">
              Every editing command receives exactly one outcome:{' '}
              <span className="font-semibold text-emerald-700">APPLIED</span>,{' '}
              <span className="font-semibold text-amber-700">NEEDS_CLARIFICATION</span>, or{' '}
              <span className="font-semibold text-rose-700">REJECTED</span>.
              Real application code validates & executes with midway rollback protection.
            </p>
          </div>

          <div className="flex items-center gap-2">
            <label className="flex items-center gap-1.5 cursor-pointer text-[11px] text-slate-600 hover:text-slate-900 select-none bg-white px-2.5 py-1 rounded-lg border border-slate-200 shadow-2xs">
              <input
                type="checkbox"
                checked={simulateMidwayFailure}
                onChange={(e) => setSimulateMidwayFailure(e.target.checked)}
                className="rounded border-slate-300 text-rose-600 focus:ring-rose-500 w-3.5 h-3.5"
              />
              <span className="font-medium text-rose-700">Simulate Failure (Test Rollback)</span>
            </label>
          </div>
        </div>

        {/* Quick Test Preset Buttons */}
        <div className="space-y-1.5">
          <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider block">
            Click to Test Protocol Outcomes:
          </span>
          <div className="flex flex-wrap gap-1.5 text-xs">
            <button
              type="button"
              onClick={() => {
                setInstructionInput('Mute the video from 00:02 to 00:05');
                handleExecuteInstruction('Mute the video from 00:02 to 00:05');
              }}
              disabled={isExecutingInstruction || isProcessing}
              className="text-[11px] px-2.5 py-1 rounded-md bg-emerald-50 text-emerald-800 border border-emerald-200 hover:bg-emerald-100 transition-colors font-medium flex items-center gap-1"
            >
              <CheckCircle2 className="w-3 h-3 text-emerald-600" />
              <span>[APPLIED] Mute 2s to 5s</span>
            </button>

            <button
              type="button"
              onClick={() => {
                setInstructionInput("Add caption 'Welcome to ClipPilot' from 1s to 4s");
                handleExecuteInstruction("Add caption 'Welcome to ClipPilot' from 1s to 4s");
              }}
              disabled={isExecutingInstruction || isProcessing}
              className="text-[11px] px-2.5 py-1 rounded-md bg-emerald-50 text-emerald-800 border border-emerald-200 hover:bg-emerald-100 transition-colors font-medium flex items-center gap-1"
            >
              <CheckCircle2 className="w-3 h-3 text-emerald-600" />
              <span>[APPLIED] Caption 1s-4s</span>
            </button>

            <button
              type="button"
              onClick={() => {
                setInstructionInput('Speed up video to 1.5x');
                handleExecuteInstruction('Speed up video to 1.5x');
              }}
              disabled={isExecutingInstruction || isProcessing}
              className="text-[11px] px-2.5 py-1 rounded-md bg-emerald-50 text-emerald-800 border border-emerald-200 hover:bg-emerald-100 transition-colors font-medium flex items-center gap-1"
            >
              <CheckCircle2 className="w-3 h-3 text-emerald-600" />
              <span>[APPLIED] 1.5x Speed</span>
            </button>

            <button
              type="button"
              onClick={() => {
                setInstructionInput('Mute the video');
                handleExecuteInstruction('Mute the video');
              }}
              disabled={isExecutingInstruction || isProcessing}
              className="text-[11px] px-2.5 py-1 rounded-md bg-amber-50 text-amber-800 border border-amber-200 hover:bg-amber-100 transition-colors font-medium flex items-center gap-1"
            >
              <HelpCircle className="w-3 h-3 text-amber-600" />
              <span>[NEEDS_CLARIFICATION] Missing Timestamp</span>
            </button>

            <button
              type="button"
              onClick={() => {
                setInstructionInput('Trim the middle part');
                handleExecuteInstruction('Trim the middle part');
              }}
              disabled={isExecutingInstruction || isProcessing}
              className="text-[11px] px-2.5 py-1 rounded-md bg-amber-50 text-amber-800 border border-amber-200 hover:bg-amber-100 transition-colors font-medium flex items-center gap-1"
            >
              <HelpCircle className="w-3 h-3 text-amber-600" />
              <span>[NEEDS_CLARIFICATION] Ambiguous Reference</span>
            </button>

            <button
              type="button"
              onClick={() => {
                setInstructionInput('Reverse the video backwards');
                handleExecuteInstruction('Reverse the video backwards');
              }}
              disabled={isExecutingInstruction || isProcessing}
              className="text-[11px] px-2.5 py-1 rounded-md bg-rose-50 text-rose-800 border border-rose-200 hover:bg-rose-100 transition-colors font-medium flex items-center gap-1"
            >
              <XCircle className="w-3 h-3 text-rose-600" />
              <span>[REJECTED] Unsupported Effect</span>
            </button>

            <button
              type="button"
              onClick={() => {
                setInstructionInput('Mute audio from 30s to 10s');
                handleExecuteInstruction('Mute audio from 30s to 10s');
              }}
              disabled={isExecutingInstruction || isProcessing}
              className="text-[11px] px-2.5 py-1 rounded-md bg-rose-50 text-rose-800 border border-rose-200 hover:bg-rose-100 transition-colors font-medium flex items-center gap-1"
            >
              <XCircle className="w-3 h-3 text-rose-600" />
              <span>[REJECTED] Invalid Range</span>
            </button>
          </div>
        </div>

        {/* Input Bar */}
        <form
          onSubmit={(e) => {
            e.preventDefault();
            handleExecuteInstruction();
          }}
          className="flex items-center gap-2"
        >
          <div className="relative flex-1">
            <input
              type="text"
              value={instructionInput}
              onChange={(e) => setInstructionInput(e.target.value)}
              placeholder="Enter an editing instruction (e.g. 'Mute from 00:02 to 00:05', 'Speed up to 1.25x')..."
              className="w-full pl-3 pr-8 py-2 text-xs rounded-lg border border-slate-300 bg-white focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 font-medium"
              disabled={isExecutingInstruction || isProcessing}
            />
            {instructionInput && (
              <button
                type="button"
                onClick={() => setInstructionInput('')}
                className="absolute right-2.5 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600 text-xs font-bold"
              >
                ×
              </button>
            )}
          </div>

          <button
            type="submit"
            disabled={!instructionInput.trim() || isExecutingInstruction || isProcessing}
            className="btn btn-primary text-xs py-2 px-3.5 flex items-center gap-1.5 shrink-0"
          >
            {isExecutingInstruction ? (
              <>
                <div className="w-3.5 h-3.5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                <span>Validating...</span>
              </>
            ) : (
              <>
                <Send className="w-3.5 h-3.5" />
                <span>Process</span>
              </>
            )}
          </button>
        </form>

        {instructionError && (
          <div className="p-2.5 rounded-lg bg-rose-50 border border-rose-200 text-rose-800 text-xs flex items-center gap-2">
            <AlertCircle className="w-4 h-4 text-rose-600 shrink-0" />
            <span>{instructionError}</span>
          </div>
        )}

        {/* Active Outcome Card */}
        {latestOutcome && (
          <div
            className={`p-3.5 rounded-xl border text-xs space-y-2.5 transition-all ${
              latestOutcome.status === 'APPLIED'
                ? 'bg-emerald-50/80 border-emerald-300 text-emerald-950'
                : latestOutcome.status === 'NEEDS_CLARIFICATION'
                ? 'bg-amber-50/80 border-amber-300 text-amber-950'
                : 'bg-rose-50/80 border-rose-300 text-rose-950'
            }`}
          >
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div className="flex items-center gap-2">
                {latestOutcome.status === 'APPLIED' && (
                  <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-bold bg-emerald-600 text-white shadow-xs">
                    <CheckCircle2 className="w-3.5 h-3.5" />
                    APPLIED
                  </span>
                )}
                {latestOutcome.status === 'NEEDS_CLARIFICATION' && (
                  <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-bold bg-amber-500 text-white shadow-xs">
                    <HelpCircle className="w-3.5 h-3.5" />
                    NEEDS_CLARIFICATION
                  </span>
                )}
                {latestOutcome.status === 'REJECTED' && (
                  <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-bold bg-rose-600 text-white shadow-xs">
                    <XCircle className="w-3.5 h-3.5" />
                    REJECTED
                  </span>
                )}

                <span className="font-mono text-[11px] text-slate-600 bg-white/80 px-2 py-0.5 rounded border border-slate-200">
                  ID: {latestOutcome.operationId}
                </span>

                {latestOutcome.rollback_performed && (
                  <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-bold bg-purple-100 text-purple-800 border border-purple-200">
                    <RotateCcw className="w-3 h-3 text-purple-600" />
                    Midway Rollback Committed
                  </span>
                )}
              </div>

              <span className="text-[10px] text-slate-500 font-mono">
                Outcome Protocol: Must-have 3
              </span>
            </div>

            {/* Instruction & Message */}
            <div className="space-y-1">
              <div className="flex items-baseline gap-2">
                <span className="font-bold text-slate-500 text-[11px] uppercase">Instruction:</span>
                <span className="font-semibold text-slate-900 font-mono text-xs">
                  "{latestOutcome.instruction}"
                </span>
              </div>
              <div className="flex items-baseline gap-2">
                <span className="font-bold text-slate-500 text-[11px] uppercase">Result:</span>
                <span className="font-medium text-slate-800">{latestOutcome.message}</span>
              </div>
            </div>

            {/* Clarification Specific Question */}
            {latestOutcome.status === 'NEEDS_CLARIFICATION' && latestOutcome.clarification_prompt && (
              <div className="p-2.5 rounded-lg bg-white/90 border border-amber-300 space-y-2">
                <div className="flex items-start gap-2 text-amber-900 font-medium">
                  <CornerDownRight className="w-4 h-4 text-amber-600 shrink-0 mt-0.5" />
                  <div>
                    <span className="font-bold block text-xs">Required Clarification:</span>
                    <p className="text-xs text-amber-800 mt-0.5">{latestOutcome.clarification_prompt}</p>
                  </div>
                </div>
                <div className="text-[11px] text-slate-500 flex items-center gap-1.5 pt-1 border-t border-amber-100">
                  <ShieldCheck className="w-3.5 h-3.5 text-amber-600" />
                  <span>Timeline remains 100% unmodified until ambiguity is resolved.</span>
                </div>
              </div>
            )}

            {/* Normalized Operation Specs */}
            {latestOutcome.operation && (
              <div className="p-2 rounded-lg bg-white/90 border border-slate-200 font-mono text-[11px] text-slate-700 flex flex-wrap items-center gap-3">
                <span className="font-bold text-slate-900 uppercase font-sans text-[10px]">
                  Normalized Operation:
                </span>
                <span className="px-1.5 py-0.5 bg-slate-100 rounded text-slate-800">
                  type: <strong>{latestOutcome.operation.type}</strong>
                </span>
                {latestOutcome.operation.start !== undefined && (
                  <span className="px-1.5 py-0.5 bg-slate-100 rounded text-slate-800">
                    start: <strong>{latestOutcome.operation.start}s</strong>
                  </span>
                )}
                {latestOutcome.operation.end !== undefined && (
                  <span className="px-1.5 py-0.5 bg-slate-100 rounded text-slate-800">
                    end: <strong>{latestOutcome.operation.end}s</strong>
                  </span>
                )}
                {latestOutcome.operation.speed !== undefined && (
                  <span className="px-1.5 py-0.5 bg-slate-100 rounded text-slate-800">
                    speed: <strong>{latestOutcome.operation.speed}x</strong>
                  </span>
                )}
                {latestOutcome.operation.text && (
                  <span className="px-1.5 py-0.5 bg-slate-100 rounded text-slate-800 truncate max-w-xs">
                    text: "{latestOutcome.operation.text}"
                  </span>
                )}
              </div>
            )}
          </div>
        )}

        {/* Audit History Log */}
        {instructionHistory.length > 0 && (
          <div className="space-y-2 pt-2 border-t border-slate-200">
            <div className="flex items-center justify-between">
              <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider flex items-center gap-1.5">
                <History className="w-3 h-3 text-slate-400" />
                <span>Instruction History Audit ({instructionHistory.length})</span>
              </span>
              <button
                type="button"
                onClick={() => setShowHistoryAudit(!showHistoryAudit)}
                className="text-[11px] text-indigo-600 hover:text-indigo-800 font-medium"
              >
                {showHistoryAudit ? 'Hide Audit Log' : 'Show Audit Log'}
              </button>
            </div>

            {showHistoryAudit && (
              <div className="max-h-48 overflow-y-auto space-y-1.5 pr-1">
                {instructionHistory.map((item, idx) => (
                  <div
                    key={item.operationId || idx}
                    className="p-2 rounded-lg bg-white border border-slate-200 flex items-center justify-between gap-2 text-[11px]"
                  >
                    <div className="flex items-center gap-2 min-w-0">
                      <span
                        className={`px-1.5 py-0.5 rounded text-[9px] font-bold tracking-wider shrink-0 ${
                          item.status === 'APPLIED'
                            ? 'bg-emerald-100 text-emerald-800'
                            : item.status === 'NEEDS_CLARIFICATION'
                            ? 'bg-amber-100 text-amber-800'
                            : 'bg-rose-100 text-rose-800'
                        }`}
                      >
                        {item.status}
                      </span>
                      <span className="font-mono text-slate-800 truncate" title={item.instruction}>
                        "{item.instruction}"
                      </span>
                    </div>

                    <div className="flex items-center gap-2 shrink-0 text-[10px] text-slate-500">
                      {item.rollback_performed && (
                        <span className="text-purple-700 font-semibold bg-purple-50 px-1 rounded">
                          Rollback
                        </span>
                      )}
                      <span className="font-mono text-slate-400">
                        {item.operationId.slice(0, 8)}…
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>

      {/* Step by Step Operations */}
      <div className="flex flex-col gap-3">
        <span className="text-xs font-bold text-[#64748B] uppercase tracking-wider">
          Sequence of Operations ({(plan.operations || []).length})
        </span>

        {(plan.operations || []).map((op, idx) => (
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

              {/* Delete operation button */}
              <button
                type="button"
                onClick={() => handleRemoveOp(idx)}
                className="p-1 rounded text-slate-400 hover:text-rose-600 hover:bg-rose-50 transition-colors"
                title="Remove this edit operation"
              >
                <Trash2 className="w-3.5 h-3.5" />
              </button>
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

              {op.type === 'cut' && (
                <div className="flex items-center gap-3">
                  <div className="flex items-center gap-1.5">
                    <span className="text-[#64748B]">Cut From (s):</span>
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
                    <span className="text-[#64748B]">Cut To (s):</span>
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

              {op.type === 'speed' && (
                <div className="flex items-center gap-3">
                  <div className="flex items-center gap-1.5">
                    <span className="text-[#64748B]">Speed:</span>
                    <select
                      value={op.parameters?.speed ?? 1.5}
                      onChange={(e) => handleUpdateOpParam(idx, 'parameters', { ...op.parameters, speed: parseFloat(e.target.value) })}
                      className="px-2 py-1 rounded-lg bg-white border border-[#CBD5E1] text-[#0F172A] text-xs font-medium outline-none focus:border-indigo-500"
                    >
                      <option value="0.5">0.5x (Slow Motion)</option>
                      <option value="0.75">0.75x (Subtle Slow)</option>
                      <option value="1.25">1.25x (Brisk)</option>
                      <option value="1.5">1.5x (Speed Up)</option>
                      <option value="2.0">2.0x (Double Speed)</option>
                    </select>
                  </div>
                </div>
              )}

              {(op.type === 'caption' || op.type === 'subtitles') && (
                <div className="flex flex-col sm:flex-row items-start sm:items-center gap-2.5 w-full">
                  <div className="flex items-center gap-1.5 flex-1">
                    <span className="text-[#64748B]">Text:</span>
                    <input
                      type="text"
                      value={op.custom_text || op.parameters?.text || ''}
                      onChange={(e) => {
                        handleUpdateOpParam(idx, 'custom_text', e.target.value);
                        handleUpdateOpParam(idx, 'parameters', { ...op.parameters, text: e.target.value });
                      }}
                      placeholder="Caption text..."
                      className="w-full px-2 py-1 rounded-lg bg-white border border-[#CBD5E1] text-[#0F172A] text-xs outline-none focus:border-indigo-500"
                    />
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-[#64748B] font-mono text-[10px]">
                      Source Anchor: [{op.start_time ?? 0}s - {op.end_time ?? 0}s]
                    </span>
                  </div>
                </div>
              )}

              {(op.type === 'mute_range' || op.type === 'beep') && (
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
                  <span className="badge badge-indigo text-[10px]">
                    {op.type === 'beep' ? '1000Hz Censorship Tone' : 'Muted Audio'}
                  </span>
                </div>
              )}

              {op.type === 'visual_effect' && (
                <div className="flex items-center gap-3">
                  <div className="flex items-center gap-1.5">
                    <span className="text-[#64748B]">Filter:</span>
                    <span className="font-semibold text-purple-700 bg-purple-50 px-2 py-0.5 rounded border border-purple-200">
                      {op.parameters?.effect || 'boxblur'}
                    </span>
                  </div>
                  <span className="text-[#64748B] font-mono text-[10px]">
                    Source Anchor: [{op.start_time ?? 0}s - {op.end_time ?? 0}s]
                  </span>
                </div>
              )}
            </div>
          </div>
        ))}
      </div>

      {/* Content-Aware Timeline Graph & Content Anchor Visualizer */}
      {plan.timeline && (
        <div className="p-4 rounded-xl border border-indigo-200 bg-gradient-to-br from-indigo-50/50 via-white to-slate-50 flex flex-col gap-3.5 shadow-xs">
          <div className="flex items-center justify-between border-b border-indigo-100 pb-2.5">
            <div className="flex items-center gap-2">
              <div className="w-6 h-6 rounded bg-indigo-600 text-white flex items-center justify-center">
                <Layers className="w-3.5 h-3.5" />
              </div>
              <div>
                <h4 className="text-xs font-bold text-[#0F172A] flex items-center gap-1.5">
                  <span>Content-Aware Timeline Graph</span>
                  <span className="badge badge-emerald text-[9px] font-bold">Anchors Preserved</span>
                </h4>
                <p className="text-[11px] text-[#64748B]">
                  Captions, mute ranges, beeps & effects mathematically bound to source frames across cuts/speeds
                </p>
              </div>
            </div>

            <button
              type="button"
              onClick={() => setShowCoordinateMapper(!showCoordinateMapper)}
              className="btn btn-secondary text-[11px] py-1 px-2.5 flex items-center gap-1.5"
              title="Test deterministic coordinate mapping"
            >
              <Calculator className="w-3 h-3 text-indigo-600" />
              <span>{showCoordinateMapper ? 'Hide Coordinate Tool' : 'Coordinate Mapping'}</span>
            </button>
          </div>

          {/* Quick Metrics Bar */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-[11px]">
            <div className="bg-white p-2.5 rounded-lg border border-slate-200 shadow-2xs">
              <span className="text-[#64748B] block text-[10px] uppercase font-semibold">Timeline Output</span>
              <span className="font-bold font-mono text-[#0F172A] text-xs">
                {plan.timeline.timeline_duration.toFixed(2)}s
              </span>
              <span className="text-[10px] text-slate-500 block">from {plan.timeline.source_duration.toFixed(2)}s source</span>
            </div>

            <div className="bg-white p-2.5 rounded-lg border border-slate-200 shadow-2xs">
              <span className="text-[#64748B] block text-[10px] uppercase font-semibold">Timeline Segments</span>
              <span className="font-bold font-mono text-indigo-700 text-xs">
                {plan.timeline.segment_count} Segment{plan.timeline.segment_count > 1 ? 's' : ''}
              </span>
              <span className="text-[10px] text-slate-500 block">
                {plan.timeline.summary.is_reordered ? 'Reordered' : 'Sequential'}
              </span>
            </div>

            <div className="bg-white p-2.5 rounded-lg border border-slate-200 shadow-2xs">
              <span className="text-[#64748B] block text-[10px] uppercase font-semibold">Active Anchors</span>
              <span className="font-bold font-mono text-emerald-700 text-xs">
                {plan.timeline.summary.active_effects_count} Effects Active
              </span>
              <span className="text-[10px] text-slate-500 block">Transformed onto output</span>
            </div>

            <div className="bg-white p-2.5 rounded-lg border border-slate-200 shadow-2xs">
              <span className="text-[#64748B] block text-[10px] uppercase font-semibold">Dropped / Cut</span>
              <span className="font-bold font-mono text-slate-700 text-xs">
                {plan.timeline.summary.dropped_effects_count} Dropped
              </span>
              <span className="text-[10px] text-slate-500 block">Content cut policy applied</span>
            </div>
          </div>

          {/* Timeline Segments Visualization */}
          {plan.timeline?.segments && plan.timeline.segments.length > 0 && (
            <div className="space-y-1.5">
              <span className="text-[10px] font-bold text-[#64748B] uppercase tracking-wider block">
                Timeline Segment Topology
              </span>
              <div className="flex flex-col sm:flex-row gap-2">
                {plan.timeline.segments.map((seg, sIdx) => (
                  <div
                    key={seg.clip_id || sIdx}
                    className="flex-1 bg-white p-2.5 rounded-lg border border-indigo-200 shadow-2xs flex flex-col justify-between gap-1.5"
                  >
                    <div className="flex items-center justify-between">
                      <span className="font-mono text-[11px] font-bold text-indigo-950 flex items-center gap-1">
                        <span className="w-2 h-2 rounded-full bg-indigo-500" />
                        {seg.clip_id}
                      </span>
                      <span className="badge badge-indigo text-[9px] font-mono">
                        {seg.speed !== 1.0 ? `${seg.speed}x Speed` : '1.0x Normal'}
                      </span>
                    </div>
                    <div className="text-[10px] text-slate-600 font-mono space-y-0.5">
                      <div>
                        <span className="text-slate-400">Source: </span>
                        <strong className="text-slate-800">{seg.source_start.toFixed(2)}s</strong> → <strong className="text-slate-800">{seg.source_end.toFixed(2)}s</strong>
                      </div>
                      <div>
                        <span className="text-slate-400">Timeline: </span>
                        <strong className="text-indigo-700">{seg.timeline_start.toFixed(2)}s</strong> → <strong className="text-indigo-700">{seg.timeline_end.toFixed(2)}s</strong> ({seg.timeline_duration.toFixed(2)}s)
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Transformed Content-Aware Effects */}
          {plan.timeline?.transformed_effects && plan.timeline.transformed_effects.length > 0 && (
            <div className="space-y-1.5">
              <span className="text-[10px] font-bold text-[#64748B] uppercase tracking-wider block">
                Preserved Content Anchors & Effects ({plan.timeline.transformed_effects.length})
              </span>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                {plan.timeline.transformed_effects.map((eff: TransformedTimelineEffect, eIdx: number) => {
                  const getStatusBadge = (status: string) => {
                    switch (status) {
                      case 'active':
                        return <span className="badge badge-emerald text-[9px]">Active</span>;
                      case 'clipped':
                        return <span className="badge badge-amber text-[9px]">Clipped to Cut</span>;
                      case 'split':
                        return <span className="badge badge-indigo text-[9px]">Split</span>;
                      default:
                        return <span className="badge badge-neutral text-[9px]">{status}</span>;
                    }
                  };

                  return (
                    <div
                      key={eff.effect_id || eIdx}
                      className="p-2 rounded-lg bg-white border border-slate-200 text-[11px] flex flex-col gap-1 shadow-2xs"
                    >
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-1.5">
                          <Tag className="w-3 h-3 text-indigo-600" />
                          <span className="font-bold text-[#0F172A] uppercase text-[10px]">
                            {eff.type}
                          </span>
                        </div>
                        {getStatusBadge(eff.status)}
                      </div>

                      {eff.label && (
                        <p className="text-[11px] font-medium text-slate-800 italic truncate">
                          "{eff.label}"
                        </p>
                      )}

                      <div className="text-[10px] font-mono text-slate-600 grid grid-cols-2 gap-1 pt-1 border-t border-slate-100">
                        <div>
                          <span className="text-slate-400 block text-[9px]">Source Anchor</span>
                          <span>{eff.source_start.toFixed(2)}s - {eff.source_end.toFixed(2)}s</span>
                        </div>
                        <div>
                          <span className="text-indigo-600 block text-[9px]">Timeline Range</span>
                          <span className="font-bold text-indigo-800">{eff.timeline_start.toFixed(2)}s - {eff.timeline_end.toFixed(2)}s</span>
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* Dropped Effects (Cut Policy Demonstration) */}
          {plan.timeline.dropped_effects && plan.timeline.dropped_effects.length > 0 && (
            <div className="p-2.5 rounded-lg bg-rose-50/60 border border-rose-200 text-[11px] space-y-1">
              <span className="text-[10px] font-bold text-rose-800 uppercase tracking-wider block">
                Dropped Effects (Cut Retention Policy)
              </span>
              <p className="text-[10px] text-rose-700">
                The following operations were anchored to source frames that were cleanly removed by cuts:
              </p>
              <div className="space-y-1">
                {plan.timeline.dropped_effects.map((dropped, dIdx) => (
                  <div key={dIdx} className="flex items-center justify-between text-[10px] font-mono bg-white/80 px-2 py-1 rounded border border-rose-100 text-rose-900">
                    <span>{dropped.type.toUpperCase()}: [{dropped.source_start.toFixed(2)}s - {dropped.source_end.toFixed(2)}s] {dropped.label ? `("${dropped.label}")` : ''}</span>
                    <span className="text-rose-600 font-semibold">Content Removed</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Interactive Coordinate Mapper Tool */}
          {showCoordinateMapper && (
            <div className="p-3 bg-indigo-100/50 rounded-xl border border-indigo-200 text-xs space-y-2.5 mt-1">
              <div className="flex items-center gap-1.5 font-bold text-indigo-950">
                <Calculator className="w-3.5 h-3.5 text-indigo-700" />
                <span>Deterministic Coordinate Mapping Tester</span>
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                {/* Source to Timeline */}
                <div className="bg-white p-2.5 rounded-lg border border-indigo-100 space-y-1.5">
                  <span className="font-semibold text-slate-700 block text-[11px]">Source Timestamp ➔ Timeline</span>
                  <div className="flex items-center gap-2">
                    <input
                      type="number"
                      step="0.25"
                      min="0"
                      max={plan.timeline.source_duration}
                      value={testSourceTime}
                      onChange={(e) => setTestSourceTime(parseFloat(e.target.value) || 0)}
                      className="w-20 px-2 py-1 rounded border border-slate-300 font-mono text-xs"
                    />
                    <span className="text-slate-500 font-mono text-xs">sec</span>
                  </div>
                  {(() => {
                    const res = mapSourceToTimeline(testSourceTime);
                    if (res.found && res.timelineTime !== null) {
                      return (
                        <div className="text-[11px] text-emerald-800 font-mono bg-emerald-50 p-1.5 rounded border border-emerald-200">
                          Timeline: <strong>{res.timelineTime.toFixed(2)}s</strong> ({res.segmentId} @ {res.speed}x)
                        </div>
                      );
                    }
                    return (
                      <div className="text-[11px] text-rose-700 font-mono bg-rose-50 p-1.5 rounded border border-rose-200">
                        Cut from timeline (not in any segment)
                      </div>
                    );
                  })()}
                </div>

                {/* Timeline to Source */}
                <div className="bg-white p-2.5 rounded-lg border border-indigo-100 space-y-1.5">
                  <span className="font-semibold text-slate-700 block text-[11px]">Timeline Timestamp ➔ Source</span>
                  <div className="flex items-center gap-2">
                    <input
                      type="number"
                      step="0.25"
                      min="0"
                      max={plan.timeline.timeline_duration}
                      value={testTimelineTime}
                      onChange={(e) => setTestTimelineTime(parseFloat(e.target.value) || 0)}
                      className="w-20 px-2 py-1 rounded border border-slate-300 font-mono text-xs"
                    />
                    <span className="text-slate-500 font-mono text-xs">sec</span>
                  </div>
                  {(() => {
                    const res = mapTimelineToSource(testTimelineTime);
                    if (res.found && res.sourceTime !== null) {
                      return (
                        <div className="text-[11px] text-indigo-800 font-mono bg-indigo-50 p-1.5 rounded border border-indigo-200">
                          Source: <strong>{res.sourceTime.toFixed(2)}s</strong> ({res.segmentId} @ {res.speed}x)
                        </div>
                      );
                    }
                    return (
                      <div className="text-[11px] text-rose-700 font-mono bg-rose-50 p-1.5 rounded border border-rose-200">
                        Out of timeline bounds
                      </div>
                    );
                  })()}
                </div>
              </div>
            </div>
          )}
        </div>
      )}

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
