import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { motion } from 'framer-motion';
import { FaSearch, FaWifi, FaNetworkWired, FaDesktop, FaServer } from 'react-icons/fa';

function App() {
    const [query, setQuery] = useState('');
    const [results, setResults] = useState([]);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);
    const [hasSearched, setHasSearched] = useState(false);

    const search = async (searchQuery) => {
        setLoading(true);
        setError(null);
        setHasSearched(true);
        try {
            const endpoint = searchQuery ? `/api/search?q=${encodeURIComponent(searchQuery)}` : '/api/devices';
            const response = await axios.get(endpoint);
            setResults(response.data);
        } catch (err) {
            setError('Failed to fetch results. Please try again.');
            console.error(err);
        } finally {
            setLoading(false);
        }
    };

    const handleSearch = (e) => {
        e.preventDefault();
        search(query);
    };

    const showAll = () => {
        setQuery('');
        search('');
    };

    return (
        <div className="min-h-screen p-4 md:p-8">
            <div className="max-w-6xl mx-auto">
                <header className="text-center mb-12">
                    <div className="flex justify-center mb-4">
                        <img src="/favicon.png" alt="Logo" className="w-16 h-16" />
                    </div>
                    <h1 className="text-4xl md:text-5xl font-bold text-primary mb-2 drop-shadow-[0_0_15px_rgba(0,212,255,0.3)]">
                        Device Tracker
                    </h1>
                    <p className="text-gray-400 text-lg">
                        Monitor and search your network devices
                    </p>
                </header>

                <div className="bg-white/5 backdrop-blur-lg rounded-2xl p-6 mb-8 border border-white/10 shadow-xl">
                    <form onSubmit={handleSearch} className="flex flex-col md:flex-row gap-4">
                        <div className="flex-1 relative">
                            <FaSearch className="absolute left-4 top-1/2 -translate-y-1/2 text-gray-400" />
                            <input
                                type="text"
                                value={query}
                                onChange={(e) => setQuery(e.target.value)}
                                placeholder="Search by hostname, IP, MAC, or time..."
                                className="w-full bg-black/30 border-2 border-primary/30 rounded-xl py-3 pl-12 pr-4 text-white placeholder-gray-500 focus:border-primary focus:shadow-[0_0_20px_rgba(0,212,255,0.2)] outline-none transition-all duration-300"
                            />
                        </div>
                        <button
                            type="submit"
                            className="bg-gradient-to-r from-primary to-blue-600 text-black font-bold py-3 px-8 rounded-xl hover:translate-y-[-2px] hover:shadow-[0_10px_30px_rgba(0,212,255,0.3)] transition-all duration-300"
                        >
                            Search
                        </button>
                        <button
                            type="button"
                            onClick={showAll}
                            className="bg-white/10 text-white font-semibold py-3 px-8 rounded-xl hover:bg-white/20 border border-white/20 transition-all duration-300"
                        >
                            Show All
                        </button>
                    </form>
                    <div className="mt-4 text-sm text-gray-500">
                        <span className="bg-primary/10 text-primary px-2 py-1 rounded mr-2">*</span> Wildcards supported
                        <span className="bg-primary/10 text-primary px-2 py-1 rounded mx-2">?</span> Single char
                        <span className="bg-primary/10 text-primary px-2 py-1 rounded mx-2">/24</span> CIDR notation
                    </div>
                </div>

                {error && (
                    <motion.div
                        initial={{ opacity: 0, y: 20 }}
                        animate={{ opacity: 1, y: 0 }}
                        className="bg-red-500/10 border border-red-500/30 text-red-400 p-4 rounded-xl text-center mb-8"
                    >
                        {error}
                    </motion.div>
                )}

                {loading ? (
                    <div className="flex justify-center py-20">
                        <div className="w-12 h-12 border-4 border-primary/30 border-t-primary rounded-full animate-spin"></div>
                    </div>
                ) : (
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                        {results.map((device, index) => (
                            <ResultItem key={index} device={device} index={index} />
                        ))}
                    </div>
                )}

                {!loading && hasSearched && results.length === 0 && !error && (
                    <div className="text-center py-20 text-gray-500">
                        <p className="text-6xl mb-4">📡</p>
                        <p className="text-xl">No devices found</p>
                    </div>
                )}
            </div>
        </div>
    );
}

function ResultItem({ device, index }) {
    const isWifi = (device.device_type || '').toLowerCase().includes('wi-fi');

    return (
        <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: index * 0.05 }}
            className="bg-white/5 backdrop-blur-md rounded-2xl p-6 border border-white/10 hover:border-primary/30 hover:shadow-[0_15px_40px_rgba(0,0,0,0.3)] hover:-translate-y-1 transition-all duration-300 group"
        >
            <div className="flex justify-between items-start mb-4">
                <h3 className="text-xl font-bold text-white truncate pr-2" title={device.hostname}>
                    {device.hostname || 'Unknown'}
                </h3>
                <span className={`px-3 py-1 rounded-full text-xs font-bold uppercase ${isWifi
                        ? 'bg-gradient-to-r from-indigo-500 to-purple-600 text-white'
                        : 'bg-gradient-to-r from-emerald-500 to-green-400 text-black'
                    }`}>
                    {device.device_type || 'Unknown'}
                </span>
            </div>

            <div className="space-y-3">
                <div className="flex justify-between items-center py-2 border-b border-white/5">
                    <span className="text-gray-500 text-sm">IP Address</span>
                    <span className="text-primary font-mono">{device.ip_address || 'N/A'}</span>
                </div>
                <div className="flex justify-between items-center py-2 border-b border-white/5">
                    <span className="text-gray-500 text-sm">MAC Address</span>
                    <span className="text-yellow-400 font-mono">{device.mac_address || 'N/A'}</span>
                </div>
                <div className="flex justify-between items-center py-2 border-b border-white/5">
                    <span className="text-gray-500 text-sm">Last Seen</span>
                    <span className="text-gray-300 text-sm text-right">
                        {device.last_seen ? new Date(device.last_seen).toLocaleString() : 'N/A'}
                    </span>
                </div>
            </div>
        </motion.div>
    );
}

export default App;
