import React, { useRef, useState } from 'react';
import { Upload, FileText } from 'lucide-react';
import { clsx } from 'clsx';

interface UploadAreaProps {
    onUpload: (file: File) => Promise<void>;
    isUploading?: boolean;
}

export const UploadArea: React.FC<UploadAreaProps> = ({ onUpload, isUploading }) => {
    const inputRef = useRef<HTMLInputElement>(null);
    const [dragActive, setDragActive] = useState(false);
    const [fileName, setFileName] = useState<string | null>(null);

    const handleDrag = (e: React.DragEvent) => {
        e.preventDefault();
        e.stopPropagation();
        if (e.type === "dragenter" || e.type === "dragover") {
            setDragActive(true);
        } else if (e.type === "dragleave") {
            setDragActive(false);
        }
    };

    const handleDrop = (e: React.DragEvent) => {
        e.preventDefault();
        e.stopPropagation();
        setDragActive(false);
        if (e.dataTransfer.files && e.dataTransfer.files[0]) {
            handleFile(e.dataTransfer.files[0]);
        }
    };

    const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        e.preventDefault();
        if (e.target.files && e.target.files[0]) {
            handleFile(e.target.files[0]);
        }
    };

    const handleFile = async (file: File) => {
        setFileName(file.name);
        await onUpload(file);
        setTimeout(() => setFileName(null), 3000); // Clear after 3s
    };

    return (
        <div className="w-full max-w-2xl mx-auto mb-8">
            <div
                className={clsx(
                    "relative border-2 border-dashed rounded-xl p-8 transition-all duration-200 ease-in-out flex flex-col items-center justify-center cursor-pointer bg-gray-50",
                    dragActive ? "border-primary-500 bg-primary-50" : "border-gray-300 hover:border-primary-300 hover:bg-gray-100",
                    isUploading && "opacity-50 cursor-not-allowed"
                )}
                onDragEnter={handleDrag}
                onDragLeave={handleDrag}
                onDragOver={handleDrag}
                onDrop={handleDrop}
                onClick={() => inputRef.current?.click()}
            >
                <input
                    ref={inputRef}
                    type="file"
                    className="hidden"
                    onChange={handleChange}
                    disabled={isUploading}
                />

                <div className="bg-white p-3 rounded-full shadow-sm mb-3">
                    <Upload className="h-6 w-6 text-primary-600" />
                </div>

                {fileName ? (
                    <div className="flex items-center space-x-2 text-primary-700 font-medium">
                        <FileText className="h-4 w-4" />
                        <span>{fileName} Uploaded!</span>
                    </div>
                ) : (
                    <div className="text-center">
                        <p className="text-gray-700 font-medium">
                            Drag & drop or <span className="text-primary-600 hover:underline">choose file</span>
                        </p>
                        <p className="text-sm text-gray-500 mt-1">
                            Supports PDF, TXT, MD
                        </p>
                    </div>
                )}
            </div>
        </div>
    );
};
