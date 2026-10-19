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
    <div className="glass-card overflow-hidden flex flex-col">
      {/* Header bar */}
      <div className="p-3.5 border-b border-[rgba(255,255,255,0.08)] flex items-center justify-between bg-black/20">
        <div className="flex items-center gap-2">
          <Film className="w-4 h-4 text-indigo-400" />
          <span className="text-sm font-semibold text-white">{title}</span>
        </div>
        <span className={`badge badge-${badgeColor} text-[10px]`}>{badge}</span>
      </div>

      {/* Video Container */}
      <div className="relative bg-black flex items-center justify-center min-h-[260px] max-h-[380px] overflow-hidden">
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
        <div className="p-3 border-t border-[rgba(255,255,255,0.06)] bg-[rgba(10,14,24,0.6)] flex flex-wrap gap-2 text-xs">
          <div className="metadata-pill">
            <Clock className="w-3.5 h-3.5 text-indigo-400" />
            <span>Duration: <strong>{metadata.duration.toFixed(1)}s</strong></span>
          </div>

          <div className="metadata-pill">
            <Maximize2 className="w-3.5 h-3.5 text-cyan-400" />
            <span>Dimensions: <strong>{metadata.width}x{metadata.height} ({metadata.aspect_ratio})</strong></span>
          </div>

          <div className="metadata-pill">
            <Zap className="w-3.5 h-3.5 text-amber-400" />
            <span>FPS: <strong>{metadata.fps}</strong></span>
          </div>

          <div className="metadata-pill">
            {metadata.has_audio ? (
              <Volume2 className="w-3.5 h-3.5 text-emerald-400" />
            ) : (
              <VolumeX className="w-3.5 h-3.5 text-rose-400" />
            )}
            <span>Audio: <strong>{metadata.has_audio ? (metadata.audio_codec || 'AAC') : 'None'}</strong></span>
          </div>

          <div className="metadata-pill">
            <span>Size: <strong>{formatBytes(metadata.size_bytes)}</strong></span>
          </div>
        </div>
      )}
    </div>
  );
};
