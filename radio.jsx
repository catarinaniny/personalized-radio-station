/* global React, ReactDOM */
const { useState, useEffect, useRef } = React;

const DEFAULT_STATIONS = [
  { id: 1, name: "DEEP FOCUS",   tag: "ambient lab loops",        mhz: 88.3,  hosts: 1, voiceA: "F", voiceB: "M", tone: 25, urls: ["https://pitchfork.com/rss/news", "https://thequietus.com/feed"], length: 30, freq: "daily" },
  { id: 2, name: "LOFI MEMORY",  tag: "nostalgic recompositions", mhz: 91.4,  hosts: 2, voiceA: "M", voiceB: "F", tone: 40, urls: ["https://stereogum.com/feed"], length: 45, freq: "daily" },
  { id: 3, name: "SOLAR DRIFT",  tag: "sun-warmed synthwave",     mhz: 94.7,  hosts: 1, voiceA: "M", voiceB: "M", tone: 15, urls: ["https://feeds.bbci.co.uk/news/rss.xml", "https://www.theverge.com/rss/index.xml", "https://hnrss.org/frontpage"], length: 60, freq: "continuous" },
  { id: 4, name: "NIGHTCREW",    tag: "midnight conversations",   mhz: 101.2, hosts: 2, voiceA: "M", voiceB: "M", tone: 75, urls: ["https://feeds.npr.org/1001/rss.xml"], length: 60, freq: "daily" },
  { id: 5, name: "LONG WAVE",    tag: "drone meditation",         mhz: 106.8, hosts: 1, voiceA: "N", voiceB: "M", tone: 10, urls: ["https://long-wave.fm/feed"], length: 30, freq: "hourly" },
];

const FREQ_MIN = 88.0;
const FREQ_MAX = 108.0;

const TIMER_MAX_SEC = 60 * 60;
const clamp = (v, lo, hi) => Math.max(lo, Math.min(hi, v));
const pad = (n) => String(Math.floor(n)).padStart(2, "0");
const pad2 = (n) => String(n).padStart(2, "0");

/* ---------- Tuner strip (frequency scanner) ---------- */
function TunerStrip({ freq, stations, onSeek }) {
  const MIN = 87.5, MAX = 108;
  const pct = (v) => ((v - MIN) / (MAX - MIN)) * 100;
  const dragRef = useRef(null);

  const ticks = [];
  for (let f = 88; f <= 108; f += 1) ticks.push({ f, major: f % 5 === 0 });

  const seekFromEvent = (e) => {
    const el = e.currentTarget;
    const rect = el.getBoundingClientRect();
    const x = clamp((e.clientX - rect.left) / rect.width, 0, 1);
    const v = Math.round((MIN + x * (MAX - MIN)) * 10) / 10;
    onSeek(v);
  };
  const onDown = (e) => {
    dragRef.current = true;
    e.currentTarget.setPointerCapture?.(e.pointerId);
    seekFromEvent(e);
  };
  const onMove = (e) => { if (dragRef.current) seekFromEvent(e); };
  const onUp = (e) => {
    dragRef.current = false;
    e.currentTarget.releasePointerCapture?.(e.pointerId);
  };

  return (
    <div className="tuner-strip">
      <div className="tuner-numbers">
        {[90, 95, 100, 105].map((f) => (
          <span key={f} className="tnum" style={{ left: `${pct(f)}%` }}>{f}</span>
        ))}
      </div>
      <div
        className="tuner-rule"
        onPointerDown={onDown}
        onPointerMove={onMove}
        onPointerUp={onUp}
        onPointerCancel={onUp}
      >
        {ticks.map(({ f, major }) => (
          <span key={f} className={"ttick" + (major ? " major" : "")} style={{ left: `${pct(f)}%` }} />
        ))}
        <div className="tpointer" style={{ left: `${pct(freq)}%` }}>
          <span className="tpoint-tip" />
          <span className="tpoint-rod" />
        </div>
      </div>
      <div className="tuner-stations">
        {stations.map((s) => {
          const active = Math.abs(s.mhz - freq) < 0.4;
          return (
            <button key={s.id} className={"tst" + (active ? " active" : "")}
                    style={{ left: `${pct(s.mhz)}%` }}
                    onClick={() => onSeek(s.mhz)}>
              <span className="tst-dot" />
              <span className="tst-lbl">{s.name}</span>
            </button>
          );
        })}
      </div>
      <div className="tuner-foot">
        <span>· 87.5 — 108 MHz</span>
        <span>FM</span>
      </div>
    </div>
  );
}

/* ---------- Frequency analyzer ---------- */
function Analyzer({ playing, columns = 32, rows = 7 }) {
  const [levels, setLevels] = useState(() => Array(columns).fill(0));
  useEffect(() => {
    if (!playing) { setLevels(Array(columns).fill(0)); return; }
    let raf, t = 0;
    const tick = () => {
      t += 0.13;
      setLevels(() => {
        const out = new Array(columns);
        for (let i = 0; i < columns; i++) {
          // smooth bandshape with a couple of moving lobes + bias toward middle
          const mid = columns / 2;
          const bias = 1 - Math.abs(i - mid) / mid * 0.55;
          const v = 0.42
            + 0.30 * Math.sin(t * 1.0 + i * 0.32)
            + 0.18 * Math.sin(t * 1.7 + i * 0.71 + 1.3)
            + 0.10 * Math.sin(t * 2.4 + i * 0.18 + 2.7);
          const jitter = (Math.random() - 0.5) * 0.08;
          out[i] = Math.max(0, Math.min(1, v * bias + jitter));
        }
        return out;
      });
      raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [playing, columns]);

  return (
    <div className="analyzer" style={{ gridTemplateColumns: `repeat(${columns}, 1fr)` }}>
      {levels.map((lvl, i) => {
        const litRows = Math.round(lvl * rows);
        return (
          <div key={i} className="an-col">
            {Array.from({ length: rows }).map((_, r) => {
              const fromBottom = rows - 1 - r;
              const lit = fromBottom < litRows;
              const hi = lit && fromBottom === litRows - 1;
              return <span key={r} className={"an-cell" + (lit ? " lit" : "") + (hi ? " hi" : "")} />;
            })}
          </div>
        );
      })}
    </div>
  );
}

/* ---------- Knob ---------- */
function Knob({ value, max, onChange, color = "#1a140a", size = 88 }) {
  const angle = -135 + (value / max) * 270;
  const drag = useRef(null);
  const onDown = (e) => { drag.current = { y: e.clientY, v: value }; e.target.setPointerCapture?.(e.pointerId); };
  const onMove = (e) => {
    if (!drag.current) return;
    const dy = drag.current.y - e.clientY;
    onChange(clamp(drag.current.v + (dy / 180) * max, 0, max));
  };
  const onUp = (e) => { drag.current = null; e.target.releasePointerCapture?.(e.pointerId); };
  const onWheel = (e) => { e.preventDefault(); onChange(clamp(value - (e.deltaY * max) / 8000, 0, max)); };

  const tickCount = 21;
  const ticks = Array.from({ length: tickCount }).map((_, i) => {
    const a = -135 + (i / (tickCount - 1)) * 270;
    const lit = i / (tickCount - 1) <= value / max + 0.001;
    const r1 = 46, r2 = 49.5;
    const x1 = 50 + r1 * Math.sin((a * Math.PI) / 180);
    const y1 = 50 - r1 * Math.cos((a * Math.PI) / 180);
    const x2 = 50 + r2 * Math.sin((a * Math.PI) / 180);
    const y2 = 50 - r2 * Math.cos((a * Math.PI) / 180);
    return <line key={i} x1={x1} y1={y1} x2={x2} y2={y2}
      stroke={lit ? color : "rgba(232,216,182,0.18)"}
      strokeWidth={i % 5 === 0 ? 1.6 : 0.8} strokeLinecap="round" />;
  });

  return (
    <div className="knob" style={{ width: size, height: size }}
         onPointerDown={onDown} onPointerMove={onMove}
         onPointerUp={onUp} onPointerCancel={onUp} onWheel={onWheel}>
      <svg viewBox="0 0 100 100">
        <defs>
          <radialGradient id={`capG${size}`} cx="0.4" cy="0.3" r="0.8">
            <stop offset="0%" stopColor="#f0d399" />
            <stop offset="55%" stopColor="#a87f3a" />
            <stop offset="100%" stopColor="#2a1c08" />
          </radialGradient>
          <linearGradient id={`bezG${size}`} x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#d8c8a4" />
            <stop offset="100%" stopColor="#3a2c14" />
          </linearGradient>
        </defs>
        {ticks}
        <circle cx="50" cy="50" r="40" fill={`url(#bezG${size})`} />
        <circle cx="50" cy="50" r="34" fill={`url(#capG${size})`} stroke="rgba(0,0,0,0.45)" strokeWidth="0.5" />
        {Array.from({ length: 24 }).map((_, i) => {
          const a = (i / 24) * 360;
          const x1 = 50 + 34 * Math.sin((a * Math.PI) / 180);
          const y1 = 50 - 34 * Math.cos((a * Math.PI) / 180);
          const x2 = 50 + 38 * Math.sin((a * Math.PI) / 180);
          const y2 = 50 - 38 * Math.cos((a * Math.PI) / 180);
          return <line key={i} x1={x1} y1={y1} x2={x2} y2={y2} stroke="rgba(0,0,0,0.4)" strokeWidth="0.7" />;
        })}
        <g transform={`rotate(${angle} 50 50)`}>
          <line x1="50" y1="50" x2="50" y2="20" stroke={color} strokeWidth="2.5" strokeLinecap="round" />
          <circle cx="50" cy="20" r="1.6" fill={color} />
        </g>
        <circle cx="50" cy="50" r="5" fill="#3a2c14" />
      </svg>
    </div>
  );
}

/* ---------- Segmented control ---------- */
function Segmented({ value, options, onChange }) {
  return (
    <div className="seg">
      {options.map(([v, label]) => (
        <button key={v} className={"seg-btn" + (v === value ? " active" : "")}
                onClick={() => onChange(v)}>{label}</button>
      ))}
    </div>
  );
}

/* ---------- Settings tabs ---------- */
function feedDomain(u) {
  try { return new URL(u).hostname.replace(/^www\./, ""); }
  catch { return u; }
}

function RssChips({ value, onChange, placeholder }) {
  const [draft, setDraft] = useState("");
  const list = value || [];
  const add = () => {
    const v = draft.trim();
    if (!v) return;
    if (list.includes(v)) { setDraft(""); return; }
    onChange([...list, v]);
    setDraft("");
  };
  const remove = (i) => onChange(list.filter((_, j) => j !== i));
  return (
    <div className="rss-chips">
      <div className="rss-input">
        <input value={draft}
               onChange={(e) => setDraft(e.target.value)}
               onKeyDown={(e) => { if (e.key === "Enter") { e.preventDefault(); add(); } }}
               placeholder={placeholder || "paste a feed URL…"} />
        <button type="button" className="rss-add" onClick={add} disabled={!draft.trim()}>+</button>
      </div>
      {list.length > 0 && (
        <div className="rss-list">
          {list.map((u, i) => (
            <span key={i} className="rss-chip" title={u}>
              <span className="rss-dot" />
              <span className="rss-chip-name">{feedDomain(u)}</span>
              <button type="button" className="rss-x" onClick={() => remove(i)} aria-label="Remove">×</button>
            </span>
          ))}
        </div>
      )}
    </div>
  );
}

function StationsTab({ stations, selected, onSelect, onChange, onCreate, onDelete }) {
  const update = (k, v) => onChange({ ...selected, [k]: v });
  return (
    <div className="stations-tab">
      <div className="vibe-picker">
        <label className="vp-label">VIBE</label>
        <div className="vp-select-wrap">
          <select className="vp-select"
                  value={selected ? selected.id : ""}
                  onChange={(e) => onSelect(Number(e.target.value))}>
            {stations.map((s, i) => (
              <option key={s.id} value={s.id}>
                {pad2(i + 1)} — {s.name} · {s.hosts}H
              </option>
            ))}
          </select>
          <span className="vp-caret">▾</span>
        </div>
        <button className="vp-new" onClick={onCreate}>+ NEW</button>
      </div>

      {!selected ? (
        <div className="station-edit empty">No vibe selected.</div>
      ) : (
        <div className="station-edit">
          <div className="edit-grid">
            <div className="row">
              <div className="field grow">
                <label>NAME</label>
                <input value={selected.name}
                       onChange={(e) => update("name", e.target.value.toUpperCase())} />
              </div>
              <div className="field grow-2">
                <label>RSS · {(selected.urls || []).length}</label>
                <RssChips value={selected.urls} onChange={(v) => update("urls", v)} />
              </div>
            </div>

            <div className="row">
              <div className="field">
                <label>HOSTS</label>
                <Segmented value={selected.hosts} options={[[1, "Solo"], [2, "Duo"]]}
                           onChange={(v) => update("hosts", v)} />
              </div>
              <div className="field">
                <label>TONE</label>
                <Segmented value={selected.tone < 50 ? "casual" : "pro"}
                           options={[["casual", "Casual"], ["pro", "Professional"]]}
                           onChange={(v) => update("tone", v === "casual" ? 25 : 75)} />
              </div>
              <div className="field">
                <label>VOICES</label>
                <div className="voices-row compact">
                  <div className="voice-cell">
                    <span className="vc-tag">A</span>
                    <Segmented value={selected.voiceA} options={[["M", "M"], ["F", "F"]]}
                               onChange={(v) => update("voiceA", v)} />
                  </div>
                  <div className={"voice-cell" + (selected.hosts === 2 ? "" : " disabled")}>
                    <span className="vc-tag">B</span>
                    <Segmented value={selected.voiceB} options={[["M", "M"], ["F", "F"]]}
                               onChange={(v) => selected.hosts === 2 && update("voiceB", v)} />
                  </div>
                </div>
              </div>
            </div>

            <div className="field actions">
              <button className="delete-btn" onClick={() => onDelete(selected.id)}>DELETE VIBE</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function CreateVibeTab({ onCreate }) {
  const [name, setName] = useState("");
  const [hosts, setHosts] = useState(1);
  const [voiceA, setVoiceA] = useState("F");
  const [voiceB, setVoiceB] = useState("M");
  const [tone, setTone] = useState("casual");
  const [urls, setUrls] = useState([]);

  const valid = name.trim().length > 0 && urls.length > 0;

  const submit = () => {
    if (!valid) return;
    onCreate({
      name: name.toUpperCase(),
      tag: "",
      hosts, voiceA, voiceB,
      tone: tone === "casual" ? 25 : 75,
      urls,
      freq: "daily",
    });
    setName(""); setUrls([]); setHosts(1); setVoiceA("F"); setVoiceB("M"); setTone("casual");
  };

  return (
    <div className="create-tab">
      <div className="create-grid">
        <div className="row">
          <div className="field grow">
            <label>NAME</label>
            <input value={name} onChange={(e) => setName(e.target.value.toUpperCase())}
                   placeholder="E.G. MORNING BRIEF" />
          </div>
          <div className="field grow-2">
            <label>RSS · {urls.length}</label>
            <RssChips value={urls} onChange={setUrls} />
          </div>
        </div>

        <div className="row">
          <div className="field">
            <label>HOSTS</label>
            <Segmented value={hosts} options={[[1, "Solo"], [2, "Duo"]]}
                       onChange={setHosts} />
          </div>
          <div className="field">
            <label>TONE</label>
            <Segmented value={tone}
                       options={[["casual", "Casual"], ["pro", "Professional"]]}
                       onChange={setTone} />
          </div>
          <div className="field">
            <label>VOICES</label>
            <div className="voices-row compact">
              <div className="voice-cell">
                <span className="vc-tag">A</span>
                <Segmented value={voiceA} options={[["M", "M"], ["F", "F"]]}
                           onChange={setVoiceA} />
              </div>
              <div className={"voice-cell" + (hosts === 2 ? "" : " disabled")}>
                <span className="vc-tag">B</span>
                <Segmented value={voiceB} options={[["M", "M"], ["F", "F"]]}
                           onChange={(v) => hosts === 2 && setVoiceB(v)} />
              </div>
            </div>
          </div>
        </div>

        <div className="field actions">
          <button className={"create-btn" + (valid ? "" : " disabled")}
                  disabled={!valid} onClick={submit}>CREATE VIBE</button>
        </div>
      </div>
    </div>
  );
}

function ApiTab() {
  const keys = [
    { name: "OpenAI",     key: "sk-proj-•••••••••••••••••••2f8a", set: true },
    { name: "Anthropic",  key: "sk-ant-•••••••••••••••••••a134",  set: true },
    { name: "ElevenLabs", key: "—",                               set: false },
    { name: "Google TTS", key: "—",                               set: false },
  ];
  return (
    <div className="simple-tab">
      <p className="tab-lead">Bring your own keys. Stations use these for generation, voices, and synthesis.</p>
      <div className="key-list">
        {keys.map((k) => (
          <div key={k.name} className="key-row">
            <span className="key-name">{k.name}</span>
            <span className={"key-val" + (k.set ? "" : " unset")}>{k.key}</span>
            <button className="key-edit">{k.set ? "EDIT" : "ADD"}</button>
          </div>
        ))}
      </div>
    </div>
  );
}

function VoicesTab() {
  const voices = [
    { name: "AURA",     gender: "F", desc: "warm · curious · low-mid" },
    { name: "ATLAS",    gender: "M", desc: "dry · steady · baritone" },
    { name: "VESPER",   gender: "F", desc: "cool · precise · alto" },
    { name: "ORION",    gender: "M", desc: "bright · animated · tenor" },
    { name: "TRACE",    gender: "N", desc: "neutral · soft · mid" },
    { name: "CINDER",   gender: "F", desc: "smoky · slow · contralto" },
  ];
  return (
    <div className="simple-tab">
      <p className="tab-lead">Six factory voices. Tap any to preview.</p>
      <div className="voice-grid">
        {voices.map((v) => (
          <button key={v.name} className="voice-card">
            <span className="voice-name">{v.name}</span>
            <span className="voice-gender">{v.gender}</span>
            <span className="voice-desc">{v.desc}</span>
            <span className="voice-play">▸</span>
          </button>
        ))}
      </div>
    </div>
  );
}

function AudioTab() {
  const [bands, setBands] = useState([60, 55, 70, 65, 50]);
  return (
    <div className="simple-tab">
      <p className="tab-lead">Per-device audio shaping. Applies to all stations.</p>
      <div className="eq-row">
        {["60Hz", "230Hz", "910Hz", "3.6kHz", "14kHz"].map((label, i) => (
          <div key={label} className="eq-col">
            <input type="range" min="0" max="100" value={bands[i]} orient="vertical"
                   onChange={(e) => setBands(bands.map((b, j) => j === i ? +e.target.value : b))} />
            <span className="eq-label">{label}</span>
          </div>
        ))}
      </div>
      <div className="audio-toggles">
        <label><input type="checkbox" defaultChecked /> Loudness normalization (-14 LUFS)</label>
        <label><input type="checkbox" /> Voice ducking under music</label>
        <label><input type="checkbox" defaultChecked /> Crossfade between segments</label>
      </div>
    </div>
  );
}

function AboutTab() {
  return (
    <div className="simple-tab about-tab">
      <div className="about-row"><span>MODEL</span><span>VibeFM / MK II</span></div>
      <div className="about-row"><span>SERIAL</span><span>SN-7042-3081</span></div>
      <div className="about-row"><span>FIRMWARE</span><span>2.1.4 (stable)</span></div>
      <div className="about-row"><span>STATIONS</span><span>5 / 12 max</span></div>
      <div className="about-row"><span>UPTIME</span><span>14d 03h 22m</span></div>
      <div className="about-row"><span>STORAGE</span><span>2.4 / 8.0 GB</span></div>
      <p className="about-foot">VibeFM — personal AI radio. Built for one listener.</p>
    </div>
  );
}

function SettingsPanel(props) {
  const [tab, setTab] = useState("vibes");
  const tabs = [
    ["vibes",  "My Vibes"],
    ["create", "Create Vibe"],
    ["api",    "API"],
  ];
  return (
    <div className="settings">
      <div className="settings-head">
        <div className="settings-title">VibeFM · SETTINGS</div>
        <div className="tabs">
          {tabs.map(([k, l]) => (
            <button key={k} className={"tab" + (tab === k ? " active" : "")}
                    onClick={() => setTab(k)}>{l}</button>
          ))}
        </div>
      </div>
      <div className="settings-body">
        {tab === "vibes"  && <StationsTab {...props} />}
        {tab === "create" && <CreateVibeTab onCreate={props.onCreate} />}
        {tab === "api"    && <ApiTab />}
      </div>
    </div>
  );
}

/* ---------- App ---------- */
function App() {
  const [freqMHz, setFreqMHz] = useState(88.3);
  const [timerSec, setTimerSec] = useState(0);
  const [stations, setStations] = useState(DEFAULT_STATIONS);
  const [editingId, setEditingId] = useState(DEFAULT_STATIONS[0].id);
  const [isOpen, setIsOpen] = useState(false);

  const playing = timerSec > 0;

  // closest station to the current dial position
  let closestIdx = 0, closestDist = Infinity;
  stations.forEach((s, i) => {
    const d = Math.abs(s.mhz - freqMHz);
    if (d < closestDist) { closestDist = d; closestIdx = i; }
  });
  const tuned = closestDist < 0.4;
  const station = stations[closestIdx] || stations[0];

  useEffect(() => {
    if (timerSec <= 0) return;
    const id = setInterval(() => setTimerSec((s) => Math.max(0, s - 1)), 1000);
    return () => clearInterval(id);
  }, [timerSec > 0]);

  useEffect(() => {
    const fit = () => {
      const w = Math.max(window.innerWidth - 80, 100);
      const h = Math.max(window.innerHeight - 80, 100);
      const scale = Math.max(0.3, Math.min(w / 720, h / 720, 1));
      document.documentElement.style.setProperty("--device-scale", scale);
    };
    fit();
    window.addEventListener("resize", fit);
    return () => window.removeEventListener("resize", fit);
  }, []);

  const stationStep = (d) => {
    const next = (closestIdx + d + stations.length) % stations.length;
    setFreqMHz(stations[next].mhz);
  };
  const updateStation = (s) => setStations((list) => list.map((x) => x.id === s.id ? s : x));
  const createStation = (partial) => {
    const id = Date.now();
    const base = { id, name: "NEW VIBE", tag: "", mhz: 99.0, hosts: 1, voiceA: "F", voiceB: "M", tone: 50, urls: [], length: 30, freq: "daily" };
    const next = { ...base, ...(partial || {}), id };
    // assign next free MHz slot if not specified
    if (!partial || partial.mhz == null) {
      let m = 88.5;
      while (stations.some((s) => Math.abs(s.mhz - m) < 0.6) && m < 107.5) m += 1.0;
      next.mhz = Math.round(m * 10) / 10;
    }
    setStations((list) => [...list, next]);
    setEditingId(id);
  };
  const deleteStation = (id) => {
    setStations((list) => {
      const next = list.filter((s) => s.id !== id);
      if (next.length) setEditingId(next[0].id);
      return next;
    });
  };

  const minutes = Math.floor(timerSec / 60);
  const seconds = timerSec % 60;
  const timerDisplay = playing ? `${pad(minutes)}:${pad(seconds)}` : "— : —";
  const editing = stations.find((s) => s.id === editingId) || stations[0];

  return (
    <div className="viewport">
      <div className="device">
        <div className="mount"></div>
        <div className="antenna"></div>

        {/* SETTINGS push button — top right of body */}
        <button className={"settings-btn" + (isOpen ? " active" : "")}
                onClick={() => setIsOpen((o) => !o)}>
          {isOpen ? "CLOSE" : "SETTINGS"}
        </button>

        <div className="body">
          <div className="top-bar">
            <div className="knob-cell">
              <Knob value={timerSec} max={TIMER_MAX_SEC} onChange={(v) => setTimerSec(Math.round(v))} color="#c5481e" />
              <span className="knob-label">TIMER</span>
              <span className="knob-value">{playing ? `${pad(minutes)}:${pad(seconds)}` : "OFF"}</span>
            </div>

            <div className="display">
              <div className="display-analyzer" aria-hidden="true">
                <Analyzer playing={playing} columns={28} rows={9} />
              </div>
              <div className="disp-row">
                <span className="disp-eyebrow">
                  {playing ? "▸ ON AIR" : "STANDBY"}
                </span>
                <span className={"power-dot" + (playing ? " on" : "")}></span>
              </div>
              <div className="disp-row">
                <span className="disp-station">
                  {tuned ? station.name : `${freqMHz.toFixed(1)} FM`}
                </span>
                <span className="disp-time">{timerDisplay}</span>
              </div>
              <TunerStrip freq={freqMHz} stations={stations} onSeek={(v) => setFreqMHz(v)} />
            </div>

            <div className="knob-cell">
              <Knob
                value={freqMHz - FREQ_MIN}
                max={FREQ_MAX - FREQ_MIN}
                onChange={(v) => setFreqMHz(Math.round((v + FREQ_MIN) * 10) / 10)}
                color="#e8d8b6"
              />
              <span className="knob-label">TUNE · MHz</span>
              <span className="knob-value">{freqMHz.toFixed(1)}</span>
            </div>
          </div>

          {/* grille area — opens to settings */}
          <div className={"grille-area" + (isOpen ? " open" : "")}>
            <div className="cabinet">
              {[14, 32, 50, 68, 86].map((x, i) => (
                <span key={i} className={"glow" + (playing ? " on" : "")}
                      style={{ left: `${x}%`, animationDelay: `${i * 0.32}s`, top: i === 2 ? "55%" : "45%" }}></span>
              ))}
            </div>

            <SettingsPanel
              stations={stations}
              selected={editing}
              onSelect={setEditingId}
              onChange={updateStation}
              onCreate={createStation}
              onDelete={deleteStation}
            />

            <div className={"grille-panel" + (isOpen ? " open" : "")}></div>
          </div>

          <div className="foot">
            <span className="brand">VibeFM</span>
            <div className="led">
              <span className={"lamp" + (playing ? " on" : "")}></span>
              <span>{playing ? "BROADCASTING" : "STANDBY"}</span>
            </div>
            <span>SN-7042</span>
          </div>

          <div className="feet"><span></span><span></span></div>
        </div>
      </div>
    </div>
  );
}

ReactDOM.createRoot(document.getElementById("root")).render(<App />);
