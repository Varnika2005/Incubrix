import React from 'react';
import { Sparkles, Wand2, ArrowRight, AlertTriangle } from 'lucide-react';

interface PromptEditorProps {
  prompt: string;
  onChange: (value: string) => void;
  onAnalyze: () => void;
  isLoading: boolean;
  suggestedRepair?: string | null;
  warnings?: string[];
}

export const PromptEditor: React.FC<PromptEditorProps> = ({
  prompt,
  onChange,
  onAnalyze,
  isLoading,
  suggestedRepair,
  warnings,
}) => {
  const exampleChips = [
    'Cut first 3 seconds, convert to 9:16 vertical, and add subtitles',
    'Keep from 0:02 to 0:08 and boost volume by 50%',
    'Convert to 1:1 square with high contrast',
    'Detect and remove silent pauses',
    'Mute audio and export at 720p HD',
  ];

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) {
      e.preventDefault();
      if (prompt.trim() && !isLoading) {
        onAnalyze();
      }
    }
  };

  return (
    <div
      className="glass-card p-6 flex flex-col gap-5 animate-fade-in-up"
      style={{
        borderColor: 'rgba(139,92,246,0.15)',
        background: 'linear-gradient(160deg, rgba(139,92,246,0.04) 0%, var(--bg-card) 30%), var(--bg-card)',
      }}
    >
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div
            className="w-9 h-9 rounded-xl flex items-center justify-center"
            style={{
              background: 'linear-gradient(135deg, rgba(139,92,246,0.2) 0%, rgba(236,72,153,0.1) 100%)',
              border: '1.5px solid rgba(139,92,246,0.35)',
              boxShadow: '0 0 15px rgba(139,92,246,0.12)',
            }}
          >
            <Sparkles className="w-4.5 h-4.5 text-violet-400" />
          </div>
          <div>
            <h3 className="text-sm font-bold text-white">Prompt Video Editor</h3>
            <p className="text-xs text-[#64748B]">Describe how you want your video transformed</p>
          </div>
        </div>
        <span
          className="text-[11px] font-medium hidden sm:inline px-2.5 py-1 rounded-lg"
          style={{
            background: 'rgba(255,255,255,0.04)',
            border: '1px solid rgba(255,255,255,0.06)',
            color: '#64748B',
          }}
        >
          Ctrl + Enter to parse
        </span>
      </div>

      {/* Textarea Input */}
      <div className="relative">
        <textarea
          value={prompt}
          onChange={(e) => onChange(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="e.g. 'Trim the opening 2.5 seconds, crop to 9:16 portrait for TikTok, increase volume by 50%, and burn subtitles'..."
          className="prompt-input pr-12 text-sm leading-relaxed"
          rows={3}
        />
        <button
          onClick={onAnalyze}
          disabled={!prompt.trim() || isLoading}
          className="absolute right-3 bottom-4 btn text-xs py-2 px-4 shadow-lg disabled:opacity-50 disabled:cursor-not-allowed font-bold"
          title="Interpret prompt into an editable execution plan"
          style={{
            background: (!prompt.trim() || isLoading)
              ? 'rgba(255,255,255,0.05)'
              : 'linear-gradient(135deg, #8B5CF6 0%, #EC4899 100%)',
            color: '#fff',
            boxShadow: (!prompt.trim() || isLoading)
              ? 'none'
              : '0 4px 16px rgba(139,92,246,0.35)',
          }}
        >
          {isLoading ? (
            <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
          ) : (
            <>
              <span>Analyze</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </>
          )}
        </button>
      </div>

      {/* Suggested Repair or Warning Notice */}
      {suggestedRepair && (
        <div
          className="p-4 rounded-2xl flex items-start gap-3 animate-fade-in-up"
          style={{
            background: 'linear-gradient(135deg, rgba(251,191,36,0.08) 0%, rgba(251,146,60,0.05) 100%)',
            border: '1px solid rgba(251,191,36,0.25)',
          }}
        >
          <AlertTriangle className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />
          <div className="text-xs">
            <span className="font-bold text-amber-300">Prompt Repair Suggestion:</span>
            <p className="text-amber-200/90 mt-0.5">{suggestedRepair}</p>
            <button
              onClick={() => {
                const match = suggestedRepair.match(/'([^']+)'/);
                if (match && match[1]) {
                  onChange(match[1]);
                }
              }}
              className="mt-2 text-[11px] font-bold text-amber-300 underline hover:text-white transition-colors"
            >
              Apply Suggested Prompt
            </button>
          </div>
        </div>
      )}

      {/* Example Prompt Chips */}
      <div>
        <div className="flex items-center gap-2 mb-2.5 text-xs text-[#64748B]">
          <Wand2 className="w-3.5 h-3.5 text-pink-400" />
          <span className="font-semibold">Quick prompt ideas:</span>
        </div>
        <div className="flex flex-wrap gap-2">
          {exampleChips.map((chip, idx) => (
            <button
              key={idx}
              onClick={() => onChange(chip)}
              className="prompt-chip"
            >
              {chip}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
};
