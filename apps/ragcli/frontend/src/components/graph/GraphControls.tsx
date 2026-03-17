import { ZoomIn, ZoomOut, Maximize2, Play, Pause } from 'lucide-react';

interface GraphControlsProps {
  onZoomIn: () => void;
  onZoomOut: () => void;
  onReset: () => void;
  onToggleLayout: () => void;
  layoutRunning: boolean;
}

export function GraphControls({ onZoomIn, onZoomOut, onReset, onToggleLayout, layoutRunning }: GraphControlsProps) {
  const btnClass = "w-9 h-9 flex items-center justify-center rounded-lg bg-elevated hover:bg-[#1c1c28] border border-border-subtle text-[#8888a0] hover:text-[#e4e4ed] transition-colors";

  return (
    <div className="absolute bottom-6 right-6 flex flex-col gap-2 z-10">
      <button onClick={onZoomIn} className={btnClass} title="Zoom In">
        <ZoomIn size={16} />
      </button>
      <button onClick={onZoomOut} className={btnClass} title="Zoom Out">
        <ZoomOut size={16} />
      </button>
      <button onClick={onReset} className={btnClass} title="Fit to Screen">
        <Maximize2 size={16} />
      </button>
      <button
        onClick={onToggleLayout}
        className={`${btnClass} ${layoutRunning ? 'animate-breathe border-accent' : ''}`}
        title={layoutRunning ? 'Pause Layout' : 'Resume Layout'}
      >
        {layoutRunning ? <Pause size={16} /> : <Play size={16} />}
      </button>
    </div>
  );
}
