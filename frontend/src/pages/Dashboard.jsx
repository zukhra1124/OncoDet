// Home page — shows system overview, quick action buttons, and model info

import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { Link } from 'react-router-dom';
import {
    Activity, BrainCircuit, Shield, Upload, TrendingUp,
    Cpu, Database, Zap, ArrowRight, CheckCircle2, AlertTriangle
} from 'lucide-react';
import { getModelStats } from '../services/api';

export default function Dashboard() {
    const [stats, setStats] = useState(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        loadStats();
    }, []);

    const loadStats = async () => {
        try {
            const data = await getModelStats();
            setStats(data.metrics);
        } catch (err) {
            console.error('Failed to load stats:', err);
        } finally {
            setLoading(false);
        }
    };

    const features = [
        {
            icon: BrainCircuit,
            title: 'Deep Learning',
            desc: 'DenseNet121 with transfer learning for accurate lung cancer detection',
            color: 'from-primary-500 to-primary-700'
        },
        {
            icon: Shield,
            title: 'Explainable AI',
            desc: 'Grad-CAM visualization shows exactly where the AI is looking',
            color: 'from-accent-500 to-accent-700'
        },
        {
            icon: Database,
            title: 'Federated Learning',
            desc: 'FedAvg simulation across multiple hospital nodes preserving privacy',
            color: 'from-emerald-500 to-emerald-700'
        },
        {
            icon: Zap,
            title: 'Real-time Inference',
            desc: 'Fast prediction with confidence scoring and review flagging',
            color: 'from-orange-500 to-orange-700'
        },
    ];

    return (
        <div className="space-y-8">
            <motion.div
                initial={{ opacity: 0, y: -20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.5 }}
            >
                <h1 className="text-3xl font-bold text-white mb-2">
                    Welcome to <span className="gradient-text">OncoDet</span>
                </h1>
                <p className="text-dark-400 text-lg">
                    AI-Driven Lung Cancer Detection from Chest X-Rays
                </p>
            </motion.div>

            {/* quick actions */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <motion.div
                    initial={{ opacity: 0, x: -20 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ duration: 0.5, delay: 0.4 }}
                >
                    <Link to="/upload" className="block">
                        <div className="glass-card-hover p-6 group">
                            <div className="flex items-center justify-between">
                                <div className="flex items-center gap-4">
                                    <div className="w-14 h-14 rounded-xl bg-gradient-to-br from-primary-600 to-accent-600 flex items-center justify-center shadow-lg shadow-primary-900/30">
                                        <Upload className="w-7 h-7 text-white" />
                                    </div>
                                    <div>
                                        <h3 className="text-lg font-semibold text-white">Analyze X-Ray</h3>
                                        <p className="text-dark-400 text-sm">Upload a chest X-ray for instant cancer screening</p>
                                    </div>
                                </div>
                                <ArrowRight className="w-5 h-5 text-dark-500 group-hover:text-primary-400 transition-colors group-hover:translate-x-1 transform transition-transform" />
                            </div>
                        </div>
                    </Link>
                </motion.div>

                <motion.div
                    initial={{ opacity: 0, x: 20 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ duration: 0.5, delay: 0.5 }}
                >
                    <Link to="/federated" className="block">
                        <div className="glass-card-hover p-6 group">
                            <div className="flex items-center justify-between">
                                <div className="flex items-center gap-4">
                                    <div className="w-14 h-14 rounded-xl bg-gradient-to-br from-emerald-600 to-cyan-600 flex items-center justify-center shadow-lg shadow-emerald-900/30">
                                        <Database className="w-7 h-7 text-white" />
                                    </div>
                                    <div>
                                        <h3 className="text-lg font-semibold text-white">Federated Training</h3>
                                        <p className="text-dark-400 text-sm">Run distributed learning simulation across hospitals</p>
                                    </div>
                                </div>
                                <ArrowRight className="w-5 h-5 text-dark-500 group-hover:text-emerald-400 transition-colors group-hover:translate-x-1 transform transition-transform" />
                            </div>
                        </div>
                    </Link>
                </motion.div>
            </div>

            {/* feature cards */}
            <div>
                <h2 className="section-title">System Capabilities</h2>
                <p className="section-subtitle mb-6">Advanced AI technologies powering precision diagnostics</p>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {features.map((feature, i) => (
                        <motion.div
                            key={feature.title}
                            initial={{ opacity: 0, y: 20 }}
                            animate={{ opacity: 1, y: 0 }}
                            transition={{ duration: 0.5, delay: 0.6 + i * 0.1 }}
                            className="glass-card-hover p-5"
                        >
                            <div className="flex items-start gap-4">
                                <div className={`w-12 h-12 rounded-xl bg-gradient-to-br ${feature.color} flex items-center justify-center flex-shrink-0`}>
                                    <feature.icon className="w-6 h-6 text-white" />
                                </div>
                                <div>
                                    <h3 className="text-white font-semibold mb-1">{feature.title}</h3>
                                    <p className="text-dark-400 text-sm leading-relaxed">{feature.desc}</p>
                                </div>
                            </div>
                        </motion.div>
                    ))}
                </div>
            </div>

            {/* model architecture info */}
            {stats && (
                <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.5, delay: 1 }}
                    className="glass-card p-6"
                >
                    <h2 className="section-title flex items-center gap-2">
                        <Cpu className="w-6 h-6 text-primary-400" />
                        Model Architecture
                    </h2>
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-4">
                        {Object.entries(stats.model_info).slice(0, 8).map(([key, value]) => (
                            <div key={key} className="bg-dark-800/40 rounded-xl p-3">
                                <p className="text-dark-500 text-xs font-medium uppercase tracking-wider">
                                    {key.replace(/_/g, ' ')}
                                </p>
                                <p className="text-white font-semibold mt-1 text-sm">{String(value)}</p>
                            </div>
                        ))}
                    </div>
                </motion.div>
            )}
        </div>
    );
}
