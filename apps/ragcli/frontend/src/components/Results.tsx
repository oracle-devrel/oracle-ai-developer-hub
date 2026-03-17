import React from 'react';
import { FileText, Sparkles } from 'lucide-react';
import { motion } from 'framer-motion';

interface Chunk {
    chunk_id: string;
    text: string;
    similarity_score: number;
}

interface ResultsProps {
    response: string | null;
    chunks: Chunk[];
}

export const Results: React.FC<ResultsProps> = ({ response, chunks }) => {
    if (!response && chunks.length === 0) return null;

    return (
        <div className="w-full max-w-4xl mx-auto">
            {response && (
                <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="mb-8"
                >
                    <div className="flex items-center space-x-2 mb-4 text-gray-800">
                        <Sparkles className="h-5 w-5 text-primary-600" />
                        <h2 className="text-xl font-medium font-sans">AI Response</h2>
                    </div>
                    <div className="bg-white p-6 rounded-2xl shadow-sm border border-gray-100 text-gray-800 leading-relaxed text-lg">
                        {response}
                    </div>
                </motion.div>
            )}

            {chunks.length > 0 && (
                <motion.div
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    transition={{ delay: 0.2 }}
                >
                    <h3 className="text-sm uppercase tracking-wider text-gray-500 font-semibold mb-4 ml-1">Sources</h3>
                    <div className="grid gap-4 md:grid-cols-2">
                        {chunks.map((chunk, i) => (
                            <div key={chunk.chunk_id || i} className="bg-gray-50 p-4 rounded-xl border border-gray-200 hover:bg-white hover:shadow-md transition-all duration-200">
                                <div className="flex items-center justify-between mb-2">
                                    <div className="flex items-center space-x-2 text-gray-600">
                                        <FileText className="h-4 w-4" />
                                        <span className="text-xs font-medium">Context {i + 1}</span>
                                    </div>
                                    <span className="text-xs text-primary-600 font-medium bg-primary-50 px-2 py-0.5 rounded-full">
                                        {Math.round(chunk.similarity_score * 100)}% match
                                    </span>
                                </div>
                                <p className="text-sm text-gray-600 line-clamp-4 font-mono">
                                    {chunk.text}
                                </p>
                            </div>
                        ))}
                    </div>
                </motion.div>
            )}
        </div>
    );
};
