import React, { useState, useRef } from 'react';
import { UploadCloud, Film, Play, AlertCircle, CheckCircle2, Sparkles } from 'lucide-react';

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
    <div className="w-full flex flex-col gap-5 animate-fade-in-up">
      {/* Drag & Drop Zone */}
      <div
        onDragOver={(e) => {
          e.preventDefault();
          setIsDragOver(true);
        }}
        onDragLeave={() => setIsDragOver(false)}
        onDrop={handleDrop}
        onClick={() => inputRef.current?.click()}
        className="relative group cursor-pointer overflow-hidden"
        style={{
          background: isDragOver
            ? 'linear-gradient(135deg, rgba(139,92,246,0.12) 0%, rgba(236,72,153,0.08) 50%, rgba(34,211,238,0.06) 100%)'
            : 'var(--bg-card)',
          border: isDragOver
            ? '2px dashed rgba(139,92,246,0.6)'
            : '2px dashed rgba(255,255,255,0.1)',
          borderRadius: '20px',
          backdropFilter: 'blur(20px)',
          padding: '40px 24px',
          transition: 'all 0.35s cubic-bezier(0.4, 0, 0.2, 1)',
          transform: isDragOver ? 'scale(1.01)' : 'scale(1)',
          boxShadow: isDragOver
            ? '0 0 60px -10px rgba(139,92,246,0.3), 0 12px 40px rgba(0,0,0,0.5)'
            : '0 8px 32px -8px rgba(0,0,0,0.5)',
        }}
      >
        <input
          ref={inputRef}
          type="file"
          accept=".mp4,.mov,.mkv,.webm,.avi"
          onChange={handleFileChange}
          className="hidden"
        />

        <div className="flex flex-col items-center justify-center text-center relative z-10">
          {/* Upload Icon with Gradient */}
          <div
            className="w-20 h-20 rounded-3xl flex items-center justify-center mb-5 group-hover:scale-110 transition-transform duration-300"
            style={{
              background: 'linear-gradient(135deg, rgba(139,92,246,0.15) 0%, rgba(236,72,153,0.1) 100%)',
              border: '1.5px solid rgba(139,92,246,0.3)',
              boxShadow: '0 0 30px rgba(139,92,246,0.15), 0 8px 24px -4px rgba(0,0,0,0.3)',
            }}
          >
            <UploadCloud className="w-9 h-9 text-violet-400" />
          </div>

          <h3 className="text-xl font-bold text-white mb-1.5">
            Upload Video to Studio
          </h3>
          <p className="text-sm text-[#94A3B8] max-w-md mb-5">
            Drag and drop your video file here, or click to browse from your device
          </p>

          {/* Specifications */}
          <div className="flex flex-wrap items-center justify-center gap-2.5">
            <span className="badge badge-indigo">MP4, MOV, WEBM, MKV</span>
            <span className="metadata-pill py-1 text-xs">Max 250 MB</span>
            <span className="metadata-pill py-1 text-xs">Up to 10 Minutes</span>
          </div>
        </div>

        {/* Animated corner decorations */}
        <div className="absolute top-3 left-3 w-5 h-5 border-l-2 border-t-2 rounded-tl-md" style={{ borderColor: 'rgba(139,92,246,0.3)' }} />
        <div className="absolute top-3 right-3 w-5 h-5 border-r-2 border-t-2 rounded-tr-md" style={{ borderColor: 'rgba(236,72,153,0.3)' }} />
        <div className="absolute bottom-3 left-3 w-5 h-5 border-l-2 border-b-2 rounded-bl-md" style={{ borderColor: 'rgba(34,211,238,0.3)' }} />
        <div className="absolute bottom-3 right-3 w-5 h-5 border-r-2 border-b-2 rounded-br-md" style={{ borderColor: 'rgba(52,211,153,0.3)' }} />
      </div>

      {/* Error state */}
      {error && (
        <div
          className="glass-card p-4 flex items-start gap-3 animate-fade-in-up"
          style={{
            borderColor: 'rgba(251,113,133,0.35)',
            background: 'linear-gradient(135deg, rgba(251,113,133,0.1) 0%, rgba(244,63,94,0.05) 100%)',
          }}
        >
          <AlertCircle className="w-5 h-5 text-rose-400 shrink-0 mt-0.5" />
          <div>
            <p className="text-sm font-semibold text-rose-300">Upload Rejected</p>
            <p className="text-xs text-rose-200/80 mt-0.5">{error}</p>
          </div>
        </div>
      )}

      {/* Quick 1-Click Interactive Demo Option */}
      <div
        className="glass-card p-6 flex flex-col sm:flex-row items-center justify-between gap-5 animate-fade-in-up"
        style={{
          borderColor: 'rgba(34,211,238,0.25)',
          background: 'linear-gradient(135deg, rgba(34,211,238,0.06) 0%, rgba(139,92,246,0.04) 50%, rgba(236,72,153,0.03) 100%), var(--bg-card)',
          animationDelay: '150ms',
        }}
      >
        <div className="flex items-center gap-4">
          <div
            className="w-12 h-12 rounded-2xl flex items-center justify-center shrink-0"
            style={{
              background: 'linear-gradient(135deg, rgba(34,211,238,0.15), rgba(139,92,246,0.1))',
              border: '1.5px solid rgba(34,211,238,0.35)',
              boxShadow: '0 0 20px rgba(34,211,238,0.1)',
            }}
          >
            <Sparkles className="w-5 h-5 text-cyan-400" />
          </div>
          <div className="text-left">
            <div className="flex items-center gap-2">
              <h4 className="text-sm font-bold text-white">Don't have a video ready?</h4>
              <span className="badge badge-cyan text-[10px] px-2 py-0.5">Instant</span>
            </div>
            <p className="text-xs text-[#94A3B8] mt-0.5">
              Load our bundled synthetic talking-head video to test real trimming, vertical 9:16 crop, silence cuts, and subtitles.
            </p>
          </div>
        </div>

        <button
          onClick={onStartDemo}
          disabled={isLoading}
          className="btn btn-accent text-xs py-2.5 px-5 shrink-0 w-full sm:w-auto font-bold"
        >
          <Play className="w-3.5 h-3.5" />
          <span>{isLoading ? 'Loading Demo...' : 'Load Demo Project'}</span>
        </button>
      </div>
    </div>
  );
};
