// ============================================================================
// HORNET Dashboard - API Integration Hooks
// Connects to your FastAPI backend at hornet/api/routes/
// ============================================================================

import { useState, useEffect, useCallback, useRef } from 'react';

// Configuration - update these for your environment
const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';
const WS_BASE = import.meta.env.VITE_WS_URL || 'ws://localhost:8000';

// ============================================================================
// Auth Hook - matches your X-API-Key header pattern
// ============================================================================
export function useAuth() {
  const [apiKey, setApiKey] = useState(() => localStorage.getItem('hornet_api_key'));
  const [isAuthenticated, setIsAuthenticated] = useState(!!apiKey);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const login = useCallback(async (key) => {
    setLoading(true);
    setError(null);
    
    try {
      // Validate key against health endpoint
      const res = await fetch(`${API_BASE}/api/v1/health`, {
        headers: { 'X-API-Key': key }
      });
      
      if (res.ok) {
        localStorage.setItem('hornet_api_key', key);
        setApiKey(key);
        setIsAuthenticated(true);
        return true;
      } else {
        throw new Error('Invalid API key');
      }
    } catch (err) {
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

  const getHeaders = useCallback(() => ({
    'Content-Type': 'application/json',
    'X-API-Key': apiKey || '',
  }), [apiKey]);

  return { apiKey, isAuthenticated, loading, error, login, logout, getHeaders };
}

// ============================================================================
// Incidents Hook - fetches from /api/v1/incidents
// ============================================================================
export function useIncidents(options = {}) {
  const { state, severity, limit = 50, offset = 0, autoRefresh = 5000 } = options;
  const { getHeaders, isAuthenticated } = useAuth();
  
  const [incidents, setIncidents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [meta, setMeta] = useState({ total: 0 });

  const fetchIncidents = useCallback(async () => {
    if (!isAuthenticated) return;
    
    try {
      const params = new URLSearchParams();
      if (state) params.append('state', state);
      if (severity) params.append('severity', severity);
      params.append('limit', limit.toString());
      params.append('offset', offset.toString());
      
      const res = await fetch(
        `${API_BASE}/api/v1/incidents?${params}`,
        { headers: getHeaders() }
      );
      
      if (!res.ok) throw new Error('Failed to fetch incidents');
      
      const data = await res.json();
      setIncidents(data.data || []);
      setMeta(data.meta || { total: 0 });
      setError(null);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [isAuthenticated, state, severity, limit, offset, getHeaders]);

  useEffect(() => {
    fetchIncidents();
    
    if (autoRefresh > 0) {
      const interval = setInterval(fetchIncidents, autoRefresh);
      return () => clearInterval(interval);
    }
  }, [fetchIncidents, autoRefresh]);

  return { incidents, loading, error, meta, refetch: fetchIncidents };
}

// ============================================================================
// Single Incident Hook - fetches from /api/v1/incidents/{id}
// ============================================================================
export function useIncident(incidentId) {
  const { getHeaders, isAuthenticated } = useAuth();
  
  const [incident, setIncident] = useState(null);
  const [findings, setFindings] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchIncident = useCallback(async () => {
    if (!isAuthenticated || !incidentId) return;
    
    try {
      const res = await fetch(
        `${API_BASE}/api/v1/incidents/${incidentId}`,
        { headers: getHeaders() }
      );
      
      if (!res.ok) throw new Error('Incident not found');
      
      const data = await res.json();
      setIncident(data);
      setFindings(data.findings || []);
      setError(null);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [isAuthenticated, incidentId, getHeaders]);

  useEffect(() => {
    fetchIncident();
  }, [fetchIncident]);

  return { incident, findings, loading, error, refetch: fetchIncident };
}

// ============================================================================
// Recent Findings Hook - fetches from /api/v1/incidents/findings/recent
// ============================================================================
export function useRecentFindings(limit = 10) {
  const { getHeaders, isAuthenticated } = useAuth();
  
  const [findings, setFindings] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!isAuthenticated) return;
    
    const fetchFindings = async () => {
      try {
        const res = await fetch(
          `${API_BASE}/api/v1/incidents/findings/recent?limit=${limit}`,
          { headers: getHeaders() }
        );
        if (res.ok) {
          const data = await res.json();
          setFindings(data);
        }
      } catch (err) {
        console.error('Failed to fetch recent findings:', err);
      } finally {
        setLoading(false);
      }
    };
    
    fetchFindings();
    const interval = setInterval(fetchFindings, 10000);
    return () => clearInterval(interval);
  }, [isAuthenticated, limit, getHeaders]);

  return { findings, loading };
}

// ============================================================================
// Stats Hook - aggregates data for dashboard cards
// ============================================================================
export function useStats() {
  const { incidents } = useIncidents({ limit: 100, autoRefresh: 5000 });
  
  const stats = {
    active: incidents.filter(i => !['CLOSED', 'ERROR'].includes(i.state)).length,
    closed: incidents.filter(i => i.state === 'CLOSED').length,
    errors: incidents.filter(i => i.state === 'ERROR').length,
    total: incidents.length,
    autoResolveRate: incidents.length > 0 
      ? Math.round((incidents.filter(i => i.state === 'CLOSED' && i.outcome === 'auto_resolved').length / incidents.length) * 100)
      : 0,
    avgConfidence: incidents.length > 0
      ? Math.round(incidents.reduce((sum, i) => sum + (i.confidence || 0), 0) / incidents.length)
      : 0,
    totalTokens: incidents.reduce((sum, i) => sum + (i.tokens_used || 0), 0),
  };

  // Calculate severity breakdown
  stats.bySeverity = {
    critical: incidents.filter(i => i.severity === 'CRITICAL').length,
    high: incidents.filter(i => i.severity === 'HIGH').length,
    medium: incidents.filter(i => i.severity === 'MEDIUM').length,
    low: incidents.filter(i => i.severity === 'LOW').length,
  };

  // Calculate state breakdown
  stats.byState = {
    detection: incidents.filter(i => i.state === 'DETECTION').length,
    enrichment: incidents.filter(i => i.state === 'ENRICHMENT').length,
    analysis: incidents.filter(i => i.state === 'ANALYSIS').length,
    proposal: incidents.filter(i => i.state === 'PROPOSAL').length,
    oversight: incidents.filter(i => i.state === 'OVERSIGHT').length,
    execution: incidents.filter(i => i.state === 'EXECUTION').length,
    closed: incidents.filter(i => i.state === 'CLOSED').length,
    error: incidents.filter(i => i.state === 'ERROR').length,
  };

  return stats;
}

// ============================================================================
// WebSocket Hook - real-time incident updates
// ============================================================================
export function useWebSocket(onMessage) {
  const { apiKey, isAuthenticated } = useAuth();
  const wsRef = useRef(null);
  const [connected, setConnected] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!isAuthenticated) return;

    const connect = () => {
      try {
        wsRef.current = new WebSocket(`${WS_BASE}/ws/incidents?api_key=${apiKey}`);
        
        wsRef.current.onopen = () => {
          setConnected(true);
          setError(null);
          console.log('WebSocket connected');
        };
        
        wsRef.current.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data);
            onMessage?.(data);
          } catch (err) {
            console.error('Failed to parse WebSocket message:', err);
          }
        };
        
        wsRef.current.onerror = (err) => {
          setError('WebSocket error');
          console.error('WebSocket error:', err);
        };
        
        wsRef.current.onclose = () => {
          setConnected(false);
          // Reconnect after 3 seconds
          setTimeout(connect, 3000);
        };
      } catch (err) {
        setError(err.message);
      }
    };

    connect();

    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, [isAuthenticated, apiKey, onMessage]);

  return { connected, error };
}

// ============================================================================
// Health Check Hook - monitors system status
// ============================================================================
export function useHealth() {
  const { getHeaders, isAuthenticated } = useAuth();
  
  const [health, setHealth] = useState({
    redis: 'unknown',
    postgres: 'unknown',
    workers: 0,
    anthropic: 'unknown',
  });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!isAuthenticated) return;
    
    const checkHealth = async () => {
      try {
        const res = await fetch(`${API_BASE}/api/v1/health`, {
          headers: getHeaders()
        });
        
        if (res.ok) {
          const data = await res.json();
          setHealth({
            redis: data.redis || 'connected',
            postgres: data.database || 'connected',
            workers: data.workers || 3,
            anthropic: data.anthropic || 'connected',
          });
        }
      } catch (err) {
        console.error('Health check failed:', err);
      } finally {
        setLoading(false);
      }
    };
    
    checkHealth();
    const interval = setInterval(checkHealth, 30000);
    return () => clearInterval(interval);
  }, [isAuthenticated, getHeaders]);

  return { health, loading };
}

// ============================================================================
// Action Hook - submit human decisions on incidents
// ============================================================================
export function useIncidentAction() {
  const { getHeaders, isAuthenticated } = useAuth();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const submitAction = useCallback(async (incidentId, action, justification = '', modifications = null) => {
    if (!isAuthenticated) return { success: false, error: 'Not authenticated' };
    
    setLoading(true);
    setError(null);
    
    try {
      const res = await fetch(
        `${API_BASE}/api/v1/incidents/${incidentId}/action`,
        {
          method: 'POST',
          headers: getHeaders(),
          body: JSON.stringify({
            response_type: action, // APPROVE | REJECT | MODIFY
            justification,
            modifications,
          }),
        }
      );
      
      if (!res.ok) throw new Error('Failed to submit action');
      
      const data = await res.json();
      return { success: true, data };
    } catch (err) {
      setError(err.message);
      return { success: false, error: err.message };
    } finally {
      setLoading(false);
    }
  }, [isAuthenticated, getHeaders]);

  return { submitAction, loading, error };
}

// ============================================================================
// Events Hook - submit new events for processing
// ============================================================================
export function useEventSubmit() {
  const { getHeaders, isAuthenticated } = useAuth();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const submitEvent = useCallback(async (event) => {
    if (!isAuthenticated) return { success: false, error: 'Not authenticated' };
    
    setLoading(true);
    setError(null);
    
    try {
      const res = await fetch(
        `${API_BASE}/api/v1/events`,
        {
          method: 'POST',
          headers: getHeaders(),
          body: JSON.stringify(event),
        }
      );
      
      if (!res.ok) throw new Error('Failed to submit event');
      
      const data = await res.json();
      return { success: true, data };
    } catch (err) {
      setError(err.message);
      return { success: false, error: err.message };
    } finally {
      setLoading(false);
    }
  }, [isAuthenticated, getHeaders]);

  return { submitEvent, loading, error };
}
