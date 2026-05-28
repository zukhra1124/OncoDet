// Shows the Grad-CAM results — lets you toggle between
// the overlay, original X-ray, and raw heatmap views

import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { Eye, Layers, Flame } from 'lucide-react';

const views = [
    { id: 'overlay', label: 'Grad-CAM Overlay', icon: Layers },
    { id: 'original', label: 'Original X-Ray', icon: Eye },
    { id: 'heatmap', label: 'Raw Heatmap', icon: Flame },
];

export default function GradCamViewer({ originalImage, overlayImage, heatmapImage }) {
    const [activeView, setActiveView] = useState('overlay');

    const getActiveImage = () => {
        switch (activeView) {
            case 'overlay': return overlayImage;
            case 'original': return originalImage;
            case 'heatmap': return heatmapImage;
            default: return overlayImage;
        }
    };

    return (
        <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.3 }}
            className="glass-card p-6"
        >
            <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
                <Layers className="w-5 h-5 text-accent-400" />
                Explainable AI — Grad-CAM Visualization
            </h3>

            {/* view toggle buttons */}
            <div className="flex gap-2 mb-4">
                {views.map(({ id, label, icon: Icon }) => (
                    <button
                        key={id}
                        onClick={() => setActiveView(id)}
                        className={`flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-medium transition-all duration-200 ${activeView === id
                                ? 'bg-primary-600/20 text-primary-300 border border-primary-500/30'
                                : 'text-dark-400 hover:text-dark-200 bg-dark-800/40 border border-transparent'
                            }`}
                    >
                        <Icon className="w-4 h-4" />
                        {label}
                    </button>
                ))}
            </div>

            {/* the image */}
            <div className="relative rounded-xl overflow-hidden bg-dark-900/60 border border-dark-700/50">
                <motion.img
                    key={activeView}
                    src={getActiveImage()}
                    alt={`${activeView} view`}
                    className="w-full max-h-96 object-contain mx-auto"
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    transition={{ duration: 0.3 }}
                />
            </div>

            {/* colour legend */}
            <div className="mt-4 flex items-center justify-center gap-6 text-xs text-dark-400">
                <div className="flex items-center gap-2">
                    <div className="w-3 h-3 rounded-full bg-blue-500" />
                    <span>Low Activation</span>
                </div>
                <div className="flex items-center gap-2">
                    <div className="w-3 h-3 rounded-full bg-green-500" />
                    <span>Medium</span>
                </div>
                <div className="flex items-center gap-2">
                    <div className="w-3 h-3 rounded-full bg-yellow-500" />
                    <span>High</span>
                </div>
                <div className="flex items-center gap-2">
                    <div className="w-3 h-3 rounded-full bg-red-500" />
                    <span>Critical Region</span>
                </div>
            </div>
        </motion.div>
    );
}
