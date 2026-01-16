import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';

// ============================================================================
// HORNET - Autonomous SOC Dashboard & Landing Page
// Customer-facing production UI - Single file version for preview
// ============================================================================

// Hornet Logo Component
const HornetLogo = ({ size = 32 }) => (
  <svg width={size} height={size} viewBox="0 0 100 100" className="hornet-logo">
    <defs>
      <linearGradient id="bodyGrad" x1="0%" y1="0%" x2="100%" y2="100%">
        <stop offset="0%" stopColor="#1e3a5f" />
        <stop offset="100%" stopColor="#0f172a" />
      </linearGradient>
      <linearGradient id="stripeGrad" x1="0%" y1="0%" x2="100%" y2="0%">
        <stop offset="0%" stopColor="#f59e0b" />
        <stop offset="100%" stopColor="#fbbf24" />
      </linearGradient>
      <linearGradient id="wingGrad" x1="0%" y1="0%" x2="100%" y2="100%">
        <stop offset="0%" stopColor="#06b6d4" />
        <stop offset="100%" stopColor="#0891b2" />
      </linearGradient>
    </defs>
    <path d="M15 35 L45 25 L50 45 L25 50 Z" fill="url(#wingGrad)" opacity="0.9"/>
    <ellipse cx="60" cy="50" rx="30" ry="18" fill="url(#bodyGrad)"/>
    <path d="M45 42 Q60 38 75 42 L75 48 Q60 44 45 48 Z" fill="url(#stripeGrad)"/>
    <path d="M48 52 Q60 48 72 52 L72 58 Q60 54 48 58 Z" fill="url(#stripeGrad)"/>
    <circle cx="85" cy="50" r="12" fill="url(#bodyGrad)"/>
    <circle cx="88" cy="48" r="4" fill="#22d3ee"/>
    <path d="M30 50 L20 55 L30 52 Z" fill="#1e3a5f"/>
    <path d="M90 40 L95 30" stroke="#f59e0b" strokeWidth="2" fill="none"/>
    <path d="M88 38 L90 28" stroke="#f59e0b" strokeWidth="2" fill="none"/>
  </svg>
);

// Swarm Visualization Component
const SwarmVisualization = () => {
  const agents = [...Array(56)].map((_, i) => ({
    id: i,
    x: 50 + Math.cos(i * 0.5) * (20 + (i % 7) * 5),
    y: 50 + Math.sin(i * 0.5) * (20 + (i % 7) * 5),
    layer: ['detection', 'intel', 'analysis', 'action', 'governance', 'meta', 'specialist'][i % 7],
  }));

  const layerColors = {
    detection: '#ef4444',
    intel: '#3b82f6',
    analysis: '#22c55e',
    action: '#f59e0b',
    governance: '#8b5cf6',
    meta: '#06b6d4',
    specialist: '#ec4899',
  };

  return (
    <div className="relative w-80 h-80">
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 z-10">
        <HornetLogo size={80} />
      </div>
      {agents.map((agent) => (
        <motion.div
          key={agent.id}
          className="absolute w-2 h-2 rounded-full"
          style={{ 
            left: `${agent.x}%`, 
            top: `${agent.y}%`,
            backgroundColor: layerColors[agent.layer]
          }}
          animate={{
            x: [0, Math.random() * 10 - 5, 0],
            y: [0, Math.random() * 10 - 5, 0],
            opacity: [0.6, 1, 0.6],
          }}
          transition={{
            duration: 2 + Math.random() * 2,
            repeat: Infinity,
            delay: agent.id * 0.05,
          }}
        />
      ))}
      <svg className="absolute inset-0 pointer-events-none" viewBox="0 0 100 100">
        {agents.slice(0, 20).map((agent, i) => (
          <motion.line
            key={i}
            x1="50" y1="50" x2={agent.x} y2={agent.y}
            stroke="rgba(245, 158, 11, 0.2)"
            strokeWidth="0.3"
            initial={{ pathLength: 0 }}
            animate={{ pathLength: 1, opacity: [0.2, 0.5, 0.2] }}
            transition={{ duration: 2, delay: i * 0.1, repeat: Infinity }}
          />
        ))}
      </svg>
    </div>
  );
};

// Landing Page Component
const LandingPage = ({ onLogin }) => {
  const [isVisible, setIsVisible] = useState(false);
  const [activeFeature, setActiveFeature] = useState(0);
  const [showPricing, setShowPricing] = useState(false);

  useEffect(() => {
    setIsVisible(true);
    const interval = setInterval(() => {
      setActiveFeature((prev) => (prev + 1) % 4);
    }, 3000);
    return () => clearInterval(interval);
  }, []);

  const features = [
    { title: '56 AI Agents', desc: 'Specialized swarm intelligence analyzing threats in parallel', icon: '🐝' },
    { title: '86% Auto-Resolution', desc: 'Most incidents resolved without human intervention', icon: '⚡' },
    { title: '180 Second Analysis', desc: '400 hours of forensics compressed to 3 minutes', icon: '🎯' },
    { title: 'Real Threat Intel', desc: 'VirusTotal, AbuseIPDB, GreyNoise, Shodan integrated', icon: '🛡️' },
  ];

  const pricing = [
    { tier: 'Starter', price: '1,499', target: 'Small MSSPs', incidents: '5,000', features: ['Email support', 'Core integrations', 'Standard SLA'] },
    { tier: 'Professional', price: '3,499', target: 'Mid-market SOCs', incidents: '25,000', features: ['Slack support', 'All integrations', 'Priority SLA'], popular: true },
    { tier: 'Enterprise', price: '7,499', target: 'Large organizations', incidents: 'Unlimited', features: ['Dedicated CSM', 'Custom integrations', 'On-prem option'] },
  ];

  return (
    <div className="min-h-screen bg-slate-950 relative overflow-hidden">
      {/* Animated Hex Grid Background */}
      <div className="fixed inset-0 pointer-events-none">
        {[...Array(30)].map((_, i) => (
          <motion.div
            key={i}
            className="absolute w-10 h-10 bg-amber-500/10"
            style={{
              left: `${Math.random() * 100}%`,
              top: `${Math.random() * 100}%`,
              clipPath: 'polygon(50% 0%, 100% 25%, 100% 75%, 50% 100%, 0% 75%, 0% 25%)'
            }}
            animate={{ opacity: [0.05, 0.15, 0.05] }}
            transition={{ duration: 3, delay: i * 0.1, repeat: Infinity }}
          />
        ))}
      </div>

      {/* Navigation */}
      <nav className="fixed top-0 left-0 right-0 flex justify-between items-center px-8 py-4 bg-slate-950/90 backdrop-blur-xl border-b border-amber-500/10 z-50">
        <div className="flex items-center gap-3">
          <HornetLogo size={40} />
          <span className="text-xl font-bold tracking-widest text-white">HORNET</span>
        </div>
        <div className="flex items-center gap-8">
          <a href="#features" className="text-slate-400 hover:text-amber-400 transition-colors text-sm font-medium">Features</a>
          <button onClick={() => setShowPricing(true)} className="text-slate-400 hover:text-amber-400 transition-colors text-sm font-medium">Pricing</button>
          <a href="#demo" className="text-slate-400 hover:text-amber-400 transition-colors text-sm font-medium">Demo</a>
          <button 
            onClick={onLogin}
            className="bg-amber-500 hover:bg-amber-400 text-slate-950 px-5 py-2.5 rounded-lg font-semibold text-sm transition-all hover:-translate-y-0.5"
          >
            Dashboard →
          </button>
        </div>
      </nav>

      {/* Hero Section */}
      <section className="min-h-screen grid grid-cols-2 items-center px-16 pt-24 pb-16 gap-16 relative z-10">
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          animate={{ opacity: isVisible ? 1 : 0, y: isVisible ? 0 : 30 }}
          transition={{ duration: 0.8 }}
          className="max-w-xl"
        >
          <div className="inline-flex items-center gap-2 bg-amber-500/10 border border-amber-500/30 px-4 py-1.5 rounded-full text-xs font-semibold tracking-widest text-amber-400 mb-6">
            <span className="w-2 h-2 bg-amber-500 rounded-full animate-pulse" />
            AUTONOMOUS SOC
          </div>
          
          <h1 className="text-5xl font-bold leading-tight mb-6 tracking-tight">
            Your SOC team,<br />
            <span className="bg-gradient-to-r from-amber-400 to-cyan-400 bg-clip-text text-transparent">
              multiplied by 56.
            </span>
          </h1>
          
          <p className="text-xl text-slate-400 mb-8 leading-relaxed">
            HORNET is an AI-powered Security Operations Center that uses a swarm of 
            specialized agents to detect, analyze, and respond to threats automatically.
          </p>

          <div className="flex items-center gap-8 py-6 border-y border-white/10 mb-8">
            <div className="flex flex-col">
              <span className="text-3xl font-bold text-amber-400 font-mono">56</span>
              <span className="text-sm text-slate-500 uppercase tracking-wide">AI Agents</span>
            </div>
            <div className="w-px h-10 bg-white/10" />
            <div className="flex flex-col">
              <span className="text-3xl font-bold text-amber-400 font-mono">86%</span>
              <span className="text-sm text-slate-500 uppercase tracking-wide">Auto-Resolved</span>
            </div>
            <div className="w-px h-10 bg-white/10" />
            <div className="flex flex-col">
              <span className="text-3xl font-bold text-amber-400 font-mono">180s</span>
              <span className="text-sm text-slate-500 uppercase tracking-wide">Avg Response</span>
            </div>
          </div>

          <div className="flex gap-4">
            <button 
              onClick={onLogin}
              className="inline-flex items-center gap-2 bg-gradient-to-r from-amber-500 to-amber-600 text-slate-950 px-8 py-4 rounded-lg font-semibold transition-all hover:-translate-y-0.5 hover:shadow-lg hover:shadow-amber-500/30"
            >
              Start Free Trial
              <svg className="w-5 h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M5 12h14M12 5l7 7-7 7"/>
              </svg>
            </button>
            <button className="inline-flex items-center gap-2 border border-white/20 hover:border-amber-500 text-white hover:text-amber-400 px-8 py-4 rounded-lg font-medium transition-all">
              Watch Demo
              <svg className="w-4 h-4" viewBox="0 0 24 24" fill="currentColor">
                <path d="M8 5v14l11-7z"/>
              </svg>
            </button>
          </div>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, scale: 0.9 }}
          animate={{ opacity: isVisible ? 1 : 0, scale: isVisible ? 1 : 0.9 }}
          transition={{ duration: 1, delay: 0.3 }}
          className="flex justify-center items-center"
        >
          <SwarmVisualization />
        </motion.div>
      </section>

      {/* ROI Section */}
      <section className="py-16 px-16 relative z-10">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          className="bg-slate-900/50 border border-amber-500/20 rounded-2xl p-12 max-w-4xl mx-auto text-center"
        >
          <h3 className="text-2xl text-slate-400 mb-8">The ROI is simple math</h3>
          <div className="flex items-center justify-center gap-8 mb-8">
            <div className="flex flex-col p-6 rounded-xl bg-red-500/10 border border-red-500/30">
              <span className="text-sm text-slate-400 mb-2">3 SOC Analysts (24/7)</span>
              <span className="text-3xl font-bold font-mono text-red-400">$255,000/yr</span>
            </div>
            <span className="text-xl text-slate-500 font-semibold">vs</span>
            <div className="flex flex-col p-6 rounded-xl bg-green-500/10 border border-green-500/30">
              <span className="text-sm text-slate-400 mb-2">HORNET Professional</span>
              <span className="text-3xl font-bold font-mono text-green-400">$42,000/yr</span>
            </div>
          </div>
          <p className="text-xl text-slate-400">
            Save <span className="text-amber-400 font-bold">$213,000</span> per year • <span className="text-amber-400 font-bold">6x ROI</span>
          </p>
        </motion.div>
      </section>

      {/* Features Section */}
      <section className="py-24 px-16 relative z-10" id="features">
        <h2 className="text-4xl font-bold text-center mb-12">Built for real-world security operations</h2>
        <div className="grid grid-cols-4 gap-6 max-w-6xl mx-auto">
          {features.map((feature, i) => (
            <motion.div
              key={i}
              className={`bg-slate-900/50 border rounded-xl p-8 transition-all ${
                activeFeature === i ? 'border-amber-500 -translate-y-1' : 'border-white/5 hover:border-amber-500/50'
              }`}
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ delay: i * 0.1 }}
            >
              <span className="text-4xl mb-4 block">{feature.icon}</span>
              <h3 className="text-xl font-semibold mb-2">{feature.title}</h3>
              <p className="text-sm text-slate-400 leading-relaxed">{feature.desc}</p>
            </motion.div>
          ))}
        </div>
      </section>

      {/* Agent Layers Section */}
      <section className="py-24 px-16 relative z-10">
        <h2 className="text-4xl font-bold text-center mb-12">7 specialized agent layers</h2>
        <div className="max-w-xl mx-auto">
          {['Detection', 'Intelligence', 'Analysis', 'Action', 'Governance', 'Meta', 'Specialists'].map((layer, i) => (
            <motion.div
              key={layer}
              className="flex items-center gap-8 py-4 border-b border-white/5"
              initial={{ opacity: 0, x: -20 }}
              whileInView={{ opacity: 1, x: 0 }}
              viewport={{ once: true }}
              transition={{ delay: i * 0.1 }}
            >
              <span className="w-28 text-sm font-semibold text-slate-400">{layer}</span>
              <div className="flex gap-2">
                {[...Array(8)].map((_, j) => (
                  <motion.div
                    key={j}
                    className="w-3 h-3 bg-amber-500 rounded-sm"
                    animate={{ opacity: [0.3, 1, 0.3] }}
                    transition={{ duration: 2, delay: (i * 8 + j) * 0.05, repeat: Infinity }}
                  />
                ))}
              </div>
            </motion.div>
          ))}
        </div>
      </section>

      {/* Integrations Section */}
      <section className="py-24 px-16 relative z-10">
        <h2 className="text-4xl font-bold text-center mb-12">Connects to your existing stack</h2>
        <div className="flex flex-wrap justify-center gap-4 max-w-4xl mx-auto">
          {['CrowdStrike', 'Microsoft Defender', 'Splunk', 'SentinelOne', 'Elastic', 'Palo Alto'].map((name, i) => (
            <motion.div
              key={name}
              className="bg-slate-900/50 border border-white/10 hover:border-amber-500 rounded-lg px-6 py-3 text-sm font-medium text-slate-400 hover:text-white transition-all"
              initial={{ opacity: 0, scale: 0.9 }}
              whileInView={{ opacity: 1, scale: 1 }}
              viewport={{ once: true }}
              transition={{ delay: i * 0.05 }}
            >
              {name}
            </motion.div>
          ))}
        </div>
      </section>

      {/* Final CTA */}
      <section className="py-32 px-16 text-center relative z-10">
        <h2 className="text-5xl font-bold mb-4">Ready to automate your SOC?</h2>
        <p className="text-xl text-slate-400 mb-8">Start your free trial today. No credit card required.</p>
        <button 
          onClick={onLogin}
          className="inline-flex items-center gap-2 bg-gradient-to-r from-amber-500 to-amber-600 text-slate-950 px-12 py-5 rounded-lg font-semibold text-lg transition-all hover:-translate-y-0.5 hover:shadow-xl hover:shadow-amber-500/30"
        >
          Get Started Free
        </button>
      </section>

      {/* Pricing Modal */}
      <AnimatePresence>
        {showPricing && (
          <motion.div
            className="fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center z-50 p-8"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={() => setShowPricing(false)}
          >
            <motion.div
              className="bg-slate-900 border border-white/10 rounded-2xl p-10 max-w-5xl w-full max-h-[90vh] overflow-y-auto relative"
              initial={{ scale: 0.9, y: 20 }}
              animate={{ scale: 1, y: 0 }}
              exit={{ scale: 0.9, y: 20 }}
              onClick={(e) => e.stopPropagation()}
            >
              <button 
                className="absolute top-6 right-6 text-3xl text-slate-500 hover:text-white"
                onClick={() => setShowPricing(false)}
              >
                ×
              </button>
              <h2 className="text-3xl font-bold text-center mb-8">Simple, transparent pricing</h2>
              <div className="grid grid-cols-3 gap-6">
                {pricing.map((plan, i) => (
                  <div 
                    key={i} 
                    className={`bg-slate-800/50 border rounded-xl p-8 text-center relative ${
                      plan.popular ? 'border-amber-500 scale-105' : 'border-white/5'
                    }`}
                  >
                    {plan.popular && (
                      <span className="absolute -top-3 left-1/2 -translate-x-1/2 bg-amber-500 text-slate-950 px-4 py-1 rounded-full text-xs font-semibold">
                        Most Popular
                      </span>
                    )}
                    <h3 className="text-2xl font-bold mb-1">{plan.tier}</h3>
                    <p className="text-slate-500 text-sm mb-6">{plan.target}</p>
                    <div className="mb-2">
                      <span className="text-xl text-slate-400 align-top">$</span>
                      <span className="text-5xl font-bold font-mono text-amber-400">{plan.price}</span>
                      <span className="text-slate-500">/mo</span>
                    </div>
                    <p className="text-slate-400 text-sm mb-6">{plan.incidents} incidents/mo</p>
                    <ul className="text-left mb-8 space-y-2">
                      {plan.features.map((f, j) => (
                        <li key={j} className="text-slate-400 text-sm pl-6 relative">
                          <span className="absolute left-0 text-green-400">✓</span>
                          {f}
                        </li>
                      ))}
                    </ul>
                    <button className={`w-full py-3 rounded-lg font-semibold transition-all ${
                      plan.popular 
                        ? 'bg-gradient-to-r from-amber-500 to-amber-600 text-slate-950' 
                        : 'border border-white/20 text-white hover:border-amber-500'
                    }`}>
                      Get Started
                    </button>
                  </div>
                ))}
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Footer */}
      <footer className="py-8 px-16 border-t border-white/5 flex flex-wrap items-center justify-between gap-4 relative z-10">
        <div className="flex items-center gap-2 text-slate-500 font-semibold">
          <HornetLogo size={24} />
          <span>HORNET</span>
        </div>
        <div className="flex gap-8">
          <a href="#" className="text-slate-500 hover:text-amber-400 text-sm">Documentation</a>
          <a href="#" className="text-slate-500 hover:text-amber-400 text-sm">API Reference</a>
          <a href="#" className="text-slate-500 hover:text-amber-400 text-sm">Status</a>
          <a href="#" className="text-slate-500 hover:text-amber-400 text-sm">Contact</a>
        </div>
        <p className="text-slate-600 text-sm">© 2025 HORNET Security. All rights reserved.</p>
      </footer>
    </div>
  );
};

// Login Page Component
const LoginPage = ({ onAuth }) => {
  const [apiKey, setApiKey] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    
    setTimeout(() => {
      if (apiKey.startsWith('hnt_') || apiKey.length > 5) {
        onAuth(apiKey);
      } else {
        setError('Invalid API key format. Keys start with hnt_');
        setLoading(false);
      }
    }, 800);
  };

  return (
    <div className="min-h-screen bg-slate-950 flex items-center justify-center relative overflow-hidden">
      {/* Background particles */}
      <div className="absolute inset-0 pointer-events-none">
        {[...Array(20)].map((_, i) => (
          <motion.div
            key={i}
            className="absolute w-1 h-1 bg-amber-500 rounded-full"
            style={{ left: `${Math.random() * 100}%`, bottom: 0 }}
            animate={{ y: [0, -200], opacity: [0, 0.5, 0] }}
            transition={{ duration: 3 + Math.random() * 2, repeat: Infinity, delay: i * 0.2 }}
          />
        ))}
      </div>
      
      <motion.div
        className="bg-slate-900/80 border border-white/10 rounded-2xl p-10 w-full max-w-md backdrop-blur-xl"
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
      >
        <div className="text-center mb-8">
          <HornetLogo size={56} />
          <h1 className="text-2xl font-bold mt-4 tracking-widest">HORNET</h1>
          <p className="text-slate-500 text-sm uppercase tracking-widest">Autonomous SOC</p>
        </div>
        
        <div onSubmit={handleSubmit}>
          <div className="mb-6">
            <label className="block text-sm font-medium text-slate-400 mb-2 uppercase tracking-wide">
              API Key
            </label>
            <input
              type="password"
              value={apiKey}
              onChange={(e) => setApiKey(e.target.value)}
              placeholder="hnt_••••••••••••••••"
              className="w-full bg-slate-800 border border-white/10 rounded-lg px-4 py-3 font-mono text-white focus:outline-none focus:border-amber-500 transition-colors"
            />
          </div>
          
          {error && (
            <div className="bg-red-500/10 border border-red-500/30 text-red-400 px-4 py-3 rounded-lg text-sm mb-6">
              {error}
            </div>
          )}
          
          <button 
            onClick={handleSubmit}
            disabled={loading}
            className="w-full bg-gradient-to-r from-amber-500 to-amber-600 text-slate-950 py-3 rounded-lg font-semibold transition-all hover:-translate-y-0.5 hover:shadow-lg hover:shadow-amber-500/30 disabled:opacity-70 disabled:cursor-not-allowed flex items-center justify-center gap-2"
          >
            {loading ? (
              <span className="w-5 h-5 border-2 border-transparent border-t-slate-950 rounded-full animate-spin" />
            ) : (
              'Authenticate'
            )}
          </button>
        </div>
        
        <div className="flex justify-center gap-4 mt-8 pt-6 border-t border-white/5">
          <a href="#" className="text-slate-500 hover:text-amber-400 text-sm">Request access</a>
          <span className="text-slate-700">•</span>
          <a href="#" className="text-slate-500 hover:text-amber-400 text-sm">Documentation</a>
        </div>
      </motion.div>
    </div>
  );
};

// Dashboard Component
const Dashboard = ({ onLogout }) => {
  const [selectedIncident, setSelectedIncident] = useState(null);
  const [filter, setFilter] = useState('all');

  const incidents = [
    { id: '646e5e8f', state: 'CLOSED', severity: 'CRITICAL', confidence: 85, tokens: 107072, age: '2h', summary: 'C2 beacon detected from 185.220.101.33 to internal host 10.0.0.50. Tor exit node confirmed via threat intel. Auto-contained and blocked.' },
    { id: 'ec534199', state: 'CLOSED', severity: 'CRITICAL', confidence: 70, tokens: 56841, age: '2h', summary: 'Suspicious outbound traffic pattern detected. Analysis confirmed false positive - legitimate CDN traffic.' },
    { id: 'e3c1d4b3', state: 'CLOSED', severity: 'CRITICAL', confidence: 70, tokens: 97735, age: '2h', summary: 'Potential data exfiltration attempt. Blocked and user notified for credential rotation.' },
    { id: '1c68e793', state: 'CLOSED', severity: 'HIGH', confidence: 95, tokens: 19806, age: '2h', summary: 'Brute force login attempt from known bad IP. Auto-blocked at firewall.' },
    { id: '925ffdf4', state: 'CLOSED', severity: 'CRITICAL', confidence: 70, tokens: 64248, age: '2h', summary: 'Malware signature detected in email attachment. Quarantined and sender blacklisted.' },
    { id: '4c7b69f3', state: 'ERROR', severity: 'CRITICAL', confidence: 85, tokens: 0, age: '1h', summary: 'Processing error - requires manual review' },
    { id: '22d10f2c', state: 'ANALYSIS', severity: 'HIGH', confidence: 45, tokens: 12500, age: '5m', summary: 'Active analysis in progress...' },
  ];

  const filteredIncidents = incidents.filter(inc => {
    if (filter === 'all') return true;
    if (filter === 'active') return !['CLOSED', 'ERROR'].includes(inc.state);
    if (filter === 'attention') return inc.state === 'ERROR' || inc.confidence < 50;
    return inc.state === filter;
  });

  const agentStatus = { intel: 'ready', analyst: 'ready', responder: 'ready', oversight: 'ready', router: 'ready' };

  const getStateStyles = (state) => {
    const styles = {
      CLOSED: 'bg-green-500/10 text-green-400',
      ERROR: 'bg-red-500/10 text-red-400',
      ANALYSIS: 'bg-blue-500/10 text-blue-400',
    };
    return styles[state] || 'bg-slate-500/10 text-slate-400';
  };

  const getSeverityStyles = (severity) => {
    const styles = {
      CRITICAL: 'bg-red-500/15 text-red-400',
      HIGH: 'bg-orange-500/15 text-orange-400',
      MEDIUM: 'bg-yellow-500/15 text-yellow-400',
      LOW: 'bg-green-500/15 text-green-400',
    };
    return styles[severity] || 'bg-slate-500/10 text-slate-400';
  };

  return (
    <div className="min-h-screen bg-slate-950">
      {/* Header */}
      <header className="flex justify-between items-center px-6 py-3 bg-slate-900 border-b border-white/5">
        <div className="flex items-center gap-4">
          <HornetLogo size={32} />
          <span className="text-lg font-bold tracking-widest">HORNET</span>
          <span className="flex items-center gap-2 text-xs font-medium text-green-400 uppercase tracking-widest">
            <span className="w-2 h-2 bg-green-400 rounded-full animate-pulse" />
            OPERATIONAL
          </span>
        </div>
        <div className="flex items-center gap-6">
          <span className="text-xs text-cyan-400">● WebSocket Live</span>
          <button 
            onClick={onLogout}
            className="border border-white/10 hover:border-amber-500 text-slate-400 hover:text-amber-400 px-4 py-2 rounded-lg text-sm transition-all"
          >
            Logout
          </button>
        </div>
      </header>

      {/* Stats Bar */}
      <div className="grid grid-cols-5 gap-4 p-6">
        {[
          { label: 'Active Incidents', value: '1', sub: 'processing now' },
          { label: 'Events / Hour', value: '23', sub: 'last 60 minutes' },
          { label: 'Agents Online', value: '56', sub: 'swarm capacity', highlight: 'cyan' },
          { label: 'Auto-Resolved', value: '86%', sub: 'no human needed', highlight: 'green' },
          { label: 'Tokens Today', value: '1927.5k', sub: '~$15.42 est.' },
        ].map((stat, i) => (
          <div key={i} className="bg-slate-900/50 border border-white/5 rounded-xl p-5">
            <span className="block text-xs text-slate-500 uppercase tracking-wide mb-2">{stat.label}</span>
            <span className={`block text-3xl font-bold font-mono ${
              stat.highlight === 'cyan' ? 'text-cyan-400' : 
              stat.highlight === 'green' ? 'text-green-400' : 'text-white'
            }`}>{stat.value}</span>
            <span className="text-xs text-slate-500">{stat.sub}</span>
          </div>
        ))}
      </div>

      {/* Main Content */}
      <div className="grid grid-cols-[1fr_340px] gap-6 px-6 pb-6">
        {/* Incident Panel */}
        <div className="bg-slate-900/50 border border-white/5 rounded-xl overflow-hidden">
          <div className="flex justify-between items-center px-6 py-4 border-b border-white/5">
            <h2 className="text-sm font-semibold uppercase tracking-wide">Incident Queue</h2>
            <div className="flex gap-3">
              <select 
                value={filter}
                onChange={(e) => setFilter(e.target.value)}
                className="bg-slate-800 border border-white/10 rounded-lg px-4 py-2 text-sm text-white"
              >
                <option value="all">All States</option>
                <option value="active">Active</option>
                <option value="attention">Needs Attention</option>
                <option value="CLOSED">Closed</option>
              </select>
              <button className="border border-amber-500 text-amber-400 hover:bg-amber-500 hover:text-slate-950 px-4 py-2 rounded-lg text-sm font-medium transition-all">
                Refresh
              </button>
            </div>
          </div>
          
          {/* Table Header */}
          <div className="grid grid-cols-[100px_90px_90px_150px_100px_60px_60px] gap-4 px-6 py-3 bg-slate-800/50 text-xs font-semibold text-slate-500 uppercase tracking-wide">
            <span>ID</span>
            <span>State</span>
            <span>Severity</span>
            <span>Confidence</span>
            <span>Tokens</span>
            <span>Age</span>
            <span></span>
          </div>
          
          {/* Table Rows */}
          {filteredIncidents.map((inc) => (
            <motion.div
              key={inc.id}
              className={`grid grid-cols-[100px_90px_90px_150px_100px_60px_60px] gap-4 px-6 py-4 border-b border-white/3 items-center cursor-pointer transition-colors ${
                inc.state === 'ERROR' ? 'bg-red-500/5' : ''
              } ${selectedIncident?.id === inc.id ? 'bg-amber-500/10' : 'hover:bg-amber-500/5'}`}
              onClick={() => setSelectedIncident(inc)}
              whileHover={{ backgroundColor: 'rgba(245, 158, 11, 0.05)' }}
            >
              <span className="font-mono text-sm text-slate-400">{inc.id}</span>
              <span className={`inline-block px-2 py-1 rounded text-xs font-semibold uppercase ${getStateStyles(inc.state)}`}>
                {inc.state}
              </span>
              <span className={`inline-block px-2 py-1 rounded text-xs font-semibold uppercase ${getSeverityStyles(inc.severity)}`}>
                {inc.severity}
              </span>
              <div className="flex items-center gap-2">
                <span className="font-mono text-sm w-10">{inc.confidence}%</span>
                <div className="flex-1 h-1.5 bg-white/10 rounded overflow-hidden">
                  <div 
                    className="h-full rounded transition-all"
                    style={{ 
                      width: `${inc.confidence}%`,
                      backgroundColor: inc.confidence >= 80 ? '#22c55e' : inc.confidence >= 50 ? '#f59e0b' : '#ef4444'
                    }}
                  />
                </div>
              </div>
              <span className="font-mono text-sm text-slate-400">{inc.tokens.toLocaleString()}</span>
              <span className="text-sm text-slate-500">{inc.age}</span>
              <button className="text-amber-400 text-sm font-medium hover:underline">View</button>
            </motion.div>
          ))}
        </div>

        {/* Sidebar */}
        <div className="flex flex-col gap-4">
          {/* Agent Activity */}
          <div className="bg-slate-900/50 border border-white/5 rounded-xl p-5">
            <h3 className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-4">Agent Activity</h3>
            <div className="space-y-3">
              {Object.entries(agentStatus).map(([agent, status]) => (
                <div key={agent} className="flex justify-between items-center">
                  <span className="text-sm text-slate-400">{agent}</span>
                  <span className="text-xs font-medium text-green-400">● Ready</span>
                </div>
              ))}
            </div>
          </div>

          {/* Requires Attention */}
          <div className="bg-slate-900/50 border border-amber-500/30 rounded-xl p-5">
            <h3 className="text-xs font-semibold text-amber-400 uppercase tracking-wide mb-4">⚠ Requires Attention</h3>
            {incidents.filter(i => i.state === 'ERROR').map(inc => (
              <div 
                key={inc.id} 
                className="bg-slate-800/50 rounded-lg p-3 cursor-pointer hover:bg-slate-800 transition-colors"
                onClick={() => setSelectedIncident(inc)}
              >
                <div className="flex justify-between items-center mb-2">
                  <span className="font-mono text-sm text-slate-400">{inc.id}</span>
                  <span className="bg-red-500/15 text-red-400 px-2 py-0.5 rounded text-xs font-semibold">ERROR</span>
                </div>
                <span className={`inline-block px-2 py-0.5 rounded text-xs font-semibold uppercase ${getSeverityStyles(inc.severity)}`}>
                  {inc.severity}
                </span>
                <span className="block text-xs text-slate-500 mt-1">Processing error</span>
              </div>
            ))}
          </div>

          {/* Recent Findings */}
          {selectedIncident && (
            <div className="bg-slate-900/50 border border-white/5 rounded-xl p-5">
              <h3 className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-4">Recent Findings</h3>
              <p className="text-sm text-slate-400 leading-relaxed">{selectedIncident.summary}</p>
            </div>
          )}

          {/* System Health */}
          <div className="bg-slate-900/50 border border-white/5 rounded-xl p-5">
            <h3 className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-4">System Health</h3>
            <div className="space-y-2">
              {['Redis', 'PostgreSQL', 'Workers', 'Anthropic API'].map((service, i) => (
                <div key={service} className="flex justify-between items-center text-sm">
                  <span className="text-slate-400">{service}</span>
                  <span className="text-xs font-medium text-green-400">
                    ● {service === 'Workers' ? '3 Active' : 'Connected'}
                  </span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Incident Detail Modal */}
      <AnimatePresence>
        {selectedIncident && (
          <motion.div
            className="fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center z-50 p-8"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={() => setSelectedIncident(null)}
          >
            <motion.div
              className="bg-slate-900 border border-white/10 rounded-2xl w-full max-w-2xl max-h-[90vh] overflow-y-auto"
              initial={{ scale: 0.95, y: 20 }}
              animate={{ scale: 1, y: 0 }}
              exit={{ scale: 0.95, y: 20 }}
              onClick={(e) => e.stopPropagation()}
            >
              <div className="flex justify-between items-start p-6 border-b border-white/5">
                <div>
                  <h2 className="text-xl font-mono mb-2">Incident {selectedIncident.id}</h2>
                  <div className="flex gap-2">
                    <span className={`px-2 py-1 rounded text-xs font-semibold uppercase ${getStateStyles(selectedIncident.state)}`}>
                      {selectedIncident.state}
                    </span>
                    <span className={`px-2 py-1 rounded text-xs font-semibold uppercase ${getSeverityStyles(selectedIncident.severity)}`}>
                      {selectedIncident.severity}
                    </span>
                  </div>
                </div>
                <button 
                  className="text-3xl text-slate-500 hover:text-white"
                  onClick={() => setSelectedIncident(null)}
                >
                  ×
                </button>
              </div>
              
              <div className="p-6">
                <div className="mb-6">
                  <h4 className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-2">Executive Summary</h4>
                  <p className="text-slate-300 leading-relaxed">{selectedIncident.summary}</p>
                </div>
                
                <div className="grid grid-cols-3 gap-4 bg-slate-800/50 rounded-lg p-4 mb-6">
                  <div className="text-center">
                    <span className="block text-xs text-slate-500 mb-1">Confidence</span>
                    <span className="text-2xl font-bold font-mono text-amber-400">{selectedIncident.confidence}%</span>
                  </div>
                  <div className="text-center">
                    <span className="block text-xs text-slate-500 mb-1">Tokens Used</span>
                    <span className="text-2xl font-bold font-mono text-amber-400">{selectedIncident.tokens.toLocaleString()}</span>
                  </div>
                  <div className="text-center">
                    <span className="block text-xs text-slate-500 mb-1">Processing Time</span>
                    <span className="text-2xl font-bold font-mono text-amber-400">{selectedIncident.age}</span>
                  </div>
                </div>

                <div>
                  <h4 className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-4">Agent Findings</h4>
                  <div className="relative pl-6 border-l-2 border-white/10">
                    {['HunterAgent', 'IntelAgent', 'AnalystAgent', 'OversightAgent'].map((agent, i) => (
                      <div key={agent} className="relative pb-4">
                        <div className="absolute -left-8 top-1 w-3 h-3 bg-amber-500 rounded-full border-2 border-slate-900" />
                        <span className="block text-sm font-medium text-white">{agent}</span>
                        <span className="text-xs text-slate-500">Analysis complete • {Math.floor(Math.random() * 5000 + 1000)} tokens</span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
              
              <div className="flex justify-end gap-3 p-6 border-t border-white/5">
                <button className="border border-white/15 text-slate-400 hover:text-white px-5 py-2 rounded-lg text-sm font-medium transition-all">
                  Export Report
                </button>
                <button className="border border-white/15 text-slate-400 hover:text-white px-5 py-2 rounded-lg text-sm font-medium transition-all">
                  View Raw Data
                </button>
                {selectedIncident.state === 'ERROR' && (
                  <button className="bg-gradient-to-r from-amber-500 to-amber-600 text-slate-950 px-5 py-2 rounded-lg text-sm font-semibold">
                    Retry Processing
                  </button>
                )}
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};

// Main App Component
export default function App() {
  const [view, setView] = useState('landing');

  if (view === 'landing') {
    return <LandingPage onLogin={() => setView('login')} />;
  }
  
  if (view === 'login') {
    return <LoginPage onAuth={() => setView('dashboard')} />;
  }
  
  return <Dashboard onLogout={() => setView('landing')} />;
}
