import React, { useState, useEffect, useRef } from 'react';
import { JobResponse, EditPlan, EditReceipt, SilenceSegment } from '../types';
import { api } from '../services/api';
import { VideoUpload } from '../components/VideoUpload';
import { VideoPlayer } from '../components/VideoPlayer';
import { PromptEditor } from '../components/PromptEditor';
import { EditPlanInspector } from '../components/EditPlanInspector';
import { ComparisonViewer } from '../components/ComparisonViewer';
import { CreatorPresets } from '../components/CreatorPresets';
import { SilenceReviewModal } from '../components/SilenceReviewModal';
import { EditReceiptModal } from '../components/EditReceiptModal';
import { RotateCcw, AlertCircle, Sparkles, CheckCircle2, Undo2, Redo2 } from 'lucide-react';

interface StudioPageProps {
  initialJob?: JobResponse | null;
  onClearJob?: () => void;
  onJobChange?: (job: JobResponse | null) => void;
}

export const StudioPage: React.FC<StudioPageProps> = ({
  initialJob,
  onClearJob,
  onJobChange,
}) => {
  const [job, setJob] = useState<JobResponse | null>(initialJob || null);
  const [prompt, setPrompt] = useState<string>(initialJob?.prompt || '');
  const [editPlan, setEditPlan] = useState<EditPlan | null>(initialJob?.edit_plan || null);
  
  // Non-Destructive Edit Timeline History (EDL) Stack
  const [planHistory, setPlanHistory] = useState<EditPlan[]>([]);
  const [historyIndex, setHistoryIndex] = useState<number>(-1);
  const [canUndo, setCanUndo] = useState<boolean>(false);
  const [canRedo, setCanRedo] = useState<boolean>(false);

  const [isUploading, setIsUploading] = useState(false);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Modals
  const [isSilenceModalOpen, setIsSilenceModalOpen] = useState(false);
  const [isReceiptModalOpen, setIsReceiptModalOpen] = useState(false);
  const [receipt, setReceipt] = useState<EditReceipt | null>(null);

  // Helper to load and restore edit history for a job
  const restoreHistoryForJob = (targetJob: JobResponse) => {
    const storageKey = `clippilot_edl_${targetJob.id}`;
    const savedHistoryStr = localStorage.getItem(storageKey);
    let loadedHistory: EditPlan[] = [];

    if (savedHistoryStr) {
      try {
        const parsed = JSON.parse(savedHistoryStr);
        if (Array.isArray(parsed) && parsed.length > 0) {
          loadedHistory = parsed;
        }
      } catch (e) {
        console.warn('Failed to parse local history for job', targetJob.id, e);
      }
    }

    if (loadedHistory.length === 0 && targetJob.edit_history && targetJob.edit_history.length > 0) {
      loadedHistory = targetJob.edit_history;
    }

    if (loadedHistory.length === 0 && targetJob.edit_plan) {
      loadedHistory = [targetJob.edit_plan];
    }

    if (loadedHistory.length > 0) {
      setPlanHistory(loadedHistory);
      const activeIdx = loadedHistory.length - 1;
      setHistoryIndex(activeIdx);
      setEditPlan(loadedHistory[activeIdx]);
      setCanUndo(activeIdx > 0);
      setCanRedo(false);
    } else {
      setPlanHistory([]);
      setHistoryIndex(-1);
      setEditPlan(targetJob.edit_plan || null);
      setCanUndo(false);
      setCanRedo(false);
    }

    // Sync authoritative undo/redo history from backend
    api.getHistory(targetJob.id)
      .then((hist) => {
        setCanUndo(hist.can_undo);
        setCanRedo(hist.can_redo);
        setHistoryIndex(hist.current_index);
        if (hist.current_state?.plan) {
          setEditPlan(hist.current_state.plan);
        }
      })
      .catch(() => {});
  };

  // Sync initialJob or restore active job on page refresh
  useEffect(() => {
    if (initialJob) {
      setJob(initialJob);
      setPrompt(initialJob.prompt || '');
      localStorage.setItem('clippilot_active_job_id', initialJob.id);
      restoreHistoryForJob(initialJob);
    } else {
      const savedJobId = localStorage.getItem('clippilot_active_job_id');
      if (savedJobId) {
        api.getJob(savedJobId)
          .then((recovered) => {
            setJob(recovered);
            setPrompt(recovered.prompt || '');
            if (onJobChange) onJobChange(recovered);
            restoreHistoryForJob(recovered);
          })
          .catch(() => {
            setJob(null);
            setPrompt('');
            setEditPlan(null);
            setPlanHistory([]);
            setHistoryIndex(-1);
            setError(null);
            setReceipt(null);
          });
      } else {
        setJob(null);
        setPrompt('');
        setEditPlan(null);
        setPlanHistory([]);
        setHistoryIndex(-1);
        setError(null);
        setReceipt(null);
      }
    }
  }, [initialJob]);

  // Polling worker for queued/processing jobs
  const pollTimerRef = useRef<number | null>(null);

  useEffect(() => {
    if (!job) return;

    if (job.status === 'queued' || job.status === 'processing') {
      setIsProcessing(true);
      pollTimerRef.current = window.setInterval(async () => {
        try {
          const updated = await api.getJob(job.id);
          setJob(updated);
          if (onJobChange) onJobChange(updated);
          if (updated.status === 'completed' || updated.status === 'failed') {
            setIsProcessing(false);
            if (pollTimerRef.current) clearInterval(pollTimerRef.current);
            if (updated.status === 'completed') {
              // Auto-load receipt
              api.getReceipt(updated.id).then(setReceipt).catch(() => {});
            }
          }
        } catch (e) {
          console.error('Polling error', e);
        }
      }, 1500);
    } else {
      setIsProcessing(false);
      if (pollTimerRef.current) clearInterval(pollTimerRef.current);
    }

    return () => {
      if (pollTimerRef.current) clearInterval(pollTimerRef.current);
    };
  }, [job?.status, job?.id]);

  // Handle plan modification with timeline history tracking
  const handlePlanChange = (updatedPlan: EditPlan) => {
    setEditPlan(updatedPlan);
    if (!job) return;

    // Non-destructive timeline stack: append new step and prune redo branch
    const upToCurrent = planHistory.slice(0, historyIndex + 1);
    const newHistory = [...upToCurrent, updatedPlan];
    setPlanHistory(newHistory);
    const newIdx = newHistory.length - 1;
    setHistoryIndex(newIdx);

    // Save to local storage for refresh recovery
    try {
      localStorage.setItem(`clippilot_edl_${job.id}`, JSON.stringify(newHistory));
    } catch (e) {
      console.warn('LocalStorage save failed', e);
    }

    setCanUndo(true);
    setCanRedo(false);

    // Persist to backend database
    api.saveHistory(job.id, newHistory, updatedPlan).catch((err) => {
      console.warn('Backend history save error', err);
    });
  };

  // Undo edit operation
  const handleUndo = async () => {
    if (job) {
      try {
        const res = await api.undo(job.id);
        if (res.current_plan) {
          setEditPlan(res.current_plan);
          setHistoryIndex(res.current_index);
          setCanUndo(res.can_undo);
          setCanRedo(res.can_redo);
          setJob((prev) => prev ? { ...prev, edit_plan: res.current_plan, timeline: res.timeline || prev.timeline } : prev);
          return;
        }
      } catch (err) {
        console.warn('Backend undo failed, falling back to local history', err);
      }
    }

    // Local fallback
    if (historyIndex > 0 && planHistory.length > 0) {
      const nextIndex = historyIndex - 1;
      const targetPlan = planHistory[nextIndex];
      setHistoryIndex(nextIndex);
      setEditPlan(targetPlan);
      setCanUndo(nextIndex > 0);
      setCanRedo(true);
      if (job) {
        api.saveHistory(job.id, planHistory, targetPlan).catch(() => {});
      }
    } else {
      setCanUndo(false);
    }
  };

  // Redo edit operation
  const handleRedo = async () => {
    if (job) {
      try {
        const res = await api.redo(job.id);
        if (res.current_plan) {
          setEditPlan(res.current_plan);
          setHistoryIndex(res.current_index);
          setCanUndo(res.can_undo);
          setCanRedo(res.can_redo);
          setJob((prev) => prev ? { ...prev, edit_plan: res.current_plan, timeline: res.timeline || prev.timeline } : prev);
          return;
        }
      } catch (err) {
        console.warn('Backend redo failed, falling back to local history', err);
      }
    }

    // Local fallback
    if (historyIndex < planHistory.length - 1) {
      const nextIndex = historyIndex + 1;
      const targetPlan = planHistory[nextIndex];
      setHistoryIndex(nextIndex);
      setEditPlan(targetPlan);
      setCanUndo(true);
      setCanRedo(nextIndex < planHistory.length - 1);
      if (job) {
        api.saveHistory(job.id, planHistory, targetPlan).catch(() => {});
      }
    } else {
      setCanRedo(false);
    }
  };

  // Global Keyboard shortcuts: Ctrl+Z (Undo), Ctrl+Y / Ctrl+Shift+Z (Redo)
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      const target = e.target as HTMLElement;
      if (target && (target.tagName === 'INPUT' || target.tagName === 'TEXTAREA' || target.isContentEditable)) {
        return;
      }

      if ((e.ctrlKey || e.metaKey) && !e.shiftKey && (e.key === 'z' || e.key === 'Z')) {
        e.preventDefault();
        handleUndo();
      } else if (
        ((e.ctrlKey || e.metaKey) && (e.key === 'y' || e.key === 'Y')) ||
        ((e.ctrlKey || e.metaKey) && e.shiftKey && (e.key === 'z' || e.key === 'Z'))
      ) {
        e.preventDefault();
        handleRedo();
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [historyIndex, planHistory, job]);

  // Handle File Upload
  const handleFileUpload = async (file: File) => {
    setIsUploading(true);
    setError(null);
    try {
      const newJob = await api.uploadVideo(file);
      setJob(newJob);
      setPrompt('');
      setEditPlan(null);
      setPlanHistory([]);
      setHistoryIndex(-1);
      localStorage.setItem('clippilot_active_job_id', newJob.id);
      if (onJobChange) onJobChange(newJob);
    } catch (err: any) {
      setError(err.message || 'Video upload failed');
    } finally {
      setIsUploading(false);
    }
  };

  // Handle 1-Click Demo
  const handleStartDemo = async () => {
    setIsUploading(true);
    setError(null);
    try {
      const demoJob = await api.createDemoJob();
      setJob(demoJob);
      localStorage.setItem('clippilot_active_job_id', demoJob.id);
      if (onJobChange) onJobChange(demoJob);
      if (demoJob.prompt) setPrompt(demoJob.prompt);
      if (demoJob.edit_plan) {
        restoreHistoryForJob(demoJob);
      }
    } catch (err: any) {
      setError(err.message || 'Failed to start demo');
    } finally {
      setIsUploading(false);
    }
  };

  // Handle Prompt Analysis
  const handleAnalyzePrompt = async () => {
    if (!job || !prompt.trim()) return;
    setIsAnalyzing(true);
    setError(null);
    try {
      const updatedJob = await api.analyzePrompt(job.id, prompt);
      setJob(updatedJob);
      if (onJobChange) onJobChange(updatedJob);
      if (updatedJob.edit_plan) {
        handlePlanChange(updatedJob.edit_plan);
      }
    } catch (err: any) {
      setError(err.message || 'Prompt analysis failed');
    } finally {
      setIsAnalyzing(false);
    }
  };

  // Handle Preset Selection
  const handleSelectPreset = (presetPrompt: string) => {
    setPrompt(presetPrompt);
    if (job) {
      setIsAnalyzing(true);
      api
        .analyzePrompt(job.id, presetPrompt)
        .then((updated) => {
          setJob(updated);
          if (onJobChange) onJobChange(updated);
          if (updated.edit_plan) {
            handlePlanChange(updated.edit_plan);
          }
        })
        .catch((err) => setError(err.message))
        .finally(() => setIsAnalyzing(false));
    }
  };

  // Handle Approval and Processing Trigger with Pre-Flight Source Integrity Verification
  const handleApproveAndProcess = async () => {
    if (!job || !editPlan) return;
    setIsProcessing(true);
    setError(null);
    try {
      // Step 1: Pre-flight source integrity check before rendering
      const integrity = await api.verifyIntegrity(job.id);
      if (!integrity.verified) {
        throw new Error(
          `Source Integrity Check Failed: Current media hash (${integrity.current_hash}) does not match immutable recorded source hash (${integrity.original_hash}). Operation cancelled to protect original video.`
        );
      }

      // Step 2: Trigger render using immutable original + EDL
      const updatedJob = await api.processJob(job.id, editPlan);
      setJob(updatedJob);
      if (onJobChange) onJobChange(updatedJob);
    } catch (err: any) {
      setError(err.message || 'Processing failed to start');
      setIsProcessing(false);
    }
  };

  // Handle Silence Cut Confirmation
  const handleConfirmSilenceCuts = (cuts: [number, number][]) => {
    if (!editPlan) return;
    const updatedOps = editPlan.operations.map((op) => {
      if (op.type === 'silence_removal') {
        return {
          ...op,
          confirmed_intervals: cuts,
          description: `Remove ${cuts.length} approved silent pauses`,
        };
      }
      return op;
    });

    handlePlanChange({
      ...editPlan,
      operations: updatedOps,
    });
  };

  // Reset Studio
  const handleResetStudio = () => {
    if (job) {
      localStorage.removeItem(`clippilot_edl_${job.id}`);
    }
    localStorage.removeItem('clippilot_active_job_id');
    setJob(null);
    setPrompt('');
    setEditPlan(null);
    setPlanHistory([]);
    setHistoryIndex(-1);
    setError(null);
    setReceipt(null);
    if (onClearJob) onClearJob();
    if (onJobChange) onJobChange(null);
  };

  return (
    <div className="w-full max-w-[1920px] mx-auto px-4 sm:px-6 lg:px-10 py-6 flex flex-col gap-6">
      {/* Top Banner & Reset */}
      {job && (
        <div className="flex flex-wrap items-center justify-between gap-3 p-3.5 bg-white border border-[#E2E8F0] rounded-xl shadow-xs">
          <div className="flex items-center gap-2.5">
            <span className="badge badge-indigo text-xs">Studio Workspace</span>
            <span className="text-xs text-[#64748B]">
              File: <strong className="text-[#0F172A]">{job.original_filename}</strong>
            </span>
            {job.input_metadata && (
              <span className="hidden md:inline-flex text-[11px] font-mono text-slate-500 bg-slate-100 px-2 py-0.5 rounded">
                {job.input_metadata.duration.toFixed(1)}s • {job.input_metadata.width}x{job.input_metadata.height} • {job.input_metadata.fps} fps
              </span>
            )}
          </div>

          <div className="flex items-center gap-2">
            {/* Prominent Undo / Redo Toolbar */}
            <div className="flex items-center gap-1 bg-slate-100 p-1 rounded-lg border border-slate-200">
              <button
                onClick={handleUndo}
                disabled={!canUndo || isProcessing}
                className="btn btn-secondary text-xs py-1.5 px-3 flex items-center gap-1.5 font-bold disabled:opacity-35 disabled:hover:bg-white disabled:cursor-not-allowed hover:bg-white transition-all shadow-xs"
                title="Undo last edit (Ctrl+Z)"
              >
                <Undo2 className="w-3.5 h-3.5 text-indigo-600" />
                <span>Undo</span>
              </button>

              <button
                onClick={handleRedo}
                disabled={!canRedo || isProcessing}
                className="btn btn-secondary text-xs py-1.5 px-3 flex items-center gap-1.5 font-bold disabled:opacity-35 disabled:hover:bg-white disabled:cursor-not-allowed hover:bg-white transition-all shadow-xs"
                title="Redo edit (Ctrl+Y)"
              >
                <Redo2 className="w-3.5 h-3.5 text-indigo-600" />
                <span>Redo</span>
              </button>
            </div>

            <button
              onClick={handleResetStudio}
              className="btn btn-secondary text-xs py-1.5 px-3"
            >
              <RotateCcw className="w-3.5 h-3.5" />
              <span>New Video Project</span>
            </button>
          </div>
        </div>
      )}

      {/* Creator Presets Bar */}
      {job && job.status !== 'completed' && (
        <CreatorPresets
          onSelectPreset={handleSelectPreset}
          disabled={isAnalyzing || isProcessing}
        />
      )}

      {/* Main Workspace Grid */}
      {!job ? (
        <div className="max-w-4xl mx-auto w-full py-8">
          <VideoUpload
            onFileSelected={handleFileUpload}
            onStartDemo={handleStartDemo}
            isLoading={isUploading}
            error={error}
          />
        </div>
      ) : (
        <div className="flex flex-col gap-6">
          <div className="studio-grid grid grid-cols-1 lg:grid-cols-12 gap-6 lg:gap-8 items-start">
            {/* Left Column: Video Player & Specs */}
            <div className="lg:col-span-7 xl:col-span-7 2xl:col-span-8 flex flex-col gap-4">
              <VideoPlayer
                src={api.getOriginalPreviewUrl(job.id)}
                metadata={job.input_metadata}
                title={job.original_filename}
                badge={job.status.toUpperCase()}
                badgeColor={job.status === 'completed' ? 'emerald' : 'indigo'}
              />

              {/* Progress Bar when processing */}
              {isProcessing && (
                <div className="card p-5 flex flex-col gap-2.5 border-indigo-200 bg-indigo-50/40">
                  <div className="flex items-center justify-between text-xs">
                    <span className="font-bold text-[#0F172A] flex items-center gap-2">
                      <div className="w-3.5 h-3.5 border-2 border-indigo-600 border-t-transparent rounded-full animate-spin" />
                      <span>Transcoding Media Pipeline ({job.progress}%)</span>
                    </span>
                    <span className="text-indigo-700 font-mono text-xs font-semibold">{job.status}</span>
                  </div>
                  <div className="progress-container">
                    <div
                      className="progress-bar-fill"
                      style={{ width: `${Math.max(job.progress, 15)}%` }}
                    />
                  </div>
                </div>
              )}
            </div>

            {/* Right Column: Prompt Editor & Edit Plan */}
            <div className="lg:col-span-5 xl:col-span-5 2xl:col-span-4 flex flex-col gap-4">
              <PromptEditor
                prompt={prompt}
                onChange={setPrompt}
                onAnalyze={handleAnalyzePrompt}
                isLoading={isAnalyzing}
                suggestedRepair={editPlan?.suggested_repair}
                warnings={editPlan?.warnings}
              />

              {editPlan && (
                <EditPlanInspector
                  plan={editPlan}
                  jobId={job.id}
                  onPlanChange={handlePlanChange}
                  onApproveAndProcess={handleApproveAndProcess}
                  onOpenSilenceReview={() => setIsSilenceModalOpen(true)}
                  onReset={() => {
                    setEditPlan(null);
                    setPlanHistory([]);
                    setHistoryIndex(-1);
                    if (job) {
                      localStorage.removeItem(`clippilot_edl_${job.id}`);
                      api.saveHistory(job.id, [], null).catch(() => {});
                    }
                  }}
                  isProcessing={isProcessing}
                  hasSilenceDetections={Boolean(job.detected_silence && job.detected_silence.length > 0)}
                  originalHash={job.original_file_hash}
                  onUndo={handleUndo}
                  onRedo={handleRedo}
                  canUndo={canUndo}
                  canRedo={canRedo}
                />
              )}
            </div>
          </div>

          {/* Error Banner */}
          {error && (
            <div className="p-4 rounded-xl border border-rose-200 bg-rose-50 flex items-start gap-3">
              <AlertCircle className="w-5 h-5 text-rose-500 shrink-0 mt-0.5" />
              <div>
                <p className="text-sm font-bold text-rose-800">Operation Error</p>
                <p className="text-xs text-rose-700 mt-0.5">{error}</p>
              </div>
            </div>
          )}

          {/* Comparison Viewer: Revealed upon Completion */}
          {job.status === 'completed' && job.output_available && (
            <ComparisonViewer
              originalSrc={api.getOriginalPreviewUrl(job.id)}
              outputSrc={api.getOutputPreviewUrl(job.id)}
              downloadUrl={api.getDownloadUrl(job.id, 'ClipPilot_Edited_Video.mp4')}
              downloadFilename="ClipPilot_Edited_Video.mp4"
              originalMeta={job.input_metadata}
              outputMeta={job.output_metadata}
              processingTime={job.processing_time_seconds}
              onDownload={() => {
                api.downloadVideo(job.id, 'ClipPilot_Edited_Video.mp4');
              }}
              onOpenReceipt={() => setIsReceiptModalOpen(true)}
            />
          )}
        </div>
      )}

      {/* Silence Review Modal */}
      <SilenceReviewModal
        isOpen={isSilenceModalOpen}
        onClose={() => setIsSilenceModalOpen(false)}
        segments={job?.detected_silence || []}
        onConfirmCuts={handleConfirmSilenceCuts}
      />

      {/* Edit Receipt Modal */}
      <EditReceiptModal
        isOpen={isReceiptModalOpen}
        onClose={() => setIsReceiptModalOpen(false)}
        receipt={receipt}
      />
    </div>
  );
};
