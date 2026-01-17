// CampaignView.jsx - Campaign Visualization Component (Ultra Polished)
import { useState, useEffect, useCallback, useMemo, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';

const API_BASE = import.meta.env?.VITE_API_URL || 'http://localhost:8000';

// SVG Icons
const Icons = {
  ip: (
    <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <circle cx="12" cy="12" r="10"/><line x1="2" y1="12" x2="22" y2="12"/><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"/>
    </svg>
  ),
  user: (
    <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/>
    </svg>
  ),
  host: (
    <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <rect x="2" y="3" width="20" height="14" rx="2" ry="2"/><line x1="8" y1="21" x2="16" y2="21"/><line x1="12" y1="17" x2="12" y2="21"/>
    </svg>
  ),
  hash: (
    <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <line x1="4" y1="9" x2="20" y2="9"/><line x1="4" y1="15" x2="20" y2="15"/><line x1="10" y1="3" x2="8" y2="21"/><line x1="16" y1="3" x2="14" y2="21"/>
    </svg>
  ),
  domain: (
    <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <circle cx="12" cy="12" r="10"/><line x1="2" y1="12" x2="22" y2="12"/><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"/>
    </svg>
  ),
  email: (
    <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z"/><polyline points="22,6 12,13 2,6"/>
    </svg>
  ),
  link: (
    <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"/><path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"/>
    </svg>
  ),
  expand: (
    <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <polyline points="15 3 21 3 21 9"/><polyline points="9 21 3 21 3 15"/><line x1="21" y1="3" x2="14" y2="10"/><line x1="3" y1="21" x2="10" y2="14"/>
    </svg>
  ),
  close: (
    <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
    </svg>
  ),
};

export function useCampaignStats(apiKey) {
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);

  const fetchStats = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/api/v1/campaigns/stats`, {
        headers: { 'X-API-Key': apiKey || localStorage.getItem('hornet_api_key') }
      });
      if (res.ok) {
        const data = await res.json();
        setStats(data);
      }
    } catch (err) {
      console.error('Failed to fetch campaign stats:', err);
    } finally {
      setLoading(false);
    }
  }, [apiKey]);

  useEffect(() => {
    fetchStats();
    const interval = setInterval(fetchStats, 10000);
    return () => clearInterval(interval);
  }, [fetchStats]);

  return { stats, loading, refetch: fetchStats };
}

export function useCampaignGraph(apiKey, hoursBack = 24) {
  const [graph, setGraph] = useState({ nodes: [], edges: [] });
  const [loading, setLoading] = useState(true);

  const fetchGraph = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/api/v1/campaigns/graph?hours_back=${hoursBack}`, {
        headers: { 'X-API-Key': apiKey || localStorage.getItem('hornet_api_key') }
      });
      if (res.ok) {
        const data = await res.json();
        setGraph(data);
      }
    } catch (err) {
      console.error('Failed to fetch campaign graph:', err);
    } finally {
      setLoading(false);
    }
  }, [apiKey, hoursBack]);

  useEffect(() => {
    fetchGraph();
  }, [fetchGraph]);

  return { graph, loading, refetch: fetchGraph };
}

const severityColors = {
  CRITICAL: { bg: '#ef4444', glow: '#fca5a5' },
  HIGH: { bg: '#f97316', glow: '#fdba74' },
  MEDIUM: { bg: '#eab308', glow: '#fde047' },
  LOW: { bg: '#22c55e', glow: '#86efac' },
};

const linkTypeColors = {
  campaign: '#f59e0b',
  same_ip: '#3b82f6',
  same_user: '#8b5cf6',
  same_host: '#10b981',
  same_hash: '#ec4899',
  'same_ip_and_user': '#f59e0b',
  'same_ip_user_and_host': '#ef4444',
  'same_user|same_hash': '#8b5cf6',
};

const entityTypeColors = {
  ip: 'text-blue-400',
  user: 'text-purple-400',
  host: 'text-green-400',
  hash: 'text-pink-400',
  domain: 'text-cyan-400',
  email: 'text-amber-400',
};

export const CampaignStats = ({ stats }) => {
  if (!stats) return null;

  const statItems = [
    { value: stats.total_links, label: 'Total Links', color: 'amber', trend: '+12%' },
    { value: stats.high_confidence_links, label: 'High Confidence', color: 'green', trend: '93%' },
    { value: stats.linked_incidents, label: 'Linked Incidents', color: 'blue', trend: null },
    { value: stats.top_shared_entities?.length || 0, label: 'Shared Entities', color: 'purple', trend: null },
  ];

  const colorClasses = {
    amber: { gradient: 'from-amber-500/20 to-amber-600/5', border: 'border-amber-500/30', text: 'text-amber-400' },
    green: { gradient: 'from-green-500/20 to-green-600/5', border: 'border-green-500/30', text: 'text-green-400' },
    blue: { gradient: 'from-blue-500/20 to-blue-600/5', border: 'border-blue-500/30', text: 'text-blue-400' },
    purple: { gradient: 'from-purple-500/20 to-purple-600/5', border: 'border-purple-500/30', text: 'text-purple-400' },
  };

  return (
    <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
      {statItems.map((stat, i) => (
        <motion.div
          key={stat.label}
          initial={{ opacity: 0, y: 20, scale: 0.95 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          transition={{ delay: i * 0.08, type: 'spring', stiffness: 100 }}
          whileHover={{ scale: 1.02, transition: { duration: 0.2 } }}
          className={`bg-gradient-to-br ${colorClasses[stat.color].gradient} ${colorClasses[stat.color].border} border rounded-xl p-4 cursor-default`}
        >
          <div className="flex items-end justify-between">
            <div className={`text-2xl md:text-3xl font-bold ${colorClasses[stat.color].text}`}>
              {stat.value}
            </div>
            {stat.trend && (
              <span className={`text-xs ${colorClasses[stat.color].text} opacity-60`}>{stat.trend}</span>
            )}
          </div>
          <div className="text-xs text-slate-400 mt-1">{stat.label}</div>
        </motion.div>
      ))}
    </div>
  );
};

// Find connected components (clusters) in the graph
function findClusters(nodes, edges) {
  const nodeIds = new Set(nodes.map(n => n.id));
  const adjacency = {};
  
  nodes.forEach(n => adjacency[n.id] = []);
  edges.forEach(e => {
    if (adjacency[e.source]) adjacency[e.source].push(e.target);
    if (adjacency[e.target]) adjacency[e.target].push(e.source);
  });

  const visited = new Set();
  const clusters = [];

  function dfs(nodeId, cluster) {
    if (visited.has(nodeId)) return;
    visited.add(nodeId);
    cluster.push(nodeId);
    (adjacency[nodeId] || []).forEach(neighbor => {
      if (nodeIds.has(neighbor)) dfs(neighbor, cluster);
    });
  }

  nodes.forEach(node => {
    if (!visited.has(node.id)) {
      const cluster = [];
      dfs(node.id, cluster);
      if (cluster.length > 0) clusters.push(cluster);
    }
  });

  return clusters.sort((a, b) => b.length - a.length);
}

export const CampaignGraph = ({ graph, onNodeClick }) => {
  const [hoveredCluster, setHoveredCluster] = useState(null);
  const [selectedCluster, setSelectedCluster] = useState(null);
  const [showAllIncidents, setShowAllIncidents] = useState(false);
  const [animationPhase, setAnimationPhase] = useState(0);
  const { nodes, edges } = graph;

  const clusters = useMemo(() => findClusters(nodes, edges), [nodes, edges]);
  
  const nodeMap = useMemo(() => {
    return Object.fromEntries(nodes.map(n => [n.id, n]));
  }, [nodes]);

  // Animate connections
  useEffect(() => {
    const interval = setInterval(() => {
      setAnimationPhase(p => (p + 1) % 100);
    }, 50);
    return () => clearInterval(interval);
  }, []);

  if (!nodes.length) {
    return (
      <div className="flex items-center justify-center h-64 text-slate-500 bg-slate-900/30 rounded-xl border border-white/5">
        <div className="text-center">
          <motion.div 
            animate={{ rotate: 360 }}
            transition={{ duration: 8, repeat: Infinity, ease: 'linear' }}
            className="text-slate-600 mb-3 inline-block"
          >
            {Icons.link}
          </motion.div>
          <p className="text-sm">No campaign correlations detected</p>
          <p className="text-xs text-slate-600 mt-1">Incidents will cluster as patterns emerge</p>
        </div>
      </div>
    );
  }

  const width = 650;
  const height = 320;
  
  // Position clusters in a nice honeycomb-ish layout
  const clusterPositions = clusters.slice(0, 12).map((cluster, i) => {
    const cols = Math.min(4, Math.ceil(Math.sqrt(clusters.length)));
    const rows = Math.ceil(Math.min(12, clusters.length) / cols);
    const col = i % cols;
    const row = Math.floor(i / cols);
    const cellWidth = width / cols;
    const cellHeight = height / rows;
    
    // Offset alternate rows for honeycomb effect
    const offsetX = row % 2 === 1 ? cellWidth * 0.25 : 0;
    
    return {
      cluster,
      x: cellWidth * (col + 0.5) + offsetX,
      y: cellHeight * (row + 0.5),
      size: Math.min(55, Math.max(28, 20 + cluster.length * 4)),
    };
  });

  // Get severity breakdown for a cluster
  const getClusterStats = (clusterIds) => {
    const stats = { CRITICAL: 0, HIGH: 0, MEDIUM: 0, LOW: 0 };
    clusterIds.forEach(id => {
      const node = nodeMap[id];
      if (node?.severity) stats[node.severity]++;
    });
    return stats;
  };

  // Get dominant severity for glow color
  const getDominantSeverity = (clusterIds) => {
    const stats = getClusterStats(clusterIds);
    return Object.entries(stats).sort((a, b) => b[1] - a[1])[0][0];
  };

  // Count edges between clusters
  const getClusterEdges = () => {
    const clusterMap = {};
    clusters.forEach((cluster, i) => {
      cluster.forEach(nodeId => clusterMap[nodeId] = i);
    });
    
    const edgeData = {};
    edges.forEach(edge => {
      const sourceCluster = clusterMap[edge.source];
      const targetCluster = clusterMap[edge.target];
      if (sourceCluster !== undefined && targetCluster !== undefined && sourceCluster !== targetCluster) {
        const key = [Math.min(sourceCluster, targetCluster), Math.max(sourceCluster, targetCluster)].join('-');
        if (!edgeData[key]) edgeData[key] = { count: 0, types: new Set() };
        edgeData[key].count++;
        edgeData[key].types.add(edge.link_type);
      }
    });
    return edgeData;
  };

  const interClusterEdges = getClusterEdges();

  const selectedClusterData = selectedCluster !== null ? clusterPositions[selectedCluster] : null;
  const incidentsToShow = showAllIncidents 
    ? selectedClusterData?.cluster || []
    : (selectedClusterData?.cluster || []).slice(0, 8);

  return (
    <div className="bg-slate-900/50 border border-white/10 rounded-xl overflow-hidden">
      {/* Graph Area */}
      <div className="relative">
        <svg width="100%" height={height} viewBox={`0 0 ${width} ${height}`} className="block">
          <defs>
            {/* Glow filters for each severity */}
            {Object.entries(severityColors).map(([sev, colors]) => (
              <filter key={sev} id={`glow-${sev}`} x="-50%" y="-50%" width="200%" height="200%">
                <feGaussianBlur stdDeviation="6" result="blur"/>
                <feFlood floodColor={colors.glow} floodOpacity="0.6"/>
                <feComposite in2="blur" operator="in"/>
                <feMerge>
                  <feMergeNode/>
                  <feMergeNode in="SourceGraphic"/>
                </feMerge>
              </filter>
            ))}
            
            {/* Animated gradient for connections */}
            <linearGradient id="connectionGradient" gradientUnits="userSpaceOnUse">
              <stop offset="0%" stopColor="#f59e0b" stopOpacity="0.1"/>
              <stop offset={`${animationPhase}%`} stopColor="#f59e0b" stopOpacity="0.8"/>
              <stop offset="100%" stopColor="#f59e0b" stopOpacity="0.1"/>
            </linearGradient>
          </defs>

          {/* Animated inter-cluster connections */}
          {clusterPositions.map((cp1, i) => 
            clusterPositions.slice(i + 1).map((cp2, j) => {
              const key = `${i}-${i + j + 1}`;
              const edgeInfo = interClusterEdges[key];
              if (!edgeInfo) return null;
              
              const isHighlighted = hoveredCluster === i || hoveredCluster === (i + j + 1) ||
                                   selectedCluster === i || selectedCluster === (i + j + 1);
              
              // Calculate control point for curved line
              const midX = (cp1.x + cp2.x) / 2;
              const midY = (cp1.y + cp2.y) / 2;
              const dx = cp2.x - cp1.x;
              const dy = cp2.y - cp1.y;
              const dist = Math.sqrt(dx * dx + dy * dy);
              const offset = dist * 0.15;
              const controlX = midX - dy / dist * offset;
              const controlY = midY + dx / dist * offset;
              
              return (
                <g key={key}>
                  {/* Connection path */}
                  <motion.path
                    d={`M ${cp1.x} ${cp1.y} Q ${controlX} ${controlY} ${cp2.x} ${cp2.y}`}
                    fill="none"
                    stroke={isHighlighted ? '#f59e0b' : '#334155'}
                    strokeWidth={isHighlighted ? 2.5 : 1.5}
                    strokeOpacity={isHighlighted ? 0.8 : 0.3}
                    strokeDasharray={isHighlighted ? 'none' : '6 4'}
                    initial={{ pathLength: 0 }}
                    animate={{ pathLength: 1 }}
                    transition={{ duration: 1, delay: i * 0.1 }}
                  />
                  
                  {/* Animated particle on connection when highlighted */}
                  {isHighlighted && (
                    <motion.circle
                      r="3"
                      fill="#f59e0b"
                      initial={{ offsetDistance: '0%' }}
                      animate={{ offsetDistance: '100%' }}
                      transition={{ duration: 2, repeat: Infinity, ease: 'linear' }}
                      style={{ offsetPath: `path('M ${cp1.x} ${cp1.y} Q ${controlX} ${controlY} ${cp2.x} ${cp2.y}')` }}
                    />
                  )}
                  
                  {/* Connection count badge */}
                  {edgeInfo.count > 1 && (
                    <g transform={`translate(${controlX}, ${controlY})`}>
                      <circle r="10" fill="#1e293b" stroke="#334155" strokeWidth="1"/>
                      <text textAnchor="middle" dominantBaseline="middle" fill="#94a3b8" fontSize="9" fontWeight="bold">
                        {edgeInfo.count}
                      </text>
                    </g>
                  )}
                </g>
              );
            })
          )}

          {/* Cluster bubbles */}
          {clusterPositions.map((cp, i) => {
            const stats = getClusterStats(cp.cluster);
            const isHovered = hoveredCluster === i;
            const isSelected = selectedCluster === i;
            const dominantSeverity = getDominantSeverity(cp.cluster);
            const glowFilter = (isHovered || isSelected) ? `url(#glow-${dominantSeverity})` : undefined;

            // Create pie segments for severity breakdown
            const total = cp.cluster.length;
            let currentAngle = -Math.PI / 2;
            const segments = [];
            const scale = isHovered ? 1.08 : isSelected ? 1.05 : 1;
            
            Object.entries(severityColors).forEach(([sev, colors]) => {
              if (stats[sev] > 0) {
                const angle = (stats[sev] / total) * Math.PI * 2;
                const startAngle = currentAngle;
                const endAngle = currentAngle + angle;
                const largeArc = angle > Math.PI ? 1 : 0;
                
                const r = cp.size * scale;
                const x1 = cp.x + r * Math.cos(startAngle);
                const y1 = cp.y + r * Math.sin(startAngle);
                const x2 = cp.x + r * Math.cos(endAngle);
                const y2 = cp.y + r * Math.sin(endAngle);
                
                segments.push(
                  <motion.path
                    key={sev}
                    d={`M ${cp.x} ${cp.y} L ${x1} ${y1} A ${r} ${r} 0 ${largeArc} 1 ${x2} ${y2} Z`}
                    fill={colors.bg}
                    fillOpacity={isHovered || isSelected ? 0.7 : 0.5}
                    stroke={colors.bg}
                    strokeWidth={isHovered || isSelected ? 2 : 1}
                    initial={{ scale: 0 }}
                    animate={{ scale: 1 }}
                    transition={{ delay: i * 0.05, type: 'spring' }}
                  />
                );
                currentAngle = endAngle;
              }
            });

            return (
              <g
                key={i}
                style={{ cursor: 'pointer' }}
                onMouseEnter={() => setHoveredCluster(i)}
                onMouseLeave={() => setHoveredCluster(null)}
                onClick={() => {
                  setSelectedCluster(selectedCluster === i ? null : i);
                  setShowAllIncidents(false);
                }}
                filter={glowFilter}
              >
                {/* Outer ring pulse animation for selected */}
                {isSelected && (
                  <motion.circle
                    cx={cp.x}
                    cy={cp.y}
                    r={cp.size * 1.2}
                    fill="none"
                    stroke={severityColors[dominantSeverity].bg}
                    strokeWidth="2"
                    initial={{ scale: 1, opacity: 0.8 }}
                    animate={{ scale: 1.3, opacity: 0 }}
                    transition={{ duration: 1.5, repeat: Infinity }}
                  />
                )}
                
                {/* Background circle */}
                <circle
                  cx={cp.x}
                  cy={cp.y}
                  r={cp.size * scale * 1.08}
                  fill="#0f172a"
                  fillOpacity={0.9}
                />
                
                {/* Pie segments */}
                {segments}
                
                {/* Inner circle with count */}
                <circle
                  cx={cp.x}
                  cy={cp.y}
                  r={cp.size * 0.42}
                  fill="#0f172a"
                />
                <text
                  x={cp.x}
                  y={cp.y + 1}
                  textAnchor="middle"
                  dominantBaseline="middle"
                  fill="#f8fafc"
                  fontSize={cp.size > 40 ? 16 : 13}
                  fontWeight="bold"
                >
                  {cp.cluster.length}
                </text>
                
                {/* Cluster label */}
                <text
                  x={cp.x}
                  y={cp.y + cp.size * scale + 14}
                  textAnchor="middle"
                  fill={isHovered || isSelected ? '#f8fafc' : '#64748b'}
                  fontSize="10"
                  fontWeight={isHovered || isSelected ? '600' : '400'}
                >
                  Campaign {i + 1}
                </text>
              </g>
            );
          })}

          {/* Hover tooltip */}
          <AnimatePresence>
            {hoveredCluster !== null && selectedCluster === null && clusterPositions[hoveredCluster] && (
              <motion.g
                initial={{ opacity: 0, scale: 0.9 }}
                animate={{ opacity: 1, scale: 1 }}
                exit={{ opacity: 0, scale: 0.9 }}
              >
                {(() => {
                  const cp = clusterPositions[hoveredCluster];
                  const stats = getClusterStats(cp.cluster);
                  const tooltipWidth = 140;
                  const tooltipHeight = 50;
                  let tooltipX = cp.x - tooltipWidth / 2;
                  let tooltipY = cp.y - cp.size - tooltipHeight - 15;
                  
                  // Keep tooltip in bounds
                  if (tooltipX < 10) tooltipX = 10;
                  if (tooltipX + tooltipWidth > width - 10) tooltipX = width - tooltipWidth - 10;
                  if (tooltipY < 10) tooltipY = cp.y + cp.size + 15;
                  
                  return (
                    <>
                      <rect
                        x={tooltipX}
                        y={tooltipY}
                        width={tooltipWidth}
                        height={tooltipHeight}
                        rx="6"
                        fill="#1e293b"
                        stroke="#334155"
                        strokeWidth="1"
                        filter="drop-shadow(0 4px 6px rgba(0,0,0,0.3))"
                      />
                      <text x={tooltipX + tooltipWidth/2} y={tooltipY + 16} textAnchor="middle" fill="#f8fafc" fontSize="11" fontWeight="600">
                        {cp.cluster.length} Incident{cp.cluster.length > 1 ? 's' : ''}
                      </text>
                      <text x={tooltipX + tooltipWidth/2} y={tooltipY + 32} textAnchor="middle" fill="#94a3b8" fontSize="9">
                        {Object.entries(stats).filter(([,v]) => v > 0).map(([k,v]) => `${v} ${k}`).join(' · ')}
                      </text>
                      <text x={tooltipX + tooltipWidth/2} y={tooltipY + 44} textAnchor="middle" fill="#f59e0b" fontSize="9">
                        Click to explore
                      </text>
                    </>
                  );
                })()}
              </motion.g>
            )}
          </AnimatePresence>
        </svg>

        {/* Selected cluster detail panel */}
        <AnimatePresence>
          {selectedCluster !== null && selectedClusterData && (
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: 20 }}
              className="absolute bottom-3 left-3 right-3 bg-slate-800/98 backdrop-blur-sm border border-white/10 rounded-xl p-4 shadow-xl"
            >
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-3">
                  <div className={`w-3 h-3 rounded-full`} style={{ backgroundColor: severityColors[getDominantSeverity(selectedClusterData.cluster)].bg }}/>
                  <span className="font-semibold text-white">Campaign {selectedCluster + 1}</span>
                  <span className="text-xs text-slate-400">({selectedClusterData.cluster.length} incidents)</span>
                </div>
                <button 
                  onClick={() => setSelectedCluster(null)}
                  className="text-slate-400 hover:text-white p-1 hover:bg-white/10 rounded transition-colors"
                >
                  {Icons.close}
                </button>
              </div>
              
              {/* Severity breakdown */}
              <div className="flex gap-4 mb-3">
                {Object.entries(getClusterStats(selectedClusterData.cluster)).map(([sev, count]) => (
                  count > 0 && (
                    <div key={sev} className="flex items-center gap-1.5">
                      <span className="w-2 h-2 rounded-full" style={{ backgroundColor: severityColors[sev].bg }}/>
                      <span className="text-xs text-slate-400">{sev}:</span>
                      <span className="text-xs text-white font-medium">{count}</span>
                    </div>
                  )
                ))}
              </div>
              
              {/* Incident IDs */}
              <div className="flex flex-wrap gap-1.5">
                {incidentsToShow.map((id, idx) => (
                  <motion.button
                    key={id}
                    initial={{ opacity: 0, scale: 0.8 }}
                    animate={{ opacity: 1, scale: 1 }}
                    transition={{ delay: idx * 0.02 }}
                    onClick={() => onNodeClick?.(id)}
                    className="px-2.5 py-1.5 bg-slate-700/50 hover:bg-amber-500/20 border border-white/5 hover:border-amber-500/30 rounded-lg text-xs font-mono text-slate-300 hover:text-amber-400 transition-all"
                  >
                    {id.slice(0, 8)}
                  </motion.button>
                ))}
                
                {/* View All button */}
                {selectedClusterData.cluster.length > 8 && !showAllIncidents && (
                  <motion.button
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    onClick={() => setShowAllIncidents(true)}
                    className="px-3 py-1.5 bg-amber-500/10 hover:bg-amber-500/20 border border-amber-500/30 rounded-lg text-xs font-medium text-amber-400 hover:text-amber-300 transition-all flex items-center gap-1"
                  >
                    {Icons.expand}
                    View All ({selectedClusterData.cluster.length - 8} more)
                  </motion.button>
                )}
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {/* Legend */}
      <div className="flex flex-wrap items-center justify-between px-4 py-3 bg-slate-800/30 border-t border-white/5">
        <div className="flex flex-wrap gap-4">
          {Object.entries(severityColors).map(([sev, colors]) => (
            <div key={sev} className="flex items-center gap-1.5">
              <span className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: colors.bg }}/>
              <span className="text-xs text-slate-500">{sev.charAt(0) + sev.slice(1).toLowerCase()}</span>
            </div>
          ))}
        </div>
        <span className="text-xs text-slate-600">
          {clusters.length} campaign{clusters.length !== 1 ? 's' : ''} detected
        </span>
      </div>
    </div>
  );
};

export const TopEntities = ({ entities }) => {
  if (!entities?.length) return null;

  const getIcon = (type) => Icons[type] || Icons.link;

  return (
    <div className="bg-slate-900/50 border border-white/10 rounded-xl overflow-hidden">
      <div className="px-4 py-3 border-b border-white/5 flex items-center justify-between">
        <h3 className="text-sm font-semibold text-white">Top Shared Entities</h3>
        <span className="text-xs text-slate-500">{entities.length} total</span>
      </div>
      <div className="divide-y divide-white/5">
        {entities.slice(0, 8).map((entity, i) => (
          <motion.div
            key={i}
            initial={{ opacity: 0, x: -10 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: i * 0.03 }}
            whileHover={{ backgroundColor: 'rgba(255,255,255,0.03)' }}
            className="flex items-center justify-between px-4 py-2.5 transition-colors cursor-default"
          >
            <div className="flex items-center gap-2.5 min-w-0">
              <span className={`${entityTypeColors[entity.entity_type] || 'text-slate-400'} opacity-80`}>
                {getIcon(entity.entity_type)}
              </span>
              <span className="text-slate-300 font-mono text-xs truncate">
                {entity.entity_value}
              </span>
            </div>
            <div className="flex items-center gap-2 flex-shrink-0">
              <span className="text-[10px] text-slate-600 uppercase tracking-wide">{entity.entity_type}</span>
              <span className="bg-amber-500/15 text-amber-400 px-2 py-0.5 rounded-md text-[10px] font-semibold min-w-[1.5rem] text-center">
                {entity.incident_count}
              </span>
            </div>
          </motion.div>
        ))}
      </div>
    </div>
  );
};

export const LinkTypes = ({ linkTypes }) => {
  if (!linkTypes?.length) return null;

  const maxCount = Math.max(...linkTypes.map(lt => lt.count));

  return (
    <div className="bg-slate-900/50 border border-white/10 rounded-xl overflow-hidden">
      <div className="px-4 py-3 border-b border-white/5">
        <h3 className="text-sm font-semibold text-white">Link Types</h3>
      </div>
      <div className="p-4 space-y-3">
        {linkTypes.map((lt, i) => (
          <motion.div
            key={i}
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: i * 0.05 }}
          >
            <div className="flex justify-between items-center mb-1.5">
              <span className="text-xs text-slate-300 capitalize">{lt.link_type.replace(/_/g, ' ').replace(/\|/g, ' + ')}</span>
              <span className="text-[10px] text-slate-500 font-mono">{lt.count}</span>
            </div>
            <div className="h-2 bg-slate-800 rounded-full overflow-hidden">
              <motion.div
                className="h-full rounded-full relative overflow-hidden"
                style={{ backgroundColor: linkTypeColors[lt.link_type] || '#f59e0b' }}
                initial={{ width: 0 }}
                animate={{ width: `${(lt.count / maxCount) * 100}%` }}
                transition={{ duration: 0.6, delay: i * 0.05, ease: 'easeOut' }}
              >
                {/* Shimmer effect */}
                <motion.div
                  className="absolute inset-0 bg-gradient-to-r from-transparent via-white/20 to-transparent"
                  initial={{ x: '-100%' }}
                  animate={{ x: '100%' }}
                  transition={{ duration: 1.5, delay: 0.5 + i * 0.1, repeat: Infinity, repeatDelay: 3 }}
                />
              </motion.div>
            </div>
            <div className="text-[10px] text-slate-600 text-right mt-1">
              {((lt.avg_confidence || 0) * 100).toFixed(0)}% avg confidence
            </div>
          </motion.div>
        ))}
      </div>
    </div>
  );
};

export const CampaignView = ({ apiKey, onIncidentClick }) => {
  const { stats, loading: statsLoading } = useCampaignStats(apiKey);
  const { graph, loading: graphLoading } = useCampaignGraph(apiKey, 24);

  if (statsLoading && graphLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <motion.div 
            className="relative w-12 h-12 mx-auto mb-4"
            animate={{ rotate: 360 }}
            transition={{ duration: 2, repeat: Infinity, ease: 'linear' }}
          >
            <div className="absolute inset-0 rounded-full border-2 border-amber-500/20"/>
            <div className="absolute inset-0 rounded-full border-2 border-transparent border-t-amber-500"/>
          </motion.div>
          <p className="text-slate-400 text-sm">Analyzing campaign correlations...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <CampaignStats stats={stats} />

      <div className="grid grid-cols-1 xl:grid-cols-5 gap-4">
        <div className="xl:col-span-3">
          <CampaignGraph graph={graph} onNodeClick={onIncidentClick} />
        </div>
        <div className="xl:col-span-2 space-y-4">
          <TopEntities entities={stats?.top_shared_entities} />
          <LinkTypes linkTypes={stats?.link_types} />
        </div>
      </div>
    </div>
  );
};

export default CampaignView;
