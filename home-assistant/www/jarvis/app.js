(function () {
  'use strict';

  // --- Configuration & Defaults ---
  const config = {
    satelliteEntity: 'assist_satellite.homelab_05_satellite_assist_satellite',
    muteEntity: 'switch.homelab_05_satellite_mute',
    mediaPlayerEntity: 'media_player.homelab_05_satellite_media_player',
    host: location.host,
    token: null
  };

  // State
  let currentState = 'idle';
  let ws = null;
  let msgId = 1;
  let reconnectTimer = null;
  let reconnectAttempts = 0;
  let blinkTimer = null;
  let glanceTimer = null;
  let isBlinking = false;
  let lastEntityStates = {};

  // DOM Elements
  const appEl = document.getElementById('app');
  const eyesEl = document.getElementById('eyes');
  const statusLabel = document.getElementById('status-text');
  const connectionBadge = document.getElementById('connection-badge');
  const promptModal = document.getElementById('token-prompt');
  const tokenInput = document.getElementById('token-input');
  const tokenSubmit = document.getElementById('token-submit');

  // --- Parse URL Parameters ---
  const urlParams = new URLSearchParams(window.location.search);
  if (urlParams.get('entity')) config.satelliteEntity = urlParams.get('entity');
  if (urlParams.get('mute')) config.muteEntity = urlParams.get('mute');
  if (urlParams.get('media')) config.mediaPlayerEntity = urlParams.get('media');
  if (urlParams.get('token')) config.token = urlParams.get('token');

  // Per-state face colors, overridden by config.json when present
  const faceColors = {};

  // Load external config.json if available
  fetch('config.json')
    .then(res => res.json())
    .then(data => {
      if (data.satellite_entity && !urlParams.get('entity')) config.satelliteEntity = data.satellite_entity;
      if (data.mute_entity && !urlParams.get('mute')) config.muteEntity = data.mute_entity;
      if (data.media_player_entity && !urlParams.get('media')) config.mediaPlayerEntity = data.media_player_entity;
      for (const state of ['idle', 'listening', 'processing', 'responding', 'muted']) {
        if (data['face_color_' + state]) faceColors[state] = data['face_color_' + state];
      }
      // Re-apply the current state so configured colors take effect
      const s = currentState;
      currentState = '';
      setState(s, statusLabel ? statusLabel.textContent : undefined);
    })
    .catch(() => {});

  // --- Token Resolution ---
  function resolveToken() {
    if (config.token) return config.token;

    // 1. Check dedicated Jarvis storage
    const savedToken = localStorage.getItem('jarvis_token');
    if (savedToken) return savedToken;

    // 2. Check Home Assistant default localStorage token (if not expired)
    try {
      const hassTokens = JSON.parse(localStorage.getItem('hassTokens'));
      if (hassTokens && hassTokens.access_token) {
        if (!hassTokens.expires || hassTokens.expires > Date.now()) {
          return hassTokens.access_token;
        }
      }
    } catch (e) {}

    return null;
  }

  // --- State & Expressions ---
  function setState(newState, customLabel) {
    if (currentState === newState && !customLabel) return;
    currentState = newState;

    // Remove existing state classes
    appEl.classList.remove('state-idle', 'state-listening', 'state-processing', 'state-responding', 'state-muted');
    appEl.classList.add('state-' + newState);
    appEl.style.removeProperty('--eye-scale-y');
    appEl.style.removeProperty('--eye-scale-x');
    appEl.style.removeProperty('--primary-color');
    appEl.style.removeProperty('--eye-bg');

    // Apply configured face color for this state when present
    if (faceColors[newState]) {
      appEl.style.setProperty('--primary-color', faceColors[newState]);
      appEl.style.setProperty('--eye-bg', faceColors[newState]);
    }

    // Update status text
    const label = customLabel || (
      newState === 'idle' ? 'JARVIS // IDLE' :
      newState === 'listening' ? 'JARVIS // LISTENING' :
      newState === 'processing' ? 'JARVIS // THINKING' :
      newState === 'responding' ? 'JARVIS // RESPONDING' :
      newState === 'muted' ? 'JARVIS // MUTED' : 'JARVIS'
    );
    if (statusLabel) statusLabel.textContent = label;

    // Reset gaze when leaving idle
    if (newState !== 'idle') {
      eyesEl.style.setProperty('--gaze-x', '0px');
      eyesEl.style.setProperty('--gaze-y', '0px');
    }
  }

  // --- Natural Blinking Engine ---
  function scheduleNextBlink() {
    clearTimeout(blinkTimer);
    if (currentState === 'muted') return; // No blinking while asleep

    // Blinks every 3.2 - 6.5 seconds when idle
    const delay = Math.random() * 3300 + 3200;
    blinkTimer = setTimeout(() => {
      performBlink(() => {
        // 15% chance of quick double-blink
        if (Math.random() < 0.15 && currentState === 'idle') {
          setTimeout(() => performBlink(scheduleNextBlink), 120);
        } else {
          scheduleNextBlink();
        }
      });
    }, delay);
  }

  function performBlink(callback) {
    if (isBlinking || currentState === 'muted') {
      if (callback) callback();
      return;
    }
    isBlinking = true;
    appEl.style.setProperty('--eye-scale-y', '0.04');

    setTimeout(() => {
      appEl.style.removeProperty('--eye-scale-y');
      isBlinking = false;
      if (callback) callback();
    }, 110);
  }

  // --- Subtle Glance / Gaze Tracking ---
  function scheduleNextGlance() {
    clearTimeout(glanceTimer);
    if (currentState !== 'idle') return;

    const delay = Math.random() * 4000 + 3500;
    glanceTimer = setTimeout(() => {
      if (currentState === 'idle' && !isBlinking) {
        // Pick subtle glance offsets
        const glances = [
          { x: -14, y: 0 },
          { x: 14, y: 0 },
          { x: -10, y: -6 },
          { x: 10, y: -6 },
          { x: 0, y: 0 }
        ];
        const chosen = glances[Math.floor(Math.random() * glances.length)];
        eyesEl.style.setProperty('--gaze-x', chosen.x + 'px');
        eyesEl.style.setProperty('--gaze-y', chosen.y + 'px');

        // Look back forward after 1.4s
        setTimeout(() => {
          if (currentState === 'idle') {
            eyesEl.style.setProperty('--gaze-x', '0px');
            eyesEl.style.setProperty('--gaze-y', '0px');
          }
        }, 1400);
      }
      scheduleNextGlance();
    }, delay);
  }

  // --- WebSocket Connection ---
  function connectWebSocket() {
    const token = resolveToken();
    if (!token) {
      showTokenPrompt();
      return;
    }

    const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${config.host}/api/websocket`;

    try {
      ws = new WebSocket(wsUrl);
    } catch (e) {
      handleDisconnect();
      return;
    }

    ws.onopen = function () {
      reconnectAttempts = 0;
    };

    ws.onmessage = function (event) {
      let data;
      try {
        data = JSON.parse(event.data);
      } catch (e) {
        return;
      }

      if (data.type === 'auth_required') {
        ws.send(JSON.stringify({
          type: 'auth',
          access_token: token
        }));
      } else if (data.type === 'auth_ok') {
        if (connectionBadge) connectionBadge.classList.remove('visible');
        if (promptModal) promptModal.style.display = 'none';

        // 1. Fetch initial states
        ws.send(JSON.stringify({
          id: ++msgId,
          type: 'get_states'
        }));

        // 2. Subscribe to live state change events
        ws.send(JSON.stringify({
          id: ++msgId,
          type: 'subscribe_events',
          event_type: 'state_changed'
        }));
      } else if (data.type === 'auth_invalid') {
        localStorage.removeItem('jarvis_token');
        showTokenPrompt('Authentication failed. Please verify your token.');
      } else if (data.type === 'result' && Array.isArray(data.result)) {
        // Initial states payload
        data.result.forEach(s => {
          lastEntityStates[s.entity_id] = s;
        });
        evaluateEntities();
      } else if (data.type === 'event' && data.event && data.event.event_type === 'state_changed') {
        const evData = data.event.data;
        if (!evData || !evData.entity_id) return;
        lastEntityStates[evData.entity_id] = evData.new_state;
        if (evData.entity_id === config.satelliteEntity ||
            evData.entity_id === config.muteEntity ||
            evData.entity_id === config.mediaPlayerEntity) {
          evaluateEntities();
        }
      }
    };

    ws.onerror = function () {
      handleDisconnect();
    };

    ws.onclose = function () {
      handleDisconnect();
    };
  }

  function handleDisconnect() {
    if (connectionBadge) connectionBadge.classList.add('visible');
    clearTimeout(reconnectTimer);
    reconnectAttempts++;
    const backoff = Math.min(1000 * Math.pow(1.5, reconnectAttempts), 5000);
    reconnectTimer = setTimeout(connectWebSocket, backoff);
  }

  // --- Evaluate Entities to State ---
  function evaluateEntities() {
    const muteState = lastEntityStates[config.muteEntity];
    const satelliteState = lastEntityStates[config.satelliteEntity];
    const mediaState = lastEntityStates[config.mediaPlayerEntity];

    // Priority 1: Mute switch
    if (muteState && muteState.state === 'on') {
      setState('muted', 'JARVIS // MUTED');
      return;
    }

    // Priority 2: Satellite state (listening, processing, responding, idle)
    if (satelliteState) {
      const st = (satelliteState.state || '').toLowerCase();
      if (st === 'listening') {
        setState('listening', 'JARVIS // LISTENING');
        return;
      }
      if (st === 'processing') {
        setState('processing', 'JARVIS // THINKING');
        return;
      }
      if (st === 'responding') {
        setState('responding', 'JARVIS // SPEAKING');
        return;
      }
    }

    // Priority 3: Media player active during assist
    if (mediaState && mediaState.state === 'playing') {
      setState('responding', 'JARVIS // SPEAKING');
      return;
    }

    // Default: Idle
    setState('idle', 'JARVIS // IDLE');
  }

  // --- Token Prompt UI ---
  function showTokenPrompt(errMsg) {
    if (!promptModal) return;
    promptModal.style.display = 'flex';
    const errEl = document.getElementById('token-error');
    if (errEl) {
      errEl.textContent = errMsg || '';
      errEl.style.display = errMsg ? 'block' : 'none';
    }
  }

  if (tokenSubmit && tokenInput) {
    tokenSubmit.addEventListener('click', () => {
      const val = tokenInput.value.trim();
      if (val) {
        localStorage.setItem('jarvis_token', val);
        config.token = val;
        promptModal.style.display = 'none';
        connectWebSocket();
      }
    });
    tokenInput.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') tokenSubmit.click();
    });
  }

  // --- Interactive Debug / Testing Keys ---
  const states = ['idle', 'listening', 'processing', 'responding', 'muted'];
  let stateIndex = 0;

  // Click on screen to cycle state for instant visual testing
  appEl.addEventListener('click', (e) => {
    if (promptModal && promptModal.contains(e.target)) return;
    stateIndex = (stateIndex + 1) % states.length;
    setState(states[stateIndex]);
  });

  // Keyboard shortcuts
  window.addEventListener('keydown', (e) => {
    if (promptModal && promptModal.style.display === 'flex') return;
    switch (e.key) {
      case '1': setState('idle'); break;
      case '2': setState('listening'); break;
      case '3': setState('processing'); break;
      case '4': setState('responding'); break;
      case '5': setState('muted'); break;
      case 'f':
      case 'F':
        if (!document.fullscreenElement) {
          document.documentElement.requestFullscreen().catch(() => {});
        } else {
          document.exitFullscreen().catch(() => {});
        }
        break;
    }
  });

  // Expose global controller for scripting/testing
  window.Jarvis = {
    setState: setState,
    getState: () => currentState,
    getWs: () => ws,
    getLastStates: () => lastEntityStates,
    config: config
  };

  // --- Initialize ---
  setState('idle');
  scheduleNextBlink();
  scheduleNextGlance();
  connectWebSocket();

})();
