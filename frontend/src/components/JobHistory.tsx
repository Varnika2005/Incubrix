import React, { useEffect, useState } from 'react';
import { JobResponse } from '../types';
import { api } from '../services/api';
import { History, X, Download, Trash2, Clock, CheckCircle2, AlertCircle, RefreshCw, Film } from 'lucide-react';

interface JobHistoryProps {
  isOpen: boolean;
  onClose: () => void;
  onSelectJob: (job: JobResponse) => void;
}

export const JobHistory: React.FC<JobHistoryProps> = ({
  isOpen,
  onClose,
  onSelectJob,
}) => {
  const [jobs, setJobs] = useState<JobResponse[]>([]);
  const [isLoading, setIsLoading] = useState(false);

  const fetchJobs = async () => {
    setIsLoading(true);
    try {
      const data = await api.listJobs();
      setJobs(data);
    } catch (e) {
      console.error(e);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    if (isOpen) {
      fetchJobs();
    }
  }, [isOpen]);

  const handleDelete = async (e: React.MouseEvent, id: string) => {
    e.stopPropagation();
    try {
      await api.deleteJob(id);
      setJobs((prev) => prev.filter((j) => j.id !== id));
    } catch (err) {
      console.error(err);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-md animate-fade-in">
      <div className="glass-card w-full max-w-2xl border-indigo-500/40 p-6 flex flex-col gap-4 shadow-2xl relative overflow-hidden animate-scale-in">
        {/* Top Rainbow Accent Strip */}
        <div
          className="absolute top-0 left-0 right-0 h-1"
          style={{
            background: 'linear-gradient(90deg, #8B5CF6 0%, #EC4899 50%, #22D3EE 100%)',
          }}
        />

        {/* Header */}
        <div className="flex items-center justify-between border-b border-[rgba(255,255,255,0.08)] pb-3">
          <div className="flex items-center gap-3">
            <div
              className="w-10 h-10 rounded-xl flex items-center justify-center text-violet-300"
              style={{
                background: 'linear-gradient(135deg, rgba(139,92,246,0.2) 0%, rgba(236,72,153,0.15) 100%)',
                border: '1px solid rgba(139,92,246,0.35)',
                boxShadow: '0 0 15px rgba(139,92,246,0.2)',
              }}
            >
              <History className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h3 className="text-base font-bold text-white">Persistent Job History</h3>
                <span className="badge badge-indigo text-[10px] font-semibold">SQLite Store</span>
              </div>
              <p className="text-xs text-[#94A3B8]">Audit log of all video editing sessions and artifacts</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={fetchJobs}
              disabled={isLoading}
              className="p-1.5 rounded-lg text-[#94A3B8] hover:text-white hover:bg-[rgba(255,255,255,0.08)] transition-colors"
              title="Refresh job list"
            >
              <RefreshCw className={`w-4 h-4 ${isLoading ? 'animate-spin text-cyan-400' : ''}`} />
            </button>
            <button
              onClick={onClose}
              className="p-1.5 rounded-lg text-[#94A3B8] hover:text-white hover:bg-[rgba(255,255,255,0.08)] transition-colors"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Jobs list */}
        <div className="max-h-96 overflow-y-auto space-y-2.5 pr-1">
          {isLoading ? (
            <div className="text-center py-12 flex flex-col items-center gap-3">
              <RefreshCw className="w-6 h-6 animate-spin text-violet-400" />
              <span className="text-xs text-[#94A3B8]">Querying SQLite job store...</span>
            </div>
          ) : jobs.length === 0 ? (
            <div className="text-center py-12 flex flex-col items-center gap-3">
              <div className="w-12 h-12 rounded-2xl bg-[rgba(255,255,255,0.03)] border border-[rgba(255,255,255,0.06)] flex items-center justify-center text-[#64748B]">
                <Film className="w-6 h-6" />
              </div>
              <p className="text-xs text-[#94A3B8]">No previous editing jobs found in database.</p>
              <span className="text-[11px] text-[#64748B]">Processed videos and edit receipts will appear here.</span>
            </div>
          ) : (
            jobs.map((job) => {
              const isCompleted = job.status === 'completed';
              const isFailed = job.status === 'failed';

              return (
                <div
                  key={job.id}
                  onClick={() => {
                    onSelectJob(job);
                    onClose();
                  }}
                  className="p-3.5 rounded-xl border border-[rgba(255,255,255,0.07)] bg-[rgba(10,14,24,0.6)] hover:border-violet-500/50 hover:bg-[rgba(30,27,58,0.5)] cursor-pointer flex items-center justify-between gap-4 transition-all duration-200 group shadow-sm hover:shadow-lg hover:shadow-violet-500/10"
                >
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1.5">
                      <span className="font-bold text-white text-xs truncate group-hover:text-violet-200 transition-colors">
                        {job.original_filename}
                      </span>
                      {isCompleted && (
                        <span className="badge badge-emerald text-[9px] flex items-center gap-1">
                          <CheckCircle2 className="w-2.5 h-2.5" />
                          completed
                        </span>
                      )}
                      {isFailed && (
                        <span className="badge badge-rose text-[9px] flex items-center gap-1">
                          <AlertCircle className="w-2.5 h-2.5" />
                          failed
                        </span>
                      )}
                      {!isCompleted && !isFailed && (
                        <span className="badge badge-amber text-[9px] flex items-center gap-1">
                          <Clock className="w-2.5 h-2.5" />
                          {job.status}
                        </span>
                      )}
                    </div>

                    {job.prompt && (
                      <p className="text-xs text-[#CBD5E1] truncate italic font-medium bg-[rgba(255,255,255,0.02)] px-2 py-0.5 rounded border border-[rgba(255,255,255,0.04)]">
                        "{job.prompt}"
                      </p>
                    )}

                    <div className="flex items-center gap-3 text-[10px] text-[#64748B] mt-1.5">
                      <span>{new Date(job.created_at).toLocaleString()}</span>
                      {job.processing_time_seconds && (
                        <span className="text-amber-300 font-medium">
                          • Processed in {job.processing_time_seconds.toFixed(1)}s
                        </span>
                      )}
                    </div>
                  </div>

                  {/* Actions */}
                  <div className="flex items-center gap-1.5 shrink-0">
                    {job.output_available && (
                      <a
                        href={api.getDownloadUrl(job.id)}
                        onClick={(e) => e.stopPropagation()}
                        download
                        className="btn btn-secondary text-xs p-2 text-cyan-300 hover:text-cyan-200 hover:border-cyan-500/50"
                        title="Download finished video"
                      >
                        <Download className="w-3.5 h-3.5" />
                      </a>
                    )}

                    <button
                      onClick={(e) => handleDelete(e, job.id)}
                      className="btn btn-danger text-xs p-2"
                      title="Delete job and files"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  </div>
                </div>
              );
            })
          )}
        </div>
      </div>
    </div>
  );
};
