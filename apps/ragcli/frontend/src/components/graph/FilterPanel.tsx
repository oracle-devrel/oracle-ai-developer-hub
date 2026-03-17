import { useState, useEffect } from 'react';
import { SlidersHorizontal, ChevronDown, ChevronUp } from 'lucide-react';
import type { GraphFilters } from '../../hooks/useGraphData';

interface FilterPanelProps {
  filters: GraphFilters;
  onApply: (filters: Partial<GraphFilters>) => void;
  loading: boolean;
}

export function FilterPanel({ filters, onApply, loading }: FilterPanelProps) {
  const [collapsed, setCollapsed] = useState(false);
  const [localFilters, setLocalFilters] = useState(filters);

  useEffect(() => {
    setLocalFilters(filters);
  }, [filters]);

  const handleApply = () => {
    onApply(localFilters);
  };

  return (
    <div className="absolute top-4 right-20 z-10 w-64">
      <div className="bg-surface border border-border-default rounded-lg shadow-lg overflow-hidden">
        <button
          onClick={() => setCollapsed(!collapsed)}
          className="w-full px-4 py-3 flex items-center justify-between text-[#e4e4ed] hover:bg-[#1c1c28] transition-colors"
        >
          <span className="flex items-center gap-2 text-sm font-medium font-display">
            <SlidersHorizontal size={14} className="text-accent" />
            Filters
          </span>
          {collapsed ? <ChevronDown size={14} /> : <ChevronUp size={14} />}
        </button>

        {!collapsed && (
          <div className="px-4 pb-4 space-y-4">
            <div>
              <label className="text-xs text-[#8888a0] font-mono block mb-1">
                Min Similarity: {localFilters.minSimilarity.toFixed(2)}
              </label>
              <input
                type="range"
                min="0"
                max="1"
                step="0.05"
                value={localFilters.minSimilarity}
                onChange={(e) => setLocalFilters(f => ({ ...f, minSimilarity: parseFloat(e.target.value) }))}
                className="w-full accent-accent"
              />
            </div>

            <div>
              <label className="text-xs text-[#8888a0] font-mono block mb-1">
                Top-K Neighbors: {localFilters.topK}
              </label>
              <input
                type="range"
                min="1"
                max="50"
                step="1"
                value={localFilters.topK}
                onChange={(e) => setLocalFilters(f => ({ ...f, topK: parseInt(e.target.value) }))}
                className="w-full accent-accent"
              />
            </div>

            <div>
              <label className="text-xs text-[#8888a0] font-mono block mb-1">
                Max Nodes: {localFilters.limit}
              </label>
              <input
                type="range"
                min="10"
                max="2000"
                step="10"
                value={localFilters.limit}
                onChange={(e) => setLocalFilters(f => ({ ...f, limit: parseInt(e.target.value) }))}
                className="w-full accent-accent"
              />
            </div>

            <button
              onClick={handleApply}
              disabled={loading}
              className="w-full py-2 rounded-lg bg-accent hover:bg-accent-dim text-white text-sm font-medium transition-colors disabled:opacity-50"
            >
              {loading ? 'Loading...' : 'Apply Filters'}
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
