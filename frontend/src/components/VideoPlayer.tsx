import React from 'react';
import { MediaMetadata } from '../types';
import { Film, Volume2, VolumeX, Clock, Maximize2, Zap } from 'lucide-react';

interface VideoPlayerProps {
  src: string;
  metadata?: MediaMetadata | null;
  title: string;
  badge?: string;
  badgeColor?: 'indigo' | 'emerald' | 'cyan' | 'amber';
}

export const VideoPlayer: React.FC<VideoPlayerProps> = ({
  src,
  metadata,
  title,
  badge = 'SOURCE',
  badgeColor = 'indigo',
}) => {
  const formatBytes = (bytes: number) => {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  return (
    <div className="card overflow-hidden flex flex-col shadow-sm">
      {/* Header bar */}
      <div className="p-3.5 border-b border-[#F1F5F9] flex items-center justify-between bg-[#F8FAFC]">
        <div className="flex items-center gap-2">
          <Film className="w-4 h-4 text-indigo-600" />
          <span className="text-sm font-bold text-[#0F172A] truncate max-w-sm">{title}</span>
        </div>
        <span className={`badge badge-${badgeColor} text-[10px]`}>{badge}</span>
      </div>

      {/* Video Container */}
      <div className="relative bg-slate-950 flex items-center justify-center min-h-[260px] max-h-[380px] overflow-hidden">
        <video
          key={src}
          src={src}
          controls
          playsInline
          className="w-full h-full max-h-[380px] object-contain"
        />
      </div>

      {/* Metadata Pill Ribbon */}
      {metadata && (
        <div className="p-3 border-t border-[#F1F5F9] bg-[#F8FAFC] flex flex-wrap gap-2 text-xs">
          <div className="badge badge-neutral text-xs py-1 px-2.5">
            <Clock className="w-3.5 h-3.5 text-indigo-600" />
            <span>Duration: <strong>{metadata.duration.toFixed(1)}s</strong></span>
          </div>

          <div className="badge badge-neutral text-xs py-1 px-2.5">
            <Maximize2 className="w-3.5 h-3.5 text-cyan-600" />
            <span>Dimensions: <strong>{metadata.width}x{metadata.height} ({metadata.aspect_ratio})</strong></span>
          </div>

          <div className="badge badge-neutral text-xs py-1 px-2.5">
            <Zap className="w-3.5 h-3.5 text-amber-600" />
            <span>FPS: <strong>{metadata.fps}</strong></span>
          </div>

          <div className="badge badge-neutral text-xs py-1 px-2.5">
            {metadata.has_audio ? (
              <Volume2 className="w-3.5 h-3.5 text-emerald-600" />
            ) : (
              <VolumeX className="w-3.5 h-3.5 text-rose-600" />
            )}
            <span>Audio: <strong>{metadata.has_audio ? (metadata.audio_codec || 'AAC') : 'None'}</strong></span>
          </div>

          <div className="badge badge-neutral text-xs py-1 px-2.5">
            <span>Size: <strong>{formatBytes(metadata.size_bytes)}</strong></span>
          </div>
        </div>
      )}
    </div>
  );
};
