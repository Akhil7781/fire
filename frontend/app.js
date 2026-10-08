// DS08 Operational Thermal Source Monitor - Client Application
// Real NASA FIRMS NRT Ingestion, Geoapify GIS Proximity & Frozen Attribution Model

let map;
let markerLayerGroup;
let selectedProximityGroup;
let currentTileLayer;
const eventMarkers = new Map(); // Map<eventId, L.circleMarker>
let currentEvents = []; // Cached array of current event features
let selectedEventId = null;
let lastKnownPollTime = null;
let lastKnownEventCount = -1;
let statusPollingTimer = null;

const CLASS_COLORS = {
  "Industrial Fire": "#ef4444",
  "Forest Fire": "#10b981",
  "Agricultural Fire": "#f59e0b",
  "Other / Persistent Thermal Source": "#8b5cf6"
};

const CLASS_BADGE_CLASSES = {
  "Industrial Fire": "badge-ind",
  "Forest Fire": "badge-for",
  "Agricultural Fire": "badge-agr",
  "Other / Persistent Thermal Source": "badge-per"
};

// =========================================================================
// Initialization
// =========================================================================
document.addEventListener("DOMContentLoaded", () => {
  initMap();
  initTopBarControls();
  initFeedFilterEvents();
  initDetailEvents();
  initModalEvents();

  // Initial data load
  fetchInitialData();
  startStatusPolling();
});

// =========================================================================
// 1. Leaflet Map Initialization
// =========================================================================
async function initMap() {
  map = L.map("map", {
    center: [22.5, 79.0], // Center of India
    zoom: 5,
    zoomControl: true,
    preferCanvas: true
  });

  markerLayerGroup = L.layerGroup().addTo(map);
  selectedProximityGroup = L.layerGroup().addTo(map);

  let tileUrl = "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png";
  let tileAttribution = 'Powered by Geoapify | &copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors';

  try {
    const res = await fetch("/live/config");
    if (res.ok) {
      const cfg = await res.json();
      if (cfg.tile_url) tileUrl = cfg.tile_url;
      if (cfg.tile_attribution) tileAttribution = cfg.tile_attribution;
    }
  } catch (err) {
    console.warn("Could not fetch /live/config, falling back to OSM tiles:", err);
  }

  currentTileLayer = L.tileLayer(tileUrl, {
    attribution: tileAttribution,
    maxZoom: 19,
    subdomains: ['a', 'b', 'c']
  });

  // Graceful fallback to OpenStreetMap if Geoapify tile error occurs
  currentTileLayer.on("tileerror", function (error, tile) {
    if (tileUrl.includes("geoapify")) {
      console.warn("Geoapify tile load issue, switching to OpenStreetMap basemap fallback.");
      map.removeLayer(currentTileLayer);
      currentTileLayer = L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
        attribution: '&copy; OpenStreetMap contributors',
        maxZoom: 19
      }).addTo(map);
    }
  });

  currentTileLayer.addTo(map);
}

// =========================================================================
// 2. Differential Live Status & Events Ingestion
// =========================================================================
async function fetchInitialData() {
  await fetchLiveStatus();
  await refreshGeoJsonEvents(true);
}

function startStatusPolling() {
  if (statusPollingTimer) clearInterval(statusPollingTimer);
  // Poll lightweight /live/status every 7 seconds
  statusPollingTimer = setInterval(async () => {
    await fetchLiveStatus();
  }, 7000);
}

async function fetchLiveStatus() {
  try {
    const res = await fetch("/live/status");
    if (!res.ok) return;
    const s = await res.json();

    // Mode dot & text
    const liveDot = document.getElementById("live-dot");
    const modeText = document.getElementById("live-mode-text");
    if (liveDot && modeText) {
      if (s.firms_connection_status === "CONNECTED" && !s.last_error) {
        liveDot.className = "status-dot green pulse";
        modeText.textContent = "LIVE NRT";
      } else if (s.firms_connection_status === "DEGRADED") {
        liveDot.className = "status-dot yellow pulse";
        modeText.textContent = "DEGRADED";
      } else {
        liveDot.className = "status-dot red";
        modeText.textContent = "ERROR";
      }
    }

    // FIRMS status text & last poll time
    const connEl = document.getElementById("firms-conn-text");
    if (connEl) {
      connEl.textContent = s.firms_connection_status === "CONNECTED" ? "Connected" : (s.firms_connection_status || "Connecting");
      connEl.className = `firms-val ${s.firms_connection_status === "CONNECTED" ? "connected" : ""}`;
    }

    const pollTimeEl = document.getElementById("last-poll-time");
    if (pollTimeEl && s.last_poll_time_utc) {
      const d = new Date(s.last_poll_time_utc);
      const timeStr = isNaN(d.getTime()) ? s.last_poll_time_utc : d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }) + " UTC";
      pollTimeEl.textContent = `(${timeStr})`;
    }

    // Counts
    const statActive = document.getElementById("stat-active-events");
    if (statActive) statActive.textContent = s.active_events_count !== undefined ? s.active_events_count : (s.total_events || 0);

    const statClassified = document.getElementById("stat-classified-events");
    if (statClassified) statClassified.textContent = s.classified_events_count !== undefined ? s.classified_events_count : (s.total_events || 0);

    // Differential trigger: only refresh events if count or timestamp changed
    const currentCount = s.active_events_count !== undefined ? s.active_events_count : (s.total_events || 0);
    const pollTime = s.last_poll_time_utc;

    if (currentCount !== lastKnownEventCount || (pollTime && pollTime !== lastKnownPollTime)) {
      lastKnownEventCount = currentCount;
      lastKnownPollTime = pollTime;
      await refreshGeoJsonEvents(false);
    }
  } catch (err) {
    console.warn("Could not query /live/status:", err);
  }
}

// =========================================================================
// 3. Differential Marker Management (No Full Re-renders)
// =========================================================================
async function refreshGeoJsonEvents(fitBoundsIfFirst = false) {
  const classFilter = document.getElementById("feed-class-filter") ? document.getElementById("feed-class-filter").value : "";
  let url = "/api/geojson";
  if (classFilter) {
    url += `?class_filter=${encodeURIComponent(classFilter)}`;
  }

  try {
    const res = await fetch(url);
    if (!res.ok) return;
    const data = await res.json();
    const features = data.features || [];
    currentEvents = features;

    // Set of current event IDs from server
    const incomingIds = new Set();

    features.forEach(feat => {
      const p = feat.properties;
      const eventId = p.event_id;
      incomingIds.add(eventId);

      const coords = feat.geometry && feat.geometry.coordinates;
      if (!coords) return;
      const latLng = [coords[1], coords[0]];
      const cls = p.predicted_class || "Other / Persistent Thermal Source";
      const color = CLASS_COLORS[cls] || "#94a3b8";

      if (eventMarkers.has(eventId)) {
        // Differential update: update position & style without recreating marker
        const marker = eventMarkers.get(eventId);
        marker.setLatLng(latLng);
        marker.setStyle({
          fillColor: color,
          color: selectedEventId === eventId ? "#38bdf8" : "#ffffff",
          weight: selectedEventId === eventId ? 3 : 1.2,
          radius: selectedEventId === eventId ? 9 : 6.5
        });
        marker.unbindTooltip();
        marker.bindTooltip(createTooltipContent(p), { direction: "top", offset: [0, -6] });
      } else {
        // Create new marker
        const marker = L.circleMarker(latLng, {
          radius: selectedEventId === eventId ? 9 : 6.5,
          fillColor: color,
          color: selectedEventId === eventId ? "#38bdf8" : "#ffffff",
          weight: selectedEventId === eventId ? 3 : 1.2,
          opacity: 0.95,
          fillOpacity: 0.85
        });

        marker.bindTooltip(createTooltipContent(p), { direction: "top", offset: [0, -6] });
        marker.on("click", () => {
          selectEvent(eventId, coords[1], coords[0]);
        });

        marker.addTo(markerLayerGroup);
        eventMarkers.set(eventId, marker);
      }
    });

    // Remove stale markers not in the incoming payload
    for (const [id, marker] of eventMarkers.entries()) {
      if (!incomingIds.has(id)) {
        markerLayerGroup.removeLayer(marker);
        eventMarkers.delete(id);
      }
    }

    // Auto-fit map on initial load if features exist
    if (fitBoundsIfFirst && features.length > 0 && map) {
      const bounds = L.latLngBounds(features.map(f => [f.geometry.coordinates[1], f.geometry.coordinates[0]]));
      map.fitBounds(bounds, { padding: [50, 50], maxZoom: 8 });
    }

    renderFeedTable(features);
  } catch (err) {
    console.error("Failed to refresh GeoJSON events:", err);
  }
}

function createTooltipContent(p) {
  const confPct = ((p.confidence || 0) * 100).toFixed(0);
  const cls = p.predicted_class || "Unclassified";
  const col = CLASS_COLORS[cls] || "#ffffff";
  return `
    <div style="font-family: sans-serif; font-size: 11px; line-height: 1.4;">
      <strong style="color: ${col};">${cls}</strong> (${confPct}%)<br/>
      <span style="color: #94a3b8;">${p.event_id}</span> | <span>${p.detection_count || 1} soundings</span>
    </div>
  `;
}

// =========================================================================
// 4. Live Events Feed
// =========================================================================
function renderFeedTable(features) {
  const tbody = document.getElementById("feed-table-body");
  const countBadge = document.getElementById("feed-count-badge");
  if (!tbody) return;

  const searchInput = document.getElementById("feed-search-input");
  const query = searchInput ? searchInput.value.trim().toLowerCase() : "";

  let filtered = features || [];
  if (query) {
    filtered = filtered.filter(f => {
      const p = f.properties;
      const id = (p.event_id || "").toLowerCase();
      const cls = (p.predicted_class || "").toLowerCase();
      const fac = (p.nearest_industry_name || p.nearest_facility_name || "").toLowerCase();
      return id.includes(query) || cls.includes(query) || fac.includes(query);
    });
  }

  if (countBadge) countBadge.textContent = filtered.length;

  if (filtered.length === 0) {
    tbody.innerHTML = `<tr><td colspan="4" class="feed-empty-cell">No thermal events matching criteria.</td></tr>`;
    return;
  }

  // Sort chronologically descending
  const sorted = [...filtered].sort((a, b) => {
    const tA = (a.properties.event_start_time || "");
    const tB = (b.properties.event_start_time || "");
    return tB.localeCompare(tA);
  });

  tbody.innerHTML = sorted.map(f => {
    const p = f.properties;
    const coords = f.geometry && f.geometry.coordinates;
    const lat = coords ? coords[1] : 0;
    const lon = coords ? coords[0] : 0;
    
    // Format compact time (e.g., 08:32)
    let timeDisplay = "-";
    if (p.event_start_time) {
      const d = new Date(p.event_start_time);
      timeDisplay = isNaN(d.getTime()) ? p.event_start_time.slice(11, 16) : d.toISOString().slice(11, 16) + " UTC";
    }

    const cls = p.predicted_class || "Unclassified";
    const confPct = ((p.confidence || 0) * 100).toFixed(0);
    const badgeColor = CLASS_COLORS[cls] || "#64748b";
    const locDisplay = `${lat.toFixed(2)}, ${lon.toFixed(2)}`;
    const isSelected = p.event_id === selectedEventId;

    return `
      <tr class="${isSelected ? 'selected' : ''}" onclick="selectEvent('${p.event_id}', ${lat}, ${lon})">
        <td class="time-col" title="${p.event_start_time}">${timeDisplay}</td>
        <td>
          <span class="badge-tag" style="background: ${badgeColor};">${cls.replace(" Fire", "").replace(" / Persistent Thermal Source", "")}</span>
        </td>
        <td class="conf-col">${confPct}%</td>
        <td title="${p.event_id} (${lat}, ${lon})">${locDisplay}</td>
      </tr>
    `;
  }).join("");
}

// =========================================================================
// 5. Selected Event Panel & Single-Event Proximity Rays
// =========================================================================
async function selectEvent(eventId, lat, lon) {
  selectedEventId = eventId;

  // Highlight selected marker on map and reset others
  for (const [id, marker] of eventMarkers.entries()) {
    if (id === eventId) {
      marker.setStyle({ color: "#38bdf8", weight: 3.5, radius: 9.5 });
      marker.bringToFront();
    } else {
      marker.setStyle({ color: "#ffffff", weight: 1.2, radius: 6.5 });
    }
  }

  // Pan to event smoothly
  if (lat && lon && map) {
    map.flyTo([lat, lon], Math.max(map.getZoom(), 8), { duration: 0.6 });
  }

  // Switch to Detail view
  document.getElementById("view-feed").style.display = "none";
  document.getElementById("view-detail").style.display = "flex";

  // Highlight row in feed table
  renderFeedTable(currentEvents);

  // Fetch full details
  try {
    const res = await fetch(`/events/${encodeURIComponent(eventId)}`);
    if (!res.ok) throw new Error("Could not retrieve event detail");
    const ev = await res.json();
    populateEventDetail(ev);
    renderSingleEventProximityRays(ev);
  } catch (err) {
    console.error("Failed to load event details:", err);
  }
}

function deselectEvent() {
  selectedEventId = null;

  // Clear proximity rays immediately
  if (selectedProximityGroup) {
    selectedProximityGroup.clearLayers();
  }

  // Reset all marker styles
  for (const [id, marker] of eventMarkers.entries()) {
    marker.setStyle({ color: "#ffffff", weight: 1.2, radius: 6.5 });
  }

  // Switch back to feed view
  document.getElementById("view-detail").style.display = "none";
  document.getElementById("view-feed").style.display = "flex";

  renderFeedTable(currentEvents);
}

function populateEventDetail(ev) {
  const cls = ev.predicted_class || "Unclassified";
  const confPct = ((ev.confidence || 0) * 100).toFixed(1);
  const color = CLASS_COLORS[cls] || "#3b82f6";

  const classBadge = document.getElementById("detail-class-badge");
  if (classBadge) {
    classBadge.textContent = cls;
    classBadge.style.background = color;
  }

  const confBadge = document.getElementById("detail-conf-badge");
  if (confBadge) confBadge.textContent = `${confPct}%`;

  // Meta rows
  document.getElementById("detail-event-id").textContent = ev.event_id || "-";
  document.getElementById("detail-coords").textContent = `${(ev.centroid_lat || 0).toFixed(4)}°, ${(ev.centroid_lon || 0).toFixed(4)}°`;
  document.getElementById("detail-time").textContent = (ev.event_start_time || "-").replace("T", " ").replace("Z", " UTC");
  document.getElementById("detail-soundings").textContent = ev.detection_count || (ev.detections ? ev.detections.length : 1);
  document.getElementById("detail-frp").textContent = `${(ev.max_frp || 0).toFixed(1)} MW`;
  
  // Ti4 from detections if available
  let maxTi4 = "-";
  if (ev.detections && ev.detections.length > 0) {
    const ti4Vals = ev.detections.map(d => d.bright_ti4).filter(v => v !== null && v !== undefined);
    if (ti4Vals.length > 0) maxTi4 = `${Math.max(...ti4Vals).toFixed(1)} K`;
  }
  document.getElementById("detail-ti4").textContent = maxTi4;
  document.getElementById("detail-persistence").textContent = ev.persistence_level || "Transient";

  // Proximity details
  const prox = ev.proximity || {};

  // 1. Industry
  const indName = prox.nearest_industry_name || ev.nearest_facility_name || "None within radius";
  const indDist = prox.distance_to_industry_km !== null && prox.distance_to_industry_km !== undefined
    ? `${prox.distance_to_industry_km.toFixed(2)} km`
    : (ev.dist_to_facility_km ? `${ev.dist_to_facility_km.toFixed(2)} km` : "N/A");
  document.getElementById("prox-industry-name").textContent = indName;
  document.getElementById("prox-industry-dist").textContent = indDist;

  // 2. School
  const schName = prox.nearest_school_name || "None within search radius";
  const schDist = prox.distance_to_school_km !== null && prox.distance_to_school_km !== undefined
    ? `${prox.distance_to_school_km.toFixed(2)} km`
    : "N/A";
  document.getElementById("prox-school-name").textContent = schName;
  document.getElementById("prox-school-dist").textContent = schDist;

  // 3. Hospital
  const hosName = prox.nearest_hospital_name || "None within search radius";
  const hosDist = prox.distance_to_hospital_km !== null && prox.distance_to_hospital_km !== undefined
    ? `${prox.distance_to_hospital_km.toFixed(2)} km`
    : "N/A";
  document.getElementById("prox-hospital-name").textContent = hosName;
  document.getElementById("prox-hospital-dist").textContent = hosDist;

  // 4. Village
  const vilName = prox.nearest_village_name || "None within search radius";
  const vilDist = prox.distance_to_village_km !== null && prox.distance_to_village_km !== undefined
    ? `${prox.distance_to_village_km.toFixed(2)} km`
    : "N/A";
  document.getElementById("prox-village-name").textContent = vilName;
  document.getElementById("prox-village-dist").textContent = vilDist;

  // Probabilities
  const pInd = (ev.prob_industrial || 0) * 100;
  const pFor = (ev.prob_forest || 0) * 100;
  const pAgr = (ev.prob_agricultural || 0) * 100;
  const pPer = (ev.prob_persistent || 0) * 100;

  document.getElementById("detail-p-ind").textContent = `${pInd.toFixed(1)}%`;
  document.getElementById("detail-bar-ind").style.width = `${pInd}%`;

  document.getElementById("detail-p-for").textContent = `${pFor.toFixed(1)}%`;
  document.getElementById("detail-bar-for").style.width = `${pFor}%`;

  document.getElementById("detail-p-agr").textContent = `${pAgr.toFixed(1)}%`;
  document.getElementById("detail-bar-agr").style.width = `${pAgr}%`;

  document.getElementById("detail-p-per").textContent = `${pPer.toFixed(1)}%`;
  document.getElementById("detail-bar-per").style.width = `${pPer}%`;
}

// Render proximity lines ONLY for the currently selected event
function renderSingleEventProximityRays(ev) {
  if (!selectedProximityGroup || !map) return;
  selectedProximityGroup.clearLayers();

  const cLat = ev.centroid_lat;
  const cLon = ev.centroid_lon;
  if (cLat === undefined || cLon === undefined) return;

  const prox = ev.proximity || {};

  // 1. Industry (Red dashed ray)
  if (prox.nearest_industry_lat && prox.nearest_industry_lon) {
    const latLng = [prox.nearest_industry_lat, prox.nearest_industry_lon];
    L.polyline([[cLat, cLon], latLng], {
      color: "#ef4444",
      weight: 2,
      dashArray: "5, 5",
      opacity: 0.9
    }).addTo(selectedProximityGroup);

    L.circleMarker(latLng, {
      radius: 5,
      fillColor: "#ef4444",
      color: "#ffffff",
      weight: 1.5,
      fillOpacity: 0.95
    }).bindTooltip(
      `<strong>Industry:</strong> ${prox.nearest_industry_name || 'Industrial Site'}<br>${(prox.distance_to_industry_km || 0).toFixed(2)} km`,
      { direction: "top", offset: [0, -6] }
    ).addTo(selectedProximityGroup);
  }

  // 2. School (Blue dashed ray)
  if (prox.nearest_school_lat && prox.nearest_school_lon) {
    const latLng = [prox.nearest_school_lat, prox.nearest_school_lon];
    L.polyline([[cLat, cLon], latLng], {
      color: "#3b82f6",
      weight: 2,
      dashArray: "5, 5",
      opacity: 0.9
    }).addTo(selectedProximityGroup);

    L.circleMarker(latLng, {
      radius: 5,
      fillColor: "#3b82f6",
      color: "#ffffff",
      weight: 1.5,
      fillOpacity: 0.95
    }).bindTooltip(
      `<strong>School:</strong> ${prox.nearest_school_name || 'School'}<br>${(prox.distance_to_school_km || 0).toFixed(2)} km`,
      { direction: "top", offset: [0, -6] }
    ).addTo(selectedProximityGroup);
  }

  // 3. Hospital (Green dashed ray)
  if (prox.nearest_hospital_lat && prox.nearest_hospital_lon) {
    const latLng = [prox.nearest_hospital_lat, prox.nearest_hospital_lon];
    L.polyline([[cLat, cLon], latLng], {
      color: "#10b981",
      weight: 2,
      dashArray: "5, 5",
      opacity: 0.9
    }).addTo(selectedProximityGroup);

    L.circleMarker(latLng, {
      radius: 5,
      fillColor: "#10b981",
      color: "#ffffff",
      weight: 1.5,
      fillOpacity: 0.95
    }).bindTooltip(
      `<strong>Hospital:</strong> ${prox.nearest_hospital_name || 'Hospital'}<br>${(prox.distance_to_hospital_km || 0).toFixed(2)} km`,
      { direction: "top", offset: [0, -6] }
    ).addTo(selectedProximityGroup);
  }

  // 4. Village (Amber dashed ray)
  if (prox.nearest_village_lat && prox.nearest_village_lon) {
    const latLng = [prox.nearest_village_lat, prox.nearest_village_lon];
    L.polyline([[cLat, cLon], latLng], {
      color: "#f59e0b",
      weight: 2,
      dashArray: "5, 5",
      opacity: 0.9
    }).addTo(selectedProximityGroup);

    L.circleMarker(latLng, {
      radius: 5,
      fillColor: "#f59e0b",
      color: "#ffffff",
      weight: 1.5,
      fillOpacity: 0.95
    }).bindTooltip(
      `<strong>Village / Settlement:</strong> ${prox.nearest_village_name || 'Village'}<br>${(prox.distance_to_village_km || 0).toFixed(2)} km`,
      { direction: "top", offset: [0, -6] }
    ).addTo(selectedProximityGroup);
  }
}

// =========================================================================
// 6. Controls & Interactions
// =========================================================================
function initTopBarControls() {
  const btnPoll = document.getElementById("btn-poll-now");
  if (btnPoll) {
    btnPoll.addEventListener("click", triggerImmediatePoll);
  }

  const btnTech = document.getElementById("btn-tech-modal");
  if (btnTech) {
    btnTech.addEventListener("click", () => {
      openTechModal();
    });
  }
}

async function triggerImmediatePoll() {
  const btnPoll = document.getElementById("btn-poll-now");
  if (!btnPoll) return;

  const originalHtml = btnPoll.innerHTML;
  btnPoll.disabled = true;
  btnPoll.innerHTML = `<span class="btn-icon">⏳</span> Polling FIRMS...`;

  try {
    const res = await fetch("/live/poll?days=1", { method: "POST" });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || "FIRMS query failed");
    }
    const data = await res.json();
    btnPoll.innerHTML = `✓ ${data.detections_fetched} Dets (${data.events_created} Evts)`;
    
    await fetchLiveStatus();
    await refreshGeoJsonEvents(true);

    setTimeout(() => {
      btnPoll.innerHTML = originalHtml;
      btnPoll.disabled = false;
    }, 3500);
  } catch (err) {
    console.error("Poll Now Error:", err);
    btnPoll.innerHTML = `✗ Error`;
    setTimeout(() => {
      btnPoll.innerHTML = originalHtml;
      btnPoll.disabled = false;
    }, 2500);
    alert("Live FIRMS query issue: " + err.message);
  }
}

function initFeedFilterEvents() {
  const classFilter = document.getElementById("feed-class-filter");
  const searchInput = document.getElementById("feed-search-input");

  if (classFilter) {
    classFilter.addEventListener("change", () => {
      refreshGeoJsonEvents(false);
    });
  }

  if (searchInput) {
    searchInput.addEventListener("input", () => {
      renderFeedTable(currentEvents);
    });
  }
}

function initDetailEvents() {
  const btnBack = document.getElementById("btn-back-to-feed");
  if (btnBack) {
    btnBack.addEventListener("click", deselectEvent);
  }
}

// =========================================================================
// 7. Technical Details Modal & Reviewer Scenarios
// =========================================================================
function initModalEvents() {
  const modal = document.getElementById("tech-modal");
  const closeBtn = document.getElementById("modal-close-btn");

  if (closeBtn && modal) {
    closeBtn.addEventListener("click", () => {
      modal.style.display = "none";
    });

    modal.addEventListener("click", (e) => {
      if (e.target === modal) {
        modal.style.display = "none";
      }
    });
  }

  // Tabs
  const tabBtns = document.querySelectorAll(".modal-tab-btn");
  tabBtns.forEach(btn => {
    btn.addEventListener("click", () => {
      tabBtns.forEach(b => b.classList.remove("active"));
      btn.classList.add("active");

      const targetTab = btn.getAttribute("data-tab");
      document.querySelectorAll(".modal-tab-content").forEach(content => {
        content.classList.toggle("active", content.id === targetTab);
      });
    });
  });

  // Demo cohort loading
  const btnLoadCohort = document.getElementById("btn-load-demo-cohort");
  if (btnLoadCohort) {
    btnLoadCohort.addEventListener("click", async () => {
      btnLoadCohort.disabled = true;
      btnLoadCohort.textContent = "Loading Demo Cohort...";
      try {
        const res = await fetch("/demo/load", { method: "POST" });
        if (!res.ok) throw new Error("Demo load failed");
        const data = await res.json();
        btnLoadCohort.textContent = `✓ Loaded ${data.thermal_events} Events`;
        await fetchLiveStatus();
        await refreshGeoJsonEvents(true);
        setTimeout(() => {
          btnLoadCohort.textContent = "⚡ Load Full Demo Cohort (619 Detections)";
          btnLoadCohort.disabled = false;
          modal.style.display = "none";
        }, 1500);
      } catch (err) {
        alert("Demo load error: " + err.message);
        btnLoadCohort.textContent = "⚡ Load Full Demo Cohort (619 Detections)";
        btnLoadCohort.disabled = false;
      }
    });
  }

  // Clear DB
  const btnClearDb = document.getElementById("btn-clear-db");
  if (btnClearDb) {
    btnClearDb.addEventListener("click", async () => {
      if (!confirm("Clear all loaded thermal events from the operational database?")) return;
      try {
        await fetch("/demo/clear", { method: "POST" });
        deselectEvent();
        await fetchLiveStatus();
        await refreshGeoJsonEvents(false);
        alert("Operational database cleared.");
      } catch (err) {
        console.error("Clear DB error:", err);
      }
    });
  }
}

async function openTechModal() {
  const modal = document.getElementById("tech-modal");
  if (modal) modal.style.display = "flex";

  // Query health endpoint for tab 4
  const healthEl = document.getElementById("modal-health-status");
  if (healthEl) {
    try {
      const res = await fetch("/live/health");
      if (res.ok) {
        const h = await res.json();
        healthEl.innerHTML = `
          <strong>Status: ${h.status}</strong> | Database: ${h.database} | FIRMS: ${h.firms_connectivity} | Geoapify: ${h.geoapify_connectivity}
        `;
      }
    } catch (e) {
      healthEl.textContent = "Health check query unavailable.";
    }
  }
}

// Reviewer scenario shortcut
window.loadScenarioEvent = async function (eventId, lat, lon) {
  const modal = document.getElementById("tech-modal");
  if (modal) modal.style.display = "none";

  // If event not already loaded, try loading demo cohort first
  if (!eventMarkers.has(eventId)) {
    try {
      await fetch("/demo/load", { method: "POST" });
      await fetchLiveStatus();
      await refreshGeoJsonEvents(false);
    } catch (err) {
      console.warn("Could not auto-load demo cohort:", err);
    }
  }

  selectEvent(eventId, lat, lon);
};
