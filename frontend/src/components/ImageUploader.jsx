// Drag-and-drop image upload zone with preview
// Also does client-side compression before sending to the backend

import React, { useCallback, useState } from 'react';
import { useDropzone } from 'react-dropzone';
import { Upload, X, FileImage, AlertCircle } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

// shrink large images before uploading so it's faster
// (a 5MB xray becomes ~200KB after this)
function compressImage(file, maxSize = 800, quality = 0.8) {
    return new Promise((resolve) => {
        // don't bother compressing small files
        if (file.size < 500 * 1024) {
            resolve(file);
            return;
        }

        const img = new Image();
        const canvas = document.createElement('canvas');
        const ctx = canvas.getContext('2d');

        img.onload = () => {
            let { width, height } = img;

            // scale down but keep aspect ratio
            if (width > maxSize || height > maxSize) {
                if (width > height) {
                    height = Math.round((height * maxSize) / width);
                    width = maxSize;
                } else {
                    width = Math.round((width * maxSize) / height);
                    height = maxSize;
                }
            }

            canvas.width = width;
            canvas.height = height;
            ctx.drawImage(img, 0, 0, width, height);

            canvas.toBlob(
                (blob) => {
                    if (blob) {
                        const compressedFile = new File([blob], file.name, {
                            type: 'image/jpeg',
                            lastModified: Date.now(),
                        });
                        resolve(compressedFile);
                    } else {
                        resolve(file);
                    }
                },
                'image/jpeg',
                quality
            );
        };

        img.onerror = () => resolve(file);
        img.src = URL.createObjectURL(file);
    });
}

export default function ImageUploader({ onFileSelect, isLoading = false }) {
    const [preview, setPreview] = useState(null);
    const [error, setError] = useState(null);

    const onDrop = useCallback(async (acceptedFiles, rejectedFiles) => {
        setError(null);

        if (rejectedFiles.length > 0) {
            setError('Invalid file type. Please upload a PNG, JPG, or JPEG image.');
            return;
        }

        if (acceptedFiles.length > 0) {
            const file = acceptedFiles[0];

            if (file.size > 16 * 1024 * 1024) {
                setError('File too large. Maximum size is 16MB.');
                return;
            }

            // show preview right away
            const reader = new FileReader();
            reader.onload = () => setPreview(reader.result);
            reader.readAsDataURL(file);

            // compress then pass to parent
            const compressedFile = await compressImage(file);
            onFileSelect(compressedFile);
        }
    }, [onFileSelect]);

    const { getRootProps, getInputProps, isDragActive } = useDropzone({
        onDrop,
        accept: {
            'image/png': ['.png'],
            'image/jpeg': ['.jpg', '.jpeg'],
            'image/bmp': ['.bmp'],
            'image/tiff': ['.tiff'],
        },
        maxFiles: 1,
        disabled: isLoading,
    });

    const clearPreview = (e) => {
        e.stopPropagation();
        setPreview(null);
        setError(null);
        onFileSelect(null);
    };

    return (
        <div className="w-full">
            <div
                {...getRootProps()}
                className={`relative border-2 border-dashed rounded-2xl p-8 text-center cursor-pointer transition-all duration-300
          ${isDragActive
                        ? 'border-primary-400 bg-primary-900/20'
                        : 'border-dark-600 hover:border-primary-500/50 hover:bg-dark-800/40'}
          ${isLoading ? 'opacity-50 pointer-events-none' : ''}
        `}
            >
                <input {...getInputProps()} />

                <AnimatePresence mode="wait">
                    {preview ? (
                        <motion.div
                            key="preview"
                            initial={{ opacity: 0, scale: 0.9 }}
                            animate={{ opacity: 1, scale: 1 }}
                            exit={{ opacity: 0, scale: 0.9 }}
                            className="relative"
                        >
                            <img
                                src={preview}
                                alt="X-ray preview"
                                className="max-h-64 mx-auto rounded-xl shadow-lg border border-dark-600"
                            />
                            <button
                                onClick={clearPreview}
                                className="absolute top-2 right-2 p-1.5 bg-dark-800/80 rounded-full hover:bg-red-600/80 transition-colors"
                            >
                                <X className="w-4 h-4" />
                            </button>
                            <p className="text-dark-400 text-sm mt-4">Click or drag to replace image</p>
                        </motion.div>
                    ) : (
                        <motion.div
                            key="empty"
                            initial={{ opacity: 0 }}
                            animate={{ opacity: 1 }}
                            exit={{ opacity: 0 }}
                            className="py-8"
                        >
                            <div className="w-16 h-16 mx-auto mb-4 rounded-2xl bg-gradient-to-br from-primary-600/20 to-accent-600/20 flex items-center justify-center">
                                {isDragActive ? (
                                    <FileImage className="w-8 h-8 text-primary-400 animate-bounce" />
                                ) : (
                                    <Upload className="w-8 h-8 text-dark-400" />
                                )}
                            </div>
                            <p className="text-lg font-medium text-dark-200 mb-2">
                                {isDragActive ? 'Drop the X-ray here' : 'Upload Chest X-Ray Image'}
                            </p>
                            <p className="text-dark-500 text-sm">
                                Drag & drop or click to browse • PNG, JPG, JPEG • Max 16MB
                            </p>
                        </motion.div>
                    )}
                </AnimatePresence>
            </div>

            <AnimatePresence>
                {error && (
                    <motion.div
                        initial={{ opacity: 0, y: -10 }}
                        animate={{ opacity: 1, y: 0 }}
                        exit={{ opacity: 0, y: -10 }}
                        className="mt-3 flex items-center gap-2 text-red-400 text-sm bg-red-900/20 border border-red-800/30 rounded-xl px-4 py-3"
                    >
                        <AlertCircle className="w-4 h-4 flex-shrink-0" />
                        {error}
                    </motion.div>
                )}
            </AnimatePresence>
        </div>
    );
}
