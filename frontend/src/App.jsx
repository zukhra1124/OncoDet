import React, { useState } from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { Menu, Brain } from 'lucide-react';
import Sidebar from './components/Sidebar';
import Dashboard from './pages/Dashboard';
import UploadPage from './pages/UploadPage';
import ResultsPage from './pages/ResultsPage';
import FederatedPage from './pages/FederatedPage';

export default function App() {
    const [sidebarOpen, setSidebarOpen] = useState(false);

    return (
        <Router>
            <div className="flex flex-col md:flex-row min-h-screen app-layout w-full">
                {/* mobile top bar */}
                <div className="md:hidden flex items-center justify-between p-4 bg-dark-900 border-b border-dark-700/50 sticky top-0 z-40 w-full shadow-md">
                    <div className="flex items-center gap-3">
                        <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-primary-500 to-accent-500 flex items-center justify-center">
                            <Brain className="w-5 h-5 text-white" />
                        </div>
                        <h1 className="text-white font-bold text-lg">Neural AI</h1>
                    </div>
                    <button onClick={() => setSidebarOpen(true)} className="p-2 text-dark-300 hover:text-white bg-dark-800 rounded-lg border border-dark-600">
                        <Menu className="w-5 h-5" />
                    </button>
                </div>

                {/* dark overlay when sidebar is open on mobile */}
                {sidebarOpen && (
                    <div 
                        className="fixed inset-0 bg-black/60 z-40 backdrop-blur-sm md:hidden"
                        onClick={() => setSidebarOpen(false)}
                    />
                )}

                {/* sidebar */}
                <div className={`fixed inset-y-0 left-0 z-50 transform ${sidebarOpen ? 'translate-x-0' : '-translate-x-full'} md:relative md:translate-x-0 transition-transform duration-300 ease-in-out`}>
                    <Sidebar onClose={() => setSidebarOpen(false)} />
                </div>

                {/* page content */}
                <main className="flex-1 w-full h-screen overflow-y-auto p-4 md:p-8">
                    <Routes>
                        <Route path="/" element={<Dashboard />} />
                        <Route path="/upload" element={<UploadPage />} />
                        <Route path="/results" element={<ResultsPage />} />
                        <Route path="/federated" element={<FederatedPage />} />
                    </Routes>
                </main>
            </div>
        </Router>
    );
}
