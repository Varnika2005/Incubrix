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

  const accentColors: Record<string, string> = {
    indigo: '#8B5CF6',
    emerald: '#34D399',
    cyan: '#22D3EE',
    amber: '#FBBF24',
  };

  return (
    <div
      className="glass-card overflow-hidden flex flex-col animate-fade-in-up"
      style={{
        borderColor: `${accentColors[badgeColor]}22`,
      }}
    >
      {/* Header bar */}
      <div
        className="p-3.5 flex items-center justify-between"
        style={{
          background: 'rgba(0,0,0,0.3)',
          borderBottom: '1px solid rgba(255,255,255,0.06)',
        }}
      >
        <div className="flex items-center gap-2.5">
          <Film className="w-4 h-4" style={{ color: accentColors[badgeColor] }} />
          <span className="text-sm font-bold text-white">{title}</span>
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
        {/* Decorative gradient overlay at bottom */}
        <div
          className="absolute bottom-0 left-0 right-0 h-12 pointer-events-none"
          style={{
            background: 'linear-gradient(transparent, rgba(0,0,0,0.4))',
          }}
        />
      </div>

      {/* Metadata Pill Ribbon */}
      {metadata && (
        <div
          className="p-3.5 flex flex-wrap gap-2 text-xs"
          style={{
            background: 'rgba(8,12,24,0.7)',
            borderTop: '1px solid rgba(255,255,255,0.05)',
          }}
        >
          <div className="metadata-pill">
            <Clock className="w-3.5 h-3.5 text-violet-400" />
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
