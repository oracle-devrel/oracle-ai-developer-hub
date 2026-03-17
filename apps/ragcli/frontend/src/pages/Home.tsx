import { useState } from 'react';
import axios from 'axios';
import { SearchBar } from '../components/SearchBar';
import { UploadArea } from '../components/UploadArea';
import { Results } from '../components/Results';
import { SearchVisualizer } from '../components/SearchVisualizer';

export function Home() {
  const [response, setResponse] = useState<string | null>(null);
  const [chunks, setChunks] = useState<any[]>([]);
  const [queryEmbedding, setQueryEmbedding] = useState<number[] | undefined>(undefined);
  const [isLoading, setIsLoading] = useState(false);
  const [isUploading, setIsUploading] = useState(false);

  const handleSearch = async (query: string) => {
    setIsLoading(true);
    setResponse(null);
    setChunks([]);
    setQueryEmbedding(undefined);
    try {
      const res = await axios.post('/api/query', {
        query,
        top_k: 5,
        min_similarity: 0.0,
        include_embeddings: true
      });
      setResponse(res.data.response);
      setChunks(res.data.chunks || []);
      setQueryEmbedding(res.data.query_embedding);
    } catch (error) {
      console.error("Search failed", error);
      setResponse("Sorry, I encountered an error while searching.");
    } finally {
      setIsLoading(false);
    }
  };

  const handleUpload = async (file: File) => {
    setIsUploading(true);
    const formData = new FormData();
    formData.append('file', file);
    try {
      await axios.post('/api/documents/upload', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
    } catch (error) {
      console.error("Upload failed", error);
      alert("Upload failed. Please check the backend connection.");
    } finally {
      setIsUploading(false);
    }
  };

  return (
    <main className="container mx-auto px-4 py-12 flex flex-col items-center">
      <div className="text-center mb-8">
        <h1 className="text-4xl font-medium text-gray-900 mb-2">
          How can I help you today?
        </h1>
        <p className="text-gray-500 text-lg">
          Upload documents and ask questions powered by RAG
        </p>
      </div>

      <SearchBar onSearch={handleSearch} isLoading={isLoading} />
      <UploadArea onUpload={handleUpload} isUploading={isUploading} />

      <div className="w-full border-t border-gray-100 my-8"></div>

      {response && (
        <div className="w-full max-w-4xl animate-in fade-in slide-in-from-bottom-4 duration-500">
          <SearchVisualizer queryEmbedding={queryEmbedding} chunks={chunks} />
        </div>
      )}

      <Results response={response} chunks={chunks} />
    </main>
  );
}
