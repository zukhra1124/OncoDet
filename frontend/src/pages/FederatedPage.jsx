// Federated learning page — configure and run the simulation, view results

import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
    LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip,
    Legend, ResponsiveContainer, BarChart, Bar
} from 'recharts';
import {
    Network, Play, Server, TrendingUp, Activity,
    Users, Loader2, CheckCircle2
} from 'lucide-react';
import LoadingSpinner from '../components/LoadingSpinner';
import { runFederatedTraining } from '../services/api';

const CLIENT_COLORS = ['#6366f1', '#06b6d4', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6'];

export default function FederatedPage() {
    const [numClients, setNumClients] = useState(4);
    const [numRounds, setNumRounds] = useState(3);
    const [isTraining, setIsTraining] = useState(false);
    const [trainingLog, setTrainingLog] = useState(null);
    const [error, setError] = useState(null);

    const startTraining = async () => {
        setIsTraining(true);
        setError(null);
        setTrainingLog(null);

        try {
            const data = await runFederatedTraining(numClients, numRounds);
            setTrainingLog(data.training_log);
        } catch (err) {
            setError(err.response?.data?.error || 'Federated training failed. Is the backend running?');
        } finally {
            setIsTraining(false);
        }
    };

    // build data for the convergence line chart
    const getConvergenceData = () => {
        if (!trainingLog) return [];
        return trainingLog.rounds.map((round) => ({
            round: `Round ${round.round}`,
            global_loss: round.global_loss,
            global_accuracy: (round.global_accuracy * 100).toFixed(1),
        }));
    };

    // build data for the client comparison bar chart
    const getClientComparisonData = () => {
        if (!trainingLog) return [];
        const lastRound = trainingLog.rounds[trainingLog.rounds.length - 1];
        return lastRound.client_metrics.map((client) => ({
            name: client.client_name,
            accuracy: (client.final_accuracy * 100).toFixed(1),
            loss: client.final_loss,
            data_size: client.data_size,
        }));
    };

    return (
        <div className="space-y-6">
            <motion.div
                initial={{ opacity: 0, y: -20 }}
                animate={{ opacity: 1, y: 0 }}
            >
                <h1 className="text-3xl font-bold text-white mb-2 flex items-center gap-3">
                    <Network className="w-8 h-8 text-accent-400" />
                    Federated Learning Simulation
                </h1>
                <p className="text-dark-400">
                    Simulate distributed model training across multiple hospital nodes using FedAvg
                </p>
            </motion.div>

            {/* controls */}
            <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.1 }}
                className="glass-card p-6"
            >
                <h2 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
                    <Server className="w-5 h-5 text-primary-400" />
                    Simulation Parameters
                </h2>

                <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                    <div>
                        <label className="text-dark-300 text-sm font-medium block mb-2">
                            Hospital Clients
                        </label>
                        <div className="flex items-center gap-3">
                            <input
                                type="range"
                                min="2"
                                max="8"
                                value={numClients}
                                onChange={(e) => setNumClients(parseInt(e.target.value))}
                                className="flex-1 h-2 bg-dark-700 rounded-lg appearance-none cursor-pointer accent-primary-500"
                                disabled={isTraining}
                            />
                            <span className="text-white font-bold text-xl w-8">{numClients}</span>
                        </div>
                    </div>

                    <div>
                        <label className="text-dark-300 text-sm font-medium block mb-2">
                            Training Rounds
                        </label>
                        <div className="flex items-center gap-3">
                            <input
                                type="range"
                                min="1"
                                max="15"
                                value={numRounds}
                                onChange={(e) => setNumRounds(parseInt(e.target.value))}
                                className="flex-1 h-2 bg-dark-700 rounded-lg appearance-none cursor-pointer accent-accent-500"
                                disabled={isTraining}
                            />
                            <span className="text-white font-bold text-xl w-8">{numRounds}</span>
                        </div>
                    </div>

                    <div className="flex items-end">
                        <button
                            onClick={startTraining}
                            disabled={isTraining}
                            className={`btn-primary w-full flex items-center justify-center gap-2 ${isTraining ? 'opacity-50 cursor-not-allowed' : ''
                                }`}
                        >
                            {isTraining ? (
                                <>
                                    <Loader2 className="w-5 h-5 animate-spin" />
                                    Training...
                                </>
                            ) : (
                                <>
                                    <Play className="w-5 h-5" />
                                    Start Training
                                </>
                            )}
                        </button>
                    </div>
                </div>

                {/* simple architecture diagram */}
                <div className="mt-6 p-4 bg-dark-800/40 rounded-xl">
                    <p className="text-dark-500 text-xs font-medium uppercase tracking-wider mb-3">Architecture</p>
                    <div className="flex items-center justify-center gap-2 flex-wrap text-sm">
                        <span className="px-3 py-1.5 rounded-lg bg-primary-600/20 text-primary-300 border border-primary-500/20">
                            🏥 Central Server
                        </span>
                        <span className="text-dark-500">↔</span>
                        {Array.from({ length: numClients }, (_, i) => (
                            <React.Fragment key={i}>
                                <span className="px-3 py-1.5 rounded-lg bg-dark-700/60 text-dark-300 border border-dark-600">
                                    Hospital {String.fromCharCode(65 + i)}
                                </span>
                                {i < numClients - 1 && <span className="text-dark-600">|</span>}
                            </React.Fragment>
                        ))}
                    </div>
                </div>
            </motion.div>

            {isTraining && (
                <LoadingSpinner message={`Running federated training with ${numClients} clients over ${numRounds} rounds...`} />
            )}

            {error && (
                <motion.div
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    className="glass-card p-5 border-red-800/30"
                >
                    <p className="text-red-400">{error}</p>
                </motion.div>
            )}

            {/* results section */}
            <AnimatePresence>
                {trainingLog && (
                    <motion.div
                        initial={{ opacity: 0, y: 20 }}
                        animate={{ opacity: 1, y: 0 }}
                        className="space-y-6"
                    >
                        {/* summary cards */}
                        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                            <div className="glass-card p-4 text-center">
                                <Users className="w-6 h-6 text-primary-400 mx-auto mb-2" />
                                <p className="text-2xl font-bold text-white">{trainingLog.num_clients}</p>
                                <p className="text-dark-400 text-sm">Clients</p>
                            </div>
                            <div className="glass-card p-4 text-center">
                                <Activity className="w-6 h-6 text-accent-400 mx-auto mb-2" />
                                <p className="text-2xl font-bold text-white">{trainingLog.num_rounds}</p>
                                <p className="text-dark-400 text-sm">Rounds</p>
                            </div>
                            <div className="glass-card p-4 text-center">
                                <TrendingUp className="w-6 h-6 text-emerald-400 mx-auto mb-2" />
                                <p className="text-2xl font-bold text-emerald-400">
                                    {(trainingLog.global_metrics[trainingLog.global_metrics.length - 1]?.accuracy * 100).toFixed(1)}%
                                </p>
                                <p className="text-dark-400 text-sm">Final Accuracy</p>
                            </div>
                            <div className="glass-card p-4 text-center">
                                <CheckCircle2 className="w-6 h-6 text-orange-400 mx-auto mb-2" />
                                <p className="text-2xl font-bold text-orange-400">
                                    {trainingLog.global_metrics[trainingLog.global_metrics.length - 1]?.loss}
                                </p>
                                <p className="text-dark-400 text-sm">Final Loss</p>
                            </div>
                        </div>

                        {/* convergence chart */}
                        <div className="glass-card p-6">
                            <h3 className="text-lg font-semibold text-white mb-4">Global Model Convergence</h3>
                            <ResponsiveContainer width="100%" height={300}>
                                <LineChart data={getConvergenceData()} style={{ backgroundColor: 'transparent' }}>
                                    <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                                    <XAxis dataKey="round" stroke="#64748b" />
                                    <YAxis yAxisId="left" stroke="#64748b" />
                                    <YAxis yAxisId="right" orientation="right" stroke="#64748b" />
                                    <Tooltip
                                        contentStyle={{
                                            backgroundColor: '#1e293b',
                                            border: '1px solid #334155',
                                            borderRadius: '12px',
                                            color: '#e2e8f0',
                                        }}
                                    />
                                    <Legend />
                                    <Line
                                        yAxisId="right"
                                        type="monotone"
                                        dataKey="global_accuracy"
                                        stroke="#10b981"
                                        strokeWidth={3}
                                        dot={{ fill: '#10b981', r: 5 }}
                                        name="Accuracy (%)"
                                    />
                                    <Line
                                        yAxisId="left"
                                        type="monotone"
                                        dataKey="global_loss"
                                        stroke="#ef4444"
                                        strokeWidth={3}
                                        dot={{ fill: '#ef4444', r: 5 }}
                                        name="Loss"
                                    />
                                </LineChart>
                            </ResponsiveContainer>
                        </div>

                        {/* client comparison */}
                        <div className="glass-card p-6">
                            <h3 className="text-lg font-semibold text-white mb-4">Client Performance Comparison (Final Round)</h3>
                            <ResponsiveContainer width="100%" height={300}>
                                <BarChart data={getClientComparisonData()} style={{ backgroundColor: 'transparent' }}>
                                    <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                                    <XAxis dataKey="name" stroke="#64748b" />
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
                                    <Bar dataKey="accuracy" name="Accuracy (%)" fill="#6366f1" radius={[8, 8, 0, 0]} />
                                    <Bar dataKey="data_size" name="Data Size" fill="#06b6d4" radius={[8, 8, 0, 0]} />
                                </BarChart>
                            </ResponsiveContainer>
                        </div>

                        {/* detailed log table */}
                        <div className="glass-card p-6 overflow-x-auto">
                            <h3 className="text-lg font-semibold text-white mb-4">Detailed Training Log</h3>
                            <table className="w-full text-sm text-left">
                                <thead>
                                    <tr className="border-b border-dark-700">
                                        <th className="py-3 px-4 text-dark-400 font-medium">Round</th>
                                        {trainingLog.client_names.map((name) => (
                                            <th key={name} className="py-3 px-4 text-dark-400 font-medium">{name}</th>
                                        ))}
                                        <th className="py-3 px-4 text-dark-400 font-medium">Global Acc.</th>
                                        <th className="py-3 px-4 text-dark-400 font-medium">Global Loss</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {trainingLog.rounds.map((round) => (
                                        <tr key={round.round} className="border-b border-dark-800 hover:bg-dark-800/40 transition-colors">
                                            <td className="py-3 px-4 text-white font-medium">{round.round}</td>
                                            {round.client_metrics.map((client) => (
                                                <td key={client.client_id} className="py-3 px-4 text-dark-300">
                                                    {(client.final_accuracy * 100).toFixed(1)}%
                                                </td>
                                            ))}
                                            <td className="py-3 px-4 text-emerald-400 font-medium">
                                                {(round.global_accuracy * 100).toFixed(1)}%
                                            </td>
                                            <td className="py-3 px-4 text-red-400">
                                                {round.global_loss}
                                            </td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    </motion.div>
                )}
            </AnimatePresence>
        </div>
    );
}
