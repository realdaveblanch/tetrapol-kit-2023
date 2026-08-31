#!/usr/bin/env python3
import os
import json
import time
import socket
from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import ThreadingMixIn
import urllib.parse
from datetime import datetime

DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>TETRAPOL Live SDR Dashboard & Multi-Device GPS Map</title>
    <!-- Leaflet CSS & JS -->
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <style>
        :root {
            --bg-dark: #0f172a;
            --bg-card: #1e293b;
            --border-card: #334155;
            --text-main: #f8fafc;
            --text-dim: #94a3b8;
            --accent-blue: #38bdf8;
            --accent-green: #22c55e;
            --accent-yellow: #eab308;
            --accent-red: #ef4444;
            --accent-purple: #a855f7;
        }
        * { box-sizing: border-box; margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }
        body { background-color: var(--bg-dark); color: var(--text-main); height: 100vh; display: flex; flex-direction: column; overflow: hidden; }
        
        /* Top Navigation Header */
        header {
            background-color: var(--bg-card);
            border-bottom: 1px solid var(--border-card);
            padding: 10px 20px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .header-title { display: flex; align-items: center; gap: 10px; font-size: 1.2rem; font-weight: 700; color: var(--accent-blue); }
        .header-stats { display: flex; gap: 15px; font-size: 0.85rem; }
        .stat-badge { background: #0f172a; padding: 4px 10px; border-radius: 6px; border: 1px solid var(--border-card); }
        .stat-badge span { color: var(--accent-green); font-weight: bold; }

        /* Main Workspace Grid */
        .main-container {
            display: grid;
            grid-template-columns: 360px 1fr 340px;
            height: calc(100vh - 54px);
            overflow: hidden;
        }

        /* Sidebars */
        .sidebar-left, .sidebar-right {
            background-color: var(--bg-card);
            border-right: 1px solid var(--border-card);
            display: flex;
            flex-direction: column;
            overflow: hidden;
        }
        .sidebar-right { border-right: none; border-left: 1px solid var(--border-card); }
        
        .panel-header {
            padding: 10px 14px;
            font-size: 0.85rem;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            color: var(--text-dim);
            border-bottom: 1px solid var(--border-card);
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .panel-content { flex: 1; overflow-y: auto; padding: 10px; display: flex; flex-direction: column; gap: 8px; }

        /* Channel Card */
        .ch-card {
            background: #0f172a;
            border: 1px solid var(--border-card);
            border-radius: 6px;
            padding: 8px 10px;
            display: flex;
            flex-direction: column;
            gap: 4px;
        }
        .ch-header { display: flex; justify-content: space-between; align-items: center; }
        .ch-freq { font-weight: bold; color: var(--accent-blue); font-size: 0.9rem; }
        .ch-badge { font-size: 0.7rem; padding: 2px 6px; border-radius: 4px; background: #334155; }
        .ch-meta { font-size: 0.75rem; color: var(--text-dim); display: flex; justify-content: space-between; }

        /* Call Item */
        .call-card {
            background: #0f172a;
            border: 1px solid var(--border-card);
            border-radius: 6px;
            padding: 8px;
            display: flex;
            flex-direction: column;
            gap: 4px;
        }
        .call-card.clear { border-left: 4px solid var(--accent-green); }
        .call-card.enc { border-left: 4px solid var(--accent-red); opacity: 0.8; }
        .call-title { font-size: 0.8rem; font-weight: 600; display: flex; justify-content: space-between; }
        audio { width: 100%; height: 28px; margin-top: 4px; }

        /* Map Container */
        #map { width: 100%; height: 100%; background: #0f172a; }

        /* GPS Emitter Item */
        .emitter-card {
            background: #0f172a;
            border: 1px solid var(--border-card);
            border-radius: 6px;
            padding: 8px 10px;
            cursor: pointer;
            transition: background 0.2s;
            display: flex;
            flex-direction: column;
            gap: 4px;
        }
        .emitter-card:hover { background: #1e293b; border-color: var(--accent-blue); }

        /* Log items */
        .event-item { font-size: 0.75rem; padding: 5px 8px; border-radius: 4px; background: #0f172a; border-left: 3px solid var(--border-card); line-height: 1.3; }
        .event-item.gps { border-left-color: var(--accent-green); }
        .event-item.otar { border-left-color: var(--accent-yellow); }
        .event-item.voice { border-left-color: var(--accent-blue); }

        /* Custom Div Icons */
        .custom-emitter-pin {
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-size: 10px;
            font-weight: bold;
            border-radius: 50%;
            border: 2px solid white;
            box-shadow: 0 0 10px rgba(0,0,0,0.5);
        }

        /* Scrollbar */
        ::-webkit-scrollbar { width: 6px; }
        ::-webkit-scrollbar-track { background: transparent; }
        ::-webkit-scrollbar-thumb { background: #334155; border-radius: 3px; }
    </style>
</head>
<body>
    <header>
        <div class="header-title">
            <span>📡 TETRAPOL Multi-Device GPS & SDR Station</span>
        </div>
        <div class="header-stats">
            <div class="stat-badge">Canales: <span id="stat-channels">0</span></div>
            <div class="stat-badge">Llamadas: <span id="stat-calls">0</span></div>
            <div class="stat-badge">Dispositivos GPS: <span id="stat-gps">0</span></div>
            <div class="stat-badge">OTAR / Seg: <span id="stat-otar">0</span></div>
        </div>
    </header>

    <div class="main-container">
        <!-- Left Sidebar: Channels & Audio Player -->
        <div class="sidebar-left">
            <div class="panel-header">
                <span>Portadoras Activas</span>
                <span id="stat-center-freq" style="font-size: 0.75rem; color: var(--accent-blue);"></span>
            </div>
            <div class="panel-content" id="channels-list" style="max-height: 40%;">
                <div style="color: var(--text-dim); font-size: 0.85rem; text-align: center; padding: 20px;">Cargando canales...</div>
            </div>
            <div class="panel-header">
                <span>Grabaciones de Voz</span>
            </div>
            <div class="panel-content" id="calls-list">
                <div style="color: var(--text-dim); font-size: 0.85rem; text-align: center; padding: 20px;">Esperando llamadas...</div>
            </div>
        </div>

        <!-- Center: Interactive Map -->
        <div style="position: relative;">
            <div id="map"></div>
        </div>

        <!-- Right Sidebar: GPS Emitters & Activity Log -->
        <div class="sidebar-right">
            <div class="panel-header">
                <span>Dispositivos GPS & Rutas</span>
                <span style="font-size: 0.75rem; color: var(--accent-green);">En Directo</span>
            </div>
            <div class="panel-content" id="gps-list" style="max-height: 45%;">
                <div style="color: var(--text-dim); font-size: 0.85rem; text-align: center; padding: 20px;">Esperando coordenadas de terminales...</div>
            </div>
            <div class="panel-header">
                <span>Registro de Eventos</span>
            </div>
            <div class="panel-content" id="events-list">
                <div style="color: var(--text-dim); font-size: 0.85rem; text-align: center; padding: 20px;">Iniciando escucha...</div>
            </div>
        </div>
    </div>

    <script>
        // 1. Inicializar Mapa Leaflet con vista predeterminada
        const map = L.map('map').setView([40.4168, -3.7038], 6);
        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            maxZoom: 19,
            attribution: '© OpenStreetMap'
        }).addTo(map);

        // Paleta de colores para múltiples dispositivos
        const DEVICE_COLORS = [
            "#22c55e", "#38bdf8", "#eab308", "#a855f7",
            "#ec4899", "#f97316", "#14b8a6", "#ef4444"
        ];

        function getDeviceColor(key) {
            let hash = 0;
            for (let i = 0; i < key.length; i++) {
                hash = key.charCodeAt(i) + ((hash << 5) - hash);
            }
            const index = Math.abs(hash) % DEVICE_COLORS.length;
            return DEVICE_COLORS[index];
        }

        const deviceMarkers = {};
        const devicePolylines = {};
        const deviceBreadcrumbs = {};
        let mapCentered = false;

        // 2. Función de actualización periódica (cada 1.5s)
        async function updateDashboard() {
            try {
                const res = await fetch('/api/data');
                const data = await res.json();

                // Actualizar Stats
                document.getElementById('stat-channels').textContent = data.channels.length;
                document.getElementById('stat-calls').textContent = data.total_calls;
                const emitterKeys = Object.keys(data.gps_emitters);
                document.getElementById('stat-gps').textContent = emitterKeys.length;
                document.getElementById('stat-otar').textContent = data.total_otar;
                if (data.center_freq) {
                    document.getElementById('stat-center-freq').textContent = (data.center_freq / 1e6).toFixed(4) + ' MHz';
                }

                // Render Canales
                const chContainer = document.getElementById('channels-list');
                chContainer.innerHTML = '';
                data.channels.forEach(ch => {
                    const el = document.createElement('div');
                    el.className = 'ch-card';
                    el.innerHTML = `
                        <div class="ch-header">
                            <span class="ch-freq">${(ch.freq / 1e6).toFixed(4)} MHz</span>
                            <span class="ch-badge">Canal #${ch.idx}</span>
                        </div>
                        <div class="ch-meta">
                            <span>Llamadas: <b>${ch.total_calls}</b></span>
                            <span>${ch.active_group ? 'TG: ' + ch.active_group : 'Reposo'}</span>
                        </div>
                    `;
                    chContainer.appendChild(el);
                });

                // Render Dispositivos GPS & Trazado de Rutas (Polylines + Breadcrumbs)
                const gpsContainer = document.getElementById('gps-list');
                
                if (emitterKeys.length > 0) {
                    gpsContainer.innerHTML = '';
                    emitterKeys.forEach(k => {
                        const em = data.gps_emitters[k];
                        const latLng = [em.lat, em.lon];
                        const devColor = getDeviceColor(k);
                        const devName = em.alias || em.terminal;
                        const history = em.history || [ [em.lat, em.lon, em.time] ];

                        // A. Crear o Actualizar Polilínea de Ruta
                        const polylinePoints = history.map(pt => [pt[0], pt[1]]);
                        if (!devicePolylines[k]) {
                            devicePolylines[k] = L.polyline(polylinePoints, {
                                color: devColor,
                                weight: 4,
                                opacity: 0.8,
                                dashArray: '6, 6'
                            }).addTo(map);
                        } else {
                            devicePolylines[k].setLatLngs(polylinePoints);
                        }

                        // B. Crear o Actualizar Marcador Principal (Última Posición)
                        const pinIcon = L.divIcon({
                            className: 'custom-emitter-pin',
                            html: `<div style='background-color:${devColor}; width:20px; height:20px; border-radius:50%; display:flex; align-items:center; justify-content:center; border:2px solid white; box-shadow:0 0 10px ${devColor};'>📍</div>`,
                            iconSize: [20, 20],
                            iconAnchor: [10, 10]
                        });

                        const popupHtml = `
                            <div style="font-family:sans-serif; min-width:180px;">
                                <div style="font-weight:bold; font-size:14px; color:${devColor}; margin-bottom:4px;">${devName}</div>
                                <div style="font-size:12px; color:#475569;"><b>ID Terminal:</b> ${em.terminal}</div>
                                <div style="font-size:12px; color:#475569;"><b>Coordenadas:</b> ${em.lat.toFixed(6)}°, ${em.lon.toFixed(6)}°</div>
                                <div style="font-size:12px; color:#475569;"><b>Puntos de ruta:</b> ${history.length}</div>
                                <div style="font-size:12px; color:#475569;"><b>Última señal:</b> ${em.time}</div>
                            </div>
                        `;

                        if (!deviceMarkers[k]) {
                            deviceMarkers[k] = L.marker(latLng, { icon: pinIcon }).addTo(map)
                                .bindPopup(popupHtml);
                        } else {
                            deviceMarkers[k].setLatLng(latLng).setPopupContent(popupHtml);
                        }

                        // C. Centrar mapa la primera vez que se detecta un emisor
                        if (!mapCentered) {
                            map.setView(latLng, 14);
                            mapCentered = true;
                        }

                        // D. Elemento en el Sidebar Derecho
                        const gCard = document.createElement('div');
                        gCard.className = 'emitter-card';
                        gCard.style.borderLeft = `4px solid ${devColor}`;
                        gCard.innerHTML = `
                            <div style="display:flex; justify-content:space-between; align-items:center;">
                                <span style="font-weight:bold; color:${devColor}; font-size:0.85rem;">${devName}</span>
                                <span style="font-size:0.7rem; color:var(--text-dim);">${history.length} pts</span>
                            </div>
                            <div style="font-size:0.75rem; color:var(--text-dim);">${em.lat.toFixed(6)}°, ${em.lon.toFixed(6)}°</div>
                            <div style="font-size:0.7rem; color:var(--text-dim); display:flex; justify-content:space-between;">
                                <span>${em.time}</span>
                                <span>${(em.freq/1e6).toFixed(4)} MHz</span>
                            </div>
                        `;
                        gCard.onclick = () => { 
                            map.setView(latLng, 16); 
                            deviceMarkers[k].openPopup(); 
                        };
                        gpsContainer.appendChild(gCard);
                    });
                }

                // Render Llamadas de Audio
                const callsContainer = document.getElementById('calls-list');
                if (data.recent_calls && data.recent_calls.length > 0) {
                    callsContainer.innerHTML = '';
                    data.recent_calls.slice(-10).reverse().forEach(c => {
                        const cCard = document.createElement('div');
                        cCard.className = 'call-card ' + (c.is_clear ? 'clear' : 'enc');
                        cCard.innerHTML = `
                            <div class="call-title">
                                <span>${(c.freq / 1e6).toFixed(4)} MHz ${c.group ? '• ' + c.group : ''}</span>
                                <span style="color: ${c.is_clear ? 'var(--accent-green)' : 'var(--accent-red)'}">
                                    ${c.is_clear ? 'EN CLARO' : 'CIFRADA'}
                                </span>
                            </div>
                            <div style="font-size:0.75rem; color:var(--text-dim); display:flex; justify-content:space-between;">
                                <span>${c.time} (${c.duration.toFixed(1)}s)</span>
                                <span>Entropía: ${c.entropy.toFixed(2)}</span>
                            </div>
                            ${c.wav_url ? `<audio controls src="${c.wav_url}" preload="none"></audio>` : ''}
                        `;
                        callsContainer.appendChild(cCard);
                    });
                }

                // Render Eventos
                const evContainer = document.getElementById('events-list');
                if (data.events && data.events.length > 0) {
                    evContainer.innerHTML = '';
                    data.events.slice(-15).reverse().forEach(ev => {
                        const evEl = document.createElement('div');
                        evEl.className = 'event-item ' + ev.type;
                        evEl.innerHTML = `<b>[${ev.time}]</b> ${ev.text}`;
                        evContainer.appendChild(evEl);
                    });
                }

            } catch (e) {
                console.error("Error actualizando dashboard:", e);
            }
        }

        setInterval(updateDashboard, 1500);
        updateDashboard();
    </script>
</body>
</html>
"""

class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    daemon_threads = True
    allow_reuse_address = True

class DashboardHandler(BaseHTTPRequestHandler):
    data_provider = None

    def log_message(self, format, *args):
        return

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        if path == "/" or path == "/index.html":
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(DASHBOARD_HTML.encode("utf-8"))
            return

        if path == "/api/data":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            data = DashboardHandler.data_provider() if DashboardHandler.data_provider else {}
            self.wfile.write(json.dumps(data).encode("utf-8"))
            return

        if path.startswith("/audio/"):
            filename = os.path.basename(path[7:])
            filepath = os.path.join("demod/tmp/live", filename)
            if os.path.exists(filepath) and filepath.endswith(".wav"):
                self.send_response(200)
                self.send_header("Content-Type", "audio/wav")
                self.send_header("Content-Length", str(os.path.getsize(filepath)))
                self.end_headers()
                with open(filepath, "rb") as f:
                    self.wfile.write(f.read())
                return
            else:
                self.send_response(404)
                self.end_headers()
                return

        self.send_response(404)
        self.end_headers()

def start_web_dashboard(port=8080, data_callback=None):
    DashboardHandler.data_provider = data_callback
    server = ThreadedHTTPServer(("0.0.0.0", port), DashboardHandler)
    return server
