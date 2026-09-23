import React, { useState } from 'react';
import { ChevronDown, ChevronUp } from 'lucide-react';
import { ThinkingOrb } from 'thinking-orbs';

interface ThinkingProcessCardProps {
  thinking: string;
  isStreaming?: boolean;
  durationSeconds?: number;
}

interface ThinkingStep {
  title: string;
  body: string;
}

export const ThinkingProcessCard: React.FC<ThinkingProcessCardProps> = ({
  thinking,
  isStreaming = false,
  durationSeconds
}) => {
  const [isExpanded, setIsExpanded] = useState<boolean>(isStreaming);

  // If no real thinking text, do NOT render a fake thinking block at all
  if (!thinking || !thinking.trim()) return null;

  // Clean raw thinking text and dynamically structure into cognitive steps
  const steps: ThinkingStep[] = React.useMemo(() => {
    let cleanText = thinking.trim();
    try {
      if (cleanText.startsWith('{') && cleanText.endsWith('}')) {
        const parsed = JSON.parse(cleanText);
        cleanText = parsed.reasoning || parsed.thought || parsed.plan || cleanText;
      }
    } catch {}

    const lines = cleanText.split('\n').map((l) => l.trim()).filter(Boolean);
    const parsedSteps: ThinkingStep[] = [];

    for (const line of lines) {
      if (line.startsWith('•') || line.startsWith('-') || line.startsWith('*') || /^\d+\./.test(line)) {
        const withoutBullet = line.replace(/^([•\-*]|\d+\.)\s*/, '').trim();
        const boldMatch = withoutBullet.match(/^\*\*([^*]+)\*\*[:\s]*(.*)$/);
        if (boldMatch) {
          parsedSteps.push({ title: boldMatch[1], body: boldMatch[2] || '' });
        } else if (withoutBullet.includes(':')) {
          const [t, ...rest] = withoutBullet.split(':');
          parsedSteps.push({ title: t.trim(), body: rest.join(':').trim() });
        } else {
          parsedSteps.push({ title: withoutBullet, body: '' });
        }
      } else {
        if (line.includes(':')) {
          const [t, ...rest] = line.split(':');
          parsedSteps.push({ title: t.trim(), body: rest.join(':').trim() });
        } else {
          const words = line.split(' ');
          if (words.length > 5) {
            const title = words.slice(0, 4).join(' ');
            const body = words.slice(4).join(' ');
            parsedSteps.push({ title, body });
          } else {
            parsedSteps.push({ title: line, body: '' });
          }
        }
      }
    }

    if (parsedSteps.length > 0) return parsedSteps;
    return [{ title: 'Reasoning trace', body: cleanText }];
  }, [thinking]);

  const formattedDuration = React.useMemo(() => {
    if (durationSeconds != null && durationSeconds > 0) {
      return `${durationSeconds.toFixed(1)}s`;
    }
    // Dynamic estimate based on thinking length to avoid static 1.4s
    const estimated = Math.max(0.5, Math.min(4.8, thinking.length / 160 + 0.3));
    return `${estimated.toFixed(1)}s`;
  }, [durationSeconds, thinking]);

  return (
    <div className="my-2 select-none">
      {/* Clean text header matching Image 1: "Thought for Xs ^" */}
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="group flex items-center gap-1.5 text-xs text-zinc-400 hover:text-zinc-200 transition-colors py-0.5 cursor-pointer"
      >
        <div className="w-4 h-4 flex items-center justify-center overflow-hidden">
          {/* Static paused orb once thinking is done */}
          <ThinkingOrb
            state={isStreaming ? 'working' : 'breathing'}
            size={20}
            color="#a1a1aa"
            theme="dark"
            paused={!isStreaming}
          />
        </div>
        <span className="font-sans font-medium text-zinc-400 group-hover:text-zinc-200">
          {isStreaming ? 'Thinking...' : `Thought for ${formattedDuration}`}
        </span>
        {isExpanded ? (
          <ChevronUp className="w-3.5 h-3.5 text-zinc-500 group-hover:text-zinc-300 ml-0.5" />
        ) : (
          <ChevronDown className="w-3.5 h-3.5 text-zinc-500 group-hover:text-zinc-300 ml-0.5" />
        )}
      </button>

      {/* Expanded structured steps */}
      {isExpanded && (
        <div className="space-y-3 pt-2.5 pb-1 pl-1 animate-slide-fade">
          {steps.map((step, idx) => (
            <div key={idx} className="space-y-0.5">
              <div className="flex items-center gap-2 text-xs font-semibold text-zinc-200 font-sans">
                <span className="text-zinc-500 font-bold">•</span>
                <span>{step.title}</span>
              </div>
              {step.body && (
                <p className="text-xs text-zinc-400 pl-3.5 leading-relaxed font-sans font-normal">
                  {step.body}
                </p>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
