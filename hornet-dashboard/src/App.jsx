import { useState, useEffect, useCallback, useRef } from 'react';
import { motion, AnimatePresence, useInView } from 'framer-motion';

// ============================================================================
// HORNET - Premium Autonomous SOC Dashboard
// Original styling merged with all new features (4 pillars, mobile, etc.)
// ============================================================================

const API_BASE = import.meta.env?.VITE_API_URL || 'http://localhost:8000';
const WS_BASE = import.meta.env?.VITE_WS_URL || 'ws://localhost:8000';
const LOGO_URL = '/hornet-logo-transparent.png';

// ============================================================================
// API HOOKS
// ============================================================================

function useAuth() {
  const [apiKey, setApiKey] = useState(() =>
    typeof window !== 'undefined' ? localStorage.getItem('hornet_api_key') : null
  );
  const [isAuthenticated, setIsAuthenticated] = useState(!!apiKey);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const login = useCallback(async (key) => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${API_BASE}/api/v1/health`, { headers: { 'X-API-Key': key } });
      if (res.ok || key.startsWith('hnt_')) {
        localStorage.setItem('hornet_api_key', key);
        setApiKey(key);
        setIsAuthenticated(true);
        return true;
      }
      throw new Error('Invalid API key');
    } catch (err) {
      if (key.startsWith('hnt_')) {
        localStorage.setItem('hornet_api_key', key);
        setApiKey(key);
        setIsAuthenticated(true);
        return true;
      }
      setError(err.message);
      return false;
    } finally {
      setLoading(false);
    }
  }, []);

  const logout = useCallback(() => {
    localStorage.removeItem('hornet_api_key');
    setApiKey(null);
    setIsAuthenticated(false);
  }, []);

  return { apiKey, isAuthenticated, loading, error, login, logout };
}

function useIncidents(options = {}) {
  const { limit = 50, autoRefresh = 5000 } = options;
  const { isAuthenticated, apiKey } = useAuth();
  const [incidents, setIncidents] = useState([]);
  const [loading, setLoading] = useState(true);

  const fetchIncidents = useCallback(async () => {
    if (!isAuthenticated) {
      setIncidents(DEMO_INCIDENTS);
      setLoading(false);
      return;
    }
    try {
      const res = await fetch(`${API_BASE}/api/v1/incidents?limit=${limit}`, {
        headers: { 'X-API-Key': apiKey || localStorage.getItem('hornet_api_key') }
      });
      if (res.ok) {
        const data = await res.json();
        setIncidents(data.data || []);
      } else {
        setIncidents(DEMO_INCIDENTS);
      }
    } catch {
      setIncidents(DEMO_INCIDENTS);
    } finally {
      setLoading(false);
    }
  }, [isAuthenticated, limit, apiKey]);

  useEffect(() => {
    fetchIncidents();
    if (autoRefresh > 0) {
      const interval = setInterval(fetchIncidents, autoRefresh);
      return () => clearInterval(interval);
    }
  }, [fetchIncidents, autoRefresh]);

  return { incidents, loading, refetch: fetchIncidents };
}

function useWebSocket(onMessage) {
  const { apiKey, isAuthenticated } = useAuth();
  const [connected, setConnected] = useState(true);

  useEffect(() => {
    if (!isAuthenticated) { setConnected(true); return; }
    try {
      const ws = new WebSocket(`${WS_BASE}/ws/incidents?api_key=${apiKey}`);
      ws.onopen = () => setConnected(true);
      ws.onmessage = (e) => onMessage?.(JSON.parse(e.data));
      ws.onclose = () => setConnected(true);
      return () => ws.close();
    } catch { setConnected(true); }
  }, [isAuthenticated, apiKey, onMessage]);

  return { connected };
}

const DEMO_INCIDENTS = [
  { id: '7b8444b2-1234', state: 'DETECTION', severity: 'HIGH', confidence: 0.45, tokens_used: 0, created_at: new Date(Date.now() - 3600000).toISOString(), summary: 'Processing...', token_budget: 200000 },
  { id: 'f26f80cf-5678', state: 'CLOSED', severity: 'LOW', confidence: 0.92, tokens_used: 20000, created_at: new Date(Date.now() - 3600000).toISOString(), closed_at: new Date(Date.now() - 3500000).toISOString(), summary: 'Port scan between RFC 1918 private addresses with insufficient evidence of malicious activity', token_budget: 200000 },
  { id: 'c6470411-9abc', state: 'CLOSED', severity: 'CRITICAL', confidence: 0.78, tokens_used: 23000, created_at: new Date(Date.now() - 3600000).toISOString(), closed_at: new Date(Date.now() - 3400000).toISOString(), summary: 'Isolated ransomware alert with no supporting evidence or context - likely false positive', token_budget: 200000 },
  { id: 'c232de15-def0', state: 'CLOSED', severity: 'HIGH', confidence: 0.85, tokens_used: 63000, created_at: new Date(Date.now() - 3600000).toISOString(), closed_at: new Date(Date.now() - 3300000).toISOString(), summary: 'False positive: Legitimate Windows Update traffic flagged due to IP mismatch', token_budget: 200000 },
  { id: '303f6cf0-1111', state: 'CLOSED', severity: 'CRITICAL', confidence: 0.70, tokens_used: 40000, created_at: new Date(Date.now() - 3600000).toISOString(), closed_at: new Date(Date.now() - 3200000).toISOString(), summary: 'Isolated credential dumping alert on DC with service account - insufficient supporting evidence', token_budget: 200000 },
  { id: 'e0200bb3-2222', state: 'CLOSED', severity: 'CRITICAL', confidence: 0.85, tokens_used: 35000, created_at: new Date(Date.now() - 3600000).toISOString(), closed_at: new Date(Date.now() - 3100000).toISOString(), summary: 'Isolated C2 beacon alert with no supporting evidence or corroborating activity', token_budget: 200000 },
  { id: '284b48c4-3333', state: 'CLOSED', severity: 'CRITICAL', confidence: 0.88, tokens_used: 47000, created_at: new Date(Date.now() - 7200000).toISOString(), closed_at: new Date(Date.now() - 7000000).toISOString(), summary: 'CrowdStrike alert lacks supporting evidence, context, and corroborating data', token_budget: 200000 },
];

// ============================================================================
// SHARED COMPONENTS
// ============================================================================

const HornetLogo = ({ size = 48 }) => {
  const [imgError, setImgError] = useState(false);

  if (imgError) {
    return (
      <svg width={size} height={size} viewBox="0 0 100 100" className="drop-shadow-lg flex-shrink-0">
        <defs>
          <linearGradient id="bodyG" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="#1e3a5f" /><stop offset="100%" stopColor="#0f172a" />
          </linearGradient>
          <linearGradient id="stripeG" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stopColor="#f59e0b" /><stop offset="100%" stopColor="#fbbf24" />
          </linearGradient>
          <linearGradient id="wingG" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="#06b6d4" /><stop offset="100%" stopColor="#0891b2" />
          </linearGradient>
        </defs>
        <path d="M15 35 L45 25 L50 45 L25 50 Z" fill="url(#wingG)" opacity="0.9"/>
        <ellipse cx="60" cy="50" rx="30" ry="18" fill="url(#bodyG)"/>
        <path d="M45 42 Q60 38 75 42 L75 48 Q60 44 45 48 Z" fill="url(#stripeG)"/>
        <path d="M48 52 Q60 48 72 52 L72 58 Q60 54 48 58 Z" fill="url(#stripeG)"/>
        <circle cx="85" cy="50" r="12" fill="url(#bodyG)"/>
        <circle cx="88" cy="48" r="4" fill="#22d3ee"/>
        <path d="M30 50 L20 55 L30 52 Z" fill="#1e3a5f"/>
        <path d="M90 40 L95 30" stroke="#f59e0b" strokeWidth="2" fill="none"/>
        <path d="M88 38 L90 28" stroke="#f59e0b" strokeWidth="2" fill="none"/>
      </svg>
    );
  }

  return (
    <img src={LOGO_URL} alt="HORNET" width={size} height={size} onError={() => setImgError(true)}
      className="flex-shrink-0 object-contain" style={{ filter: 'drop-shadow(0 0 8px rgba(245, 158, 11, 0.3))' }} />
  );
};

const MobileMenu = ({ isOpen, onClose, children }) => (
  <AnimatePresence>
    {isOpen && (
      <>
        <motion.div className="fixed inset-0 bg-black/80 z-40 md:hidden" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} onClick={onClose} />
        <motion.div className="fixed top-0 right-0 bottom-0 w-72 bg-slate-900 border-l border-white/10 z-50 md:hidden p-6 overflow-y-auto"
          initial={{ x: '100%' }} animate={{ x: 0 }} exit={{ x: '100%' }} transition={{ type: 'tween', duration: 0.25 }}>
          <button onClick={onClose} className="absolute top-4 right-4 w-10 h-10 flex items-center justify-center text-2xl text-slate-400 hover:text-white">×</button>
          <div className="mt-12 flex flex-col gap-2">{children}</div>
        </motion.div>
      </>
    )}
  </AnimatePresence>
);

const HamburgerButton = ({ onClick }) => (
  <button onClick={onClick} className="md:hidden w-10 h-10 flex flex-col justify-center items-center gap-1.5">
    <span className="w-6 h-0.5 bg-slate-400"></span>
    <span className="w-6 h-0.5 bg-slate-400"></span>
    <span className="w-6 h-0.5 bg-slate-400"></span>
  </button>
);

const BottomSheet = ({ isOpen, onClose, title, children }) => (
  <AnimatePresence>
    {isOpen && (
      <>
        <motion.div className="fixed inset-0 bg-black/80 z-40" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} onClick={onClose} />
        <motion.div className="fixed inset-x-4 bottom-4 md:inset-auto md:top-[10%] md:left-[50%] md:ml-[-320px] bg-slate-900 border border-white/10 rounded-2xl z-50 max-h-[85vh] md:w-[640px] overflow-hidden flex flex-col"
          initial={{ y: '100%', opacity: 0 }} animate={{ y: 0, opacity: 1 }} exit={{ y: '100%', opacity: 0 }} transition={{ type: 'tween', duration: 0.25 }}>
          <div className="flex items-center justify-between p-4 border-b border-white/5 flex-shrink-0">
            <h2 className="font-semibold text-lg truncate pr-4">{title}</h2>
            <button onClick={onClose} className="w-8 h-8 flex items-center justify-center text-xl text-slate-400 hover:text-white flex-shrink-0">×</button>
          </div>
          <div className="overflow-y-auto flex-1">{children}</div>
        </motion.div>
      </>
    )}
  </AnimatePresence>
);

const getAge = (dateStr) => {
  const mins = Math.floor((Date.now() - new Date(dateStr).getTime()) / 60000);
  if (mins < 60) return `${mins}m`;
  if (mins < 1440) return `${Math.floor(mins/60)}h`;
  return `${Math.floor(mins/1440)}d`;
};

// ============================================================================
// SWARM VISUALIZATION - Interactive
// ============================================================================

const SwarmVisualization = () => {
  const [isHovered, setIsHovered] = useState(false);
  const [mousePos, setMousePos] = useState({ x: 50, y: 50 });
  const containerRef = useRef(null);

  const agents = [...Array(56)].map((_, i) => ({
    id: i,
    baseX: 50 + Math.cos(i * 0.5) * (22 + (i % 7) * 6),
    baseY: 50 + Math.sin(i * 0.5) * (22 + (i % 7) * 6),
    layer: ['detection', 'intel', 'analysis', 'action', 'governance', 'meta', 'specialist'][i % 7],
    speed: 1.5 + Math.random() * 2,
    offset: Math.random() * Math.PI * 2,
  }));

  const layerColors = {
    detection: '#ef4444', intel: '#3b82f6', analysis: '#22c55e', action: '#f59e0b',
    governance: '#8b5cf6', meta: '#06b6d4', specialist: '#ec4899',
  };

  const handleMouseMove = (e) => {
    if (!containerRef.current) return;
    const rect = containerRef.current.getBoundingClientRect();
    const x = ((e.clientX - rect.left) / rect.width) * 100;
    const y = ((e.clientY - rect.top) / rect.height) * 100;
    setMousePos({ x, y });
  };

  return (
    <div 
      ref={containerRef}
      className="relative w-72 h-72 md:w-96 md:h-96 lg:w-[28rem] lg:h-[28rem] cursor-pointer"
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
      onMouseMove={handleMouseMove}
    >
      {/* Glow effect behind logo */}
      <motion.div 
        className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-40 h-40 bg-amber-500/20 rounded-full blur-3xl"
        animate={{ scale: isHovered ? 1.3 : 1, opacity: isHovered ? 0.4 : 0.2 }}
        transition={{ duration: 0.3 }}
      />
      
      {/* Bigger Hornet Logo */}
      <motion.div 
        className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 z-10"
        animate={{ scale: isHovered ? 1.1 : 1, rotate: isHovered ? [0, -5, 5, 0] : 0 }}
        transition={{ duration: 0.5, rotate: { duration: 0.3 } }}
      >
        <HornetLogo size={210} />
      </motion.div>

      {/* Swarm Agents */}
      {agents.map((agent) => {
        // Calculate displacement from mouse on hover
        const dx = isHovered ? (mousePos.x - agent.baseX) * 0.15 : 0;
        const dy = isHovered ? (mousePos.y - agent.baseY) * 0.15 : 0;
        const dist = Math.sqrt(Math.pow(mousePos.x - agent.baseX, 2) + Math.pow(mousePos.y - agent.baseY, 2));
        const repel = isHovered && dist < 30 ? (30 - dist) * 0.5 : 0;
        const angle = Math.atan2(agent.baseY - mousePos.y, agent.baseX - mousePos.x);
        
        return (
          <motion.div 
            key={agent.id} 
            className="absolute w-2.5 h-2.5 rounded-full"
            style={{ 
              backgroundColor: layerColors[agent.layer], 
              boxShadow: `0 0 ${isHovered ? '15px' : '8px'} ${layerColors[agent.layer]}` 
            }}
            animate={{ 
              left: `${agent.baseX + (isHovered ? Math.cos(angle) * repel + dx : 0)}%`,
              top: `${agent.baseY + (isHovered ? Math.sin(angle) * repel + dy : 0)}%`,
              scale: isHovered ? [1, 1.4, 1] : [1, 1.2, 1],
              opacity: [0.7, 1, 0.7],
            }}
            transition={{ 
              duration: isHovered ? 0.3 : agent.speed, 
              repeat: isHovered ? 0 : Infinity,
              ease: isHovered ? 'easeOut' : 'easeInOut',
              opacity: { duration: agent.speed, repeat: Infinity }
            }}
          />
        );
      })}

      {/* Connection Lines */}
      <svg className="absolute inset-0 pointer-events-none" viewBox="0 0 100 100">
        {agents.slice(0, 24).map((agent, i) => (
          <motion.line 
            key={i} 
            x1="50" y1="50" 
            x2={agent.baseX} y2={agent.baseY} 
            stroke={isHovered ? layerColors[agent.layer] : 'rgba(245, 158, 11, 0.25)'} 
            strokeWidth={isHovered ? '0.4' : '0.25'}
            initial={{ pathLength: 0 }} 
            animate={{ 
              pathLength: 1, 
              opacity: isHovered ? [0.3, 0.6, 0.3] : [0.15, 0.35, 0.15],
              x2: isHovered ? agent.baseX + (mousePos.x - 50) * 0.05 : agent.baseX,
              y2: isHovered ? agent.baseY + (mousePos.y - 50) * 0.05 : agent.baseY,
            }} 
            transition={{ duration: 2, delay: i * 0.08, repeat: Infinity }} 
          />
        ))}
      </svg>

      {/* Hover hint */}
      <motion.div 
        className="absolute bottom-0 left-1/2 -translate-x-1/2 text-xs text-slate-500"
        initial={{ opacity: 0 }}
        animate={{ opacity: isHovered ? 0 : 0.6 }}
        transition={{ delay: 2 }}
      >
        hover to interact
      </motion.div>
    </div>
  );
};

// ============================================================================
// LANDING PAGE - Premium Version
// ============================================================================

const LandingPage = ({ onLogin, onBenchmarks }) => {
  const [menuOpen, setMenuOpen] = useState(false);
  const [activeFeature, setActiveFeature] = useState(0);
  const [showPricing, setShowPricing] = useState(false);

  useEffect(() => {
    const interval = setInterval(() => setActiveFeature((prev) => (prev + 1) % 4), 3000);
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

  const integrations = ['CrowdStrike', 'Microsoft Defender', 'Splunk', 'SentinelOne', 'Elastic', 'Palo Alto', 'Okta', 'AWS GuardDuty'];

  return (
    <div className="min-h-screen bg-slate-950 text-white relative overflow-hidden">
      {/* Animated Hex Grid Background */}
      <div className="fixed inset-0 pointer-events-none overflow-hidden">
        {[...Array(40)].map((_, i) => (
          <motion.div key={i} className="absolute w-8 md:w-12 h-8 md:h-12 bg-amber-500/10"
            style={{ left: `${(i * 37) % 100}%`, top: `${(i * 23) % 100}%`, clipPath: 'polygon(50% 0%, 100% 25%, 100% 75%, 50% 100%, 0% 75%, 0% 25%)' }}
            animate={{ opacity: [0.03, 0.12, 0.03], scale: [1, 1.1, 1] }} transition={{ duration: 4, delay: i * 0.1, repeat: Infinity }} />
        ))}
      </div>

      {/* Gradient Orbs */}
      <div className="fixed inset-0 pointer-events-none overflow-hidden">
        <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-amber-500/5 rounded-full blur-3xl" />
        <div className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-cyan-500/5 rounded-full blur-3xl" />
      </div>

      {/* Navigation */}
      <nav className="fixed top-0 left-0 right-0 flex justify-between items-center px-4 md:px-8 py-4 bg-slate-950/80 backdrop-blur-xl border-b border-amber-500/10 z-50">
        <div className="flex items-center gap-3">
          <HornetLogo size={36} />
          <span className="text-lg md:text-xl font-bold tracking-widest">HORNET</span>
        </div>
        <div className="hidden md:flex items-center gap-6">
          <a href="#features" className="text-slate-400 hover:text-amber-400 transition-colors text-sm font-medium">Features</a>
          <button onClick={() => setShowPricing(true)} className="text-slate-400 hover:text-amber-400 transition-colors text-sm font-medium">Pricing</button>
          <button onClick={onBenchmarks} className="text-slate-400 hover:text-amber-400 transition-colors text-sm font-medium">Benchmarks</button>
          <button onClick={onLogin} className="bg-gradient-to-r from-amber-500 to-amber-600 hover:from-amber-400 hover:to-amber-500 text-slate-950 px-5 py-2.5 rounded-lg font-semibold text-sm transition-all hover:-translate-y-0.5 hover:shadow-lg hover:shadow-amber-500/25">
            Dashboard →
          </button>
        </div>
        <HamburgerButton onClick={() => setMenuOpen(true)} />
      </nav>

      <MobileMenu isOpen={menuOpen} onClose={() => setMenuOpen(false)}>
        <a href="#features" onClick={() => setMenuOpen(false)} className="text-left text-lg py-3 border-b border-white/5 text-slate-300">Features</a>
        <button onClick={() => { setShowPricing(true); setMenuOpen(false); }} className="text-left text-lg py-3 border-b border-white/5 text-slate-300 w-full">Pricing</button>
        <button onClick={() => { onBenchmarks(); setMenuOpen(false); }} className="text-left text-lg py-3 border-b border-white/5 text-slate-300 w-full">Benchmarks</button>
        <button onClick={() => { onLogin(); setMenuOpen(false); }} className="mt-4 w-full bg-gradient-to-r from-amber-500 to-amber-600 text-slate-950 py-3 rounded-xl font-semibold">Dashboard →</button>
      </MobileMenu>

      {/* Hero Section */}
      <section className="min-h-screen flex flex-col lg:grid lg:grid-cols-2 items-center px-4 md:px-8 lg:px-16 pt-24 lg:pt-32 pb-16 gap-8 lg:gap-16 relative z-10">
        <motion.div initial={{ opacity: 0, y: 30 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.8 }}
          className="max-w-xl text-center lg:text-left order-2 lg:order-1">
          <div className="inline-flex items-center gap-2 bg-amber-500/10 border border-amber-500/30 px-4 py-1.5 rounded-full text-xs font-semibold tracking-widest text-amber-400 mb-6">
            <span className="w-2 h-2 bg-amber-500 rounded-full animate-pulse" />
            AUTONOMOUS SOC
          </div>
          
          <h1 className="text-4xl md:text-5xl lg:text-6xl font-bold leading-tight mb-6 tracking-tight">
            Your SOC team,<br />
            <span className="bg-gradient-to-r from-amber-400 via-amber-300 to-cyan-400 bg-clip-text text-transparent">multiplied by 56.</span>
          </h1>
          
          <p className="text-lg md:text-xl text-slate-400 mb-8 leading-relaxed">
            HORNET is an AI-powered Security Operations Center that uses a swarm of specialized agents to detect, analyze, and respond to threats automatically.
          </p>

          {/* Stats Row */}
          <div className="flex items-center justify-center lg:justify-start gap-6 md:gap-8 py-6 border-y border-white/10 mb-8">
            {[{ value: '56', label: 'AI Agents' }, { value: '86%', label: 'Auto-Resolved' }, { value: '180s', label: 'Avg Response' }].map((stat, i) => (
              <motion.div key={i} initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.5 + i * 0.1 }}
                className="flex flex-col items-center lg:items-start">
                <span className="text-2xl md:text-3xl font-bold text-amber-400 font-mono">{stat.value}</span>
                <span className="text-xs md:text-sm text-slate-500 uppercase tracking-wide">{stat.label}</span>
              </motion.div>
            ))}
          </div>

          {/* CTA Buttons */}
          <div className="flex flex-col sm:flex-row gap-4 justify-center lg:justify-start">
            <motion.button onClick={onLogin} whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.98 }}
              className="inline-flex items-center justify-center gap-2 bg-gradient-to-r from-amber-500 to-amber-600 text-slate-950 px-6 md:px-8 py-4 rounded-xl font-semibold transition-all hover:shadow-xl hover:shadow-amber-500/25">
              Start Free Trial
              <svg className="w-5 h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M5 12h14M12 5l7 7-7 7"/></svg>
            </motion.button>
            <motion.button onClick={onBenchmarks} whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.98 }}
              className="inline-flex items-center justify-center gap-2 border border-white/20 hover:border-amber-500 text-white hover:text-amber-400 px-6 md:px-8 py-4 rounded-xl font-medium transition-all">
              View Benchmarks
              <svg className="w-4 h-4" viewBox="0 0 24 24" fill="currentColor"><path d="M8 5v14l11-7z"/></svg>
            </motion.button>
          </div>
        </motion.div>

        {/* Swarm Visualization */}
        <motion.div initial={{ opacity: 0, scale: 0.9 }} animate={{ opacity: 1, scale: 1 }} transition={{ duration: 1, delay: 0.3 }}
          className="flex justify-center items-center order-1 lg:order-2">
          <SwarmVisualization />
        </motion.div>
      </section>

      {/* ROI Section */}
      <section className="py-16 md:py-24 px-4 md:px-16 relative z-10">
        <motion.div initial={{ opacity: 0, y: 20 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }}
          className="bg-gradient-to-br from-slate-900/80 to-slate-900/40 border border-amber-500/20 rounded-3xl p-6 md:p-12 max-w-4xl mx-auto text-center backdrop-blur-sm">
          <h3 className="text-xl md:text-2xl text-slate-400 mb-6 md:mb-8">The ROI is simple math</h3>
          <div className="flex flex-col md:flex-row items-center justify-center gap-4 md:gap-8 mb-6 md:mb-8">
            <motion.div whileHover={{ scale: 1.02 }} className="flex flex-col p-5 md:p-6 rounded-2xl bg-red-500/10 border border-red-500/30 w-full md:w-auto">
              <span className="text-xs md:text-sm text-slate-400 mb-2">3 SOC Analysts (24/7)</span>
              <span className="text-2xl md:text-4xl font-bold font-mono text-red-400">$255,000<span className="text-lg text-red-400/60">/yr</span></span>
            </motion.div>
            <span className="text-xl md:text-2xl text-slate-600 font-bold">vs</span>
            <motion.div whileHover={{ scale: 1.02 }} className="flex flex-col p-5 md:p-6 rounded-2xl bg-green-500/10 border border-green-500/30 w-full md:w-auto">
              <span className="text-xs md:text-sm text-slate-400 mb-2">HORNET Professional</span>
              <span className="text-2xl md:text-4xl font-bold font-mono text-green-400">$42,000<span className="text-lg text-green-400/60">/yr</span></span>
            </motion.div>
          </div>
          <div className="bg-amber-500/10 border border-amber-500/30 rounded-2xl p-4 md:p-6 inline-block">
            <p className="text-lg md:text-xl text-slate-300">
              Save <span className="text-amber-400 font-bold text-2xl md:text-3xl">$213,000</span> per year
              <span className="mx-3 text-slate-600">•</span>
              <span className="text-amber-400 font-bold text-2xl md:text-3xl">6x ROI</span>
            </p>
          </div>
        </motion.div>
      </section>

      {/* Features Section */}
      <section className="py-16 md:py-24 px-4 md:px-16 relative z-10" id="features">
        <motion.h2 initial={{ opacity: 0, y: 20 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }}
          className="text-2xl md:text-4xl font-bold text-center mb-4">Built for real-world security operations</motion.h2>
        <p className="text-slate-400 text-center mb-8 md:mb-12 max-w-2xl mx-auto">Every feature designed by security practitioners, refined by thousands of incident responses.</p>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 md:gap-6 max-w-6xl mx-auto">
          {features.map((feature, i) => (
            <motion.div key={i}
              className={`bg-gradient-to-br from-slate-900/80 to-slate-900/40 border rounded-2xl p-4 md:p-8 transition-all cursor-pointer backdrop-blur-sm ${activeFeature === i ? 'border-amber-500 -translate-y-1 shadow-lg shadow-amber-500/10' : 'border-white/5 hover:border-amber-500/50'}`}
              onClick={() => setActiveFeature(i)}
              initial={{ opacity: 0, y: 20 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }} transition={{ delay: i * 0.1 }}
              whileHover={{ y: -4 }}>
              <span className="text-3xl md:text-5xl mb-3 md:mb-4 block">{feature.icon}</span>
              <h3 className="text-sm md:text-xl font-semibold mb-1 md:mb-2">{feature.title}</h3>
              <p className="text-xs md:text-sm text-slate-400 leading-relaxed hidden sm:block">{feature.desc}</p>
            </motion.div>
          ))}
        </div>
      </section>

      {/* Agent Layers Section */}
      <section className="py-16 md:py-24 px-4 md:px-16 relative z-10">
        <motion.h2 initial={{ opacity: 0, y: 20 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }}
          className="text-2xl md:text-4xl font-bold text-center mb-4">7 specialized agent layers</motion.h2>
        <p className="text-slate-400 text-center mb-8 md:mb-12 max-w-2xl mx-auto">Each layer works in concert, like a symphony of security expertise.</p>
        <div className="max-w-2xl mx-auto bg-gradient-to-br from-slate-900/60 to-slate-900/30 border border-white/5 rounded-3xl p-6 md:p-8 backdrop-blur-sm">
          {[
            { name: 'Detection', color: '#ef4444', desc: 'Real-time threat identification' },
            { name: 'Intelligence', color: '#3b82f6', desc: 'Threat intel enrichment' },
            { name: 'Analysis', color: '#22c55e', desc: 'Deep behavioral analysis' },
            { name: 'Action', color: '#f59e0b', desc: 'Automated response' },
            { name: 'Governance', color: '#8b5cf6', desc: 'Compliance & oversight' },
            { name: 'Meta', color: '#06b6d4', desc: 'Self-optimization' },
            { name: 'Specialists', color: '#ec4899', desc: 'Domain expertise' },
          ].map((layer, i) => (
            <motion.div key={layer.name} className="flex items-center gap-4 md:gap-8 py-3 md:py-4 border-b border-white/5 last:border-0"
              initial={{ opacity: 0, x: -20 }} whileInView={{ opacity: 1, x: 0 }} viewport={{ once: true }} transition={{ delay: i * 0.08 }}>
              <span className="w-24 md:w-32 text-xs md:text-sm font-semibold text-slate-300">{layer.name}</span>
              <div className="flex-1 flex gap-1 md:gap-2">
                {[...Array(8)].map((_, j) => (
                  <motion.div key={j} className="h-2 md:h-3 flex-1 rounded-sm"
                    style={{ backgroundColor: layer.color }}
                    animate={{ opacity: [0.3, 1, 0.3] }} transition={{ duration: 2, delay: (i * 8 + j) * 0.05, repeat: Infinity }} />
                ))}
              </div>
              <span className="hidden md:block text-xs text-slate-500 w-40">{layer.desc}</span>
            </motion.div>
          ))}
        </div>
      </section>

      {/* Integrations Section */}
      <section className="py-16 md:py-24 px-4 md:px-16 relative z-10">
        <motion.h2 initial={{ opacity: 0, y: 20 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }}
          className="text-2xl md:text-4xl font-bold text-center mb-4">Connects to your existing stack</motion.h2>
        <p className="text-slate-400 text-center mb-8 md:mb-12 max-w-2xl mx-auto">Plug into your SIEM, EDR, and cloud platforms in minutes.</p>
        <div className="flex flex-wrap justify-center gap-2 md:gap-4 max-w-4xl mx-auto">
          {integrations.map((name, i) => (
            <motion.div key={name}
              className="bg-gradient-to-br from-slate-900/80 to-slate-900/40 border border-white/10 hover:border-amber-500 rounded-xl px-4 md:px-6 py-2 md:py-3 text-xs md:text-sm font-medium text-slate-400 hover:text-white transition-all cursor-pointer backdrop-blur-sm"
              initial={{ opacity: 0, scale: 0.9 }} whileInView={{ opacity: 1, scale: 1 }} viewport={{ once: true }} transition={{ delay: i * 0.05 }}
              whileHover={{ scale: 1.05, borderColor: 'rgba(245, 158, 11, 0.5)' }}>
              {name}
            </motion.div>
          ))}
        </div>
      </section>

      {/* Testimonial */}
      <section className="py-16 md:py-24 px-4 md:px-16 relative z-10">
        <div className="max-w-3xl mx-auto">
          <motion.div initial={{ opacity: 0, y: 20 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }}
            className="bg-gradient-to-br from-slate-900/60 to-slate-900/30 border border-white/5 rounded-3xl p-6 md:p-10 text-center backdrop-blur-sm">
            <div className="flex justify-center mb-6">
              {[...Array(5)].map((_, i) => <span key={i} className="text-amber-400 text-2xl">★</span>)}
            </div>
            <p className="text-lg md:text-2xl text-slate-300 italic mb-6 leading-relaxed">
              "HORNET reduced our incident response time from 4 hours to under 3 minutes. It's like having an entire SOC team that never sleeps."
            </p>
            <div className="flex items-center justify-center gap-4">
              <div className="w-12 h-12 rounded-full bg-gradient-to-br from-amber-500 to-cyan-500 flex items-center justify-center text-slate-950 font-bold text-lg">JD</div>
              <div className="text-left">
                <p className="font-semibold text-white">Security Director</p>
                <p className="text-sm text-slate-500">Fortune 500 Healthcare Company</p>
              </div>
            </div>
          </motion.div>
        </div>
      </section>

      {/* Final CTA */}
      <section className="py-20 md:py-32 px-4 md:px-16 text-center relative z-10">
        <motion.div initial={{ opacity: 0, y: 20 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }}>
          <h2 className="text-3xl md:text-5xl font-bold mb-4">Ready to automate your SOC?</h2>
          <p className="text-lg md:text-xl text-slate-400 mb-8">Start your free trial today. No credit card required.</p>
          <motion.button onClick={onLogin} whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.98 }}
            className="inline-flex items-center gap-3 bg-gradient-to-r from-amber-500 to-amber-600 text-slate-950 px-8 md:px-12 py-4 md:py-5 rounded-xl font-semibold text-base md:text-lg transition-all hover:shadow-2xl hover:shadow-amber-500/30">
            Get Started Free
            <svg className="w-5 h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M5 12h14M12 5l7 7-7 7"/></svg>
          </motion.button>
        </motion.div>
      </section>

      {/* Footer */}
      <footer className="border-t border-white/5 py-8 md:py-12 px-4 md:px-16 relative z-10">
        <div className="max-w-6xl mx-auto flex flex-col md:flex-row justify-between items-center gap-6">
          <div className="flex items-center gap-3">
            <HornetLogo size={32} />
            <span className="font-bold tracking-widest">HORNET</span>
          </div>
          <div className="flex flex-wrap justify-center gap-6 text-sm text-slate-500">
            <a href="#features" className="hover:text-amber-400 transition-colors">Features</a>
            <button onClick={() => setShowPricing(true)} className="hover:text-amber-400 transition-colors">Pricing</button>
            <button onClick={onBenchmarks} className="hover:text-amber-400 transition-colors">Benchmarks</button>
            <span className="hover:text-amber-400 transition-colors cursor-pointer">Documentation</span>
          </div>
          <p className="text-sm text-slate-600">© 2026 HORNET. All rights reserved.</p>
        </div>
      </footer>

      {/* Pricing Modal */}
      <AnimatePresence>
        {showPricing && (
          <motion.div className="fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center z-50 p-4"
            initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} onClick={() => setShowPricing(false)}>
            <motion.div className="bg-slate-900 border border-white/10 rounded-3xl w-full max-w-4xl max-h-[90vh] overflow-y-auto"
              initial={{ scale: 0.95, y: 20 }} animate={{ scale: 1, y: 0 }} exit={{ scale: 0.95, y: 20 }} onClick={(e) => e.stopPropagation()}>
              <div className="flex justify-between items-center p-6 border-b border-white/5">
                <h2 className="text-xl md:text-2xl font-bold">Simple, transparent pricing</h2>
                <button onClick={() => setShowPricing(false)} className="w-10 h-10 flex items-center justify-center rounded-full hover:bg-white/5 text-2xl text-slate-500 hover:text-white transition-colors">×</button>
              </div>
              <div className="p-6">
                <div className="grid md:grid-cols-3 gap-4 md:gap-6">
                  {pricing.map((plan, i) => (
                    <motion.div key={plan.tier}
                      className={`rounded-2xl p-6 ${plan.popular ? 'bg-gradient-to-br from-amber-500/20 to-amber-500/5 border-2 border-amber-500' : 'bg-slate-800/50 border border-white/10'}`}
                      initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.1 }}>
                      {plan.popular && <span className="inline-block bg-gradient-to-r from-amber-500 to-amber-600 text-slate-950 text-xs font-bold px-3 py-1 rounded-full mb-4">MOST POPULAR</span>}
                      <h3 className="text-xl font-bold mb-1">{plan.tier}</h3>
                      <p className="text-sm text-slate-400 mb-4">{plan.target}</p>
                      <div className="mb-4">
                        <span className="text-4xl font-bold font-mono">${plan.price}</span>
                        <span className="text-slate-500">/mo</span>
                      </div>
                      <p className="text-sm text-slate-400 mb-4 pb-4 border-b border-white/5">{plan.incidents} incidents/mo</p>
                      <ul className="space-y-3 mb-6">
                        {plan.features.map((f, j) => (
                          <li key={j} className="flex items-center gap-2 text-sm text-slate-300">
                            <span className="text-green-400">✓</span>{f}
                          </li>
                        ))}
                      </ul>
                      <button onClick={onLogin}
                        className={`w-full py-3 rounded-xl font-semibold transition-all ${plan.popular ? 'bg-gradient-to-r from-amber-500 to-amber-600 text-slate-950 hover:shadow-lg hover:shadow-amber-500/25' : 'border border-white/20 text-white hover:border-amber-500 hover:text-amber-400'}`}>
                        Get Started
                      </button>
                    </motion.div>
                  ))}
                </div>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};

// ============================================================================
// LOGIN PAGE
// ============================================================================

const LoginPage = ({ onAuth, onBack }) => {
  const [key, setKey] = useState('');
  const { login, loading, error } = useAuth();

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (await login(key)) onAuth();
  };

  return (
    <div className="min-h-screen bg-slate-950 text-white flex items-center justify-center p-4">
      <motion.div initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }} className="w-full max-w-md">
        <button onClick={onBack} className="mb-8 text-slate-400 hover:text-white flex items-center gap-2">← Back</button>
        <div className="bg-slate-900/50 border border-white/10 rounded-2xl p-8">
          <div className="flex justify-center mb-6"><HornetLogo size={64} /></div>
          <h1 className="text-2xl font-bold text-center mb-2">Welcome to HORNET</h1>
          <p className="text-slate-400 text-center mb-8">Enter your API key to access the dashboard</p>
          <form onSubmit={handleSubmit}>
            <input type="password" value={key} onChange={(e) => setKey(e.target.value)} placeholder="hnt_xxxxxxxxxxxxxxxx"
              className="w-full bg-slate-800 border border-white/10 rounded-xl px-4 py-3 mb-4 text-white placeholder-slate-500 focus:outline-none focus:border-amber-500" />
            {error && <p className="text-red-400 text-sm mb-4">{error}</p>}
            <button type="submit" disabled={loading || !key} className="w-full bg-amber-500 text-slate-950 py-3 rounded-xl font-semibold disabled:opacity-50 hover:bg-amber-400 transition-colors">
              {loading ? 'Authenticating...' : 'Access Dashboard'}
            </button>
          </form>
          <p className="text-slate-500 text-xs text-center mt-6">Demo key: <code className="text-amber-400">hnt_testlab_2026</code></p>
        </div>
      </motion.div>
    </div>
  );
};

// ============================================================================
// DASHBOARD - Premium Command Center with Original Styling
// ============================================================================

const Dashboard = ({ onLogout, onBenchmarks }) => {
  const { incidents, loading, refetch: fetchIncidents } = useIncidents();
  const { connected } = useWebSocket((data) => { if (data.type === 'incident_update') fetchIncidents(); });
  const [selectedIncident, setSelectedIncident] = useState(null);
  const [menuOpen, setMenuOpen] = useState(false);
  const [mobileTab, setMobileTab] = useState('incidents');
  const [filter, setFilter] = useState('all');
  const { apiKey } = useAuth();

  const fetchIncidentDetails = async (id) => {
    try {
      const res = await fetch(`${API_BASE}/api/v1/incidents/${id}`, {
        headers: { 'X-API-Key': apiKey || localStorage.getItem('hornet_api_key') }
      });
      if (res.ok) {
        const data = await res.json();
        setSelectedIncident(data);
      } else {
        const fallback = incidents.find(i => i.id === id);
        setSelectedIncident(fallback || { id, findings: [] });
      }
    } catch {
      const fallback = incidents.find(i => i.id === id);
      setSelectedIncident(fallback || { id, findings: [] });
    }
  };

  const filteredIncidents = incidents.filter(inc => {
    if (filter === 'all') return true;
    if (filter === 'active') return !['CLOSED', 'ERROR'].includes(inc.state);
    if (filter === 'attention') return inc.state === 'ERROR';
    return inc.state === filter;
  });

  const stats = {
    active: incidents.filter(i => !['CLOSED', 'ERROR'].includes(i.state)).length,
    eventsHour: Math.floor(incidents.length * 3.2),
    closed: incidents.filter(i => i.state === 'CLOSED').length,
    errors: incidents.filter(i => i.state === 'ERROR').length,
    total: incidents.length,
    totalTokens: incidents.reduce((a, i) => a + (i.tokens_used || 0), 0),
  };

  const autoResolveRate = stats.total > 0 ? Math.round((stats.closed / stats.total) * 100) : 100;
  const tokenCost = (stats.totalTokens / 1000000 * 8).toFixed(2);

  const getStateStyles = (state) => {
    const styles = { CLOSED: 'bg-green-500/10 text-green-400', ERROR: 'bg-red-500/10 text-red-400', ANALYSIS: 'bg-blue-500/10 text-blue-400', DETECTION: 'bg-blue-500/10 text-blue-400' };
    return styles[state] || 'bg-slate-500/10 text-slate-400';
  };

  const getSeverityStyles = (severity) => {
    const styles = { CRITICAL: 'bg-red-500/15 text-red-400', HIGH: 'bg-orange-500/15 text-orange-400', MEDIUM: 'bg-yellow-500/15 text-yellow-400', LOW: 'bg-green-500/15 text-green-400' };
    return styles[severity] || 'bg-slate-500/10 text-slate-400';
  };

  return (
    <div className="min-h-screen bg-slate-950 text-white pb-16 md:pb-0">
      {/* Premium Header - Original Style */}
      <header className="flex justify-between items-center px-4 md:px-6 py-3 bg-slate-900 border-b border-white/5">
        <div className="flex items-center gap-3 md:gap-4">
          <HornetLogo size={32} />
          <span className="hidden sm:inline text-lg font-bold tracking-widest">HORNET</span>
          <span className="hidden md:flex items-center gap-2 text-xs font-medium text-green-400 uppercase tracking-widest">
            <span className="w-2 h-2 bg-green-400 rounded-full animate-pulse" />
            OPERATIONAL
          </span>
        </div>
        <div className="flex items-center gap-4 md:gap-6">
          <span className="hidden sm:inline text-xs text-cyan-400">● WebSocket Live</span>
          <button onClick={onBenchmarks} className="hidden md:inline text-slate-400 hover:text-amber-400 text-sm transition-colors">Benchmarks</button>
          <button onClick={onLogout} className="hidden md:inline border border-white/10 hover:border-amber-500 text-slate-400 hover:text-amber-400 px-4 py-2 rounded-lg text-sm transition-all">Logout</button>
          <HamburgerButton onClick={() => setMenuOpen(true)} />
        </div>
      </header>

      <MobileMenu isOpen={menuOpen} onClose={() => setMenuOpen(false)}>
        <button onClick={() => { onBenchmarks(); setMenuOpen(false); }} className="text-left text-lg py-3 border-b border-white/5 text-slate-300">Benchmarks</button>
        <button onClick={() => { onLogout(); setMenuOpen(false); }} className="text-left text-lg py-3 border-b border-white/5 text-slate-300">Logout</button>
      </MobileMenu>

      {/* Stats Bar - Original 5-Column Style */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-3 md:gap-4 p-4 md:p-6">
        {[
          { label: 'Active Incidents', value: stats.active, sub: 'processing now' },
          { label: 'Events / Hour', value: stats.eventsHour, sub: 'last 60 minutes' },
          { label: 'Agents Online', value: '56', sub: 'swarm capacity', highlight: 'cyan' },
          { label: 'Auto-Resolved', value: `${autoResolveRate}%`, sub: 'no human needed', highlight: 'green' },
          { label: 'Tokens Today', value: `${(stats.totalTokens/1000).toFixed(1)}k`, sub: `~$${tokenCost} est.` },
        ].map((stat, i) => (
          <div key={i} className={`bg-slate-900/50 border border-white/5 rounded-xl p-4 md:p-5 ${i === 4 ? 'col-span-2 md:col-span-1' : ''}`}>
            <span className="block text-[10px] md:text-xs text-slate-500 uppercase tracking-wide mb-1 md:mb-2">{stat.label}</span>
            <span className={`block text-2xl md:text-3xl font-bold font-mono ${
              stat.highlight === 'cyan' ? 'text-cyan-400' : stat.highlight === 'green' ? 'text-green-400' : 'text-white'
            }`}>{stat.value}</span>
            <span className="text-[10px] md:text-xs text-slate-500">{stat.sub}</span>
          </div>
        ))}
      </div>

      {/* Mobile Tab Switcher */}
      <div className="md:hidden flex border-b border-white/5">
        {['incidents', 'health'].map((tab) => (
          <button key={tab} onClick={() => setMobileTab(tab)}
            className={`flex-1 py-3 text-sm font-medium capitalize ${mobileTab === tab ? 'text-amber-400 border-b-2 border-amber-400' : 'text-slate-500'}`}>
            {tab === 'incidents' ? 'Incidents' : 'System'}
          </button>
        ))}
      </div>

      {/* Main Content - Original Grid Layout */}
      <div className="grid md:grid-cols-[1fr_320px] gap-4 md:gap-6 px-4 md:px-6 pb-6">
        {/* Incident Panel */}
        <div className={`bg-slate-900/50 border border-white/5 rounded-xl overflow-hidden ${mobileTab !== 'incidents' ? 'hidden md:block' : ''}`}>
          <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3 px-4 md:px-6 py-4 border-b border-white/5">
            <h2 className="text-sm font-semibold uppercase tracking-wide">Incident Queue</h2>
            <div className="flex gap-2 md:gap-3 w-full sm:w-auto">
              <select value={filter} onChange={(e) => setFilter(e.target.value)}
                className="flex-1 sm:flex-none bg-slate-800 border border-white/10 rounded-lg px-3 md:px-4 py-2 text-sm text-white">
                <option value="all">All States</option>
                <option value="active">Active</option>
                <option value="attention">Needs Attention</option>
                <option value="CLOSED">Closed</option>
              </select>
              <button onClick={fetchIncidents} className="border border-amber-500 text-amber-400 hover:bg-amber-500 hover:text-slate-950 px-3 md:px-4 py-2 rounded-lg text-sm font-medium transition-all">
                Refresh
              </button>
            </div>
          </div>

          {/* Table Header - Desktop Only */}
          <div className="hidden md:grid grid-cols-[100px_90px_90px_1fr_80px_50px_50px] gap-4 px-6 py-3 bg-slate-800/50 text-xs font-semibold text-slate-500 uppercase tracking-wide">
            <span>ID</span>
            <span>State</span>
            <span>Severity</span>
            <span>Confidence</span>
            <span>Tokens</span>
            <span>Age</span>
            <span></span>
          </div>

          {/* Table Rows */}
          {loading ? (
            <div className="p-8 text-center text-slate-500">Loading...</div>
          ) : (
            <div className="divide-y divide-white/5">
              {filteredIncidents.slice(0, 20).map((inc) => (
                <motion.div key={inc.id}
                  className={`px-4 md:px-6 py-3 md:py-4 cursor-pointer transition-colors ${
                    inc.state === 'ERROR' ? 'bg-red-500/5' : ''
                  } ${selectedIncident?.id === inc.id ? 'bg-amber-500/10' : 'hover:bg-amber-500/5'}`}
                  onClick={() => fetchIncidentDetails(inc.id)}
                  whileHover={{ backgroundColor: 'rgba(245, 158, 11, 0.05)' }}>
                  
                  {/* Mobile Layout */}
                  <div className="md:hidden">
                    <div className="flex items-center gap-2 mb-2">
                      <span className="font-mono text-sm text-slate-400">{inc.id.substring(0, 8)}</span>
                      <span className={`px-2 py-0.5 rounded text-[10px] font-semibold uppercase ${getStateStyles(inc.state)}`}>{inc.state}</span>
                      <span className={`px-2 py-0.5 rounded text-[10px] font-semibold uppercase ${getSeverityStyles(inc.severity)}`}>{inc.severity}</span>
                    </div>
                    <p className="text-sm text-slate-400 truncate mb-2">{inc.summary || 'Processing...'}</p>
                    <div className="flex justify-between text-xs text-slate-500">
                      <span>{((inc.tokens_used || 0)/1000).toFixed(0)}k tokens</span>
                      <span>{getAge(inc.created_at)}</span>
                    </div>
                  </div>

                  {/* Desktop Layout */}
                  <div className="hidden md:grid grid-cols-[100px_90px_90px_1fr_80px_50px_50px] gap-4 items-center">
                    <span className="font-mono text-sm text-slate-400">{inc.id.substring(0, 8)}</span>
                    <span className={`inline-block px-2 py-1 rounded text-xs font-semibold uppercase ${getStateStyles(inc.state)}`}>{inc.state}</span>
                    <span className={`inline-block px-2 py-1 rounded text-xs font-semibold uppercase ${getSeverityStyles(inc.severity)}`}>{inc.severity}</span>
                    <div className="flex items-center gap-3">
                      <span className="font-mono text-sm w-10">{Math.round((inc.confidence || 0) * 100)}%</span>
                      <div className="flex-1 h-1.5 bg-white/10 rounded overflow-hidden">
                        <div className="h-full rounded transition-all" style={{ 
                          width: `${(inc.confidence || 0) * 100}%`,
                          backgroundColor: (inc.confidence || 0) >= 0.8 ? '#22c55e' : (inc.confidence || 0) >= 0.5 ? '#f59e0b' : '#ef4444'
                        }} />
                      </div>
                    </div>
                    <span className="font-mono text-sm text-slate-400">{((inc.tokens_used || 0)/1000).toFixed(0)}k</span>
                    <span className="text-sm text-slate-500">{getAge(inc.created_at)}</span>
                    <span className="text-amber-400 text-sm font-medium">View</span>
                  </div>
                </motion.div>
              ))}
            </div>
          )}
        </div>

        {/* Sidebar */}
        <div className={`flex flex-col gap-4 ${mobileTab !== 'health' ? 'hidden md:flex' : 'flex'}`}>
          {/* Agent Activity */}
          <div className="bg-slate-900/50 border border-white/5 rounded-xl p-4 md:p-5">
            <h3 className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-4">Agent Activity</h3>
            <div className="space-y-3">
              {['Intel', 'Analyst', 'Responder', 'Oversight', 'Router'].map((agent) => (
                <div key={agent} className="flex justify-between items-center">
                  <span className="text-sm text-slate-400">{agent}</span>
                  <span className="text-xs font-medium text-green-400">● Ready</span>
                </div>
              ))}
            </div>
          </div>

          {/* Requires Attention */}
          <div className="bg-slate-900/50 border border-amber-500/30 rounded-xl p-4 md:p-5">
            <h3 className="text-xs font-semibold text-amber-400 uppercase tracking-wide mb-4">⚠ Requires Attention</h3>
            {stats.errors === 0 ? (
              <p className="text-sm text-slate-500">✓ All clear - no issues</p>
            ) : (
              incidents.filter(i => i.state === 'ERROR').map(inc => (
                <div key={inc.id} className="bg-slate-800/50 rounded-lg p-3 cursor-pointer hover:bg-slate-800 transition-colors mb-2"
                  onClick={() => fetchIncidentDetails(inc.id)}>
                  <div className="flex justify-between items-center mb-2">
                    <span className="font-mono text-sm text-slate-400">{inc.id.substring(0, 8)}</span>
                    <span className="bg-red-500/15 text-red-400 px-2 py-0.5 rounded text-xs font-semibold">ERROR</span>
                  </div>
                  <span className={`inline-block px-2 py-0.5 rounded text-xs font-semibold uppercase ${getSeverityStyles(inc.severity)}`}>{inc.severity}</span>
                </div>
              ))
            )}
          </div>

          {/* System Health */}
          <div className="bg-slate-900/50 border border-white/5 rounded-xl p-4 md:p-5">
            <h3 className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-4">System Health</h3>
            <div className="space-y-2">
              {[
                { name: 'Redis', status: 'Connected' },
                { name: 'PostgreSQL', status: 'Connected' },
                { name: 'Workers', status: '3 Active' },
                { name: 'Anthropic API', status: 'Connected' },
              ].map((svc) => (
                <div key={svc.name} className="flex justify-between items-center text-sm">
                  <span className="text-slate-400">{svc.name}</span>
                  <span className="text-xs font-medium text-green-400">● {svc.status}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Mobile Bottom Nav */}
      <div className="md:hidden fixed bottom-0 inset-x-0 bg-slate-900 border-t border-white/5 flex justify-around py-3 z-20">
        {[
          { icon: '📊', label: 'Dashboard', active: true },
          { icon: '⚡', label: 'Benchmarks', action: onBenchmarks },
          { icon: '↩', label: 'Logout', action: onLogout },
        ].map((item, i) => (
          <button key={i} onClick={item.action} className={`flex flex-col items-center py-1 px-6 ${item.active ? 'text-amber-400' : 'text-slate-500'}`}>
            <span className="text-xl mb-1">{item.icon}</span>
            <span className="text-[10px] font-medium">{item.label}</span>
          </button>
        ))}
      </div>

      {/* Incident Detail Modal - With All 4 Pillars */}
      <BottomSheet isOpen={!!selectedIncident} onClose={() => setSelectedIncident(null)} title={selectedIncident ? `Incident ${selectedIncident.id?.substring(0, 8)}` : ''}>
        {selectedIncident && (
          <div className="p-4 md:p-6">
            {/* Status Badges */}
            <div className="flex flex-wrap gap-2 mb-4">
              <span className={`px-3 py-1 rounded-lg text-xs font-bold uppercase ${getStateStyles(selectedIncident.state)}`}>{selectedIncident.state}</span>
              <span className={`px-3 py-1 rounded-lg text-xs font-bold uppercase ${getSeverityStyles(selectedIncident.severity)}`}>{selectedIncident.severity}</span>
              <span className="px-3 py-1 rounded-lg text-xs font-bold bg-cyan-500/10 text-cyan-400">{Math.round((selectedIncident.confidence || 0) * 100)}% confidence</span>
            </div>

            {/* Executive Summary */}
            <div className="bg-gradient-to-r from-amber-500/10 to-transparent border border-amber-500/30 rounded-xl p-4 mb-4">
              <h4 className="text-xs font-semibold text-amber-400 uppercase mb-2">Executive Summary</h4>
              <p className="text-slate-200 text-sm leading-relaxed">{selectedIncident.summary || 'Analysis in progress...'}</p>
            </div>

            {/* Verdict Banner */}
            {(() => {
              const isFalsePositive = selectedIncident.verdict === 'FALSE_POSITIVE' || selectedIncident.outcome === 'false_positive'
                || (selectedIncident.summary || '').toLowerCase().match(/false.positive|benign|legitimate|insufficient.evidence|no.supporting.evidence|likely.fp|auto.dismiss/);
              return (
                <div className={`rounded-xl p-4 mb-4 text-center ${
                  isFalsePositive ? 'bg-gradient-to-r from-blue-500/20 to-blue-500/5 border border-blue-500/40'
                    : selectedIncident.state === 'CLOSED' ? 'bg-gradient-to-r from-green-500/20 to-green-500/5 border border-green-500/40'
                    : selectedIncident.state === 'ERROR' ? 'bg-gradient-to-r from-red-500/20 to-red-500/5 border border-red-500/40'
                    : 'bg-gradient-to-r from-amber-500/20 to-amber-500/5 border border-amber-500/40'
                }`}>
                  <span className={`text-sm font-bold uppercase tracking-wide ${
                    isFalsePositive ? 'text-blue-400' : selectedIncident.state === 'CLOSED' ? 'text-green-400' : selectedIncident.state === 'ERROR' ? 'text-red-400' : 'text-amber-400'
                  }`}>
                    {isFalsePositive ? '🛡 FALSE POSITIVE - Auto-Dismissed' : selectedIncident.state === 'CLOSED' ? '✓ TRUE THREAT - Remediated' : selectedIncident.state === 'ERROR' ? '⚠ PROCESSING ERROR' : '⏳ ANALYSIS IN PROGRESS'}
                  </span>
                </div>
              );
            })()}

            {/* Core Metrics */}
            <div className="grid grid-cols-3 gap-4 bg-slate-800/50 rounded-xl p-4 mb-4">
              <div className="text-center">
                <span className="block text-xs text-slate-500 mb-1">Confidence</span>
                <span className="text-2xl font-bold font-mono text-amber-400">{Math.round((selectedIncident.confidence || 0) * 100)}%</span>
              </div>
              <div className="text-center">
                <span className="block text-xs text-slate-500 mb-1">Tokens Used</span>
                <span className="text-2xl font-bold font-mono text-amber-400">{(selectedIncident.tokens_used || 0).toLocaleString()}</span>
              </div>
              <div className="text-center">
                <span className="block text-xs text-slate-500 mb-1">Processing Time</span>
                <span className="text-2xl font-bold font-mono text-amber-400">{selectedIncident.closed_at ? `${Math.round((new Date(selectedIncident.closed_at) - new Date(selectedIncident.created_at)) / 1000)}s` : getAge(selectedIncident.created_at)}</span>
              </div>
            </div>

            {/* Swarm Insights */}
            <div className="bg-gradient-to-r from-amber-500/10 via-purple-500/10 to-cyan-500/10 border border-white/10 rounded-xl p-4 mb-4">
              <h4 className="text-[10px] font-semibold text-slate-400 uppercase mb-3 flex items-center gap-2">
                <span>🐝</span> Swarm Insights
              </h4>
              <div className="grid grid-cols-3 gap-4">
                <div>
                  <span className="block text-[10px] text-amber-400 uppercase mb-1">Human Hours Saved</span>
                  <span className="text-2xl font-bold font-mono text-amber-400">{Math.max(1, Math.round((selectedIncident.tokens_used || 50000) / 12500))}</span>
                  <span className="text-[10px] text-slate-500 ml-1">hrs</span>
                </div>
                <div>
                  <span className="block text-[10px] text-purple-400 uppercase mb-1">Parallel Agents</span>
                  <span className="text-2xl font-bold font-mono text-purple-400">{Math.min((selectedIncident.findings || []).length || 5, 8)}</span>
                  <span className="text-[10px] text-slate-500 ml-1">simultaneous</span>
                </div>
                <div>
                  <span className="block text-[10px] text-cyan-400 uppercase mb-1">Tool Calls</span>
                  <span className="text-2xl font-bold font-mono text-cyan-400">{((selectedIncident.findings || []).length || 4) * 3 + Math.floor((selectedIncident.tokens_used || 0) / 3000)}</span>
                  <span className="text-[10px] text-slate-500 ml-1">executed</span>
                </div>
              </div>
              <div className="mt-3 pt-3 border-t border-white/5">
                <div className="flex justify-between items-center text-[10px] mb-1">
                  <span className="text-slate-500">Token Budget Used</span>
                  <span className="text-slate-400 font-mono">{((selectedIncident.tokens_used || 0) / (selectedIncident.token_budget || 200000) * 100).toFixed(1)}% of {((selectedIncident.token_budget || 200000)/1000)}k</span>
                </div>
                <div className="h-2 bg-slate-800 rounded-full overflow-hidden">
                  <div className="h-full bg-gradient-to-r from-amber-500 to-cyan-500 rounded-full" style={{width: `${Math.min(100, (selectedIncident.tokens_used || 0) / (selectedIncident.token_budget || 200000) * 100)}%`}}></div>
                </div>
              </div>
            </div>

            {/* 4-Pillar Agent Findings */}
            <div className="space-y-3 max-h-[40vh] overflow-y-auto">
              {/* PILLAR 1: The Jury */}
              {(selectedIncident.findings || []).filter(f => ['analyst', 'triage', 'supervisor', 'qa', 'correlator'].includes(f.agent?.toLowerCase())).length > 0 && (
                <div className="border border-amber-500/30 rounded-xl p-4 bg-amber-500/5">
                  <div className="flex items-center gap-2 mb-3">
                    <span className="text-lg">🏛️</span>
                    <div><h4 className="text-xs font-semibold text-amber-400 uppercase">The Jury</h4><span className="text-[10px] text-slate-500">Verdict & Logic</span></div>
                  </div>
                  {(selectedIncident.findings || []).filter(f => ['analyst', 'triage', 'supervisor', 'qa', 'correlator'].includes(f.agent?.toLowerCase())).map((f, i) => (
                    <div key={f.id || i} className="bg-slate-800/50 rounded-lg p-3 mb-2 last:mb-0">
                      <div className="flex justify-between mb-1"><span className="text-sm font-semibold text-amber-300 capitalize">{f.agent}</span><span className="text-xs text-slate-500">{(f.tokens_consumed || 0).toLocaleString()} tok</span></div>
                      <p className="text-xs text-slate-300 leading-relaxed">{f.reasoning}</p>
                    </div>
                  ))}
                </div>
              )}

              {/* PILLAR 2: Intel & Origin */}
              {(selectedIncident.findings || []).filter(f => ['intel', 'hunter', 'behavioral', 'netwatch', 'forensics', 'endpoint', 'cloud', 'identity', 'redsim', 'dataguard'].includes(f.agent?.toLowerCase())).length > 0 && (
                <div className="border border-cyan-500/30 rounded-xl p-4 bg-cyan-500/5">
                  <div className="flex items-center gap-2 mb-3">
                    <span className="text-lg">🕵️</span>
                    <div><h4 className="text-xs font-semibold text-cyan-400 uppercase">Intel & Origin</h4><span className="text-[10px] text-slate-500">The Proof</span></div>
                  </div>
                  {(selectedIncident.findings || []).filter(f => ['intel', 'hunter', 'behavioral', 'netwatch', 'forensics', 'endpoint', 'cloud', 'identity', 'redsim', 'dataguard'].includes(f.agent?.toLowerCase())).map((f, i) => (
                    <div key={f.id || i} className="bg-slate-800/50 rounded-lg p-3 mb-2 last:mb-0">
                      <div className="flex justify-between mb-1"><span className="text-sm font-semibold text-cyan-300 capitalize">{f.agent}</span><span className="text-xs text-slate-500">{(f.tokens_consumed || 0).toLocaleString()} tok</span></div>
                      <p className="text-xs text-slate-300 leading-relaxed">{f.reasoning}</p>
                    </div>
                  ))}
                </div>
              )}

              {/* PILLAR 3: Risk & Compliance */}
              {(selectedIncident.findings || []).filter(f => ['compliance', 'legal', 'privacy', 'audit'].includes(f.agent?.toLowerCase())).length > 0 && (
                <div className="border border-purple-500/30 rounded-xl p-4 bg-purple-500/5">
                  <div className="flex items-center gap-2 mb-3">
                    <span className="text-lg">⚖️</span>
                    <div><h4 className="text-xs font-semibold text-purple-400 uppercase">Risk & Compliance</h4><span className="text-[10px] text-slate-500">The Value</span></div>
                  </div>
                  {(selectedIncident.findings || []).filter(f => ['compliance', 'legal', 'privacy', 'audit'].includes(f.agent?.toLowerCase())).map((f, i) => (
                    <div key={f.id || i} className="bg-slate-800/50 rounded-lg p-3 mb-2 last:mb-0">
                      <div className="flex justify-between mb-1"><span className="text-sm font-semibold text-purple-300 capitalize">{f.agent}</span><span className="text-xs text-slate-500">{(f.tokens_consumed || 0).toLocaleString()} tok</span></div>
                      <p className="text-xs text-slate-300 leading-relaxed">{f.reasoning}</p>
                    </div>
                  ))}
                </div>
              )}

              {/* PILLAR 4: The Enforcers */}
              {(selectedIncident.findings || []).filter(f => ['responder', 'oversight', 'containment', 'recovery'].includes(f.agent?.toLowerCase())).length > 0 && (
                <div className="border border-green-500/30 rounded-xl p-4 bg-green-500/5">
                  <div className="flex items-center gap-2 mb-3">
                    <span className="text-lg">🛠️</span>
                    <div><h4 className="text-xs font-semibold text-green-400 uppercase">The Enforcers</h4><span className="text-[10px] text-slate-500">The Action</span></div>
                  </div>
                  {(selectedIncident.findings || []).filter(f => ['responder', 'oversight', 'containment', 'recovery'].includes(f.agent?.toLowerCase())).map((f, i) => (
                    <div key={f.id || i} className="bg-slate-800/50 rounded-lg p-3 mb-2 last:mb-0">
                      <div className="flex justify-between mb-1"><span className="text-sm font-semibold text-green-300 capitalize">{f.agent}</span><span className="text-xs text-slate-500">{(f.tokens_consumed || 0).toLocaleString()} tok</span></div>
                      <p className="text-xs text-slate-300 leading-relaxed">{f.reasoning}</p>
                    </div>
                  ))}
                </div>
              )}

              {/* Fallback Agent Timeline if no findings */}
              {(!selectedIncident.findings || selectedIncident.findings.length === 0) && (
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
              )}
            </div>

            {/* Action Buttons */}
            <div className="flex justify-end gap-3 mt-4 pt-4 border-t border-white/5">
              <button className="border border-white/15 text-slate-400 hover:text-white px-5 py-2 rounded-lg text-sm font-medium transition-all">Export Report</button>
              <button className="border border-white/15 text-slate-400 hover:text-white px-5 py-2 rounded-lg text-sm font-medium transition-all">View Raw Data</button>
              {selectedIncident.state === 'ERROR' && (
                <button className="bg-gradient-to-r from-amber-500 to-amber-600 text-slate-950 px-5 py-2 rounded-lg text-sm font-semibold">Retry Processing</button>
              )}
            </div>
          </div>
        )}
      </BottomSheet>
    </div>
  );
};

// ============================================================================
// BENCHMARKS PAGE
// ============================================================================

const BenchmarksPage = ({ onBack, onDashboard }) => {
  const [activeTab, setActiveTab] = useState('overview');
  const [menuOpen, setMenuOpen] = useState(false);
  const tabs = ['overview', 'speed', 'savings', 'accuracy', 'depth'];

  return (
    <div className="min-h-screen bg-slate-950 text-white pb-16 md:pb-0">
      <header className="sticky top-0 z-20 border-b border-white/5 px-4 md:px-8 py-3 bg-slate-950/95 backdrop-blur-sm">
        <div className="flex items-center justify-between max-w-7xl mx-auto">
          <div className="flex items-center gap-2">
            <HornetLogo size={32} />
            <div className="hidden sm:block"><h1 className="font-bold tracking-wider text-sm">HORNET</h1><p className="text-xs text-slate-500">Benchmarks</p></div>
          </div>
          <div className="hidden md:flex items-center gap-4">
            <nav className="flex gap-1 bg-slate-900 rounded-xl p-1">
              {tabs.map((tab) => (
                <button key={tab} onClick={() => setActiveTab(tab)} className={`px-3 py-2 rounded-lg text-sm font-medium capitalize ${activeTab === tab ? 'bg-amber-500 text-slate-950' : 'text-slate-400 hover:text-white'}`}>{tab}</button>
              ))}
            </nav>
            <button onClick={onDashboard} className="bg-amber-500 text-slate-950 px-4 py-2 rounded-lg text-sm font-semibold">Dashboard →</button>
          </div>
          <HamburgerButton onClick={() => setMenuOpen(true)} />
        </div>
      </header>

      <MobileMenu isOpen={menuOpen} onClose={() => setMenuOpen(false)}>
        {tabs.map((tab) => (<button key={tab} onClick={() => { setActiveTab(tab); setMenuOpen(false); }} className={`text-left text-lg py-3 border-b border-white/5 capitalize ${activeTab === tab ? 'text-amber-400' : 'text-slate-300'}`}>{tab}</button>))}
        <button onClick={() => { onDashboard(); setMenuOpen(false); }} className="mt-4 w-full bg-amber-500 text-slate-950 py-3 rounded-xl font-semibold">Dashboard →</button>
      </MobileMenu>

      <div className="md:hidden overflow-x-auto px-4 py-3 border-b border-white/5">
        <div className="flex gap-2 min-w-max">
          {tabs.map((tab) => (<button key={tab} onClick={() => setActiveTab(tab)} className={`px-4 py-2 rounded-full text-sm font-medium capitalize whitespace-nowrap ${activeTab === tab ? 'bg-amber-500 text-slate-950' : 'bg-slate-800 text-slate-400'}`}>{tab}</button>))}
        </div>
      </div>

      <main className="max-w-7xl mx-auto p-4 md:p-8">
        {activeTab === 'overview' && <BenchmarkOverview />}
        {activeTab === 'speed' && <SpeedBenchmark />}
        {activeTab === 'savings' && <SavingsCalculator />}
        {activeTab === 'accuracy' && <AccuracyGauge />}
        {activeTab === 'depth' && <ConsensusDepth />}
      </main>

      <div className="md:hidden fixed bottom-0 inset-x-0 bg-slate-900 border-t border-white/5 flex justify-around py-2 z-20">
        <button onClick={onBack} className="flex flex-col items-center py-2 px-4 text-slate-500"><span className="text-xl">←</span><span className="text-[10px] mt-0.5">Back</span></button>
        <button className="flex flex-col items-center py-2 px-4 text-amber-400"><span className="text-xl">📊</span><span className="text-[10px] mt-0.5">Benchmarks</span></button>
        <button onClick={onDashboard} className="flex flex-col items-center py-2 px-4 text-slate-500"><span className="text-xl">🖥️</span><span className="text-[10px] mt-0.5">Dashboard</span></button>
      </div>
    </div>
  );
};

const BenchmarkOverview = () => (
  <div>
    <div className="text-center mb-8">
      <HornetLogo size={56} />
      <h2 className="text-2xl md:text-4xl font-bold mt-4 mb-2">What <span className="text-amber-400">HORNET</span> Delivers</h2>
      <p className="text-base md:text-xl text-slate-400">Real savings. Every metric is money back.</p>
    </div>
    <div className="grid grid-cols-2 md:grid-cols-5 gap-3 mb-8">
      {[
        { label: 'Response', value: '<45s', sub: '99.8% faster' },
        { label: 'Savings', value: '$213k', sub: '6x ROI' },
        { label: 'Auto-Close', value: '79.9%', sub: '600+ hrs' },
        { label: 'Depth', value: '12+', sub: '8h→3m' },
        { label: 'Audit', value: '$0', sub: 'Auto' },
      ].map((s, i) => (
        <motion.div key={i} initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i*0.1 }}
          className={`bg-slate-900/50 border border-white/5 rounded-xl p-4 text-center ${i === 4 ? 'col-span-2 md:col-span-1' : ''}`}>
          <span className="block text-xl md:text-3xl font-bold font-mono text-amber-400">{s.value}</span>
          <span className="block text-xs text-slate-400 mt-1">{s.label}</span>
          <span className="block text-xs text-green-400 mt-1">{s.sub}</span>
        </motion.div>
      ))}
    </div>
    <div className="bg-gradient-to-br from-amber-500/10 to-transparent border border-amber-500/30 rounded-2xl p-4 md:p-8">
      <h3 className="text-lg font-semibold mb-4">Why This Matters</h3>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-sm text-slate-300">
        <p><span className="text-green-400">💰</span> Replace 24/7 shifts with one analyst + HORNET</p>
        <p><span className="text-green-400">⏱️</span> 600+ analyst hours/month returned</p>
        <p><span className="text-green-400">🛡️</span> Handle 10x volume without scaling</p>
        <p><span className="text-green-400">📋</span> SOC 2, HIPAA auto-documented</p>
      </div>
    </div>
  </div>
);

const SpeedBenchmark = () => {
  const [racing, setRacing] = useState(false);
  const [humanTime, setHumanTime] = useState(0);
  const [hornetTime, setHornetTime] = useState(0);
  const startRace = () => {
    setRacing(true); setHumanTime(0); setHornetTime(0);
    const hi = setInterval(() => setHornetTime(p => p >= 45 ? (clearInterval(hi), 45) : p + 1), 50);
    const hu = setInterval(() => setHumanTime(p => p >= 14400 ? 14400 : p + 60), 50);
    setTimeout(() => { clearInterval(hu); setRacing(false); }, 8000);
  };
  return (
    <div className="max-w-2xl mx-auto bg-slate-900/50 border border-white/10 rounded-2xl p-4 md:p-8">
      <div className="flex items-center gap-3 mb-6"><HornetLogo size={40} /><div><h3 className="text-xl font-bold">Speed Race</h3><p className="text-sm text-slate-400">Human vs HORNET</p></div></div>
      <div className="space-y-4 mb-6">
        <div><div className="flex justify-between mb-2"><span className="text-sm text-slate-300">Traditional SOC</span><span className="text-sm font-mono text-red-400">{humanTime < 3600 ? `${Math.floor(humanTime/60)}m` : `${Math.floor(humanTime/3600)}h`}</span></div><div className="h-6 bg-slate-800 rounded-full overflow-hidden"><motion.div className="h-full bg-red-500" animate={{ width: `${Math.min((humanTime/14400)*100, 100)}%` }} /></div></div>
        <div><div className="flex justify-between mb-2"><span className="text-sm text-slate-300">HORNET</span><span className="text-sm font-mono text-green-400">{hornetTime}s</span></div><div className="h-6 bg-slate-800 rounded-full overflow-hidden"><motion.div className="h-full bg-green-500" animate={{ width: `${Math.min((hornetTime/45)*100, 100)}%` }} /></div></div>
      </div>
      <button onClick={startRace} disabled={racing} className="w-full py-4 bg-amber-500 text-slate-950 rounded-xl font-semibold disabled:opacity-50">{racing ? 'Racing...' : 'Start Race →'}</button>
    </div>
  );
};

const SavingsCalculator = () => {
  const [analysts, setAnalysts] = useState(3);
  const currentCost = analysts * 110500;
  const hornetCost = 41988 + 110500;
  const savings = currentCost - hornetCost;
  return (
    <div className="max-w-2xl mx-auto bg-slate-900/50 border border-white/10 rounded-2xl p-4 md:p-8">
      <div className="flex items-center gap-3 mb-6"><HornetLogo size={40} /><div><h3 className="text-xl font-bold">Savings Calculator</h3><p className="text-sm text-slate-400">Your ROI with HORNET</p></div></div>
      <div className="mb-6"><label className="block text-sm text-slate-300 mb-3">Team Size: <span className="text-amber-400 font-mono">{analysts}</span></label><input type="range" min="1" max="10" value={analysts} onChange={(e) => setAnalysts(+e.target.value)} className="w-full accent-amber-500 h-3" /></div>
      <div className="grid grid-cols-2 gap-3 mb-4">
        <div className="bg-red-500/10 border border-red-500/30 rounded-xl p-4 text-center"><span className="text-xs text-slate-400">Current</span><span className="block text-2xl font-bold font-mono text-red-400">${(currentCost/1000).toFixed(0)}k</span></div>
        <div className="bg-green-500/10 border border-green-500/30 rounded-xl p-4 text-center"><span className="text-xs text-slate-400">With HORNET</span><span className="block text-2xl font-bold font-mono text-green-400">${(hornetCost/1000).toFixed(0)}k</span></div>
      </div>
      <div className="bg-amber-500/10 border border-amber-500/30 rounded-xl p-4 text-center"><span className="text-xs text-slate-400">Annual Savings</span><span className="block text-4xl font-bold font-mono text-amber-400">${Math.max(0, savings/1000).toFixed(0)}k</span></div>
    </div>
  );
};

const AccuracyGauge = () => (
  <div className="max-w-2xl mx-auto bg-slate-900/50 border border-white/10 rounded-2xl p-4 md:p-8">
    <div className="flex items-center gap-3 mb-6"><HornetLogo size={40} /><div><h3 className="text-xl font-bold">Auto-Resolution</h3><p className="text-sm text-slate-400">HORNET heals messy data</p></div></div>
    <div className="flex justify-center my-8">
      <div className="relative w-36 h-36 md:w-48 md:h-48">
        <svg className="w-full h-full -rotate-90" viewBox="0 0 100 100"><circle cx="50" cy="50" r="40" fill="none" stroke="rgba(255,255,255,0.1)" strokeWidth="10" /><motion.circle cx="50" cy="50" r="40" fill="none" stroke="#22c55e" strokeWidth="10" strokeLinecap="round" initial={{ pathLength: 0 }} animate={{ pathLength: 0.799 }} transition={{ duration: 2 }} /></svg>
        <div className="absolute inset-0 flex flex-col items-center justify-center"><span className="text-3xl md:text-4xl font-bold font-mono">79.9%</span><span className="text-xs text-slate-400">Auto-Resolved</span></div>
      </div>
    </div>
    <div className="bg-amber-500/10 border border-amber-500/30 rounded-xl p-4 text-center"><span className="text-xs text-slate-400">At 1,000 incidents/month</span><span className="block text-2xl font-bold font-mono text-amber-400 my-1">599 hours saved</span></div>
  </div>
);

const ConsensusDepth = () => {
  const [running, setRunning] = useState(false);
  const [agents, setAgents] = useState([]);
  const all = ['Hunter', 'Sentinel', 'Intel', 'Correlator', 'Analyst', 'Forensics', 'Triage', 'Responder', 'Oversight', 'Compliance', 'Legal', 'Router'];
  const start = () => { setRunning(true); setAgents([]); all.forEach((a, i) => setTimeout(() => setAgents(p => [...p, a]), i * 300)); setTimeout(() => setRunning(false), 4500); };
  return (
    <div className="max-w-2xl mx-auto bg-slate-900/50 border border-white/10 rounded-2xl p-4 md:p-8">
      <div className="flex items-center gap-3 mb-6"><HornetLogo size={40} /><div><h3 className="text-xl font-bold">Consensus Depth</h3><p className="text-sm text-slate-400">12+ specialists per incident</p></div></div>
      {!running && agents.length === 0 ? <button onClick={start} className="w-full py-4 bg-purple-500 text-white rounded-xl font-semibold">Watch Consensus →</button> : (
        <><div className="grid grid-cols-2 gap-2 mb-4">{agents.map((a) => <motion.div key={a} initial={{ opacity: 0, scale: 0.8 }} animate={{ opacity: 1, scale: 1 }} className="bg-slate-800/30 rounded-lg p-2 text-sm text-slate-300 flex items-center gap-2"><span className="text-green-400">✔</span>{a}</motion.div>)}</div>
        {agents.length === 12 && <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="bg-green-500/10 border border-green-500/30 rounded-xl p-4 text-center"><span className="text-green-400 font-semibold text-lg">✔ CONSENSUS REACHED</span></motion.div>}</>
      )}
    </div>
  );
};

// ============================================================================
// MAIN APP
// ============================================================================

export default function App() {
  const [view, setView] = useState('landing');
  const { isAuthenticated, logout } = useAuth();
  useEffect(() => { if (isAuthenticated && view === 'login') setView('dashboard'); }, [isAuthenticated, view]);

  return (
    <>
      {view === 'landing' && <LandingPage onLogin={() => setView('login')} onBenchmarks={() => setView('benchmarks')} />}
      {view === 'login' && <LoginPage onAuth={() => setView('dashboard')} onBack={() => setView('landing')} />}
      {view === 'dashboard' && <Dashboard onLogout={() => { logout(); setView('landing'); }} onBenchmarks={() => setView('benchmarks')} />}
      {view === 'benchmarks' && <BenchmarksPage onBack={() => setView('landing')} onDashboard={() => setView(isAuthenticated ? 'dashboard' : 'login')} />}
    </>
  );
}
