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
      icon: <Smartphone className="w-4 h-4 text-cyan-600" />,
      prompt: 'Convert to 9:16 vertical portrait for TikTok/Reels, crop to fill frame, and add subtitles',
      badge: 'POPULAR',
      badgeColor: 'badge-cyan',
    },
    {
      title: 'YouTube Standard',
      subtitle: '16:9 Landscape 1080p',
      icon: <Youtube className="w-4 h-4 text-rose-600" />,
      prompt: 'Convert to 16:9 widescreen landscape at 1080p Full HD',
      badge: '1080P',
      badgeColor: 'badge-coral',
    },
    {
      title: 'Square Feed Post',
      subtitle: '1:1 Square Format',
      icon: <Square className="w-4 h-4 text-amber-600" />,
      prompt: 'Convert to 1:1 square format for Instagram feed',
      badge: 'SOCIAL',
      badgeColor: 'badge-orange',
    },
    {
      title: 'Subtitle & Clean',
      subtitle: 'Silence Cut + Captions',
      icon: <Captions className="w-4 h-4 text-indigo-600" />,
      prompt: 'Remove silent pauses, boost audio volume by 50%, and burn subtitles',
      badge: 'AI SPEECH',
      badgeColor: 'badge-indigo',
    },
  ];

  return (
    <div className="flex flex-col gap-2.5">
      <div className="flex items-center gap-1.5 text-xs text-[#66627B]">
        <Zap className="w-3.5 h-3.5 text-[#6654F0]" />
        <span className="font-bold uppercase tracking-wider text-[11px]">Creator Quick Presets:</span>
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5">
        {presets.map((preset, idx) => (
          <button
            key={idx}
            disabled={disabled}
            onClick={() => onSelectPreset(preset.prompt)}
            className="card card-interactive p-3.5 text-left flex flex-col justify-between gap-2.5 border-[#E6E2F0] hover:border-[#6654F0] disabled:opacity-50 disabled:cursor-not-allowed group shadow-sm rounded-2xl"
          >
            <div className="flex items-center justify-between w-full">
              <div className="w-7 h-7 rounded-lg bg-[#EFEDF8] border border-[#E6E2F0] flex items-center justify-center group-hover:scale-105 transition-transform">
                {preset.icon}
              </div>
              <span className={`badge ${preset.badgeColor} text-[9px] px-1.5 py-0.5`}>{preset.badge}</span>
            </div>

            <div>
              <h4 className="text-xs font-bold text-[#191832] group-hover:text-[#6654F0] transition-colors">
                {preset.title}
              </h4>
              <p className="text-[11px] text-[#66627B]">{preset.subtitle}</p>
            </div>
          </button>
        ))}
      </div>
    </div>
  );
};
