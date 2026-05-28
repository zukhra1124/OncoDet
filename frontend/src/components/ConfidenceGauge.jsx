// Circular gauge that shows the model's confidence score
// Colour changes based on confidence level (green/yellow/red)

import React, { useEffect, useState } from 'react';
import { motion } from 'framer-motion';

export default function ConfidenceGauge({ confidence = 0, size = 180 }) {
    const [animatedValue, setAnimatedValue] = useState(0);

    const radius = (size - 20) / 2;
    const circumference = 2 * Math.PI * radius;
    const strokeDashoffset = circumference - (animatedValue / 100) * circumference;

    useEffect(() => {
        const timer = setTimeout(() => setAnimatedValue(confidence), 300);
        return () => clearTimeout(timer);
    }, [confidence]);

    const getColor = (val) => {
        if (val >= 80) return { stroke: '#10b981', text: 'text-emerald-400', label: 'High Confidence' };
        if (val >= 60) return { stroke: '#f59e0b', text: 'text-amber-400', label: 'Moderate' };
        return { stroke: '#ef4444', text: 'text-red-400', label: 'Needs Review' };
    };

    const colorInfo = getColor(confidence);

    return (
        <motion.div
            initial={{ opacity: 0, scale: 0.8 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.6, delay: 0.2 }}
            className="flex flex-col items-center"
        >
            <div className="relative" style={{ width: size, height: size }}>
                <svg width={size} height={size} className="transform -rotate-90">
                    {/* background ring */}
                    <circle
                        cx={size / 2}
                        cy={size / 2}
                        r={radius}
                        stroke="#1e293b"
                        strokeWidth="12"
                        fill="none"
                    />
                    {/* coloured progress ring */}
                    <circle
                        cx={size / 2}
                        cy={size / 2}
                        r={radius}
                        stroke={colorInfo.stroke}
                        strokeWidth="12"
                        fill="none"
                        className="gauge-ring"
                        strokeDasharray={circumference}
                        strokeDashoffset={strokeDashoffset}
                        style={{ filter: `drop-shadow(0 0 6px ${colorInfo.stroke}40)` }}
                    />
                </svg>

                {/* percentage in the middle */}
                <div className="absolute inset-0 flex flex-col items-center justify-center">
                    <span className={`text-4xl font-bold ${colorInfo.text}`}>
                        {animatedValue.toFixed(1)}%
                    </span>
                    <span className="text-dark-400 text-xs mt-1">{colorInfo.label}</span>
                </div>
            </div>
        </motion.div>
    );
}
