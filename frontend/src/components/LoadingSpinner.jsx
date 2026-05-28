// Animated loading spinner with a pulsing brain icon

import React from 'react';
import { motion } from 'framer-motion';
import { Brain } from 'lucide-react';

export default function LoadingSpinner({ message = 'Analyzing...', size = 'md' }) {
    const sizeClasses = {
        sm: 'w-8 h-8',
        md: 'w-16 h-16',
        lg: 'w-24 h-24',
    };

    return (
        <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="flex flex-col items-center justify-center py-12"
        >
            <div className="relative">
                <motion.div
                    className={`${sizeClasses[size]} border-4 border-dark-700 border-t-primary-500 rounded-full`}
                    animate={{ rotate: 360 }}
                    transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}
                />

                <div className="absolute inset-0 flex items-center justify-center">
                    <motion.div
                        animate={{ scale: [1, 1.2, 1] }}
                        transition={{ duration: 2, repeat: Infinity }}
                    >
                        <Brain className="w-6 h-6 text-primary-400" />
                    </motion.div>
                </div>
            </div>

            <motion.p
                className="text-dark-400 text-sm mt-4 font-medium"
                animate={{ opacity: [0.5, 1, 0.5] }}
                transition={{ duration: 2, repeat: Infinity }}
            >
                {message}
            </motion.p>
        </motion.div>
    );
}
