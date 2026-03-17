import React, { useEffect, useRef } from 'react';


interface ChunkResult {
    chunk_id: string;
    document_id: string;
    text: string;
    similarity_score: number;
    embedding?: number[];
}

interface SearchVisualizerProps {
    queryEmbedding?: number[];
    chunks: ChunkResult[];
}

export const SearchVisualizer: React.FC<SearchVisualizerProps> = ({ queryEmbedding, chunks }) => {
    const canvasRef = useRef<HTMLCanvasElement>(null);
    const containerRef = useRef<HTMLDivElement>(null);

    // Color map function: -1 (blue) to 0 (black) to 1 (red)
    // Adjust sensitivity based on typical embedding value range (often small like -0.1 to 0.1 for high dims)
    const getColor = (value: number) => {
        // Amplify value for visibility
        const amplified = value * 10;
        const r = Math.max(0, Math.min(255, amplified * 255));
        const b = Math.max(0, Math.min(255, -amplified * 255));
        return `rgb(${r}, 0, ${b})`;
    };

    // Draw heatmap
    useEffect(() => {
        if (!canvasRef.current || !queryEmbedding || chunks.length === 0) return;

        const canvas = canvasRef.current;
        const ctx = canvas.getContext('2d');
        if (!ctx) return;

        const width = canvas.width;

        // Rows: Query | Gap | Result 1 | Contrib 1 | ...
        const rowHeight = 20;
        const gap = 5;
        const rowsPerResult = 2; // Embedding + Contribution

        const totalHeight = rowHeight + gap + (chunks.length * (rowHeight * rowsPerResult + gap));
        canvas.height = totalHeight;

        // Clear
        ctx.fillStyle = '#0f172a'; // Slate-900 bg
        ctx.fillRect(0, 0, width, totalHeight);

        const dim = queryEmbedding.length;
        const barWidth = width / dim;

        // Draw Query
        for (let i = 0; i < dim; i++) {
            ctx.fillStyle = getColor(queryEmbedding[i]);
            ctx.fillRect(i * barWidth, 0, barWidth, rowHeight);
        }

        // Draw Label
        ctx.fillStyle = 'white';
        ctx.font = '10px monospace';
        ctx.fillText('Query Vector', 5, rowHeight - 5);

        let y = rowHeight + gap;

        chunks.forEach((chunk, idx) => {
            const chunkEmb = chunk.embedding;
            if (!chunkEmb) return;

            // Draw Chunk Embedding
            for (let i = 0; i < dim; i++) {
                ctx.fillStyle = getColor(chunkEmb[i]);
                ctx.fillRect(i * barWidth, y, barWidth, rowHeight);
            }
            ctx.fillStyle = 'rgba(255, 255, 255, 0.8)';
            ctx.fillText(`Result #${idx + 1} (${chunk.similarity_score.toFixed(4)})`, 5, y + rowHeight - 5);

            y += rowHeight;

            // Draw Contribution (Element-wise Product)
            // Dot Product = Sum(q[i] * d[i])
            // We visualize q[i] * d[i]
            for (let i = 0; i < dim; i++) {
                const contribution = queryEmbedding[i] * chunkEmb[i];
                // Contribution is usually positive for matches, negative for mismatches
                // We use same color scale but maybe brighter?
                ctx.fillStyle = getColor(contribution * 5); // Amplify more?
                ctx.fillRect(i * barWidth, y, barWidth, rowHeight / 2); // Thinner line
            }
            ctx.fillStyle = 'rgba(100, 255, 100, 0.8)';
            ctx.fillText(`Match Contribution`, 5, y + (rowHeight / 2) - 2);

            y += (rowHeight / 2) + gap;
        });

    }, [queryEmbedding, chunks]);

    if (!queryEmbedding || chunks.length === 0) return null;

    return (
        <div className="w-full max-w-4xl mx-auto mb-8 bg-slate-900 rounded-xl overflow-hidden shadow-2xl border border-slate-700">
            <div className="p-4 border-b border-slate-700 flex justify-between items-center">
                <h3 className="text-white font-medium flex items-center gap-2">
                    <span className="w-2 h-2 rounded-full bg-green-500 animate-pulse"></span>
                    Vector Space Visualization
                </h3>
                <span className="text-xs text-slate-400 font-mono">
                    {queryEmbedding.length} Dimensions (R: Pos, B: Neg)
                </span>
            </div>
            <div className="p-4 overflow-x-auto" ref={containerRef}>
                <canvas
                    ref={canvasRef}
                    width={containerRef.current?.clientWidth || 800}
                    height={300}
                    className="w-full h-auto"
                />
            </div>
            <div className="px-4 py-2 bg-slate-800 text-xs text-slate-400 flex justify-between font-mono">
                <div>Top: Query Vector</div>
                <div>Middle: Result Vector</div>
                <div>Bottom: Contribution (Q × D)</div>
            </div>
        </div>
    );
};
