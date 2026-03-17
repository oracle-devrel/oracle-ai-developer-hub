import { useState } from 'react';
import { Search } from 'lucide-react';

interface GraphSearchProps {
  onSearch: (query: string) => void;
  loading: boolean;
}

export function GraphSearch({ onSearch, loading }: GraphSearchProps) {
  const [query, setQuery] = useState('');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (query.trim()) {
      onSearch(query.trim());
    }
  };

  return (
    <div className="absolute top-4 right-4 z-10 w-80">
      <form onSubmit={handleSubmit} className="relative">
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search embeddings..."
          className="w-full bg-surface border border-border-default rounded-lg pl-10 pr-4 py-2.5 text-sm text-[#e4e4ed] placeholder-[#5a5a70] font-mono focus:outline-none focus:border-accent transition-colors"
        />
        <Search size={14} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-[#5a5a70]" />
        {loading && (
          <div className="absolute right-3.5 top-1/2 -translate-y-1/2">
            <div className="w-4 h-4 border-2 border-accent border-t-transparent rounded-full animate-spin" />
          </div>
        )}
      </form>
    </div>
  );
}
