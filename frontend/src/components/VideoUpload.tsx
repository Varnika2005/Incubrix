import React, { useState, useRef } from 'react';
import { UploadCloud, Film, Play, AlertCircle } from 'lucide-react';

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
        className={`card p-10 sm:p-12 flex flex-col items-center justify-center text-center cursor-pointer border-2 border-dashed rounded-3xl transition-all ${
          isDragOver
            ? 'border-[#6654F0] bg-[#EFEDF8]/50 scale-[1.01]'
            : 'border-[#D5CEE5] hover:border-[#6654F0] hover:bg-[#FBFBFE]'
        }`}
      >
        <input
          ref={inputRef}
          type="file"
          accept=".mp4,.mov,.mkv,.webm,.avi"
          onChange={handleFileChange}
          className="hidden"
        />

        <div className="w-16 h-16 rounded-2xl bg-[#EFEDF8] border border-[#E6E2F0] flex items-center justify-center mb-4 text-[#6654F0] transition-transform group-hover:scale-105">
          <UploadCloud className="w-8 h-8" />
        </div>

        <h3 className="text-xl font-bold text-[#191832] mb-1.5">
          Upload Video to Studio
        </h3>
        <p className="text-sm text-[#66627B] max-w-sm mb-5 leading-relaxed">
          Drag and drop your video file here, or click to browse from your device
        </p>

        {/* Specifications */}
        <div className="flex flex-wrap items-center justify-center gap-2 text-xs">
          <span className="badge badge-indigo">MP4, MOV, WEBM, MKV</span>
          <span className="badge badge-neutral">Max 250 MB</span>
          <span className="badge badge-neutral">Up to 10 Minutes</span>
        </div>
      </div>

      {/* Error state */}
      {error && (
        <div className="p-4 rounded-2xl border border-rose-200 bg-rose-50 flex items-start gap-3 text-rose-700">
          <AlertCircle className="w-5 h-5 text-rose-500 shrink-0 mt-0.5" />
          <div>
            <p className="text-sm font-bold text-rose-800">Upload Issue</p>
            <p className="text-xs text-rose-700 mt-0.5">{error}</p>
          </div>
        </div>
      )}

      {/* Quick 1-Click Interactive Demo Option */}
      <div className="card p-5 border border-[#15B8C9]/30 bg-[#E7F9FA]/40 rounded-2xl flex flex-col sm:flex-row items-center justify-between gap-4">
        <div className="flex items-center gap-3.5">
          <div className="w-10 h-10 rounded-xl bg-[#E7F9FA] border border-[#15B8C9]/30 flex items-center justify-center text-[#15B8C9] shrink-0">
            <Film className="w-5 h-5" />
          </div>
          <div className="text-left">
            <div className="flex items-center gap-2">
              <h4 className="text-sm font-bold text-[#191832]">Don't have a video ready?</h4>
              <span className="badge badge-cyan text-[10px] px-1.5 py-0.5">Instant</span>
            </div>
            <p className="text-xs text-[#66627B] mt-0.5">
              Launch our bundled talking-head demo project with zero upload wait time.
            </p>
          </div>
        </div>

        <button
          onClick={onStartDemo}
          disabled={isLoading}
          className="btn btn-accent text-xs py-2.5 px-4 font-bold shrink-0 rounded-xl shadow-xs"
        >
          <Play className={`w-3.5 h-3.5 ${isLoading ? 'animate-spin' : ''}`} />
          <span>{isLoading ? 'Booting...' : '1-Click Demo'}</span>
        </button>
      </div>
    </div>
  );
};
