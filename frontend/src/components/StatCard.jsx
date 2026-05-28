// Dashboard stat card — icon, label, big number, optional trend arrow

import React from 'react';
import { motion } from 'framer-motion';

export default function StatCard({ icon: Icon, label, value, trend, color = 'primary', delay = 0 }) {
    const colorMap = {
        primary: 'from-primary-500/20 to-primary-600/10 border-primary-500/20',
        accent: 'from-accent-500/20 to-accent-600/10 border-accent-500/20',
        green: 'from-emerald-500/20 to-emerald-600/10 border-emerald-500/20',
        orange: 'from-orange-500/20 to-orange-600/10 border-orange-500/20',
    };

    const iconColorMap = {
        primary: 'text-primary-400',
        accent: 'text-accent-400',
        green: 'text-emerald-400',
        orange: 'text-orange-400',
    };

    return (
        <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay }}
            className={`glass-card-hover p-6 bg-gradient-to-br ${colorMap[color]} border`}
        >
            <div className="flex items-start justify-between">
                <div>
                    <p className="text-dark-400 text-sm font-medium mb-1">{label}</p>
                    <p className="text-3xl font-bold text-white">{value}</p>
                    {trend && (
                        <p className={`text-xs mt-2 ${trend > 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                            {trend > 0 ? '↑' : '↓'} {Math.abs(trend)}% from last
                        </p>
                    )}
                </div>
                <div className={`p-3 rounded-xl bg-dark-800/60 ${iconColorMap[color]}`}>
                    <Icon className="w-6 h-6" />
                </div>
            </div>
        </motion.div>
    );
}
