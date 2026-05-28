// Upload page — drag-and-drop a chest X-ray for lung cancer analysis

import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { Upload, Scan, FileWarning, Info, XCircle, ShieldX, CheckCircle2 } from 'lucide-react';
import ImageUploader from '../components/ImageUploader';
import LoadingSpinner from '../components/LoadingSpinner';
import { predictImage } from '../services/api';

export default function UploadPage() {
    const navigate = useNavigate();
    const [selectedFile, setSelectedFile] = useState(null);
    const [isAnalyzing, setIsAnalyzing] = useState(false);
    const [error, setError] = useState(null);
    const [rejection, setRejection] = useState(null);

    const handleAnalyze = async () => {
        if (!selectedFile) return;

        setIsAnalyzing(true);
        setError(null);
        setRejection(null);

        try {
            const result = await predictImage(selectedFile);
            navigate('/results', { state: { result } });
        } catch (err) {
            console.error('Analysis failed:', err);

            // check if this is a chest X-ray rejection (not a generic error)
            const responseData = err.response?.data;
            if (responseData?.is_chest_xray === false) {
                setRejection({
                    reason: responseData.rejection_reason,
                    checks: responseData.validation_checks || []
                });
            } else {
                setError(
                    responseData?.error ||
                    'Analysis failed. Please check if the backend server is running.'
                );
            }
            setIsAnalyzing(false);
        }
    };

    return (
        <div className="max-w-3xl mx-auto space-y-6">
            <motion.div
                initial={{ opacity: 0, y: -20 }}
                animate={{ opacity: 1, y: 0 }}
            >
                <h1 className="text-3xl font-bold text-white mb-2 flex items-center gap-3">
                    <Upload className="w-8 h-8 text-primary-400" />
                    Upload Chest X-Ray for Cancer Analysis
                </h1>
                <p className="text-dark-400">
                    Upload a chest X-ray image for AI-powered lung cancer detection with explainable Grad-CAM results.
                </p>
            </motion.div>

            <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.1 }}
                className="glass-card p-6"
            >
                <ImageUploader
                    onFileSelect={(file) => {
                        setSelectedFile(file);
                        setRejection(null);
                        setError(null);
                    }}
                    isLoading={isAnalyzing}
                />

                {selectedFile && !isAnalyzing && (
                    <motion.div
                        initial={{ opacity: 0, y: 10 }}
                        animate={{ opacity: 1, y: 0 }}
                        className="mt-6 flex justify-center"
                    >
                        <button
                            onClick={handleAnalyze}
                            className="btn-primary flex items-center gap-3 text-lg px-8 py-4"
                        >
                            <Scan className="w-5 h-5" />
                            Analyze with AI
                        </button>
                    </motion.div>
                )}

                {isAnalyzing && (
                    <div className="mt-6">
                        <LoadingSpinner message="Running AI Analysis (this may take a moment)..." />
                    </div>
                )}
            </motion.div>

            {/* chest X-ray rejection card */}
            {rejection && (
                <motion.div
                    initial={{ opacity: 0, y: 10, scale: 0.98 }}
                    animate={{ opacity: 1, y: 0, scale: 1 }}
                    className="glass-card p-6 border border-violet-500/30 bg-violet-900/10"
                >
                    <div className="flex items-start gap-4">
                        <div className="w-12 h-12 rounded-xl bg-violet-500/15 flex items-center justify-center flex-shrink-0">
                            <ShieldX className="w-6 h-6 text-violet-400" />
                        </div>
                        <div className="flex-1">
                            <h3 className="text-violet-300 font-bold text-lg mb-1">
                                Not a Chest X-Ray
                            </h3>
                            <p className="text-violet-400/80 text-sm mb-4">
                                Our validation system detected that the uploaded image is not a valid chest X-ray. 
                                Please upload a proper PA (posteroanterior) or AP (anteroposterior) chest radiograph.
                            </p>

                            {/* show individual check results */}
                            {rejection.checks.length > 0 && (
                                <div className="space-y-2 mb-4">
                                    <p className="text-dark-400 text-xs uppercase tracking-wider font-medium">
                                        Validation Checks
                                    </p>
                                    {rejection.checks.map((check, idx) => (
                                        <div
                                            key={idx}
                                            className="flex items-center gap-2 text-sm"
                                        >
                                            {check.passed ? (
                                                <CheckCircle2 className="w-4 h-4 text-emerald-400 flex-shrink-0" />
                                            ) : (
                                                <XCircle className="w-4 h-4 text-red-400 flex-shrink-0" />
                                            )}
                                            <span className={check.passed ? 'text-dark-300' : 'text-red-300'}>
                                                {check.name}
                                            </span>
                                            <span className="text-dark-500 text-xs ml-auto">
                                                {check.passed ? 'Passed' : 'Failed'}
                                            </span>
                                        </div>
                                    ))}
                                </div>
                            )}

                            <button
                                onClick={() => {
                                    setRejection(null);
                                    setSelectedFile(null);
                                }}
                                className="px-4 py-2 rounded-xl bg-violet-500/15 text-violet-300 text-sm font-medium hover:bg-violet-500/25 transition-all border border-violet-500/20"
                            >
                                Try Another Image
                            </button>
                        </div>
                    </div>
                </motion.div>
            )}

            {error && (
                <motion.div
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="glass-card p-5 border-red-800/30 bg-red-900/10"
                >
                    <div className="flex items-start gap-3">
                        <FileWarning className="w-5 h-5 text-red-400 mt-0.5 flex-shrink-0" />
                        <div>
                            <h3 className="text-red-300 font-semibold mb-1">Analysis Failed</h3>
                            <p className="text-red-400/80 text-sm">{error}</p>
                        </div>
                    </div>
                </motion.div>
            )}

            {/* how it works section */}
            <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.2 }}
                className="glass-card p-5"
            >
                <div className="flex items-start gap-3">
                    <Info className="w-5 h-5 text-accent-400 mt-0.5 flex-shrink-0" />
                    <div>
                        <h3 className="text-white font-semibold mb-2">How it works</h3>
                        <ol className="text-dark-400 text-sm space-y-2">
                            <li className="flex items-start gap-2">
                                <span className="w-5 h-5 rounded-full bg-primary-600/20 text-primary-400 text-xs flex items-center justify-center flex-shrink-0 mt-0.5">1</span>
                                <span>Upload a chest X-ray image (PNG, JPG, JPEG, DICOM converted)</span>
                            </li>
                            <li className="flex items-start gap-2">
                                <span className="w-5 h-5 rounded-full bg-violet-600/20 text-violet-400 text-xs flex items-center justify-center flex-shrink-0 mt-0.5">2</span>
                                <span>Image is validated to ensure it's a real chest X-ray (OOD detection)</span>
                            </li>
                            <li className="flex items-start gap-2">
                                <span className="w-5 h-5 rounded-full bg-primary-600/20 text-primary-400 text-xs flex items-center justify-center flex-shrink-0 mt-0.5">3</span>
                                <span>Image is preprocessed (resize to 224×224, normalize with ImageNet stats)</span>
                            </li>
                            <li className="flex items-start gap-2">
                                <span className="w-5 h-5 rounded-full bg-primary-600/20 text-primary-400 text-xs flex items-center justify-center flex-shrink-0 mt-0.5">4</span>
                                <span>DenseNet121 model runs inference and outputs NORMAL / CANCER with confidence scores</span>
                            </li>
                            <li className="flex items-start gap-2">
                                <span className="w-5 h-5 rounded-full bg-primary-600/20 text-primary-400 text-xs flex items-center justify-center flex-shrink-0 mt-0.5">5</span>
                                <span>Grad-CAM generates visual explanation highlighting suspicious tumour regions</span>
                            </li>
                            <li className="flex items-start gap-2">
                                <span className="w-5 h-5 rounded-full bg-primary-600/20 text-primary-400 text-xs flex items-center justify-center flex-shrink-0 mt-0.5">6</span>
                                <span>If confidence is below 65%, the result is flagged as "Needs Clinical Review" — always consult an oncologist</span>
                            </li>
                        </ol>
                    </div>
                </div>
            </motion.div>
        </div>
    );
}
