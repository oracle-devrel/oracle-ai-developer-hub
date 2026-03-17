import React, { useState } from 'react';
import { Search } from 'lucide-react';

interface SearchBarProps {
    onSearch: (query: string) => void;
    isLoading?: boolean;
}

export const SearchBar: React.FC<SearchBarProps> = ({ onSearch, isLoading }) => {
    const [query, setQuery] = useState('');

    const handleSubmit = (e: React.FormEvent) => {
        e.preventDefault();
        if (query.trim()) {
            onSearch(query);
        }
    };

    return (
        <form onSubmit={handleSubmit} className="w-full max-w-2xl mx-auto mt-8 mb-8">
            <div className="relative group">
                <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none">
                    <Search className="h-5 w-5 text-gray-400 group-focus-within:text-primary-500 transition-colors" />
                </div>
                <input
                    type="text"
                    value={query}
                    onChange={(e) => setQuery(e.target.value)}
                    placeholder="Ask anything..."
                    className="block w-full pl-12 pr-4 py-3 bg-white border border-gray-200 rounded-full text-gray-900 placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-primary-100 focus:border-transparent shadow-google hover:shadow-google-hover transition-all duration-200 ease-in-out"
                    disabled={isLoading}
                />
                {isLoading && (
                    <div className="absolute inset-y-0 right-0 pr-4 flex items-center">
                        <div className="animate-spin h-5 w-5 border-2 border-primary-500 rounded-full border-t-transparent"></div>
                    </div>
                )}
            </div>
        </form>
    );
};
