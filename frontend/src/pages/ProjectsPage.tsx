import React, { useEffect, useState } from 'react';
import { JobResponse, EditReceipt } from '../types';
import { api } from '../services/api';
import { useAuth } from '../context/AuthContext';
import { EditReceiptModal } from '../components/EditReceiptModal';
import {
  FileVideo,
  Sparkles,
  Download,
  Trash2,
  Clock,
  CheckCircle2,
  AlertCircle,
  FileText,
  Plus,
  RefreshCw,
  Film,
  Lock,
} from 'lucide-react';

interface ProjectsPageProps {
  onSelectJob: (job: JobResponse) => void;
  onNewProject: () => void;
  onNavigateToLogin: () => void;
}

export const ProjectsPage: React.FC<ProjectsPageProps> = ({
  onSelectJob,
  onNewProject,
  onNavigateToLogin,
}) => {
  const { isAuthenticated, user } = useAuth();
  const [jobs, setJobs] = useState<JobResponse[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Receipt Modal State
  const [activeReceipt, setActiveReceipt] = useState<EditReceipt | null>(null);
  const [isReceiptLoading, setIsReceiptLoading] = useState(false);

  const fetchJobs = async () => {
    if (!isAuthenticated) return;
    setIsLoading(true);
    setError(null);
    try {
      const data = await api.listJobs();
      setJobs(data);
    } catch (err: any) {
      setError(err.message || 'Failed to load projects');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchJobs();
  }, [isAuthenticated]);

  const handleDelete = async (jobId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    if (!window.confirm('Are you sure you want to delete this project? This will permanently delete associated video files.')) {
      return;
    }

    try {
      await api.deleteJob(jobId);
      setJobs((prev) => prev.filter((j) => j.id !== jobId));
    } catch (err: any) {
      alert(`Delete failed: ${err.message || 'Unknown error'}`);
    }
  };

  const handleOpenReceipt = async (jobId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    setIsReceiptLoading(true);
    try {
      const receipt = await api.getReceipt(jobId);
      setActiveReceipt(receipt);
    } catch (err: any) {
      alert(`Failed to load receipt: ${err.message || 'Unknown error'}`);
    } finally {
      setIsReceiptLoading(false);
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'completed':
        return <span className="badge badge-emerald">Completed</span>;
      case 'processing':
      case 'queued':
        return <span className="badge badge-cyan animate-pulse">Processing</span>;
      case 'awaiting_approval':
      case 'analyzing':
        return <span className="badge badge-indigo">Plan Ready</span>;
      case 'failed':
        return <span className="badge badge-coral">Failed</span>;
      default:
        return <span className="badge badge-neutral">Uploaded</span>;
    }
  };

  if (!isAuthenticated) {
    return (
      <div className="max-w-4xl mx-auto py-16 px-4 text-center flex flex-col items-center gap-6">
        <div className="w-16 h-16 rounded-2xl bg-indigo-50 border border-indigo-200 flex items-center justify-center text-indigo-600 shadow-sm">
          <Lock className="w-8 h-8" />
        </div>
        <h1 className="text-2xl font-bold text-[#0F172A]">Sign in to access your project history</h1>
        <p className="text-sm text-[#64748B] max-w-md">
          Every video you upload and process is securely associated with your creator account. Sign in to view and download past exports.
        </p>
        <button
          onClick={onNavigateToLogin}
          className="btn btn-primary text-sm py-2.5 px-6 font-bold shadow-md shadow-indigo-500/20"
        >
          <span>Sign In to Your Account</span>
        </button>
      </div>
    );
  }

  return (
    <div className="w-full max-w-[1920px] mx-auto py-8 px-4 sm:px-6 lg:px-10 flex flex-col gap-8">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 border-b border-[#E2E8F0] pb-6">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl sm:text-3xl font-extrabold text-[#191832] tracking-tight">
              My Video Projects
            </h1>
            <span className="badge badge-indigo text-xs">{jobs.length} Projects</span>
          </div>
          <p className="text-xs sm:text-sm text-[#66627B] mt-1">
            Authoritative project repository for <span className="font-semibold text-[#191832]">{user?.email}</span>
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={fetchJobs}
            disabled={isLoading}
            className="btn btn-secondary text-xs py-2 px-3"
            title="Refresh project list"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? 'animate-spin' : ''}`} />
            <span>Refresh</span>
          </button>

          <button
            onClick={onNewProject}
            className="btn btn-primary text-xs py-2 px-4 font-bold shadow-sm"
          >
            <Plus className="w-3.5 h-3.5" />
            <span>New Video Edit</span>
          </button>
        </div>
      </div>

      {/* Error Message */}
      {error && (
        <div className="p-4 rounded-xl bg-rose-50 border border-rose-200 text-rose-700 text-xs flex items-center gap-2">
          <AlertCircle className="w-4 h-4 shrink-0 text-rose-500" />
          <span>{error}</span>
        </div>
      )}

      {/* Projects List or Empty State */}
      {isLoading && jobs.length === 0 ? (
        <div className="py-20 text-center flex flex-col items-center gap-3 text-[#64748B]">
          <div className="w-8 h-8 border-2 border-indigo-600 border-t-transparent rounded-full animate-spin" />
          <p className="text-xs font-semibold">Loading your projects...</p>
        </div>
      ) : jobs.length === 0 ? (
        <div className="card p-12 text-center flex flex-col items-center gap-4 max-w-md mx-auto my-8 border-dashed">
          <div className="w-14 h-14 rounded-2xl bg-indigo-50 border border-indigo-200 flex items-center justify-center text-indigo-600">
            <FileVideo className="w-7 h-7" />
          </div>
          <div>
            <h3 className="text-base font-bold text-[#0F172A]">No projects created yet</h3>
            <p className="text-xs text-[#64748B] mt-1">
              Start by uploading a video or experimenting with the 1-click interactive demo.
            </p>
          </div>
          <button
            onClick={onNewProject}
            className="btn btn-primary text-xs py-2 px-5 font-bold shadow-sm"
          >
            <Plus className="w-3.5 h-3.5" />
            <span>Start Your First Video</span>
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {jobs.map((job) => (
            <div
              key={job.id}
              onClick={() => onSelectJob(job)}
              className="card card-interactive p-5 flex flex-col justify-between cursor-pointer group"
            >
              <div>
                <div className="flex items-start justify-between gap-3 mb-3">
                  <div className="flex items-center gap-2 min-w-0">
                    <div className="w-8 h-8 rounded-lg bg-indigo-50 text-indigo-600 flex items-center justify-center shrink-0">
                      <Film className="w-4 h-4" />
                    </div>
                    <div className="min-w-0">
                      <h3 className="text-xs font-bold text-[#0F172A] truncate group-hover:text-indigo-600 transition-colors">
                        {job.original_filename}
                      </h3>
                      <p className="text-[10px] text-[#94A3B8] flex items-center gap-1 mt-0.5">
                        <Clock className="w-2.5 h-2.5" />
                        {new Date(job.created_at).toLocaleDateString()} at{' '}
                        {new Date(job.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                      </p>
                    </div>
                  </div>
                  {getStatusBadge(job.status)}
                </div>

                {job.prompt && (
                  <div className="mb-4 bg-[#F8FAFC] border border-[#E2E8F0] p-2.5 rounded-lg">
                    <p className="text-[11px] text-[#475569] font-mono line-clamp-2">
                      "{job.prompt}"
                    </p>
                  </div>
                )}

                {job.input_metadata && (
                  <div className="grid grid-cols-3 gap-1.5 text-center text-[10px] text-[#64748B] mb-4 bg-slate-50 p-2 rounded-lg border border-slate-100">
                    <div>
                      <span className="block text-[#94A3B8]">Duration</span>
                      <span className="font-semibold text-[#0F172A]">{job.input_metadata.duration.toFixed(1)}s</span>
                    </div>
                    <div>
                      <span className="block text-[#94A3B8]">Resolution</span>
                      <span className="font-semibold text-[#0F172A]">{job.input_metadata.width}x{job.input_metadata.height}</span>
                    </div>
                    <div>
                      <span className="block text-[#94A3B8]">Ratio</span>
                      <span className="font-semibold text-[#0F172A]">{job.input_metadata.aspect_ratio}</span>
                    </div>
                  </div>
                )}
              </div>

              <div className="pt-3 border-t border-[#F1F5F9] flex items-center justify-between gap-2">
                <span className="text-[11px] font-semibold text-indigo-600 group-hover:underline">
                  Open in Studio →
                </span>

                <div className="flex items-center gap-1">
                  {job.status === 'completed' && (
                    <>
                      <button
                        type="button"
                        onClick={(e) => handleOpenReceipt(job.id, e)}
                        className="p-1.5 rounded-lg hover:bg-[#F1F5F9] text-[#64748B] hover:text-[#0F172A]"
                        title="View Cryptographic Edit Receipt"
                      >
                        <FileText className="w-3.5 h-3.5" />
                      </button>

                      <button
                        type="button"
                        onClick={(e) => {
                          e.stopPropagation();
                          const baseName = job.original_filename ? job.original_filename.replace(/\.[^/.]+$/, '') : job.id.slice(0, 8);
                          api.downloadVideo(job.id, `clippilot_${baseName}_edited.mp4`);
                        }}
                        className="p-1.5 rounded-lg hover:bg-emerald-50 text-emerald-600 transition-colors"
                        title="Download Finished Video (MP4)"
                      >
                        <Download className="w-3.5 h-3.5" />
                      </button>
                    </>
                  )}

                  <button
                    type="button"
                    onClick={(e) => handleDelete(job.id, e)}
                    className="p-1.5 rounded-lg hover:bg-rose-50 text-[#94A3B8] hover:text-rose-600 transition-colors"
                    title="Delete Project and Media"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Edit Receipt Modal */}
      <EditReceiptModal
        receipt={activeReceipt}
        isOpen={!!activeReceipt}
        onClose={() => setActiveReceipt(null)}
      />
    </div>
  );
};
