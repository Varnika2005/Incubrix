import React, { useEffect, useState } from 'react';
import { JobResponse } from '../types';
import { api } from '../services/api';
import { useAuth } from '../context/AuthContext';
import { History, X, Download, Trash2, Lock } from 'lucide-react';

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
  const { isAuthenticated } = useAuth();
  const [jobs, setJobs] = useState<JobResponse[]>([]);
  const [isLoading, setIsLoading] = useState(false);

  const fetchJobs = async () => {
    if (!isAuthenticated) return;
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
  }, [isOpen, isAuthenticated]);

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
    <div className="modal-overlay">
      <div className="modal-content p-6 flex flex-col gap-4 max-w-2xl">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-[#F1F5F9] pb-3">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-indigo-50 border border-indigo-200 flex items-center justify-center text-indigo-600">
              <History className="w-4 h-4" />
            </div>
            <div>
              <h3 className="text-sm font-bold text-[#0F172A]">Persistent Job History</h3>
              <p className="text-xs text-[#64748B]">Audit log of your video editing sessions in SQLite</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-[#94A3B8] hover:text-[#0F172A] hover:bg-[#F1F5F9]"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Jobs list */}
        <div className="max-h-96 overflow-y-auto space-y-2 pr-1">
          {!isAuthenticated ? (
            <div className="text-center py-12 text-xs text-[#64748B] flex flex-col items-center gap-2">
              <Lock className="w-6 h-6 text-indigo-600" />
              <span>Please sign in to view your private job history.</span>
            </div>
          ) : isLoading ? (
            <div className="text-center py-12 text-xs text-[#64748B]">
              Loading persisted jobs...
            </div>
          ) : jobs.length === 0 ? (
            <div className="text-center py-12 text-xs text-[#64748B]">
              No previous editing jobs found in database.
            </div>
          ) : (
            jobs.map((job) => {
              const statusColor =
                job.status === 'completed'
                  ? 'emerald'
                  : job.status === 'failed'
                  ? 'coral'
                  : 'orange';

              return (
                <div
                  key={job.id}
                  onClick={() => {
                    onSelectJob(job);
                    onClose();
                  }}
                  className="p-3.5 rounded-xl border border-[#E2E8F0] bg-[#F8FAFC] hover:border-indigo-300 hover:bg-indigo-50/20 cursor-pointer flex items-center justify-between gap-4 transition-all"
                >
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="font-bold text-[#0F172A] text-xs truncate">
                        {job.original_filename}
                      </span>
                      <span className={`badge badge-${statusColor} text-[9px]`}>
                        {job.status}
                      </span>
                    </div>

                    {job.prompt && (
                      <p className="text-xs text-[#475569] truncate font-mono">
                        "{job.prompt}"
                      </p>
                    )}

                    <div className="flex items-center gap-3 text-[10px] text-[#64748B] mt-1">
                      <span>{new Date(job.created_at).toLocaleString()}</span>
                      {job.processing_time_seconds && (
                        <span>• Processed in {job.processing_time_seconds.toFixed(1)}s</span>
                      )}
                    </div>
                  </div>

                  {/* Actions */}
                  <div className="flex items-center gap-1.5 shrink-0">
                    {job.output_available && (
                      <button
                        type="button"
                        onClick={(e) => {
                          e.stopPropagation();
                          const baseName = job.original_filename ? job.original_filename.replace(/\.[^/.]+$/, '') : job.id.slice(0, 8);
                          api.downloadVideo(job.id, `clippilot_${baseName}_edited.mp4`);
                        }}
                        className="btn btn-secondary text-xs p-2 text-indigo-600"
                        title="Download finished video (MP4)"
                      >
                        <Download className="w-3.5 h-3.5" />
                      </button>
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
