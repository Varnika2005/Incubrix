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
import { RotateCcw, AlertCircle, Sparkles, CheckCircle2 } from 'lucide-react';

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

  // Modals
  const [isSilenceModalOpen, setIsSilenceModalOpen] = useState(false);
  const [isReceiptModalOpen, setIsReceiptModalOpen] = useState(false);
  const [receipt, setReceipt] = useState<EditReceipt | null>(null);

  // Sync initialJob
  useEffect(() => {
    if (initialJob) {
      setJob(initialJob);
      if (initialJob.prompt) setPrompt(initialJob.prompt);
      if (initialJob.edit_plan) setEditPlan(initialJob.edit_plan);
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

  // Handle File Upload
  const handleFileUpload = async (file: File) => {
    setIsUploading(true);
    setError(null);
    try {
      const newJob = await api.uploadVideo(file);
      setJob(newJob);
      setPrompt('');
      setEditPlan(null);
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
      if (demoJob.edit_plan) setEditPlan(demoJob.edit_plan);
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
          if (updated.edit_plan) setEditPlan(updated.edit_plan);
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
    if (onClearJob) onClearJob();
  };

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
            className="btn btn-secondary text-xs py-1.5 px-3"
          >
            <RotateCcw className="w-3.5 h-3.5" />
            <span>New Video Project</span>
          </button>
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
        <div className="max-w-2xl mx-auto w-full py-8">
          <VideoUpload
            onFileSelected={handleFileUpload}
            onStartDemo={handleStartDemo}
            isLoading={isUploading}
            error={error}
          />
        </div>
      ) : (
        <div className="flex flex-col gap-6">
          <div className="studio-grid">
            {/* Left Column: Video Player & Specs */}
            <div className="flex flex-col gap-4">
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
            <div className="flex flex-col gap-4">
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
                  onPlanChange={setEditPlan}
                  onApproveAndProcess={handleApproveAndProcess}
                  onOpenSilenceReview={() => setIsSilenceModalOpen(true)}
                  onReset={() => setEditPlan(null)}
                  isProcessing={isProcessing}
                  hasSilenceDetections={Boolean(job.detected_silence && job.detected_silence.length > 0)}
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
              originalMeta={job.input_metadata}
              outputMeta={job.output_metadata}
              processingTime={job.processing_time_seconds}
              onDownload={() => {
                window.location.href = api.getDownloadUrl(job.id);
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
