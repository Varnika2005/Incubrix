import React from 'react';
import { Youtube, Smartphone, Square, Captions, Zap } from 'lucide-react';

interface CreatorPresetsProps {
  onSelectPreset: (promptText: string) => void;
  disabled: boolean;
}

export const CreatorPresets: React.FC<CreatorPresetsProps> = ({
  onSelectPreset,
  disabled,
}) => {
  const presets = [
    {
      title: 'TikTok / Reel',
      subtitle: '9:16 Vertical Crop',
      icon: <Smartphone className="w-4.5 h-4.5" />,
      prompt: 'Convert to 9:16 vertical portrait for TikTok/Reels, crop to fill frame, and add subtitles',
      badge: 'POPULAR',
      iconColor: '#67E8F9',
      gradient: 'linear-gradient(135deg, rgba(34,211,238,0.12), rgba(34,211,238,0.03))',
      borderColor: 'rgba(34,211,238,0.2)',
      badgeType: 'badge-cyan',
    },
    {
      title: 'YouTube Standard',
      subtitle: '16:9 Landscape 1080p',
      icon: <Youtube className="w-4.5 h-4.5" />,
      prompt: 'Convert to 16:9 widescreen landscape at 1080p Full HD',
      badge: '1080P',
      iconColor: '#FB7185',
      gradient: 'linear-gradient(135deg, rgba(251,113,133,0.12), rgba(251,113,133,0.03))',
      borderColor: 'rgba(251,113,133,0.2)',
      badgeType: 'badge-rose',
    },
    {
      title: 'Square Feed Post',
      subtitle: '1:1 Square Format',
      icon: <Square className="w-4.5 h-4.5" />,
      prompt: 'Convert to 1:1 square format for Instagram feed',
      badge: 'SOCIAL',
      iconColor: '#FBBF24',
      gradient: 'linear-gradient(135deg, rgba(251,191,36,0.12), rgba(251,191,36,0.03))',
      borderColor: 'rgba(251,191,36,0.2)',
      badgeType: 'badge-amber',
    },
    {
      title: 'Subtitle & Clean',
      subtitle: 'Silence Cut + Captions',
      icon: <Captions className="w-4.5 h-4.5" />,
      prompt: 'Remove silent pauses, boost audio volume by 50%, and burn subtitles',
      badge: 'AI SPEECH',
      iconColor: '#F9A8D4',
      gradient: 'linear-gradient(135deg, rgba(236,72,153,0.12), rgba(236,72,153,0.03))',
      borderColor: 'rgba(236,72,153,0.2)',
      badgeType: 'badge-magenta',
    },
  ];

  return (
    <div className="flex flex-col gap-3 animate-fade-in-up" style={{ animationDelay: '100ms' }}>
      <div className="flex items-center gap-2 text-xs text-[#64748B]">
        <Zap className="w-3.5 h-3.5 text-violet-400" />
        <span className="font-bold uppercase tracking-wider text-[11px]">Creator Quick Presets:</span>
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        {presets.map((preset, idx) => (
          <button
            key={idx}
            disabled={disabled}
            onClick={() => onSelectPreset(preset.prompt)}
            className="glass-card glass-card-interactive p-4 text-left flex flex-col justify-between gap-3 disabled:opacity-50 disabled:cursor-not-allowed group"
            style={{
              borderColor: preset.borderColor,
            }}
          >
            <div className="flex items-center justify-between w-full">
              <div
                className="w-8 h-8 rounded-lg flex items-center justify-center group-hover:scale-110 transition-transform duration-300"
                style={{
                  background: preset.gradient,
                  border: `1px solid ${preset.borderColor}`,
                  color: preset.iconColor,
                }}
              >
                {preset.icon}
              </div>
              <span className={`badge ${preset.badgeType} text-[8px] px-1.5 py-0.5`}>{preset.badge}</span>
            </div>

            <div>
              <h4 className="text-xs font-bold text-white group-hover:text-[var(--text-main)] transition-colors">
                {preset.title}
              </h4>
              <p className="text-[10px] text-[#64748B] mt-0.5">{preset.subtitle}</p>
            </div>
          </button>
        ))}
      </div>
    </div>
  );
};
