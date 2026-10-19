import React, { useState, useRef } from 'react';
import { UploadCloud, Film, Play, AlertCircle, CheckCircle2 } from 'lucide-react';

interface VideoUploadProps {
  onFileSelected: (file: File) => void;
  onStartDemo: () => void;
  isLoading: boolean;
  error?: string | null;
}

export const VideoUpload: React.FC<VideoUploadProps> = ({
  onFileSelected,
  onStartDemo,
  isLoading,
  error,
}) => {
  const [isDragOver, setIsDragOver] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      onFileSelected(e.dataTransfer.files[0]);
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      onFileSelected(e.target.files[0]);
    }
  };

  return (
    <div className="w-full flex flex-col gap-4">
      {/* Drag & Drop Zone */}
      <div
        onDragOver={(e) => {
          e.preventDefault();
          setIsDragOver(true);
        }}
        onDragLeave={() => setIsDragOver(false)}
        onDrop={handleDrop}
        onClick={() => inputRef.current?.click()}
        className={`glass-card p-8 flex flex-col items-center justify-center text-center cursor-pointer border-2 border-dashed transition-all ${
          isDragOver
            ? 'border-indigo-500 bg-indigo-500/10 scale-[1.01]'
            : 'border-[rgba(255,255,255,0.12)] hover:border-indigo-400/40 hover:bg-[rgba(255,255,255,0.02)]'
        }`}
      >
        <input
          ref={inputRef}
          type="file"
          accept=".mp4,.mov,.mkv,.webm,.avi"
          onChange={handleFileChange}
          className="hidden"
        />

        <div className="w-16 h-16 rounded-2xl bg-indigo-500/10 border border-indigo-500/30 flex items-center justify-center mb-4 text-indigo-400 group-hover:scale-110 transition-transform">
          <UploadCloud className="w-8 h-8" />
        </div>

        <h3 className="text-lg font-semibold text-white mb-1">
          Upload Video to Studio
        </h3>
        <p className="text-sm text-[#94A3B8] max-w-sm mb-4">
          Drag and drop your video file here, or click to browse from your device
        </p>

        {/* Specifications */}
        <div className="flex flex-wrap items-center justify-center gap-2 text-xs text-[#64748B]">
          <span className="badge badge-indigo">MP4, MOV, WEBM, MKV</span>
          <span className="metadata-pill py-1">Max 250 MB</span>
          <span className="metadata-pill py-1">Up to 10 Minutes</span>
        </div>
      </div>

      {/* Error state */}
      {error && (
        <div className="glass-card p-4 border-rose-500/40 bg-rose-500/10 flex items-start gap-3">
          <AlertCircle className="w-5 h-5 text-rose-400 shrink-0 mt-0.5" />
          <div>
            <p className="text-sm font-semibold text-rose-300">Upload Rejected</p>
            <p className="text-xs text-rose-200/80 mt-0.5">{error}</p>
          </div>
        </div>
      )}

      {/* Quick 1-Click Interactive Demo Option */}
      <div className="glass-card p-5 border-cyan-500/30 bg-gradient-to-r from-cyan-950/20 to-indigo-950/20 flex flex-col sm:flex-row items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-cyan-500/20 border border-cyan-500/40 flex items-center justify-center text-cyan-400 shrink-0">
            <Film className="w-5 h-5" />
          </div>
          <div className="text-left">
            <div className="flex items-center gap-2">
              <h4 className="text-sm font-semibold text-white">Don't have a video ready?</h4>
              <span className="badge badge-cyan text-[10px] px-1.5 py-0.5">Instant</span>
            </div>
            <p className="text-xs text-[#94A3B8] mt-0.5">
              Load our bundled synthetic talking-head video to test real trimming, vertical 9:16 crop, silence cuts, and subtitles.
            </p>
          </div>
        </div>

        <button
          onClick={onStartDemo}
          disabled={isLoading}
          className="btn btn-accent text-xs py-2.5 px-4 shrink-0 w-full sm:w-auto"
        >
          <Play className="w-3.5 h-3.5" />
          <span>{isLoading ? 'Loading Demo...' : 'Load Demo Project'}</span>
        </button>
      </div>
    </div>
  );
};
