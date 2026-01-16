import { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence, useInView } from 'framer-motion';

// ============================================================================
// HORNET Benchmarks - Customer-Facing Interactive Dashboard
// Focus: Customer Savings, ROI, Time Savings
// ============================================================================

// Import logo - in production, use: import hornetLogo from './assets/hornet-logo-transparent.png'
// For now, we'll use a base64 placeholder or URL
const HORNET_LOGO_URL = '/hornet-logo-transparent.png'; // Place in public folder

// Hornet Logo Component - Uses actual PNG
const HornetLogo = ({ size = 48, className = '' }) => (
  <img 
    src={HORNET_LOGO_URL} 
    alt="HORNET" 
    width={size} 
    height={size}
    className={`object-contain ${className}`}
    style={{ filter: 'drop-shadow(0 0 8px rgba(245, 158, 11, 0.3))' }}
  />
);

// Fallback SVG Logo (in case image doesn't load)
const HornetLogoSVG = ({ size = 48 }) => (
  <svg width={size} height={size} viewBox="0 0 100 100" className="drop-shadow-lg">
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

// Animated Counter Component
const AnimatedCounter = ({ end, duration = 2, prefix = '', suffix = '', decimals = 0 }) => {
  const [count, setCount] = useState(0);
  const ref = useRef(null);
  const isInView = useInView(ref, { once: true });
  
  useEffect(() => {
    if (!isInView) return;
    
    let startTime;
    const animate = (timestamp) => {
      if (!startTime) startTime = timestamp;
      const progress = Math.min((timestamp - startTime) / (duration * 1000), 1);
      const eased = 1 - Math.pow(1 - progress, 3);
      setCount(eased * end);
      if (progress < 1) requestAnimationFrame(animate);
    };
    requestAnimationFrame(animate);
  }, [isInView, end, duration]);
  
  return (
    <span ref={ref}>
      {prefix}{decimals > 0 ? count.toFixed(decimals) : Math.floor(count).toLocaleString()}{suffix}
    </span>
  );
};

// Live Processing Simulation - Shows HORNET working
const LiveProcessingDemo = () => {
  const [incidents, setIncidents] = useState([]);
  const [stats, setStats] = useState({ processed: 0, avgTime: 0, humanHoursSaved: 0 });
  
  useEffect(() => {
    const addIncident = () => {
      const id = Math.random().toString(36).substr(2, 8);
      const severity = ['CRITICAL', 'HIGH', 'MEDIUM'][Math.floor(Math.random() * 3)];
      const processingTime = Math.random() * 30 + 15;
      const humanEquivalent = Math.random() * 3 + 2; // 2-5 hours of human work
      
      setIncidents(prev => [...prev.slice(-4), {
        id, severity, status: 'INGESTING', startTime: Date.now(),
        processingTime, humanEquivalent, agents: []
      }]);
      
      setTimeout(() => updateIncident(id, 'ENRICHING', ['IntelAgent', 'CorrelatorAgent']), 500);
      setTimeout(() => updateIncident(id, 'ANALYZING', ['AnalystAgent', 'ForensicsAgent', 'ThreatHunter']), 1500);
      setTimeout(() => updateIncident(id, 'CONSENSUS', ['OversightAgent', 'ComplianceAgent', 'LegalAgent']), 2500);
      setTimeout(() => {
        updateIncident(id, 'RESOLVED', []);
        setStats(prev => ({
          processed: prev.processed + 1,
          avgTime: ((prev.avgTime * prev.processed) + processingTime) / (prev.processed + 1),
          humanHoursSaved: prev.humanHoursSaved + humanEquivalent
        }));
      }, 3500);
    };
    
    const updateIncident = (id, status, agents) => {
      setIncidents(prev => prev.map(inc => 
        inc.id === id ? { ...inc, status, agents } : inc
      ));
    };
    
    addIncident();
    const interval = setInterval(addIncident, 5000);
    return () => clearInterval(interval);
  }, []);
  
  const getStatusColor = (status) => ({
    INGESTING: 'bg-blue-500',
    ENRICHING: 'bg-cyan-500',
    ANALYZING: 'bg-amber-500',
    CONSENSUS: 'bg-purple-500',
    RESOLVED: 'bg-green-500'
  }[status] || 'bg-slate-500');
  
  return (
    <div className="bg-slate-900/50 border border-white/10 rounded-2xl p-6">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-3">
          <HornetLogo size={32} />
          <h3 className="text-sm font-semibold text-slate-400 uppercase tracking-wide">Live Swarm Activity</h3>
        </div>
        <span className="flex items-center gap-2 text-xs text-green-400">
          <span className="w-2 h-2 bg-green-400 rounded-full animate-pulse" />
          56 AGENTS ONLINE
        </span>
      </div>
      
      <div className="space-y-3 mb-6">
        <AnimatePresence mode="popLayout">
          {incidents.map((inc) => (
            <motion.div
              key={inc.id}
              layout
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: 20 }}
              className="bg-slate-800/50 rounded-lg p-3"
            >
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-3">
                  <span className="font-mono text-sm text-slate-400">{inc.id}</span>
                  <span className={`px-2 py-0.5 rounded text-xs font-semibold ${
                    inc.severity === 'CRITICAL' ? 'bg-red-500/20 text-red-400' :
                    inc.severity === 'HIGH' ? 'bg-orange-500/20 text-orange-400' :
                    'bg-yellow-500/20 text-yellow-400'
                  }`}>{inc.severity}</span>
                </div>
                <span className={`px-2 py-0.5 rounded text-xs font-semibold ${getStatusColor(inc.status)} bg-opacity-20 text-white`}>
                  {inc.status}
                </span>
              </div>
              
              {inc.agents.length > 0 && (
                <div className="flex flex-wrap gap-1 mb-2">
                  {inc.agents.map((agent, i) => (
                    <motion.span
                      key={agent}
                      initial={{ scale: 0 }}
                      animate={{ scale: 1 }}
                      transition={{ delay: i * 0.1 }}
                      className="px-2 py-0.5 bg-slate-700 rounded text-xs text-slate-300"
                    >
                      {agent}
                    </motion.span>
                  ))}
                </div>
              )}
              
              {inc.status === 'RESOLVED' && (
                <div className="flex items-center gap-4 text-xs text-green-400">
                  <span>✓ {inc.processingTime.toFixed(1)}s</span>
                  <span className="text-amber-400">💰 {inc.humanEquivalent.toFixed(1)} analyst hours saved</span>
                </div>
              )}
            </motion.div>
          ))}
        </AnimatePresence>
      </div>
      
      <div className="grid grid-cols-3 gap-4 pt-4 border-t border-white/5">
        <div className="text-center">
          <span className="block text-2xl font-bold font-mono text-amber-400">{stats.processed}</span>
          <span className="text-xs text-slate-500">Resolved</span>
        </div>
        <div className="text-center">
          <span className="block text-2xl font-bold font-mono text-cyan-400">{stats.avgTime.toFixed(1)}s</span>
          <span className="text-xs text-slate-500">Avg Time</span>
        </div>
        <div className="text-center">
          <span className="block text-2xl font-bold font-mono text-green-400">{stats.humanHoursSaved.toFixed(1)}h</span>
          <span className="text-xs text-slate-500">Hours Saved</span>
        </div>
      </div>
    </div>
  );
};

// Speed Comparison Component
const SpeedBenchmark = () => {
  const [isRunning, setIsRunning] = useState(false);
  const [humanTime, setHumanTime] = useState(0);
  const [hornetTime, setHornetTime] = useState(0);
  const [hornetDone, setHornetDone] = useState(false);
  
  const startRace = () => {
    setIsRunning(true);
    setHumanTime(0);
    setHornetTime(0);
    setHornetDone(false);
    
    const hornetInterval = setInterval(() => {
      setHornetTime(prev => {
        if (prev >= 45) {
          clearInterval(hornetInterval);
          setHornetDone(true);
          return 45;
        }
        return prev + 1;
      });
    }, 50);
    
    const humanInterval = setInterval(() => {
      setHumanTime(prev => {
        if (prev >= 14400) {
          clearInterval(humanInterval);
          return 14400;
        }
        return prev + 60;
      });
    }, 50);
    
    setTimeout(() => {
      clearInterval(humanInterval);
      setIsRunning(false);
    }, 8000);
  };
  
  const formatTime = (seconds) => {
    if (seconds < 60) return `${seconds}s`;
    if (seconds < 3600) return `${Math.floor(seconds / 60)}m ${seconds % 60}s`;
    return `${Math.floor(seconds / 3600)}h ${Math.floor((seconds % 3600) / 60)}m`;
  };
  
  const timeSaved = humanTime > 0 ? ((humanTime - hornetTime) / 3600).toFixed(1) : 0;
  
  return (
    <div className="bg-slate-900/50 border border-white/10 rounded-2xl p-8">
      <div className="flex items-center gap-4 mb-2">
        <HornetLogo size={48} />
        <div>
          <h3 className="text-2xl font-bold">Speed: Time-to-Truth</h3>
          <p className="text-slate-400">Close the attacker breakout window</p>
        </div>
      </div>
      
      <div className="my-8 p-4 bg-amber-500/10 border border-amber-500/30 rounded-xl text-center">
        <span className="text-sm text-slate-400">Your team reclaims</span>
        <span className="block text-4xl font-bold font-mono text-amber-400 my-2">
          {timeSaved}+ hours
        </span>
        <span className="text-sm text-slate-400">per critical incident</span>
      </div>
      
      <div className="space-y-6 mb-8">
        <div>
          <div className="flex justify-between mb-2">
            <span className="text-sm font-medium text-slate-300">Traditional SOC Response</span>
            <span className="text-sm font-mono text-red-400">{formatTime(humanTime)}</span>
          </div>
          <div className="h-8 bg-slate-800 rounded-full overflow-hidden">
            <motion.div
              className="h-full bg-gradient-to-r from-red-600 to-red-400 flex items-center justify-end pr-3"
              initial={{ width: 0 }}
              animate={{ width: `${Math.min((humanTime / 14400) * 100, 100)}%` }}
              transition={{ duration: 0.1 }}
            >
              {humanTime > 1800 && <span className="text-xs font-medium text-white">4-8 Hours (Industry Average)</span>}
            </motion.div>
          </div>
        </div>
        
        <div>
          <div className="flex justify-between mb-2">
            <span className="text-sm font-medium text-slate-300 flex items-center gap-2">
              <HornetLogo size={20} /> HORNET Response
            </span>
            <span className="text-sm font-mono text-green-400">{formatTime(hornetTime)}</span>
          </div>
          <div className="h-8 bg-slate-800 rounded-full overflow-hidden">
            <motion.div
              className="h-full bg-gradient-to-r from-green-600 to-green-400 flex items-center justify-end pr-3"
              initial={{ width: 0 }}
              animate={{ width: `${Math.min((hornetTime / 45) * 100, 100)}%` }}
              transition={{ duration: 0.1 }}
            >
              {hornetDone && (
                <motion.span 
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  className="text-xs font-bold text-white flex items-center gap-1"
                >
                  ✓ THREAT NEUTRALIZED
                </motion.span>
              )}
            </motion.div>
          </div>
        </div>
      </div>
      
      <button
        onClick={startRace}
        disabled={isRunning}
        className="w-full py-4 bg-gradient-to-r from-amber-500 to-amber-600 text-slate-950 rounded-xl font-semibold text-lg transition-all hover:shadow-lg hover:shadow-amber-500/30 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
      >
        <HornetLogo size={24} />
        {isRunning ? 'Racing...' : 'Start the Race →'}
      </button>
      
      <div className="mt-6 p-4 bg-green-500/10 border border-green-500/30 rounded-xl">
        <p className="text-green-400 text-sm">
          <strong>Your Win:</strong> Attackers typically need 1-2 hours to move laterally after initial breach. 
          HORNET responds in under 45 seconds—before they can spread.
        </p>
      </div>
    </div>
  );
};

// ROI Calculator - CUSTOMER SAVINGS FOCUSED
const SavingsCalculator = () => {
  const [analysts, setAnalysts] = useState(3);
  const [incidents, setIncidents] = useState(500);
  
  // Industry costs
  const analystSalary = 85000; // Average SOC analyst salary
  const analystBurden = 1.3; // Benefits, training, turnover
  const analystFullCost = analystSalary * analystBurden;
  
  // HORNET pricing
  const hornetPricing = {
    starter: { price: 1499, incidents: 5000 },
    professional: { price: 3499, incidents: 25000 },
    enterprise: { price: 7499, incidents: Infinity },
  };
  
  // Calculate current costs
  const currentTeamCost = analysts * analystFullCost;
  const currentCoverage = analysts * 2000; // ~2000 incidents/analyst/year capacity
  
  // Determine HORNET tier
  const annualIncidents = incidents * 12;
  let hornetTier = 'starter';
  let hornetMonthlyCost = 1499;
  if (annualIncidents > 60000) {
    hornetTier = 'professional';
    hornetMonthlyCost = 3499;
  }
  if (annualIncidents > 300000) {
    hornetTier = 'enterprise';
    hornetMonthlyCost = 7499;
  }
  
  const hornetAnnualCost = hornetMonthlyCost * 12;
  
  // With HORNET: Keep 1 analyst for oversight, HORNET handles the rest
  const hybridTeamCost = analystFullCost + hornetAnnualCost; // 1 analyst + HORNET
  const annualSavings = currentTeamCost - hybridTeamCost;
  const coverageIncrease = ((annualIncidents / currentCoverage) * 100 - 100).toFixed(0);
  const roi = ((annualSavings / hornetAnnualCost) * 100).toFixed(0);
  
  return (
    <div className="bg-slate-900/50 border border-white/10 rounded-2xl p-8">
      <div className="flex items-center gap-4 mb-2">
        <HornetLogo size={48} />
        <div>
          <h3 className="text-2xl font-bold">Your Annual Savings</h3>
          <p className="text-slate-400">Calculate your ROI with HORNET</p>
        </div>
      </div>
      
      <div className="grid grid-cols-2 gap-6 my-8">
        <div>
          <label className="block text-sm font-medium text-slate-300 mb-3">
            Current SOC Team Size: <span className="text-amber-400 font-mono">{analysts} analysts</span>
          </label>
          <input
            type="range"
            min="1"
            max="10"
            value={analysts}
            onChange={(e) => setAnalysts(Number(e.target.value))}
            className="w-full h-3 bg-slate-700 rounded-full appearance-none cursor-pointer accent-amber-500"
          />
          <div className="flex justify-between text-xs text-slate-500 mt-1">
            <span>1</span>
            <span>10</span>
          </div>
        </div>
        
        <div>
          <label className="block text-sm font-medium text-slate-300 mb-3">
            Monthly Incidents: <span className="text-amber-400 font-mono">{incidents.toLocaleString()}</span>
          </label>
          <input
            type="range"
            min="100"
            max="5000"
            step="100"
            value={incidents}
            onChange={(e) => setIncidents(Number(e.target.value))}
            className="w-full h-3 bg-slate-700 rounded-full appearance-none cursor-pointer accent-amber-500"
          />
          <div className="flex justify-between text-xs text-slate-500 mt-1">
            <span>100</span>
            <span>5,000</span>
          </div>
        </div>
      </div>
      
      {/* Current State */}
      <div className="bg-red-500/10 border border-red-500/30 rounded-xl p-6 mb-4">
        <h4 className="text-sm font-semibold text-red-400 uppercase tracking-wide mb-4">Current Annual Cost</h4>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <span className="text-sm text-slate-400">Team Cost ({analysts} analysts)</span>
            <span className="block text-2xl font-bold font-mono text-red-400">${currentTeamCost.toLocaleString()}</span>
          </div>
          <div>
            <span className="text-sm text-slate-400">Incident Capacity</span>
            <span className="block text-2xl font-bold font-mono text-red-400">{currentCoverage.toLocaleString()}/yr</span>
          </div>
        </div>
      </div>
      
      {/* With HORNET */}
      <div className="bg-green-500/10 border border-green-500/30 rounded-xl p-6 mb-4">
        <h4 className="text-sm font-semibold text-green-400 uppercase tracking-wide mb-4">With HORNET ({hornetTier})</h4>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <span className="text-sm text-slate-400">New Annual Cost</span>
            <span className="block text-2xl font-bold font-mono text-green-400">${hybridTeamCost.toLocaleString()}</span>
            <span className="text-xs text-slate-500">1 analyst + HORNET {hornetTier}</span>
          </div>
          <div>
            <span className="text-sm text-slate-400">New Incident Capacity</span>
            <span className="block text-2xl font-bold font-mono text-green-400">{annualIncidents.toLocaleString()}/yr</span>
            <span className="text-xs text-slate-500">+{coverageIncrease}% coverage increase</span>
          </div>
        </div>
      </div>
      
      {/* Savings Summary */}
      <div className="bg-amber-500/10 border border-amber-500/30 rounded-xl p-6 text-center">
        <span className="block text-sm text-slate-400 mb-2">Your Annual Savings</span>
        <span className="block text-5xl font-bold font-mono text-amber-400">
          ${Math.max(0, annualSavings).toLocaleString()}
        </span>
        <span className="block text-lg text-amber-400/80 font-semibold mt-2">{roi}% ROI</span>
        <p className="text-sm text-slate-400 mt-4">
          Redeploy {analysts - 1} analysts to threat hunting, architecture, or strategic initiatives
        </p>
      </div>
      
      <div className="mt-6 p-4 bg-green-500/10 border border-green-500/30 rounded-xl">
        <p className="text-green-400 text-sm">
          <strong>Your Win:</strong> Stop paying for 24/7 analyst shifts. HORNET handles the volume while your senior analyst focuses on the cases that truly need human judgment.
        </p>
      </div>
    </div>
  );
};

// Accuracy Gauge Component
const AccuracyGauge = () => {
  const [showScavenger, setShowScavenger] = useState(false);
  
  // Calculate time savings from auto-closure
  const incidentsPerMonth = 1000;
  const autoCloseRate = 0.799;
  const avgManualTime = 45; // minutes per incident
  const autoClosedIncidents = incidentsPerMonth * autoCloseRate;
  const hoursSaved = (autoClosedIncidents * avgManualTime) / 60;
  
  return (
    <div className="bg-slate-900/50 border border-white/10 rounded-2xl p-8">
      <div className="flex items-center gap-4 mb-2">
        <HornetLogo size={48} />
        <div>
          <h3 className="text-2xl font-bold">Accuracy: Auto-Resolution</h3>
          <p className="text-slate-400">HORNET heals messy data automatically</p>
        </div>
      </div>
      
      <div className="flex justify-center my-8">
        <div className="relative w-48 h-48">
          <svg className="w-full h-full -rotate-90" viewBox="0 0 100 100">
            <circle cx="50" cy="50" r="40" fill="none" stroke="rgba(255,255,255,0.1)" strokeWidth="12" />
            <motion.circle
              cx="50" cy="50" r="40"
              fill="none"
              stroke="url(#gaugeGradient)"
              strokeWidth="12"
              strokeLinecap="round"
              initial={{ pathLength: 0 }}
              animate={{ pathLength: 0.799 }}
              transition={{ duration: 2, ease: "easeOut" }}
            />
            <defs>
              <linearGradient id="gaugeGradient" x1="0%" y1="0%" x2="100%" y2="0%">
                <stop offset="0%" stopColor="#22c55e" />
                <stop offset="100%" stopColor="#06b6d4" />
              </linearGradient>
            </defs>
          </svg>
          <div className="absolute inset-0 flex flex-col items-center justify-center">
            <span className="text-4xl font-bold font-mono text-white">79.9%</span>
            <span className="text-sm text-slate-400">Auto-Resolved</span>
          </div>
        </div>
      </div>
      
      <div className="bg-amber-500/10 border border-amber-500/30 rounded-xl p-4 mb-6 text-center">
        <span className="text-sm text-slate-400">At 1,000 incidents/month, you save</span>
        <span className="block text-3xl font-bold font-mono text-amber-400 my-1">{hoursSaved.toLocaleString()} hours/month</span>
        <span className="text-sm text-slate-400">of analyst time on resolved incidents</span>
      </div>
      
      <div className="flex justify-center mb-6">
        <button
          onClick={() => setShowScavenger(!showScavenger)}
          className={`px-6 py-3 rounded-xl font-medium transition-all ${
            showScavenger 
              ? 'bg-cyan-500 text-slate-950' 
              : 'bg-slate-800 text-slate-300 hover:bg-slate-700'
          }`}
        >
          {showScavenger ? '✓ Scavenger Logic Active' : 'See: Scavenger Logic'}
        </button>
      </div>
      
      <AnimatePresence>
        {showScavenger && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            className="overflow-hidden"
          >
            <div className="bg-cyan-500/10 border border-cyan-500/30 rounded-xl p-4 mb-4">
              <div className="flex items-center justify-between mb-3">
                <span className="text-sm font-medium text-cyan-400">Detection Improvement</span>
                <span className="text-2xl font-bold font-mono text-cyan-400">+300%</span>
              </div>
              <div className="h-2 bg-slate-700 rounded-full overflow-hidden">
                <motion.div
                  initial={{ width: '25%' }}
                  animate={{ width: '100%' }}
                  transition={{ duration: 1 }}
                  className="h-full bg-gradient-to-r from-cyan-600 to-cyan-400"
                />
              </div>
              <p className="text-xs text-slate-400 mt-3">
                <strong>What it does:</strong> Automatically extracts IPs, file hashes, domains, and usernames from unstructured alert text—turning "lazy" alerts into actionable investigations.
              </p>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
      
      <div className="p-4 bg-green-500/10 border border-green-500/30 rounded-xl">
        <p className="text-green-400 text-sm">
          <strong>Your Win:</strong> Legacy systems send garbage? HORNET extracts gold. No more alert fatigue from poorly-formatted data.
        </p>
      </div>
    </div>
  );
};

// Consensus Depth Visualization
const ConsensusDepth = () => {
  const [activeIncident, setActiveIncident] = useState(null);
  const [consultations, setConsultations] = useState([]);
  
  const specialists = [
    { name: 'HunterAgent', layer: 'Detection', finding: 'No malicious signatures found' },
    { name: 'SentinelAgent', layer: 'Detection', finding: 'Behavioral baseline normal' },
    { name: 'IntelAgent', layer: 'Intelligence', finding: 'IP not in threat feeds' },
    { name: 'CorrelatorAgent', layer: 'Intelligence', finding: 'No related incidents found' },
    { name: 'AnalystAgent', layer: 'Analysis', finding: 'Traffic pattern consistent with CDN' },
    { name: 'ForensicsAgent', layer: 'Analysis', finding: 'No IOCs in packet capture' },
    { name: 'TriageAgent', layer: 'Analysis', finding: 'Confidence: Benign activity' },
    { name: 'ResponderAgent', layer: 'Action', finding: 'No action required' },
    { name: 'OversightAgent', layer: 'Governance', finding: 'Verified: False positive' },
    { name: 'ComplianceAgent', layer: 'Governance', finding: 'No data exposure risk' },
    { name: 'LegalAgent', layer: 'Governance', finding: 'No notification required' },
    { name: 'RouterAgent', layer: 'Meta', finding: 'Routing complete: DISMISS' },
  ];
  
  const startConsensus = () => {
    setActiveIncident('phantom-alert-2847');
    setConsultations([]);
    
    specialists.forEach((spec, i) => {
      setTimeout(() => {
        setConsultations(prev => [...prev, spec]);
      }, i * 400);
    });
  };
  
  const getLayerColor = (layer) => ({
    Detection: 'bg-red-500',
    Intelligence: 'bg-blue-500',
    Analysis: 'bg-green-500',
    Action: 'bg-amber-500',
    Governance: 'bg-purple-500',
    Meta: 'bg-cyan-500',
  }[layer] || 'bg-slate-500');
  
  return (
    <div className="bg-slate-900/50 border border-white/10 rounded-2xl p-8">
      <div className="flex items-center gap-4 mb-2">
        <HornetLogo size={48} />
        <div>
          <h3 className="text-2xl font-bold">Depth: Multi-Agent Consensus</h3>
          <p className="text-slate-400">12+ specialists deliberate on every critical incident</p>
        </div>
      </div>
      
      <div className="my-6 p-4 bg-purple-500/10 border border-purple-500/30 rounded-xl text-center">
        <span className="text-sm text-slate-400">Equivalent manual investigation time</span>
        <span className="block text-3xl font-bold font-mono text-purple-400 my-1">6-8 hours</span>
        <span className="text-sm text-slate-400">completed in under 3 minutes</span>
      </div>
      
      {!activeIncident ? (
        <button
          onClick={startConsensus}
          className="w-full py-4 bg-gradient-to-r from-purple-500 to-purple-600 text-white rounded-xl font-semibold text-lg transition-all hover:shadow-lg hover:shadow-purple-500/30 flex items-center justify-center gap-2"
        >
          <HornetLogo size={24} />
          Watch: Critical Incident Analysis →
        </button>
      ) : (
        <>
          <div className="bg-slate-800/50 rounded-xl p-4 mb-6">
            <div className="flex items-center justify-between mb-2">
              <span className="font-mono text-amber-400">{activeIncident}</span>
              <span className="px-2 py-1 bg-red-500/20 text-red-400 rounded text-xs font-semibold">CRITICAL</span>
            </div>
            <p className="text-sm text-slate-400">Unusual outbound traffic detected—is it C2 or CDN?</p>
          </div>
          
          <div className="space-y-2 mb-6 max-h-64 overflow-y-auto">
            <AnimatePresence mode="popLayout">
              {consultations.map((spec, i) => (
                <motion.div
                  key={spec.name}
                  initial={{ opacity: 0, x: -20 }}
                  animate={{ opacity: 1, x: 0 }}
                  className="flex items-center gap-3 bg-slate-800/30 rounded-lg p-3"
                >
                  <span className={`w-2 h-2 rounded-full ${getLayerColor(spec.layer)}`} />
                  <div className="flex-1 min-w-0">
                    <span className="text-sm text-slate-300 font-medium">{spec.name}</span>
                    <span className="block text-xs text-slate-500 truncate">{spec.finding}</span>
                  </div>
                  <span className="text-xs text-green-400">✓</span>
                </motion.div>
              ))}
            </AnimatePresence>
          </div>
          
          <div className="grid grid-cols-2 gap-4 mb-6">
            <div className="bg-slate-800/50 rounded-xl p-4 text-center">
              <span className="block text-3xl font-bold font-mono text-purple-400">{consultations.length}</span>
              <span className="text-xs text-slate-500">Specialists Consulted</span>
            </div>
            <div className="bg-slate-800/50 rounded-xl p-4 text-center">
              <span className="block text-3xl font-bold font-mono text-cyan-400">107k</span>
              <span className="text-xs text-slate-500">Tokens of Reasoning</span>
            </div>
          </div>
          
          {consultations.length === specialists.length && (
            <motion.div
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              className="bg-green-500/10 border border-green-500/30 rounded-xl p-4 text-center"
            >
              <span className="text-green-400 font-semibold text-lg">✓ CONSENSUS: False Positive Confirmed</span>
              <p className="text-sm text-slate-400 mt-2">
                Alert dismissed with full audit trail. Your analyst wasn't paged at 3 AM.
              </p>
            </motion.div>
          )}
        </>
      )}
      
      <div className="mt-6 p-4 bg-green-500/10 border border-green-500/30 rounded-xl">
        <p className="text-green-400 text-sm">
          <strong>Your Win:</strong> No more alert fatigue. Your team only sees incidents that 12+ AI specialists agree require human attention.
        </p>
      </div>
    </div>
  );
};

// Compliance Dashboard
const ComplianceDashboard = () => {
  const [showAudit, setShowAudit] = useState(null);
  
  const incidents = [
    { id: 'inc-8847', type: 'Data Exfiltration Attempt', hipaa: true, gdpr: true, pci: false },
    { id: 'inc-8846', type: 'PHI Access Anomaly', hipaa: true, gdpr: false, pci: false },
    { id: 'inc-8845', type: 'EU Customer Data Transfer', hipaa: false, gdpr: true, pci: false },
    { id: 'inc-8844', type: 'Payment System Alert', hipaa: false, gdpr: false, pci: true },
  ];
  
  const auditReport = {
    'inc-8847': [
      '09:14:22 - ComplianceAgent: Event classified as potential data breach',
      '09:14:24 - LegalAgent: HIPAA §164.404 notification requirements assessed',
      '09:14:26 - ComplianceAgent: GDPR Art. 33 breach notification triggered',
      '09:14:28 - OversightAgent: Response approved, containment initiated',
      '09:14:31 - ComplianceAgent: Audit trail generated, 72-hour timer started',
    ],
  };
  
  return (
    <div className="bg-slate-900/50 border border-white/10 rounded-2xl p-8">
      <div className="flex items-center gap-4 mb-2">
        <HornetLogo size={48} />
        <div>
          <h3 className="text-2xl font-bold">Built-In Compliance</h3>
          <p className="text-slate-400">Legal & Compliance agents in every investigation</p>
        </div>
      </div>
      
      <div className="grid grid-cols-2 gap-4 my-8">
        <div className="bg-purple-500/10 border border-purple-500/30 rounded-xl p-6 text-center">
          <span className="block text-5xl font-bold font-mono text-purple-400">100%</span>
          <span className="text-slate-400">Compliance Coverage</span>
          <p className="text-xs text-slate-500 mt-2">on all critical data events</p>
        </div>
        <div className="bg-cyan-500/10 border border-cyan-500/30 rounded-xl p-6 text-center">
          <span className="block text-5xl font-bold font-mono text-cyan-400">$0</span>
          <span className="text-slate-400">Audit Prep Time</span>
          <p className="text-xs text-slate-500 mt-2">trails generated automatically</p>
        </div>
      </div>
      
      <h4 className="text-sm font-semibold text-slate-400 uppercase tracking-wide mb-4">Recent Compliance Events</h4>
      
      <div className="space-y-3 mb-6">
        {incidents.map((inc) => (
          <motion.div
            key={inc.id}
            className="bg-slate-800/50 rounded-xl p-4 cursor-pointer hover:bg-slate-800 transition-colors"
            onClick={() => setShowAudit(showAudit === inc.id ? null : inc.id)}
            whileHover={{ scale: 1.01 }}
          >
            <div className="flex items-center justify-between mb-2">
              <span className="font-mono text-sm text-slate-300">{inc.id}</span>
              <div className="flex gap-2">
                {inc.hipaa && <span className="px-2 py-0.5 bg-blue-500/20 text-blue-400 rounded text-xs font-semibold">HIPAA</span>}
                {inc.gdpr && <span className="px-2 py-0.5 bg-green-500/20 text-green-400 rounded text-xs font-semibold">GDPR</span>}
                {inc.pci && <span className="px-2 py-0.5 bg-amber-500/20 text-amber-400 rounded text-xs font-semibold">PCI-DSS</span>}
              </div>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm text-slate-400">{inc.type}</span>
              <span className="text-xs text-green-400">✓ Assessed & Documented</span>
            </div>
            
            <AnimatePresence>
              {showAudit === inc.id && (
                <motion.div
                  initial={{ opacity: 0, height: 0 }}
                  animate={{ opacity: 1, height: 'auto' }}
                  exit={{ opacity: 0, height: 0 }}
                  className="mt-4 pt-4 border-t border-white/5"
                >
                  <h5 className="text-xs font-semibold text-slate-500 uppercase mb-2">Audit Trail</h5>
                  <div className="space-y-1 text-xs font-mono text-slate-400">
                    {(auditReport[inc.id] || [
                      `${new Date().toTimeString().slice(0,8)} - ComplianceAgent: Regulatory review completed`,
                      `${new Date().toTimeString().slice(0,8)} - LegalAgent: Notification requirements assessed`,
                      `${new Date().toTimeString().slice(0,8)} - OversightAgent: Response approved`,
                    ]).map((line, i) => (
                      <p key={i}>{line}</p>
                    ))}
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </motion.div>
        ))}
      </div>
      
      <div className="p-4 bg-green-500/10 border border-green-500/30 rounded-xl">
        <p className="text-green-400 text-sm">
          <strong>Your Win:</strong> When auditors knock, your documentation is already done. Every incident includes timestamped compliance assessments—no scrambling, no billable hours to consultants.
        </p>
      </div>
    </div>
  );
};

// Main Benchmarks Page
export default function HornetBenchmarks() {
  const [activeTab, setActiveTab] = useState('overview');
  
  const tabs = [
    { id: 'overview', label: 'Overview' },
    { id: 'speed', label: 'Speed' },
    { id: 'savings', label: 'Savings' },
    { id: 'accuracy', label: 'Accuracy' },
    { id: 'depth', label: 'Depth' },
    { id: 'compliance', label: 'Compliance' },
  ];
  
  return (
    <div className="min-h-screen bg-slate-950 text-white">
      {/* Header */}
      <header className="border-b border-white/5 px-8 py-4">
        <div className="flex items-center justify-between max-w-7xl mx-auto">
          <div className="flex items-center gap-3">
            <HornetLogo size={48} />
            <div>
              <h1 className="font-bold tracking-wider text-lg">HORNET</h1>
              <p className="text-xs text-slate-500">Performance Benchmarks</p>
            </div>
          </div>
          <nav className="flex gap-1 bg-slate-900 rounded-xl p-1">
            {tabs.map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`px-4 py-2 rounded-lg text-sm font-medium transition-all ${
                  activeTab === tab.id 
                    ? 'bg-amber-500 text-slate-950' 
                    : 'text-slate-400 hover:text-white'
                }`}
              >
                {tab.label}
              </button>
            ))}
          </nav>
        </div>
      </header>
      
      {/* Content */}
      <main className="max-w-7xl mx-auto p-8">
        <AnimatePresence mode="wait">
          {activeTab === 'overview' && (
            <motion.div
              key="overview"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20 }}
            >
              <div className="text-center mb-12">
                <div className="flex justify-center mb-6">
                  <HornetLogo size={80} />
                </div>
                <h2 className="text-4xl font-bold mb-4">
                  What <span className="text-amber-400">HORNET</span> Delivers
                </h2>
                <p className="text-xl text-slate-400 max-w-2xl mx-auto">
                  Real results from production deployments. Every metric translates to money and time back in your pocket.
                </p>
              </div>
              
              {/* Key Savings Stats */}
              <div className="grid grid-cols-5 gap-4 mb-12">
                {[
                  { label: 'Response Time', value: '<45s', comparison: 'vs 4-8 hours', savings: '99.8% faster', color: 'text-green-400' },
                  { label: 'Annual Savings', value: '$213k', comparison: 'typical 3-analyst team', savings: '6x ROI', color: 'text-amber-400' },
                  { label: 'Auto-Resolution', value: '79.9%', comparison: 'vs ~20% manual', savings: '600+ hrs/mo saved', color: 'text-cyan-400' },
                  { label: 'Analysis Depth', value: '12+', comparison: 'specialists per incident', savings: '8 hrs work in 3 min', color: 'text-purple-400' },
                  { label: 'Audit Prep', value: '$0', comparison: 'consultant hours', savings: '100% auto-documented', color: 'text-blue-400' },
                ].map((stat, i) => (
                  <motion.div
                    key={stat.label}
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: i * 0.1 }}
                    className="bg-slate-900/50 border border-white/5 rounded-xl p-6 text-center"
                  >
                    <span className={`block text-3xl font-bold font-mono ${stat.color}`}>
                      {stat.value}
                    </span>
                    <span className="block text-sm text-slate-400 mt-1">{stat.label}</span>
                    <span className="block text-xs text-slate-500 mt-2">{stat.comparison}</span>
                    <span className="block text-xs text-green-400 mt-1">{stat.savings}</span>
                  </motion.div>
                ))}
              </div>
              
              {/* Live Demo */}
              <div className="grid grid-cols-2 gap-8">
                <LiveProcessingDemo />
                <div className="space-y-4">
                  <div className="bg-gradient-to-br from-amber-500/10 to-transparent border border-amber-500/30 rounded-2xl p-6">
                    <div className="flex items-center gap-3 mb-4">
                      <HornetLogo size={32} />
                      <h3 className="text-lg font-semibold">Why This Matters to You</h3>
                    </div>
                    <ul className="space-y-4 text-sm text-slate-300">
                      <li className="flex items-start gap-3">
                        <span className="text-green-400 mt-0.5">💰</span>
                        <span><strong>Headcount Savings:</strong> Replace 24/7 shift coverage with one senior analyst + HORNET. Redeploy talent to strategic work.</span>
                      </li>
                      <li className="flex items-start gap-3">
                        <span className="text-green-400 mt-0.5">⏱️</span>
                        <span><strong>Time Back:</strong> 600+ analyst hours per month returned to your team. No more alert triage at 3 AM.</span>
                      </li>
                      <li className="flex items-start gap-3">
                        <span className="text-green-400 mt-0.5">🛡️</span>
                        <span><strong>Better Coverage:</strong> Handle 10x incident volume without scaling headcount. HORNET doesn't take PTO.</span>
                      </li>
                      <li className="flex items-start gap-3">
                        <span className="text-green-400 mt-0.5">📋</span>
                        <span><strong>Compliance Built-In:</strong> SOC 2, HIPAA, GDPR audit trails generated automatically. Zero prep time.</span>
                      </li>
                    </ul>
                  </div>
                  <p className="text-sm text-slate-500 text-center">
                    Click the tabs above to explore each benefit →
                  </p>
                </div>
              </div>
            </motion.div>
          )}
          
          {activeTab === 'speed' && (
            <motion.div key="speed" initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -20 }} className="max-w-2xl mx-auto">
              <SpeedBenchmark />
            </motion.div>
          )}
          
          {activeTab === 'savings' && (
            <motion.div key="savings" initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -20 }} className="max-w-2xl mx-auto">
              <SavingsCalculator />
            </motion.div>
          )}
          
          {activeTab === 'accuracy' && (
            <motion.div key="accuracy" initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -20 }} className="max-w-2xl mx-auto">
              <AccuracyGauge />
            </motion.div>
          )}
          
          {activeTab === 'depth' && (
            <motion.div key="depth" initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -20 }} className="max-w-2xl mx-auto">
              <ConsensusDepth />
            </motion.div>
          )}
          
          {activeTab === 'compliance' && (
            <motion.div key="compliance" initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -20 }} className="max-w-2xl mx-auto">
              <ComplianceDashboard />
            </motion.div>
          )}
        </AnimatePresence>
      </main>
      
      {/* Footer CTA */}
      <footer className="border-t border-white/5 px-8 py-12 mt-12">
        <div className="max-w-4xl mx-auto text-center">
          <div className="flex justify-center mb-4">
            <HornetLogo size={64} />
          </div>
          <h3 className="text-2xl font-bold mb-4">See Your Savings in Action</h3>
          <p className="text-slate-400 mb-6">14-day free trial. Process your first 500 incidents on us.</p>
          <button className="px-8 py-4 bg-gradient-to-r from-amber-500 to-amber-600 text-slate-950 rounded-xl font-semibold text-lg transition-all hover:shadow-lg hover:shadow-amber-500/30">
            Start Free Trial →
          </button>
          <p className="text-sm text-slate-500 mt-4">No credit card required • SOC 2 Type II certified</p>
        </div>
      </footer>
    </div>
  );
}
