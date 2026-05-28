// Model performance dashboard — confusion matrix, training curves, ROC, metrics

import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import {
    LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip,
    Legend, ResponsiveContainer, AreaChart, Area
} from 'recharts';
import {
    BarChart3, Target, TrendingUp, Award, RefreshCw
} from 'lucide-react';
import LoadingSpinner from '../components/LoadingSpinner';
import { getModelStats } from '../services/api';

export default function PerformancePage() {
    const [metrics, setMetrics] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    useEffect(() => {
        loadMetrics();
    }, []);

    const loadMetrics = async () => {
        setLoading(true);
        setError(null);
        try {
            const data = await getModelStats();
            setMetrics(data.metrics);
        } catch (err) {
            setError('Failed to load metrics. Is the backend running?');
        } finally {
            setLoading(false);
        }
    };

    const getTrainingData = () => {
        if (!metrics) return [];
        return metrics.training_history.epochs.map((epoch, i) => ({
            epoch,
            train_loss: metrics.training_history.train_loss[i],
            val_loss: metrics.training_history.val_loss[i],
            train_accuracy: (metrics.training_history.train_accuracy[i] * 100).toFixed(1),
            val_accuracy: (metrics.training_history.val_accuracy[i] * 100).toFixed(1),
        }));
    };

    const getRocData = () => {
        if (!metrics) return [];
        return metrics.roc_curve.data;
    };

    if (loading) return <LoadingSpinner message="Loading model performance metrics..." />;

    if (error) {
        return (
            <div className="glass-card p-8 text-center">
                <p className="text-red-400 mb-4">{error}</p>
                <button onClick={loadMetrics} className="btn-primary">
                    <RefreshCw className="w-4 h-4 mr-2 inline" /> Retry
                </button>
            </div>
        );
    }

    if (!metrics) return null;

    const { confusion_matrix, classification_report, model_info, roc_curve } = metrics;

    return (
        <div className="space-y-6">
            <motion.div
                initial={{ opacity: 0, y: -20 }}
                animate={{ opacity: 1, y: 0 }}
            >
                <h1 className="text-3xl font-bold text-white mb-2 flex items-center gap-3">
                    <BarChart3 className="w-8 h-8 text-primary-400" />
                    Model Performance
                </h1>
                <p className="text-dark-400">
                    Comprehensive evaluation metrics for the OncologyNet lung cancer classifier
                </p>
            </motion.div>

            {/* key metrics */}
            <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
                {[
                    { label: 'Accuracy', value: `${(classification_report.accuracy * 100).toFixed(1)}%`, icon: Target, color: 'text-primary-400' },
                    { label: 'Precision', value: `${(classification_report.precision * 100).toFixed(1)}%`, icon: Award, color: 'text-accent-400' },
                    { label: 'Recall', value: `${(classification_report.recall * 100).toFixed(1)}%`, icon: TrendingUp, color: 'text-emerald-400' },
                    { label: 'F1 Score', value: `${(classification_report.f1_score * 100).toFixed(1)}%`, icon: BarChart3, color: 'text-orange-400' },
                    { label: 'AUC-ROC', value: roc_curve.auc.toFixed(3), icon: TrendingUp, color: 'text-purple-400' },
                ].map((metric, i) => (
                    <motion.div
                        key={metric.label}
                        initial={{ opacity: 0, y: 20 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: i * 0.1 }}
                        className="glass-card p-4 text-center"
                    >
                        <metric.icon className={`w-6 h-6 ${metric.color} mx-auto mb-2`} />
                        <p className="text-2xl font-bold text-white">{metric.value}</p>
                        <p className="text-dark-400 text-xs mt-1">{metric.label}</p>
                    </motion.div>
                ))}
            </div>

            {/* confusion matrix */}
            <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.2 }}
                className="glass-card p-6"
            >
                <h3 className="text-lg font-semibold text-white mb-4">Confusion Matrix</h3>
                <div className="flex flex-col items-center">
                    <div className="grid grid-cols-3 gap-1 text-center max-w-md">
                        <div></div>
                        <div className="text-dark-400 text-sm font-medium py-2">Pred: Normal</div>
                        <div className="text-dark-400 text-sm font-medium py-2">Pred: Cancer</div>

                        <div className="text-dark-400 text-sm font-medium py-2 flex items-center justify-end pr-3">
                            Actual: Normal
                        </div>
                        <div className="bg-emerald-900/40 border border-emerald-700/30 rounded-xl p-4 m-1">
                            <p className="text-2xl font-bold text-emerald-400">{confusion_matrix.true_negative}</p>
                            <p className="text-dark-500 text-xs">TN</p>
                        </div>
                        <div className="bg-red-900/20 border border-red-800/20 rounded-xl p-4 m-1">
                            <p className="text-2xl font-bold text-red-400">{confusion_matrix.false_positive}</p>
                            <p className="text-dark-500 text-xs">FP</p>
                        </div>

                        <div className="text-dark-400 text-sm font-medium py-2 flex items-center justify-end pr-3">
                            Actual: Cancer
                        </div>
                        <div className="bg-orange-900/20 border border-orange-800/20 rounded-xl p-4 m-1">
                            <p className="text-2xl font-bold text-orange-400">{confusion_matrix.false_negative}</p>
                            <p className="text-dark-500 text-xs">FN</p>
                        </div>
                        <div className="bg-emerald-900/40 border border-emerald-700/30 rounded-xl p-4 m-1">
                            <p className="text-2xl font-bold text-emerald-400">{confusion_matrix.true_positive}</p>
                            <p className="text-dark-500 text-xs">TP</p>
                        </div>
                    </div>
                    <p className="text-dark-500 text-xs mt-4">
                        Total samples: {classification_report.total_samples} |
                        Specificity: {(classification_report.specificity * 100).toFixed(1)}%
                    </p>
                </div>
            </motion.div>

            {/* training curves */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                <motion.div
                    initial={{ opacity: 0, x: -20 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: 0.3 }}
                    className="glass-card p-6"
                >
                    <h3 className="text-lg font-semibold text-white mb-4">Training & Validation Loss</h3>
                    <ResponsiveContainer width="100%" height={300}>
                        <LineChart data={getTrainingData()} style={{ backgroundColor: 'transparent' }}>
                            <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                            <XAxis dataKey="epoch" stroke="#64748b" label={{ value: 'Epoch', position: 'bottom', fill: '#64748b' }} />
                            <YAxis stroke="#64748b" />
                            <Tooltip
                                contentStyle={{
                                    backgroundColor: '#1e293b',
                                    border: '1px solid #334155',
                                    borderRadius: '12px',
                                    color: '#e2e8f0',
                                }}
                            />
                            <Legend />
                            <Line type="monotone" dataKey="train_loss" stroke="#6366f1" strokeWidth={2} dot={false} name="Train Loss" />
                            <Line type="monotone" dataKey="val_loss" stroke="#f59e0b" strokeWidth={2} dot={false} name="Val Loss" />
                        </LineChart>
                    </ResponsiveContainer>
                </motion.div>

                <motion.div
                    initial={{ opacity: 0, x: 20 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: 0.4 }}
                    className="glass-card p-6"
                >
                    <h3 className="text-lg font-semibold text-white mb-4">Training & Validation Accuracy</h3>
                    <ResponsiveContainer width="100%" height={300}>
                        <LineChart data={getTrainingData()} style={{ backgroundColor: 'transparent' }}>
                            <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                            <XAxis dataKey="epoch" stroke="#64748b" label={{ value: 'Epoch', position: 'bottom', fill: '#64748b' }} />
                            <YAxis stroke="#64748b" domain={[0, 100]} />
                            <Tooltip
                                contentStyle={{
                                    backgroundColor: '#1e293b',
                                    border: '1px solid #334155',
                                    borderRadius: '12px',
                                    color: '#e2e8f0',
                                }}
                            />
                            <Legend />
                            <Line type="monotone" dataKey="train_accuracy" stroke="#10b981" strokeWidth={2} dot={false} name="Train Acc (%)" />
                            <Line type="monotone" dataKey="val_accuracy" stroke="#06b6d4" strokeWidth={2} dot={false} name="Val Acc (%)" />
                        </LineChart>
                    </ResponsiveContainer>
                </motion.div>
            </div>

            {/* ROC curve */}
            <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.5 }}
                className="glass-card p-6"
            >
                <h3 className="text-lg font-semibold text-white mb-2">ROC Curve</h3>
                <p className="text-dark-400 text-sm mb-4">AUC = {roc_curve.auc.toFixed(4)}</p>
                <ResponsiveContainer width="100%" height={350}>
                    <AreaChart data={getRocData()} style={{ backgroundColor: 'transparent' }}>
                        <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                        <XAxis
                            dataKey="fpr"
                            stroke="#64748b"
                            label={{ value: 'False Positive Rate', position: 'bottom', fill: '#64748b' }}
                        />
                        <YAxis
                            dataKey="tpr"
                            stroke="#64748b"
                            label={{ value: 'True Positive Rate', angle: -90, position: 'left', fill: '#64748b' }}
                        />
                        <Tooltip
                            contentStyle={{
                                backgroundColor: '#1e293b',
                                border: '1px solid #334155',
                                borderRadius: '12px',
                                color: '#e2e8f0',
                            }}
                        />
                        <Area
                            type="monotone"
                            dataKey="tpr"
                            stroke="#6366f1"
                            strokeWidth={3}
                            fill="url(#rocGradient)"
                        />
                        <defs>
                            <linearGradient id="rocGradient" x1="0" y1="0" x2="0" y2="1">
                                <stop offset="5%" stopColor="#6366f1" stopOpacity={0.3} />
                                <stop offset="95%" stopColor="#6366f1" stopOpacity={0} />
                            </linearGradient>
                        </defs>
                    </AreaChart>
                </ResponsiveContainer>
            </motion.div>

            {/* model config */}
            <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.6 }}
                className="glass-card p-6"
            >
                <h3 className="text-lg font-semibold text-white mb-4">Model Configuration</h3>
                <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
                    {Object.entries(model_info).map(([key, value]) => (
                        <div key={key} className="bg-dark-800/40 rounded-xl p-3">
                            <p className="text-dark-500 text-xs uppercase tracking-wider">
                                {key.replace(/_/g, ' ')}
                            </p>
                            <p className="text-white font-semibold text-sm mt-1">{String(value)}</p>
                        </div>
                    ))}
                </div>
            </motion.div>
        </div>
    );
}
