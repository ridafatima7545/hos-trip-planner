import React, { useEffect, useMemo, useRef, useState } from "react";
import { createRoot } from "react-dom/client";
import { CalendarClock, Download, Fuel, MapPin, Moon, Route, Truck } from "lucide-react";
import { MapContainer, Marker, Polyline, Popup, TileLayer, useMap } from "react-leaflet";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import "./styles.css";
import blankLog from "./assets/blank-paper-log.png";

const API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:8000";

const statusRows = {
  OFF: 193,
  SB: 211,
  DRIVING: 229,
  ON: 247,
};

const statusLabels = {
  OFF: "Off duty",
  SB: "Sleeper berth",
  DRIVING: "Driving",
  ON: "On duty",
};

const stopIcon = (type) =>
  new L.DivIcon({
    className: `stop-marker ${type}`,
    html: `<span>${type === "fuel" ? "F" : type === "rest" ? "R" : type === "pickup" ? "P" : type === "dropoff" ? "D" : "S"}</span>`,
    iconSize: [30, 30],
    iconAnchor: [15, 15],
  });

function FitRoute({ points }) {
  const map = useMap();

  useEffect(() => {
    if (!points?.length) return;
    map.fitBounds(L.latLngBounds(points), { padding: [32, 32] });
  }, [map, points]);

  return null;
}

function RouteMap({ result }) {
  const points = result?.route?.geometry || [];
  const stops = result?.stops || [];
  const center = points[0] || [39.5, -98.35];

  return (
    <div className="mapShell">
      <MapContainer center={center} zoom={5} scrollWheelZoom className="routeMap">
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />
        {points.length > 0 && <Polyline positions={points} pathOptions={{ color: "#2563eb", weight: 5 }} />}
        {stops.map((stop, index) => (
          <Marker key={`${stop.type}-${index}-${stop.routeMile}`} position={[stop.lat, stop.lon]} icon={stopIcon(stop.type)}>
            <Popup>
              <strong>{stop.label}</strong>
              <br />
              Mile {stop.routeMile}
              {stop.time ? (
                <>
                  <br />
                  {formatDateTime(stop.time)}
                </>
              ) : null}
            </Popup>
          </Marker>
        ))}
        <FitRoute points={points} />
      </MapContainer>
    </div>
  );
}

function LogCanvas({ log, inputs }) {
  const canvasRef = useRef(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    const ctx = canvas.getContext("2d");
    const image = new Image();
    image.src = blankLog;
    image.onload = () => {
      canvas.width = image.width;
      canvas.height = image.height;
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      ctx.drawImage(image, 0, 0);
      drawLog(ctx, log, inputs);
    };
  }, [log, inputs]);

  const download = () => {
    const link = document.createElement("a");
    link.download = `daily-log-day-${log.dayNumber}.png`;
    link.href = canvasRef.current.toDataURL("image/png");
    link.click();
  };

  return (
    <div className="logCard">
      <div className="logHeader">
        <div>
          <strong>Day {log.dayNumber}</strong>
          <span>{formatDate(log.date)}</span>
        </div>
        <button type="button" className="iconButton" onClick={download} title="Download log sheet">
          <Download size={17} />
        </button>
      </div>
      <canvas ref={canvasRef} className="logCanvas" aria-label={`Daily log for ${log.date}`} />
    </div>
  );
}

function drawLog(ctx, log, inputs) {
  const gridX = 62;
  const gridW = 392;
  const totalHoursX = 481;
  const pxPerHour = gridW / 24;
  const rowY = statusRows;

  ctx.save();
  ctx.fillStyle = "#111827";
  ctx.strokeStyle = "#111827";
  ctx.lineWidth = 2;
  ctx.textBaseline = "middle";

  const [year, month, day] = log.date.split("-");
  drawCenteredText(ctx, month, 183, 15, 28, 7);
  drawCenteredText(ctx, day, 229, 15, 28, 7);
  drawCenteredText(ctx, year, 276, 15, 34, 7);
  drawFieldText(ctx, inputs.currentLocation || "Current location", 96, 44, 142, 8);
  drawFieldText(ctx, inputs.dropoffLocation || "Destination", 289, 44, 144, 8);
  drawCenteredText(ctx, log.totals.DRIVING.toFixed(1), 96, 78, 74, 8);
  drawCenteredText(ctx, totalMilesForLog(log).toFixed(1), 180, 78, 74, 8);
  drawCenteredText(ctx, "Unit 1", 136, 111, 156, 7);

  drawDutyStatusLine(ctx, log.segments, gridX, pxPerHour, rowY);

  const remarks = log.segments
    .filter((segment) => segment.remark && segment.status !== "OFF")
    .map((segment) => `${hourLabel(segment.startHour)} ${segment.remark}${segment.location ? ` - ${segment.location}` : ""}`);

  ctx.fillStyle = "#111827";
  remarks.slice(0, 5).forEach((remark, index) => {
    drawFieldText(ctx, remark, 24, 292 + index * 8, 456, 6.8);
  });

  ctx.font = "7px Arial";
  ctx.textAlign = "center";
  ctx.textBaseline = "alphabetic";
  ctx.fillText(log.totals.OFF.toFixed(1), totalHoursX, 195);
  ctx.fillText(log.totals.SB.toFixed(1), totalHoursX, 213);
  ctx.fillText(log.totals.DRIVING.toFixed(1), totalHoursX, 231);
  ctx.fillText(log.totals.ON.toFixed(1), totalHoursX, 249);
  ctx.fillText(Object.values(log.totals).reduce((sum, value) => sum + value, 0).toFixed(1), totalHoursX, 280);
  ctx.restore();
}

function drawDutyStatusLine(ctx, segments, gridX, pxPerHour, rowY) {
  const visibleSegments = segments
    .map((segment) => ({
      ...segment,
      x1: gridX + segment.startHour * pxPerHour,
      x2: gridX + segment.endHour * pxPerHour,
      y: rowY[segment.status],
    }))
    .filter((segment) => segment.y && segment.endHour > segment.startHour)
    .sort((a, b) => a.startHour - b.startHour);

  ctx.save();
  ctx.strokeStyle = "#111827";
  ctx.lineWidth = 2;
  ctx.lineCap = "butt";
  ctx.lineJoin = "miter";

  visibleSegments.forEach((segment, index) => {
    const y = rowY[segment.status];
    ctx.beginPath();
    ctx.moveTo(segment.x1, y);
    ctx.lineTo(segment.x2, y);
    ctx.stroke();

    const next = visibleSegments[index + 1];
    if (next && Math.abs(next.x1 - segment.x2) < 1.5 && next.y !== segment.y) {
      ctx.beginPath();
      ctx.moveTo(segment.x2, segment.y);
      ctx.lineTo(next.x1, next.y);
      ctx.stroke();
    }
  });
  ctx.restore();
}

function drawFieldText(ctx, text, x, y, maxWidth, fontSize) {
  ctx.save();
  ctx.font = `${fontSize}px Arial`;
  ctx.textAlign = "left";
  ctx.textBaseline = "middle";
  ctx.fillText(fitText(ctx, String(text), maxWidth), x, y);
  ctx.restore();
}

function drawCenteredText(ctx, text, centerX, centerY, maxWidth, fontSize) {
  ctx.save();
  ctx.font = `${fontSize}px Arial`;
  ctx.textAlign = "center";
  ctx.textBaseline = "middle";
  ctx.fillText(fitText(ctx, String(text), maxWidth), centerX, centerY);
  ctx.restore();
}

function fitText(ctx, text, maxWidth) {
  if (ctx.measureText(text).width <= maxWidth) return text;
  let clipped = text;
  while (clipped.length > 3 && ctx.measureText(`${clipped}...`).width > maxWidth) {
    clipped = clipped.slice(0, -1);
  }
  return `${clipped}...`;
}

function totalMilesForLog(log) {
  const driving = log.segments.filter((segment) => segment.status === "DRIVING");
  if (!driving.length) return 0;
  return driving.reduce((sum, segment) => sum + Math.max(0, (segment.endRouteMile || segment.routeMile) - segment.routeMile), 0);
}

function hourLabel(value) {
  const hours = Math.floor(value);
  const minutes = Math.round((value - hours) * 60);
  return `${String(hours).padStart(2, "0")}:${String(minutes).padStart(2, "0")}`;
}

function formatDate(value) {
  return new Intl.DateTimeFormat(undefined, { month: "short", day: "numeric", year: "numeric" }).format(new Date(`${value}T00:00:00`));
}

function formatDateTime(value) {
  return new Intl.DateTimeFormat(undefined, {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  }).format(new Date(value));
}

function App() {
  const [form, setForm] = useState({
    currentLocation: "Chicago, IL",
    pickupLocation: "Indianapolis, IN",
    dropoffLocation: "Dallas, TX",
    currentCycleUsed: "18",
    startAt: new Date().toISOString().slice(0, 16),
  });
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const timeline = useMemo(() => result?.events || [], [result]);

  const update = (event) => setForm((current) => ({ ...current, [event.target.name]: event.target.value }));

  const submit = async (event) => {
    event.preventDefault();
    setLoading(true);
    setError("");
    try {
      const response = await fetch(`${API_BASE}/api/plan-trip/`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(form),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || "Trip planning failed.");
      setResult(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <main>
      <section className="workspace">
        <aside className="plannerPanel">
          <div className="brand">
            <Truck size={26} />
            <div>
              <h1>HOS Trip Planner</h1>
              <p>Route, duty status, fuel, rest, and FMCSA-style paper logs.</p>
            </div>
          </div>

          <form onSubmit={submit} className="tripForm">
            <label>
              Current location
              <input name="currentLocation" value={form.currentLocation} onChange={update} required />
            </label>
            <label>
              Pickup location
              <input name="pickupLocation" value={form.pickupLocation} onChange={update} required />
            </label>
            <label>
              Dropoff location
              <input name="dropoffLocation" value={form.dropoffLocation} onChange={update} required />
            </label>
            <div className="formGrid">
              <label>
                Cycle used
                <input name="currentCycleUsed" type="number" min="0" max="70" step="0.25" value={form.currentCycleUsed} onChange={update} required />
              </label>
              <label>
                Start
                <input name="startAt" type="datetime-local" value={form.startAt} onChange={update} />
              </label>
            </div>
            <button type="submit" className="primaryButton" disabled={loading}>
              <Route size={18} />
              {loading ? "Planning..." : "Plan trip"}
            </button>
            {error ? <div className="errorBox">{error}</div> : null}
          </form>

          {result ? (
            <div className="assumptions">
              {result.assumptions.map((item) => (
                <p key={item}>{item}</p>
              ))}
            </div>
          ) : null}
        </aside>

        <section className="mainPanel">
          {result ? (
            <>
              <div className="summaryGrid">
                <Metric icon={<MapPin />} label="Miles" value={result.summary.totalMiles} />
                <Metric icon={<CalendarClock />} label="Elapsed hours" value={result.summary.elapsedHours} />
                <Metric icon={<Fuel />} label="Fuel stops" value={result.summary.fuelStops} />
                <Metric icon={<Moon />} label="Log days" value={result.summary.logDays} />
              </div>

              <RouteMap result={result} />

              <section className="detailsGrid">
                <div className="panel">
                  <h2>Route Instructions</h2>
                  <div className="routeLegs">
                    {result.route.legs.map((leg) => (
                      <div className="routeLeg" key={leg.name}>
                        <strong>{leg.from} to {leg.to}</strong>
                        <span>{leg.miles} mi · {leg.hours} driving hrs</span>
                      </div>
                    ))}
                  </div>
                </div>

                <div className="panel">
                  <h2>Duty Timeline</h2>
                  <div className="timeline">
                    {timeline.map((event, index) => (
                      <div className={`timelineItem ${event.status.toLowerCase()}`} key={`${event.start}-${index}`}>
                        <span>{formatDateTime(event.start)}</span>
                        <strong>{statusLabels[event.status]}</strong>
                        <p>{event.remark}</p>
                      </div>
                    ))}
                  </div>
                </div>
              </section>

              <section className="logsSection">
                <h2>Daily Log Sheets</h2>
                <div className="logsGrid">
                  {result.logs.map((log) => (
                    <LogCanvas key={log.date} log={log} inputs={result.inputs} />
                  ))}
                </div>
              </section>
            </>
          ) : (
            <div className="emptyState">
              <Route size={46} />
              <h2>Enter a trip to generate the route and logs.</h2>
              <p>The planner will return legal stops, rests, fuel events, and downloadable daily log sheets.</p>
            </div>
          )}
        </section>
      </section>
    </main>
  );
}

function Metric({ icon, label, value }) {
  return (
    <div className="metric">
      {React.cloneElement(icon, { size: 20 })}
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

createRoot(document.getElementById("root")).render(<App />);
