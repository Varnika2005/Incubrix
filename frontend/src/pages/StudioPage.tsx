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
import {
  RotateCcw,
  AlertCircle,
  Sparkles,
  CheckCircle2,
  Zap,
  Sliders,
  Film,
  Code,
  Layers,
  Check,
  Clock,
  HardDrive,
  Info,
} from 'lucide-react';

interface StudioPageProps {
  initialJob?: JobResponse | null;
  onClearJob?: () => void;
}

export const StudioPage: React.FC<StudioPageProps> = ({
  initialJob,
  onClearJob,
}) => {
  const [job, setJob] = useState<JobResponse | null>(initialJob || null);
  const [prompt, setPrompt] = useState<string>(initialJob?.prompt || '');
  const [editPlan, setEditPlan] = useState<EditPlan | null>(initialJob?.edit_plan || null);
  
  const [isUploading, setIsUploading] = useState(false);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Active Right Column Tab
  const [activeTab, setActiveTab] = useState<'prompt' | 'plan' | 'specs'>('prompt');

  // Modals
  const [isSilenceModalOpen, setIsSilenceModalOpen] = useState(false);
  const [isReceiptModalOpen, setIsReceiptModalOpen] = useState(false);
  const [receipt, setReceipt] = useState<EditReceipt | null>(null);

  // Sync initialJob
  useEffect(() => {
    if (initialJob) {
      setJob(initialJob);
      if (initialJob.prompt) setPrompt(initialJob.prompt);
      if (initialJob.edit_plan) {
        setEditPlan(initialJob.edit_plan);
        setActiveTab('plan');
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
          if (updated.status === 'completed' || updated.status === 'failed') {
            setIsProcessing(false);
            if (pollTimerRef.current) clearInterval(pollTimerRef.current);
            if (updated.status === 'completed') {
              // Auto-load receipt and switch tab
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

  // Handle File Upload
  const handleFileUpload = async (file: File) => {
    setIsUploading(true);
    setError(null);
    try {
      const newJob = await api.uploadVideo(file);
      setJob(newJob);
      setPrompt('');
      setEditPlan(null);
      setActiveTab('prompt');
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
      if (demoJob.prompt) setPrompt(demoJob.prompt);
      if (demoJob.edit_plan) {
        setEditPlan(demoJob.edit_plan);
        setActiveTab('plan');
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
      if (updatedJob.edit_plan) {
        setEditPlan(updatedJob.edit_plan);
        setActiveTab('plan');
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
          if (updated.edit_plan) {
            setEditPlan(updated.edit_plan);
            setActiveTab('plan');
          }
        })
        .catch((err) => setError(err.message))
        .finally(() => setIsAnalyzing(false));
    }
  };

  // Handle Approval and Processing Trigger
  const handleApproveAndProcess = async () => {
    if (!job || !editPlan) return;
    setIsProcessing(true);
    setError(null);
    try {
      const updatedJob = await api.processJob(job.id, editPlan);
      setJob(updatedJob);
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

    setEditPlan({
      ...editPlan,
      operations: updatedOps,
    });
  };

  // Reset Studio
  const handleResetStudio = () => {
    setJob(null);
    setPrompt('');
    setEditPlan(null);
    setError(null);
    setReceipt(null);
    setActiveTab('prompt');
    if (onClearJob) onClearJob();
  };

  // Compute Current Workflow Step (1..5)
  const currentStep = !job
    ? 1
    : isProcessing
    ? 4
    : job.status === 'completed'
    ? 5
    : editPlan
    ? 3
    : 2;

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 flex flex-col gap-6">
      {/* Top Banner & Reset */}
      {job && (
        <div className="flex flex-wrap items-center justify-between gap-3 p-3.5 bg-white border border-[#E2E8F0] rounded-xl shadow-xs">
          <div className="flex items-center gap-2.5">
            <span className="badge badge-indigo text-xs">Active Workspace</span>
            <span className="text-xs text-[#64748B]">
              File: <strong className="text-[#0F172A]">{job.original_filename}</strong>
            </span>
          </div>

          <button
            onClick={handleResetStudio}
            className="btn btn-secondary text-xs py-1.5 px-3 font-semibold"
          >
            <RotateCcw className="w-3.5 h-3.5" />
            <span>New Video Project</span>
          </button>
        </div>
      )}

      {/* Creator Presets Strip */}
      {job && job.status !== 'completed' && (
        <div className="flex flex-col gap-2">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold uppercase tracking-wider text-[#94A3B8] flex items-center gap-1.5">
              <Sparkles className="w-3.5 h-3.5 text-violet-400" />
              <span>Instant Creator Presets</span>
            </span>
            <span className="text-[11px] text-[#64748B]">Click any card to auto-synthesize plan</span>
          </div>
          <CreatorPresets
            onSelectPreset={handleSelectPreset}
            disabled={isAnalyzing || isProcessing}
          />
        </div>
      )}

      {/* Main Workspace Layout */}
      {!job ? (
        <div className="max-w-2xl mx-auto w-full py-6">
          <VideoUpload
            onFileSelected={handleFileUpload}
            onStartDemo={handleStartDemo}
            isLoading={isUploading}
            error={error}
          />
        </div>
      ) : (
        <div className="flex flex-col gap-6">
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
            {/* Left Column: Video Preview & Progress (7 Columns) */}
            <div className="lg:col-span-7 flex flex-col gap-4">
              <VideoPlayer
                src={api.getOriginalPreviewUrl(job.id)}
                metadata={job.input_metadata}
                title={job.original_filename}
                badge={job.status.toUpperCase()}
                badgeColor={job.status === 'completed' ? 'emerald' : 'indigo'}
              />

              {/* Progress Card when processing */}
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

                  {/* Stage breakdown checklist */}
                  <div className="grid grid-cols-3 gap-2 pt-1 text-[11px]">
                    <div className="flex items-center gap-1.5 text-emerald-400 font-semibold">
                      <Check className="w-3 h-3" />
                      <span>AST Plan Validated</span>
                    </div>
                    <div className="flex items-center gap-1.5 text-cyan-400 font-semibold">
                      <Check className="w-3 h-3" />
                      <span>Filtergraph Built</span>
                    </div>
                    <div className="flex items-center gap-1.5 text-violet-300 font-semibold">
                      <Clock className="w-3 h-3 animate-spin" />
                      <span>Transcoding Streams</span>
                    </div>
                  </div>
                </div>
              )}
            </div>

            {/* Right Column: Structured Tabbed Inspector (5 Columns) */}
            <div className="lg:col-span-5 flex flex-col gap-3">
              {/* Tabs Navigation */}
              <div className="tab-container">
                <button
                  onClick={() => setActiveTab('prompt')}
                  className={`tab-pill flex-1 justify-center ${activeTab === 'prompt' ? 'tab-pill-active' : ''}`}
                >
                  <Sparkles className="w-3.5 h-3.5" />
                  <span>Prompt Editor</span>
                </button>
                <button
                  onClick={() => setActiveTab('plan')}
                  className={`tab-pill flex-1 justify-center ${activeTab === 'plan' ? 'tab-pill-active' : ''}`}
                >
                  <Sliders className="w-3.5 h-3.5" />
                  <span>Edit Plan {editPlan ? `(${editPlan.operations.length})` : ''}</span>
                </button>
                <button
                  onClick={() => setActiveTab('specs')}
                  className={`tab-pill flex-1 justify-center ${activeTab === 'specs' ? 'tab-pill-active' : ''}`}
                >
                  <Info className="w-3.5 h-3.5" />
                  <span>Diagnostics</span>
                </button>
              </div>

              {/* Tab 1: Prompt Editor */}
              {activeTab === 'prompt' && (
                <div className="flex flex-col gap-4 animate-fade-in-up">
                  <PromptEditor
                    prompt={prompt}
                    onChange={setPrompt}
                    onAnalyze={handleAnalyzePrompt}
                    isLoading={isAnalyzing}
                    suggestedRepair={editPlan?.suggested_repair}
                    warnings={editPlan?.warnings}
                  />

                  {editPlan && (
                    <div className="p-4 rounded-xl bg-violet-500/10 border border-violet-500/20 flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                        <span className="text-xs font-bold text-white">
                          Edit Plan Synthesized ({editPlan.operations.length} operations)
                        </span>
                      </div>
                      <button
                        onClick={() => setActiveTab('plan')}
                        className="btn btn-secondary text-xs py-1 px-2.5"
                      >
                        Inspect Plan
                      </button>
                    </div>
                  )}
                </div>
              )}

              {/* Tab 2: Edit Plan Inspector */}
              {activeTab === 'plan' && (
                <div className="flex flex-col gap-4 animate-fade-in-up">
                  {editPlan ? (
                    <EditPlanInspector
                      plan={editPlan}
                      onPlanChange={setEditPlan}
                      onApproveAndProcess={handleApproveAndProcess}
                      onOpenSilenceReview={() => setIsSilenceModalOpen(true)}
                      onReset={() => {
                        setEditPlan(null);
                        setActiveTab('prompt');
                      }}
                      isProcessing={isProcessing}
                      hasSilenceDetections={Boolean(job.detected_silence && job.detected_silence.length > 0)}
                    />
                  ) : (
                    <div className="glass-card p-8 text-center flex flex-col items-center gap-3">
                      <div className="w-10 h-10 rounded-xl bg-[rgba(255,255,255,0.03)] border border-[rgba(255,255,255,0.08)] flex items-center justify-center text-[#64748B]">
                        <Sliders className="w-5 h-5" />
                      </div>
                      <p className="text-xs font-bold text-white">No Edit Plan Generated Yet</p>
                      <p className="text-[11px] text-[#94A3B8]">
                        Type an instruction in the Prompt Editor or select a Creator Preset to generate a plan.
                      </p>
                      <button
                        onClick={() => setActiveTab('prompt')}
                        className="btn btn-primary text-xs py-2 px-4 mt-2"
                      >
                        Go to Prompt Editor
                      </button>
                    </div>
                  )}
                </div>
              )}

              {/* Tab 3: Media Diagnostics */}
              {activeTab === 'specs' && job.input_metadata && (
                <div className="glass-card p-5 flex flex-col gap-4 animate-fade-in-up">
                  <div className="flex items-center gap-2 border-b border-[rgba(255,255,255,0.08)] pb-3">
                    <HardDrive className="w-4 h-4 text-cyan-400" />
                    <h4 className="text-xs font-bold text-white uppercase tracking-wider">
                      FFprobe Stream Metadata
                    </h4>
                  </div>

                  <div className="space-y-2.5 text-xs">
                    <div className="flex justify-between p-2 rounded-lg bg-black/40">
                      <span className="text-[#94A3B8]">Resolution</span>
                      <span className="font-mono font-bold text-white">
                        {job.input_metadata.width} x {job.input_metadata.height}
                      </span>
                    </div>
                    <div className="flex justify-between p-2 rounded-lg bg-black/40">
                      <span className="text-[#94A3B8]">Duration</span>
                      <span className="font-mono font-bold text-amber-300">
                        {job.input_metadata.duration.toFixed(2)} seconds
                      </span>
                    </div>
                    <div className="flex justify-between p-2 rounded-lg bg-black/40">
                      <span className="text-[#94A3B8]">Aspect Ratio</span>
                      <span className="font-mono font-bold text-cyan-300">
                        {job.input_metadata.aspect_ratio}
                      </span>
                    </div>
                    <div className="flex justify-between p-2 rounded-lg bg-black/40">
                      <span className="text-[#94A3B8]">Frame Rate</span>
                      <span className="font-mono font-bold text-white">
                        {job.input_metadata.fps?.toFixed(1) || '24.0'} FPS
                      </span>
                    </div>
                    <div className="flex justify-between p-2 rounded-lg bg-black/40">
                      <span className="text-[#94A3B8]">Video Codec</span>
                      <span className="font-mono font-bold text-emerald-400">
                        {job.input_metadata.video_codec?.toUpperCase() || 'H264'}
                      </span>
                    </div>
                    <div className="flex justify-between p-2 rounded-lg bg-black/40">
                      <span className="text-[#94A3B8]">Audio Codec</span>
                      <span className="font-mono font-bold text-violet-300">
                        {job.input_metadata.audio_codec?.toUpperCase() || 'AAC'}
                      </span>
                    </div>
                  </div>

                  {job.detected_silence && job.detected_silence.length > 0 && (
                    <div className="p-3 rounded-xl bg-pink-500/10 border border-pink-500/20 text-xs">
                      <span className="text-pink-300 font-bold block mb-1">
                        Detected Audio Pauses
                      </span>
                      <span className="text-[#CBD5E1] text-[11px]">
                        {job.detected_silence.length} silent intervals detected via dB probe.
                      </span>
                    </div>
                  )}
                </div>
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
            <div className="animate-fade-in-up">
              <ComparisonViewer
                originalSrc={api.getOriginalPreviewUrl(job.id)}
                outputSrc={api.getOutputPreviewUrl(job.id)}
                originalMeta={job.input_metadata}
                outputMeta={job.output_metadata}
                processingTime={job.processing_time_seconds}
                onDownload={() => {
                  window.location.href = api.getDownloadUrl(job.id);
                }}
                onOpenReceipt={() => setIsReceiptModalOpen(true)}
              />
            </div>
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
