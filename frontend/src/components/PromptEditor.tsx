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
    <div className="card p-6 flex flex-col gap-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-[#EFEDF8] border border-[#E6E2F0] flex items-center justify-center text-[#6654F0]">
            <Sparkles className="w-4 h-4" />
          </div>
          <div>
            <h3 className="text-sm font-bold text-[#191832]">Prompt Video Editor</h3>
            <p className="text-xs text-[#66627B]">Describe how you want your video transformed</p>
          </div>
        </div>
        <span className="text-[11px] text-[#8E8A9F] hidden sm:inline font-mono">Ctrl + Enter to parse</span>
      </div>

      {/* Textarea Input */}
      <div className="relative">
        <textarea
          value={prompt}
          onChange={(e) => onChange(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="e.g. 'Trim the opening 2.5 seconds, crop to 9:16 portrait for TikTok, increase volume by 50%, and burn subtitles'..."
          className="form-input pr-28 text-sm leading-relaxed min-h-[90px] resize-y"
          rows={3}
        />
        <button
          onClick={onAnalyze}
          disabled={!prompt.trim() || isLoading}
          className="absolute right-3 bottom-3 btn btn-primary text-xs py-2 px-3.5 shadow-sm disabled:opacity-50 disabled:cursor-not-allowed"
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
        <div className="p-3.5 rounded-xl border border-amber-200 bg-amber-50 flex items-start gap-3">
          <AlertTriangle className="w-4 h-4 text-amber-600 shrink-0 mt-0.5" />
          <div className="text-xs">
            <span className="font-bold text-amber-800">Prompt Repair Suggestion:</span>
            <p className="text-amber-700 mt-0.5">{suggestedRepair}</p>
            <button
              onClick={() => {
                const match = suggestedRepair.match(/'([^']+)'/);
                if (match && match[1]) {
                  onChange(match[1]);
                }
              }}
              className="mt-2 text-[11px] font-bold text-amber-900 underline hover:text-black"
            >
              Apply Suggested Prompt
            </button>
          </div>
        </div>
      )}

      {/* Example Prompt Chips */}
      <div>
        <div className="flex items-center gap-1.5 mb-2 text-xs text-[#64748B]">
          <Wand2 className="w-3 h-3 text-cyan-600" />
          <span>Quick prompt ideas:</span>
        </div>
        <div className="flex flex-wrap gap-2">
          {exampleChips.map((chip, idx) => (
            <button
              key={idx}
              onClick={() => onChange(chip)}
              className="px-2.5 py-1.5 rounded-lg bg-[#F1F5F9] hover:bg-indigo-50 border border-[#E2E8F0] hover:border-indigo-200 text-[#334155] hover:text-indigo-700 text-xs text-left transition-colors font-medium"
            >
              {chip}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
};
