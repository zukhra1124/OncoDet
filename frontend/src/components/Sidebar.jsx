// Sidebar nav — shows on desktop, slides in on mobile

import React from 'react';
import { NavLink } from 'react-router-dom';
import {
    Home,
    Upload,
    Activity,
    Network,
    Stethoscope,
    Brain,
    X
} from 'lucide-react';

const navItems = [
    { path: '/', icon: Home, label: 'Dashboard' },
    { path: '/upload', icon: Upload, label: 'Upload X-Ray' },
    { path: '/results', icon: Activity, label: 'Results' },
    { path: '/federated', icon: Network, label: 'Federated Learning' },
];

export default function Sidebar({ onClose }) {
    return (
        <aside className="w-72 bg-dark-900/80 backdrop-blur-xl border-r border-dark-700/50 flex flex-col min-h-screen sticky top-0">
            {/* logo + app name */}
            <div className="p-6 border-b border-dark-700/50 flex items-center justify-between">
                <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-primary-500 to-accent-500 flex items-center justify-center">
                        <Brain className="w-6 h-6 text-white" />
                    </div>
                    <div>
                        <h1 className="text-lg font-bold text-white">OncoDet</h1>
                        <p className="text-xs text-dark-400">Lung Cancer Detection</p>
                    </div>
                </div>
                {onClose && (
                    <button onClick={onClose} className="md:hidden p-2 text-dark-400 hover:text-white bg-dark-800 rounded-lg">
                        <X className="w-5 h-5" />
                    </button>
                )}
            </div>

            {/* nav links */}
            <nav className="flex-1 p-4 space-y-1">
                {navItems.map(({ path, icon: Icon, label }) => (
                    <NavLink
                        key={path}
                        to={path}
                        onClick={onClose}
                        className={({ isActive }) =>
                            `flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-medium transition-all duration-200 group ${isActive
                                ? 'bg-gradient-to-r from-primary-600/20 to-accent-600/10 text-primary-300 border border-primary-500/20'
                                : 'text-dark-400 hover:text-dark-200 hover:bg-dark-800/60'
                            }`
                        }
                    >
                        <Icon className="w-5 h-5 transition-transform group-hover:scale-110" />
                        <span>{label}</span>
                    </NavLink>
                ))}
            </nav>

            {/* bottom badge */}
            <div className="p-4 border-t border-dark-700/50">
                <div className="glass-card p-4 text-center">
                    <Stethoscope className="w-8 h-8 text-accent-400 mx-auto mb-2" />
                    <p className="text-xs text-dark-400">AI-Powered Oncology</p>
                    <p className="text-xs text-dark-500">Chest X-Ray Analysis</p>
                </div>
            </div>
        </aside>
    );
}
