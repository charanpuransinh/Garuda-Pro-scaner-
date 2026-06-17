// server.js — Garuda Power WebSocket Server
// Node.js + Express + WebSocket

const express    = require('express');
const http       = require('http');
const WebSocket  = require('ws');
const { exec }   = require('child_process');
const path       = require('path');
const fs         = require('fs');

const app    = express();
const server = http.createServer(app);
const wss    = new WebSocket.Server({ server });

const PORT = process.env.PORT || 3000;

// ══════════════════════════════════════════
// SERVE FRONTEND FILES
// ══════════════════════════════════════════
app.use(express.static(path.join(__dirname, '../frontend')));
app.use(express.json());

// Homepage = master panel
app.get('/', (req, res) => {
  res.sendFile(path.join(__dirname, '../frontend/master-panel.html'));
});

// ══════════════════════════════════════════
// WEBSOCKET — सभी clients को data भेजो
// ══════════════════════════════════════════
let latestData = {};   // Last scan results store here
let clients    = new Set();

wss.on('connection', (ws) => {
  clients.add(ws);
  console.log(`🔌 Client connected — Total: ${clients.size}`);

  // Naye client ko turant latest data do
  if (Object.keys(latestData).length > 0) {
    ws.send(JSON.stringify({ type: 'FULL_UPDATE', data: latestData }));
  }

  ws.on('close', () => {
    clients.delete(ws);
    console.log(`❌ Client disconnected — Total: ${clients.size}`);
  });

  ws.on('message', (msg) => {
    try {
      const parsed = JSON.parse(msg);
      if (parsed.type === 'REQUEST_SCAN') {
        triggerScan(parsed.symbol || 'RELIANCE');
      }
    } catch(e) {}
  });
});

// Broadcast to all connected clients
function broadcast(data) {
  const msg = JSON.stringify(data);
  clients.forEach(ws => {
    if (ws.readyState === WebSocket.OPEN) {
      ws.send(msg);
    }
  });
}

// ══════════════════════════════════════════
// SCAN TRIGGER — Python scanner chalao
// ══════════════════════════════════════════
function triggerScan(symbol = 'RELIANCE') {
  console.log(`🔍 Scanning: ${symbol}`);
  broadcast({ type: 'SCAN_START', symbol });

  const cmd = `python3 ${path.join(__dirname, 'run_scanners.py')} ${symbol}`;

  exec(cmd, { timeout: 60000 }, (error, stdout, stderr) => {
    if (error) {
      console.error(`❌ Scanner Error: ${error.message}`);
      broadcast({ type: 'SCAN_ERROR', error: error.message });
      return;
    }

    try {
      const results = JSON.parse(stdout);
      latestData = results;
      broadcast({ type: 'SCAN_RESULT', data: results, timestamp: new Date().toISOString() });
      console.log(`✅ Scan complete — ${Object.keys(results).length} scanners`);
    } catch(e) {
      console.error('❌ Parse Error:', stderr || stdout);
      broadcast({ type: 'SCAN_ERROR', error: 'Parse failed' });
    }
  });
}

// ══════════════════════════════════════════
// REST API ENDPOINTS
// ══════════════════════════════════════════
app.get('/api/status', (req, res) => {
  res.json({
    status: 'online',
    clients: clients.size,
    lastScan: latestData.timestamp || null,
    scanners: Object.keys(latestData).length
  });
});

app.post('/api/scan', (req, res) => {
  const symbol = req.body.symbol || 'RELIANCE';
  triggerScan(symbol);
  res.json({ status: 'triggered', symbol });
});

app.get('/api/results', (req, res) => {
  res.json(latestData);
});

// ══════════════════════════════════════════
// AUTO SCAN — हर 5 मिनट में automatic
// ══════════════════════════════════════════
const DEFAULT_SYMBOLS = [
  'RELIANCE', 'TCS', 'INFY', 'HDFCBANK',
  'ICICIBANK', 'SBIN', 'WIPRO', 'AXISBANK'
];

let symbolIndex = 0;

setInterval(() => {
  const sym = DEFAULT_SYMBOLS[symbolIndex % DEFAULT_SYMBOLS.length];
  symbolIndex++;
  triggerScan(sym);
}, 5 * 60 * 1000); // 5 minutes

// ══════════════════════════════════════════
// START SERVER
// ══════════════════════════════════════════
server.listen(PORT, () => {
  console.log(`\n🦅 GARUDA POWER SERVER STARTED`);
  console.log(`📡 Port: ${PORT}`);
  console.log(`🌐 URL: http://localhost:${PORT}`);
  console.log(`⏰ Auto-scan: every 5 minutes\n`);

  // First scan on startup
  setTimeout(() => triggerScan('RELIANCE'), 3000);
});
