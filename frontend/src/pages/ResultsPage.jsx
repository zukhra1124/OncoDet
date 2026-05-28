// Results page — shows prediction, confidence gauge, Grad-CAM, and details

import React from 'react';
import { useLocation, Link, Navigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import {
    CheckCircle2, AlertTriangle, ArrowLeft, Upload,
    ShieldCheck, ShieldAlert, BarChart3, BadgeCheck
} from 'lucide-react';
import ConfidenceGauge from '../components/ConfidenceGauge';
import GradCamViewer from '../components/GradCamViewer';

export default function ResultsPage() {
    const location = useLocation();
    const result = location.state?.result;

    // if someone lands here directly without analysing anything, send them to upload
    if (!result) {
        return <Navigate to="/upload" replace />;
    }

    const isCancer = result.prediction === 'CANCER';
    const needsReview = result.needs_review;

    return (
        <div className="max-w-5xl mx-auto space-y-6">
            <motion.div
                initial={{ opacity: 0, y: -20 }}
                animate={{ opacity: 1, y: 0 }}
                className="flex items-center justify-between"
            >
                <div>
                    <h1 className="text-3xl font-bold text-white mb-2">Analysis Results</h1>
                    <p className="text-dark-400">AI-powered diagnostic analysis complete</p>
                </div>
                <Link
                    to="/upload"
                    className="btn-secondary flex items-center gap-2"
                >
                    <Upload className="w-4 h-4" />
                    New Analysis
                </Link>
            </motion.div>

            {/* main prediction card */}
            <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.1 }}
                className={`glass-card p-6 border ${needsReview
                        ? 'border-amber-500/30 bg-amber-900/5'
                        : isCancer
                            ? 'border-red-500/30 bg-red-900/5'
                            : 'border-emerald-500/30 bg-emerald-900/5'
                    }`}
            >
                <div className="flex flex-col md:flex-row items-center gap-8">
                    <div className="flex-1 text-center md:text-left">
                        <div className="flex items-center justify-center md:justify-start gap-3 mb-3">
                            {needsReview ? (
                                <ShieldAlert className="w-8 h-8 text-amber-400" />
                            ) : isCancer ? (
                                <AlertTriangle className="w-8 h-8 text-red-400" />
                            ) : (
                                <ShieldCheck className="w-8 h-8 text-emerald-400" />
                            )}
                            <span className={`text-4xl font-bold ${needsReview ? 'text-amber-400' : isCancer ? 'text-red-400' : 'text-emerald-400'
                                }`}>
                                {result.prediction}
                            </span>
                        </div>

                        {needsReview && (
                            <motion.div
                                initial={{ opacity: 0, scale: 0.9 }}
                                animate={{ opacity: 1, scale: 1 }}
                                className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-amber-900/30 border border-amber-500/30 text-amber-300 text-sm font-medium mb-4"
                            >
                                <AlertTriangle className="w-4 h-4" />
                                Needs Clinical Review — Low Confidence
                            </motion.div>
                        )}

                        {/* show that the image passed chest X-ray validation */}
                        {result.is_chest_xray && (
                            <motion.div
                                initial={{ opacity: 0, scale: 0.9 }}
                                animate={{ opacity: 1, scale: 1 }}
                                transition={{ delay: 0.2 }}
                                className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-violet-900/25 border border-violet-500/25 text-violet-300 text-xs font-medium mb-4 ml-2"
                            >
                                <BadgeCheck className="w-3.5 h-3.5" />
                                Validated Chest X-Ray
                            </motion.div>
                        )}

                        {/* per-class probability bars */}
                        <div className="space-y-3 mt-4">
                            {result.probabilities && Object.entries(result.probabilities).map(([cls, prob]) => (
                                <div key={cls} className="space-y-1">
                                    <div className="flex justify-between text-sm">
                                        <span className="text-dark-300 font-medium">{cls}</span>
                                        <span className="text-dark-400">{prob}%</span>
                                    </div>
                                    <div className="w-full bg-dark-800 rounded-full h-2.5">
                                        <motion.div
                                            initial={{ width: 0 }}
                                            animate={{ width: `${prob}%` }}
                                            transition={{ duration: 1, delay: 0.5 }}
                                            className={`h-2.5 rounded-full ${cls === 'CANCER' ? 'bg-gradient-to-r from-red-500 to-red-400' : 'bg-gradient-to-r from-emerald-500 to-emerald-400'
                                                }`}
                                        />
                                    </div>
                                </div>
                            ))}
                        </div>
                    </div>

                    <div className="flex-shrink-0">
                        <ConfidenceGauge confidence={result.confidence} size={200} />
                    </div>
                </div>
            </motion.div>

            {/* Grad-CAM images */}
            {result.gradcam_image && (
                <GradCamViewer
                    originalImage={result.original_image}
                    overlayImage={result.gradcam_image}
                    heatmapImage={result.heatmap_image}
                />
            )}

            {/* extra details */}
            <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.4 }}
                className="glass-card p-6"
            >
                <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
                    <BarChart3 className="w-5 h-5 text-primary-400" />
                    Analysis Details
                </h3>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                    <div className="bg-dark-800/40 rounded-xl p-4">
                        <p className="text-dark-500 text-xs uppercase tracking-wider">Confidence</p>
                        <p className="text-white font-bold text-lg mt-1">{result.confidence}%</p>
                    </div>
                    <div className="bg-dark-800/40 rounded-xl p-4">
                        <p className="text-dark-500 text-xs uppercase tracking-wider">Threshold</p>
                        <p className="text-white font-bold text-lg mt-1">{(result.threshold * 100)}%</p>
                    </div>
                    <div className="bg-dark-800/40 rounded-xl p-4">
                        <p className="text-dark-500 text-xs uppercase tracking-wider">Status</p>
                        <p className={`font-bold text-lg mt-1 ${needsReview ? 'text-amber-400' : 'text-emerald-400'}`}>
                            {result.status === 'needs_review' ? 'Review' : 'Confirmed'}
                        </p>
                    </div>
                    <div className="bg-dark-800/40 rounded-xl p-4">
                        <p className="text-dark-500 text-xs uppercase tracking-wider">Timestamp</p>
                        <p className="text-white font-medium text-sm mt-1">
                            {new Date(result.timestamp).toLocaleTimeString()}
                        </p>
                    </div>
                </div>
            </motion.div>

            <div className="flex justify-center pt-4">
                <Link to="/upload" className="btn-secondary flex items-center gap-2">
                    <ArrowLeft className="w-4 h-4" />
                    Analyze Another Image
                </Link>
            </div>
        </div>
    );
}
