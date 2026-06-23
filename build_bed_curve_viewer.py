#!/usr/bin/env python3
JB_STR = "jb_A1561_bed_curve_viewer_v01.py since 2026.06.16"
print(JB_STR)

import csv
import html
import json
from pathlib import Path


CSV_NAME = "_jb_debug_inference_20260616_164810.csv"
HTML_NAME = "index.html"
SVG_NAME = "overview_curve_pic.svg"
APP_TITLE = "BED debug inference curve viewer v02 (windows)"
STATE_ORDER = ["EMP", "IBD", "ALT", "NBD", "BTH"]
STATE_TO_Y = {name: idx for idx, name in enumerate(STATE_ORDER)}


def to_float(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def read_rows(csv_path):
    rows = []
    with csv_path.open(newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            fn = int(float(row["fn"]))
            x_sum = sum(to_float(row.get(f"x{i}", 0)) for i in range(1, 7))
            rows.append(
                {
                    "fn": fn,
                    "pred_name": row.get("pred_name", ""),
                    "prev_name": row.get("prev_name", ""),
                    "current_name": row.get("current_name", ""),
                    "final_name": row.get("final_name", ""),
                    "alt_prob": to_float(row.get("alt_prob", 0)),
                    "xsum": x_sum,
                    "current_changed": row.get("current_name", "") != row.get("final_name", ""),
                }
            )
    return rows


def make_overview_svg(rows, svg_path):
    width = 1600
    height = 700
    pad_l = 70
    pad_r = 30
    pad_t = 45
    state_h = 360
    gap = 32
    curve_h = 220
    min_fn = rows[0]["fn"]
    max_fn = rows[-1]["fn"]
    max_xsum = max(row["xsum"] for row in rows) or 1

    def sx(fn):
        return pad_l + (fn - min_fn) / max(1, max_fn - min_fn) * (width - pad_l - pad_r)

    def sy_state(name):
        return pad_t + (len(STATE_ORDER) - 1 - STATE_TO_Y.get(name, 0)) / (len(STATE_ORDER) - 1) * state_h

    def sy_curve(v):
        top = pad_t + state_h + gap
        return top + curve_h - (v / max_xsum) * curve_h

    chunks = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#fbfbfb"/>',
        '<style>text{font-family:Arial,sans-serif;fill:#263238}.grid{stroke:#dfe5e8;stroke-width:1}.axis{stroke:#65727a;stroke-width:1.3}.shade{fill:#d7e7f0;opacity:.55}.pred{stroke:#2f7cc0}.current{stroke:#3b9d46}.final{stroke:#d14524}.curve{stroke:#2677bf;fill:none;stroke-width:1.4}</style>',
        '<text x="800" y="28" text-anchor="middle" font-size="20">BED debug inference overview</text>',
    ]

    in_shade = False
    shade_start = None
    for row in rows:
        if row["current_changed"] and not in_shade:
            in_shade = True
            shade_start = row["fn"]
        if in_shade and not row["current_changed"]:
            x = sx(shade_start)
            w = max(1, sx(row["fn"]) - x)
            chunks.append(f'<rect class="shade" x="{x:.2f}" y="{pad_t}" width="{w:.2f}" height="{state_h + gap + curve_h}"/>')
            in_shade = False
    if in_shade:
        x = sx(shade_start)
        chunks.append(f'<rect class="shade" x="{x:.2f}" y="{pad_t}" width="{sx(max_fn) - x:.2f}" height="{state_h + gap + curve_h}"/>')

    for state in STATE_ORDER:
        y = sy_state(state)
        chunks.append(f'<line class="grid" x1="{pad_l}" y1="{y:.2f}" x2="{width - pad_r}" y2="{y:.2f}"/>')
        chunks.append(f'<text x="{pad_l - 14}" y="{y + 5:.2f}" text-anchor="end" font-size="14">{state}</text>')

    for cls, key in [("pred", "pred_name"), ("current", "current_name"), ("final", "final_name")]:
        pts = " ".join(f'{sx(row["fn"]):.2f},{sy_state(row[key]):.2f}' for row in rows)
        chunks.append(f'<polyline class="{cls}" points="{pts}" fill="none" stroke-width="1.5"/>')

    chunks.append(f'<line class="axis" x1="{pad_l}" y1="{pad_t}" x2="{pad_l}" y2="{pad_t + state_h}"/>')
    chunks.append(f'<line class="axis" x1="{pad_l}" y1="{pad_t + state_h}" x2="{width - pad_r}" y2="{pad_t + state_h}"/>')

    curve_top = pad_t + state_h + gap
    chunks.append(f'<line class="axis" x1="{pad_l}" y1="{curve_top}" x2="{pad_l}" y2="{curve_top + curve_h}"/>')
    chunks.append(f'<line class="axis" x1="{pad_l}" y1="{curve_top + curve_h}" x2="{width - pad_r}" y2="{curve_top + curve_h}"/>')
    curve_pts = " ".join(f'{sx(row["fn"]):.2f},{sy_curve(row["xsum"]):.2f}' for row in rows)
    chunks.append(f'<polyline class="curve" points="{curve_pts}"/>')
    chunks.append(f'<text x="{pad_l - 14}" y="{curve_top + 5}" text-anchor="end" font-size="14">{int(max_xsum)}</text>')
    chunks.append(f'<text x="{pad_l - 14}" y="{curve_top + curve_h + 5}" text-anchor="end" font-size="14">0</text>')
    chunks.append(f'<text x="{width / 2}" y="{height - 16}" text-anchor="middle" font-size="15">fn {min_fn} ... {max_fn}</text>')
    chunks.append("</svg>")
    svg_path.write_text("\n".join(chunks), encoding="utf-8")


def make_html(rows, html_path):
    data_json = json.dumps(rows, separators=(",", ":"))
    csv_files = sorted(
        path.name
        for path in html_path.parent.iterdir()
        if path.is_file() and path.suffix.lower() == ".csv" and not path.name.startswith(".")
    )
    csv_files_json = json.dumps(csv_files, separators=(",", ":"))
    min_fn = rows[0]["fn"]
    max_fn = rows[-1]["fn"]
    max_xsum = max(row["xsum"] for row in rows) or 1
    title = html.escape(CSV_NAME)
    html_text = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{APP_TITLE}</title>
  <style>
    :root {{
      color-scheme: light;
      --bg: #f6f8fa;
      --panel: #ffffff;
      --line: #d9e0e5;
      --text: #18232b;
      --muted: #65727c;
      --blue: #2f7cc0;
      --orange: #ee8b31;
      --green: #3b9d46;
      --red: #d14524;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      background: var(--bg);
      color: var(--text);
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Arial, sans-serif;
    }}
    header {{
      display: grid;
      grid-template-columns: 1fr auto;
      gap: 12px;
      align-items: center;
      padding: 14px 18px;
      background: var(--panel);
      border-bottom: 1px solid var(--line);
      position: sticky;
      top: 0;
      z-index: 5;
    }}
    h1 {{
      margin: 0;
      font-size: 18px;
      font-weight: 700;
      letter-spacing: 0;
    }}
    .sub {{
      margin-top: 4px;
      color: var(--muted);
      font-size: 13px;
    }}
    .toolbar {{
      display: flex;
      gap: 8px;
      flex-wrap: wrap;
      justify-content: flex-end;
    }}
    button, select, .file-button {{
      height: 34px;
      border: 1px solid #c6d0d8;
      border-radius: 7px;
      background: #fff;
      color: var(--text);
      padding: 0 10px;
      font-size: 13px;
      cursor: pointer;
    }}
    .file-button {{
      display: inline-flex;
      align-items: center;
      gap: 6px;
      white-space: nowrap;
    }}
    .file-button input {{ display: none; }}
    button:hover, .file-button:hover {{ background: #eef4f8; }}
    .folder-select {{
      min-width: 210px;
      max-width: 320px;
    }}
    main {{
      height: calc(100vh - 67px);
      display: grid;
      grid-template-rows: auto 1fr auto;
      gap: 10px;
      padding: 12px;
    }}
    .controls {{
      display: grid;
      grid-template-columns: 86px 1fr 92px 130px;
      gap: 10px;
      align-items: center;
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 10px 12px;
    }}
    label {{ font-weight: 650; font-size: 13px; }}
    input[type="range"] {{ width: 100%; }}
    output {{
      font-variant-numeric: tabular-nums;
      font-size: 14px;
      color: #0f3146;
    }}
    .readout {{
      font-variant-numeric: tabular-nums;
      color: var(--muted);
      text-align: right;
      font-size: 13px;
    }}
    .state-percentages {{
      grid-column: 1 / -1;
      display: flex;
      gap: 8px;
      flex-wrap: wrap;
      align-items: center;
      font-size: 13px;
      color: var(--text);
    }}
    .percent-chip {{
      border: 1px solid #cbd6dd;
      background: #fff;
      border-radius: 6px;
      padding: 5px 8px;
      font-variant-numeric: tabular-nums;
    }}
    .percent-chip strong {{
      margin-right: 4px;
      color: #0f3146;
    }}
    .plot-wrap {{
      min-height: 420px;
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      overflow: hidden;
      position: relative;
    }}
    canvas {{
      width: 100%;
      height: 100%;
      display: block;
      cursor: grab;
    }}
    canvas.dragging {{ cursor: grabbing; }}
    .hint {{
      position: absolute;
      right: 12px;
      bottom: 10px;
      color: #5f6c76;
      font-size: 12px;
      background: rgba(255,255,255,.82);
      border: 1px solid rgba(190,202,211,.75);
      border-radius: 6px;
      padding: 5px 7px;
      pointer-events: none;
    }}
    .legend {{
      display: flex;
      flex-wrap: wrap;
      gap: 12px 18px;
      align-items: center;
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 9px 12px;
      font-size: 13px;
    }}
    .item {{ display: inline-flex; align-items: center; gap: 6px; }}
    .swatch {{ width: 22px; height: 3px; border-radius: 2px; display: inline-block; }}
    .box {{ width: 16px; height: 10px; background: rgba(111,166,201,.22); border: 1px solid rgba(111,166,201,.45); display: inline-block; }}
    .triangle {{
      width: 0;
      height: 0;
      border-left: 7px solid transparent;
      border-right: 7px solid transparent;
      border-bottom: 16px solid #2f7cc0;
      filter: drop-shadow(0 0 0 #173a59);
    }}
    .keep-square {{
      width: 14px;
      height: 14px;
      background: #2e9f51;
      border: 1px solid #176f35;
      border-radius: 2px;
      display: inline-block;
    }}
    .low-cloud-dot {{
      width: 13px;
      height: 13px;
      background: #8e44ad;
      border: 2px solid #ffffff;
      box-shadow: 0 0 0 1px #5e2b75;
      border-radius: 50%;
      display: inline-block;
    }}
    @media (max-width: 760px) {{
      header {{ grid-template-columns: 1fr; }}
      .toolbar {{ justify-content: flex-start; }}
      main {{ height: auto; min-height: calc(100vh - 67px); }}
      .plot-wrap {{ height: 65vh; }}
      .controls {{ grid-template-columns: 62px 1fr 78px; }}
      .readout {{ grid-column: 1 / -1; text-align: left; }}
    }}
  </style>
</head>
<body>
  <header>
    <div>
      <h1>{APP_TITLE}</h1>
      <div id="datasetInfo" class="sub">{title} · {len(rows)} rows · fn {min_fn} to {max_fn}</div>
    </div>
    <div class="toolbar">
      <button id="localPcBtn" type="button" title="Read CSV from this Windows PC">1 Local PC</button>
      <input id="csvFile" type="file" accept=".csv,text/csv" hidden>
      <button id="githubRepoBtn" type="button" title="Read selected CSV from GitHub repository">2 GitHub repo</button>
      <button id="dropboxLinkBtn" type="button" title="Read CSV from a Dropbox shared link">3 Dropbox link</button>
      <select id="folderFileSelect" class="folder-select" title="CSV files in this folder"></select>
      <button id="openFolderFileBtn" type="button">Load CSV</button>
      <select id="followMode" title="Slider behavior">
        <option value="center">slider centers view</option>
        <option value="cursor">slider moves cursor only</option>
      </select>
      <button id="resetBtn" type="button">Reset view</button>
      <button id="exportBtn" type="button">Save PNG</button>
    </div>
  </header>
  <main>
    <section class="controls" aria-label="fn slider">
      <label for="fnSlider">fn</label>
      <input id="fnSlider" type="range" min="{min_fn}" max="{max_fn}" value="{min_fn}" step="1">
      <output id="fnValue">{min_fn}</output>
      <div id="pointReadout" class="readout"></div>
      <div id="statePercentages" class="state-percentages"></div>
    </section>
    <section class="plot-wrap">
      <canvas id="plot"></canvas>
      <div class="hint">drag = pan · wheel = zoom · shift+wheel = vertical zoom</div>
    </section>
    <section class="legend">
      <span class="item"><span class="swatch" style="background:var(--blue)"></span>pred_name</span>
      <span class="item"><span class="swatch" style="background:var(--green)"></span>current_name</span>
      <span class="item"><span class="swatch" style="background:var(--red)"></span>final_name</span>
      <span class="item"><span class="swatch" style="background:#2677bf"></span>sum(x1..x6)</span>
      <span class="item"><span class="triangle"></span>ALT entry point</span>
      <span class="item"><span class="keep-square"></span>KEEP IBD state</span>
      <span class="item"><span class="low-cloud-dot"></span>NBD sum &lt; 10</span>
      <span class="item"><span class="swatch" style="background:#d6a500;border-top:1px dashed #d6a500"></span>YELLOW on ALT</span>
      <span class="item"><span class="swatch" style="background:#2e9f51;border-top:1px dashed #2e9f51"></span>GREEN on IBD</span>
      <span class="item"><span class="box"></span>current_name != final_name</span>
    </section>
  </main>
  <script>
    let rows = {data_json};
    const csvFiles = {csv_files_json};
    const githubRawBase = "https://raw.githubusercontent.com/greenmoon/codex_on_bed_project_windowsBased/main/";
    const stateOrder = {json.dumps(STATE_ORDER)};
    const stateToY = Object.fromEntries(stateOrder.map((name, i) => [name, i]));
    const fnDurationMs = 80;
    let minFn = {min_fn};
    let maxFn = {max_fn};
    let maxXsum = {max_xsum};
    let currentCsvName = {json.dumps(CSV_NAME)};
    const canvas = document.getElementById("plot");
    const slider = document.getElementById("fnSlider");
    const fnValue = document.getElementById("fnValue");
    const readout = document.getElementById("pointReadout");
    const datasetInfo = document.getElementById("datasetInfo");
    const statePercentages = document.getElementById("statePercentages");
    const localPcBtn = document.getElementById("localPcBtn");
    const csvFile = document.getElementById("csvFile");
    const githubRepoBtn = document.getElementById("githubRepoBtn");
    const dropboxLinkBtn = document.getElementById("dropboxLinkBtn");
    const folderFileSelect = document.getElementById("folderFileSelect");
    const openFolderFileBtn = document.getElementById("openFolderFileBtn");
    const followMode = document.getElementById("followMode");
    const resetBtn = document.getElementById("resetBtn");
    const exportBtn = document.getElementById("exportBtn");
    const ctx = canvas.getContext("2d");
    const colors = {{
      pred_name: "#2f7cc0",
      current_name: "#3b9d46",
      final_name: "#d14524",
      xsum: "#2677bf",
      grid: "#dfe5e8",
      text: "#263238",
      axis: "#65727a",
      guideYellow: "#d6a500",
      guideGreen: "#2e9f51",
      lowCloud: "#8e44ad",
      lowCloudStroke: "#5e2b75",
      shade: "rgba(111,166,201,.18)",
      cursor: "rgba(24,35,43,.62)"
    }};
    let cursorFn = minFn;
    let view = {{ xMin: minFn, xMax: maxFn, curveYMin: 0, curveYMax: Math.max(10, maxXsum * 1.06) }};
    let dragging = false;
    let lastMouse = null;
    let pointer = null;

    function resizeCanvas() {{
      const rect = canvas.getBoundingClientRect();
      const dpr = window.devicePixelRatio || 1;
      canvas.width = Math.max(300, Math.floor(rect.width * dpr));
      canvas.height = Math.max(300, Math.floor(rect.height * dpr));
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      draw();
    }}

    function layout() {{
      const w = canvas.clientWidth;
      const h = canvas.clientHeight;
      const pad = {{ l: 82, r: 34, t: 44, b: 42 }};
      const stateH = Math.max(190, Math.floor((h - pad.t - pad.b) * 0.56));
      const gap = 30;
      const curveTop = pad.t + stateH + gap;
      const curveH = Math.max(120, h - curveTop - pad.b);
      return {{ w, h, pad, stateH, gap, curveTop, curveH, plotW: w - pad.l - pad.r }};
    }}

    function xToScreen(fn, L = layout()) {{
      return L.pad.l + (fn - view.xMin) / (view.xMax - view.xMin) * L.plotW;
    }}

    function screenToX(x, L = layout()) {{
      return view.xMin + (x - L.pad.l) / L.plotW * (view.xMax - view.xMin);
    }}

    function stateToScreen(name, L = layout()) {{
      const idx = stateToY[name] ?? 0;
      const innerTop = L.pad.t + 20;
      const innerH = L.stateH - 20;
      return innerTop + (stateOrder.length - 1 - idx) / (stateOrder.length - 1) * innerH;
    }}

    function curveToScreen(v, L = layout()) {{
      return L.curveTop + L.curveH - (v - view.curveYMin) / (view.curveYMax - view.curveYMin) * L.curveH;
    }}

    function visibleRows(extra = 2) {{
      const left = view.xMin - extra;
      const right = view.xMax + extra;
      return rows.filter(r => r.fn >= left && r.fn <= right);
    }}

    function nearestRow(fn) {{
      let lo = 0;
      let hi = rows.length - 1;
      while (lo < hi) {{
        const mid = Math.floor((lo + hi) / 2);
        if (rows[mid].fn < fn) lo = mid + 1;
        else hi = mid;
      }}
      const a = rows[Math.max(0, lo - 1)];
      const b = rows[Math.min(rows.length - 1, lo)];
      return Math.abs(a.fn - fn) <= Math.abs(b.fn - fn) ? a : b;
    }}

    function parseCsvText(text) {{
      const table = [];
      let row = [];
      let cell = "";
      let inQuotes = false;
      for (let i = 0; i < text.length; i++) {{
        const ch = text[i];
        const next = text[i + 1];
        if (ch === '"') {{
          if (inQuotes && next === '"') {{
            cell += '"';
            i += 1;
          }} else {{
            inQuotes = !inQuotes;
          }}
        }} else if (ch === "," && !inQuotes) {{
          row.push(cell);
          cell = "";
        }} else if ((ch === "\\n" || ch === "\\r") && !inQuotes) {{
          if (ch === "\\r" && next === "\\n") i += 1;
          row.push(cell);
          if (row.some(value => value.trim() !== "")) table.push(row);
          row = [];
          cell = "";
        }} else {{
          cell += ch;
        }}
      }}
      row.push(cell);
      if (row.some(value => value.trim() !== "")) table.push(row);
      return table;
    }}

    function toNumber(value, fallback = 0) {{
      const n = Number(value);
      return Number.isFinite(n) ? n : fallback;
    }}

    function formatElapsedTime(totalMs) {{
      totalMs = Math.max(0, Math.round(totalMs));
      const ms = totalMs % 1000;
      const totalSeconds = Math.floor(totalMs / 1000);
      const seconds = totalSeconds % 60;
      const totalMinutes = Math.floor(totalSeconds / 60);
      const minutes = totalMinutes % 60;
      const hours = Math.floor(totalMinutes / 60);
      return `${{String(hours).padStart(2, "0")}}:${{String(minutes).padStart(2, "0")}}:${{String(seconds).padStart(2, "0")}}.${{String(ms).padStart(3, "0")}}`;
    }}

    function formatFnTime(fn) {{
      return formatElapsedTime((fn - minFn) * fnDurationMs);
    }}

    function rowsFromCsv(text) {{
      const table = parseCsvText(text);
      if (table.length < 2) throw new Error("CSV has no data rows");
      const headers = table[0].map(name => name.trim().replace(/^\\uFEFF/, ""));
      const index = Object.fromEntries(headers.map((name, i) => [name, i]));
      for (const required of ["fn", "pred_name", "current_name", "final_name"]) {{
        if (!(required in index)) throw new Error(`Missing required column: ${{required}}`);
      }}
      const parsed = [];
      for (const values of table.slice(1)) {{
        const get = (name) => values[index[name]] ?? "";
        const fn = Math.round(toNumber(get("fn"), NaN));
        if (!Number.isFinite(fn)) continue;
        let xsum = 0;
        for (let i = 1; i <= 6; i++) xsum += toNumber(get(`x${{i}}`), 0);
        const currentName = get("current_name");
        const finalName = get("final_name");
        parsed.push({{
          fn,
          pred_name: get("pred_name"),
          prev_name: "prev_name" in index ? get("prev_name") : "",
          current_name: currentName,
          final_name: finalName,
          alt_prob: "alt_prob" in index ? toNumber(get("alt_prob"), 0) : 0,
          xsum,
          current_changed: currentName !== finalName
        }});
      }}
      if (!parsed.length) throw new Error("CSV has no valid fn rows");
      parsed.sort((a, b) => a.fn - b.fn);
      return parsed;
    }}

    function formatPercent(count, total) {{
      if (!total) return "0.0%";
      return `${{(count / total * 100).toFixed(1)}}%`;
    }}

    function updateStatePercentages() {{
      const total = rows.length;
      const ibd = rows.filter(row => row.final_name === "IBD").length;
      const emp = rows.filter(row => row.final_name === "EMP").length;
      const ibdEmp = ibd + emp;
      statePercentages.innerHTML = `
        <span class="percent-chip"><strong>IBD</strong>${{formatPercent(ibd, total)}} (${{ibd}}/${{total}})</span>
        <span class="percent-chip"><strong>EMP</strong>${{formatPercent(emp, total)}} (${{emp}}/${{total}})</span>
        <span class="percent-chip"><strong>IBD+EMP</strong>${{formatPercent(ibdEmp, total)}} (${{ibdEmp}}/${{total}})</span>
      `;
    }}

    function setDataset(nextRows, fileName) {{
      rows = nextRows;
      minFn = rows[0].fn;
      maxFn = rows[rows.length - 1].fn;
      maxXsum = Math.max(1, ...rows.map(row => row.xsum));
      currentCsvName = fileName;
      slider.min = String(minFn);
      slider.max = String(maxFn);
      slider.value = String(minFn);
      fnValue.value = String(minFn);
      cursorFn = minFn;
      view = {{ xMin: minFn, xMax: maxFn, curveYMin: 0, curveYMax: Math.max(10, maxXsum * 1.06) }};
      datasetInfo.textContent = `${{currentCsvName}} · ${{rows.length}} rows · fn ${{minFn}} to ${{maxFn}}`;
      updateStatePercentages();
      draw();
    }}

    function fileUrl(fileName) {{
      return fileName.split("/").map(part => encodeURIComponent(part)).join("/");
    }}

    function populateWorkingFiles() {{
      folderFileSelect.innerHTML = "";
      for (const fileName of csvFiles) {{
        const option = document.createElement("option");
        option.value = fileName;
        option.textContent = fileName;
        if (fileName === currentCsvName) option.selected = true;
        folderFileSelect.appendChild(option);
      }}
    }}

    async function fetchCsvUrl(url, displayName) {{
      try {{
        readout.textContent = `Loading ${{displayName}} ...`;
        const response = await fetch(url);
        if (!response.ok) throw new Error(`HTTP ${{response.status}}`);
        const text = await response.text();
        const nextRows = rowsFromCsv(text);
        setDataset(nextRows, displayName);
      }} catch (error) {{
        readout.textContent = `CSV load error: ${{error.message}}`;
      }}
    }}

    async function openWorkingFile(fileName) {{
      if (!fileName) return;
      fetchCsvUrl(fileUrl(fileName), fileName);
    }}

    async function openGithubFile(fileName) {{
      if (!fileName) return;
      fetchCsvUrl(githubRawBase + fileUrl(fileName), `GitHub: ${{fileName}}`);
    }}

    function normalizeDropboxUrl(url) {{
      const trimmed = url.trim();
      if (!trimmed) return "";
      try {{
        const parsed = new URL(trimmed);
        if (parsed.hostname.endsWith("dropbox.com")) {{
          parsed.searchParams.delete("dl");
          parsed.searchParams.delete("raw");
          parsed.searchParams.set("raw", "1");
          return parsed.toString();
        }}
      }} catch (error) {{
        return trimmed;
      }}
      return trimmed;
    }}

    function drawGrid(L) {{
      ctx.clearRect(0, 0, L.w, L.h);
      ctx.fillStyle = "#fbfbfb";
      ctx.fillRect(0, 0, L.w, L.h);
      ctx.font = "13px -apple-system, BlinkMacSystemFont, Segoe UI, Arial";
      ctx.textBaseline = "middle";
      ctx.strokeStyle = colors.grid;
      ctx.lineWidth = 1;

      for (const state of stateOrder) {{
        const y = stateToScreen(state, L);
        ctx.beginPath();
        ctx.moveTo(L.pad.l, y);
        ctx.lineTo(L.w - L.pad.r, y);
        ctx.stroke();
        ctx.fillStyle = colors.text;
        ctx.textAlign = "right";
        ctx.fillText(state, L.pad.l - 12, y);
      }}

      drawStateGuide(L, "ALT", colors.guideYellow, "YELLOW");
      drawStateGuide(L, "IBD", colors.guideGreen, "GREEN");

      ctx.font = "12px -apple-system, BlinkMacSystemFont, Segoe UI, Arial";
      ctx.fillStyle = colors.text;
      ctx.textBaseline = "alphabetic";
      ctx.textAlign = "left";
      ctx.fillText(formatFnTime(view.xMin), L.pad.l, L.pad.t - 26);
      ctx.textAlign = "center";
      ctx.fillText(`dt=${{formatElapsedTime((view.xMax - view.xMin) * fnDurationMs)}}`, L.pad.l + L.plotW / 2, L.pad.t - 26);
      ctx.textAlign = "right";
      ctx.fillText(formatFnTime(view.xMax), L.w - L.pad.r, L.pad.t - 26);
      ctx.textBaseline = "middle";
      ctx.font = "13px -apple-system, BlinkMacSystemFont, Segoe UI, Arial";

      const ticks = 6;
      ctx.textAlign = "center";
      ctx.fillStyle = colors.text;
      for (let i = 0; i <= ticks; i++) {{
        const fn = view.xMin + (view.xMax - view.xMin) * i / ticks;
        const x = xToScreen(fn, L);
        ctx.strokeStyle = colors.grid;
        ctx.beginPath();
        ctx.moveTo(x, L.pad.t);
        ctx.lineTo(x, L.curveTop + L.curveH);
        ctx.stroke();
        if (i === 0) ctx.textAlign = "left";
        else if (i === ticks) ctx.textAlign = "right";
        else ctx.textAlign = "center";
        ctx.fillText(String(Math.round(fn)), x, L.h - 20);
      }}

      const yTicks = 4;
      ctx.textAlign = "right";
      for (let i = 0; i <= yTicks; i++) {{
        const val = view.curveYMin + (view.curveYMax - view.curveYMin) * i / yTicks;
        const y = curveToScreen(val, L);
        ctx.strokeStyle = colors.grid;
        ctx.beginPath();
        ctx.moveTo(L.pad.l, y);
        ctx.lineTo(L.w - L.pad.r, y);
        ctx.stroke();
        ctx.fillStyle = colors.text;
        ctx.fillText(String(Math.round(val)), L.pad.l - 12, y);
      }}

      ctx.strokeStyle = colors.axis;
      ctx.lineWidth = 1.2;
      for (const [top, bottom] of [[L.pad.t, L.pad.t + L.stateH], [L.curveTop, L.curveTop + L.curveH]]) {{
        ctx.beginPath();
        ctx.moveTo(L.pad.l, top);
        ctx.lineTo(L.pad.l, bottom);
        ctx.lineTo(L.w - L.pad.r, bottom);
        ctx.stroke();
      }}

      ctx.textAlign = "left";
      ctx.fillStyle = colors.text;
      ctx.font = "14px -apple-system, BlinkMacSystemFont, Segoe UI, Arial";
      ctx.fillText("State", L.pad.l, L.pad.t - 8);
      ctx.fillText("sum(x1..x6)", L.pad.l, L.curveTop - 18);
      ctx.textAlign = "center";
      ctx.fillText("fn", L.pad.l + L.plotW / 2, L.h - 7);
    }}

    function drawStateGuide(L, state, color, label) {{
      const y = stateToScreen(state, L);
      ctx.save();
      ctx.strokeStyle = color;
      ctx.lineWidth = 2;
      ctx.setLineDash([9, 7]);
      ctx.beginPath();
      ctx.moveTo(L.pad.l, y);
      ctx.lineTo(L.w - L.pad.r, y);
      ctx.stroke();
      ctx.setLineDash([]);
      ctx.fillStyle = "rgba(255,255,255,.88)";
      ctx.strokeStyle = color;
      ctx.lineWidth = 1;
      ctx.font = "12px -apple-system, BlinkMacSystemFont, Segoe UI, Arial";
      const text = `${{label}} on ${{state}}`;
      const textWidth = ctx.measureText(text).width;
      const boxX = L.w - L.pad.r - textWidth - 14;
      const boxY = y - 12;
      roundRect(boxX, boxY, textWidth + 10, 22, 5);
      ctx.fill();
      ctx.stroke();
      ctx.fillStyle = color;
      ctx.textAlign = "left";
      ctx.textBaseline = "middle";
      ctx.fillText(text, boxX + 5, y);
      ctx.restore();
    }}

    function drawShades(L, data) {{
      let start = null;
      for (const row of data) {{
        if (row.current_changed && start === null) start = row.fn;
        if (!row.current_changed && start !== null) {{
          drawShadeBand(L, start, row.fn);
          start = null;
        }}
      }}
      if (start !== null) drawShadeBand(L, start, data[data.length - 1].fn);
    }}

    function drawShadeBand(L, startFn, endFn) {{
      const x1 = xToScreen(startFn, L);
      const x2 = xToScreen(endFn, L);
      ctx.fillStyle = colors.shade;
      ctx.fillRect(Math.max(L.pad.l, x1), L.pad.t, Math.max(1, x2 - x1), L.curveTop + L.curveH - L.pad.t);
    }}

    function drawStepLine(L, data, key, color) {{
      if (!data.length) return;
      ctx.strokeStyle = color;
      ctx.lineWidth = 1.8;
      ctx.beginPath();
      let lastX = xToScreen(data[0].fn, L);
      let lastY = stateToScreen(data[0][key], L);
      ctx.moveTo(lastX, lastY);
      for (let i = 1; i < data.length; i++) {{
        const x = xToScreen(data[i].fn, L);
        const y = stateToScreen(data[i][key], L);
        ctx.lineTo(x, lastY);
        ctx.lineTo(x, y);
        lastX = x;
        lastY = y;
      }}
      ctx.stroke();
    }}

    function drawCurve(L, data) {{
      if (!data.length) return;
      ctx.strokeStyle = colors.xsum;
      ctx.lineWidth = 1.7;
      ctx.beginPath();
      data.forEach((row, i) => {{
        const x = xToScreen(row.fn, L);
        const y = curveToScreen(row.xsum, L);
        if (i === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
      }});
      ctx.stroke();
    }}

    function drawAltEntryMarkers(L, data) {{
      ctx.fillStyle = "#2f7cc0";
      ctx.strokeStyle = "#173a59";
      ctx.lineWidth = 1.3;
      let prev = null;
      for (const row of data) {{
        const enteredAlt = row.final_name === "ALT" && prev && prev.final_name !== "ALT";
        if (enteredAlt) {{
          const x = xToScreen(row.fn, L);
          const y = stateToScreen("ALT", L);
          ctx.beginPath();
          ctx.moveTo(x, y - 9);
          ctx.lineTo(x - 7, y + 7);
          ctx.lineTo(x + 7, y + 7);
          ctx.closePath();
          ctx.fill();
          ctx.stroke();
        }}
        prev = row;
      }}
    }}

    function drawKeepIbdMarkers(L, data) {{
      ctx.fillStyle = "#2e9f51";
      ctx.strokeStyle = "#176f35";
      ctx.lineWidth = 1.2;
      const y = stateToScreen("IBD", L);
      let lastX = -Infinity;
      for (const row of data) {{
        const keepIbd = row.current_name !== row.final_name && row.final_name === "IBD";
        if (!keepIbd) continue;
        const x = xToScreen(row.fn, L);
        if (x - lastX < 16) continue;
        ctx.beginPath();
        ctx.rect(x - 5, y - 5, 10, 10);
        ctx.fill();
        ctx.stroke();
        lastX = x;
      }}
    }}

    function drawLowCloudNbdMarkers(L, data) {{
      ctx.fillStyle = colors.lowCloud;
      ctx.strokeStyle = colors.lowCloudStroke;
      ctx.lineWidth = 1.4;
      const y = stateToScreen("NBD", L);
      let lastX = -Infinity;
      for (const row of data) {{
        const lowCloudNbd = row.final_name === "NBD" && row.xsum < 10;
        if (!lowCloudNbd) continue;
        const x = xToScreen(row.fn, L);
        if (x - lastX < 10) continue;
        ctx.beginPath();
        ctx.arc(x, y, 4.8, 0, Math.PI * 2);
        ctx.fill();
        ctx.stroke();
        lastX = x;
      }}
    }}

    function drawCursor(L) {{
      const row = nearestRow(cursorFn);
      const x = xToScreen(row.fn, L);
      ctx.strokeStyle = colors.cursor;
      ctx.lineWidth = 1;
      ctx.setLineDash([4, 4]);
      ctx.beginPath();
      ctx.moveTo(x, L.pad.t);
      ctx.lineTo(x, L.curveTop + L.curveH);
      ctx.stroke();
      ctx.setLineDash([]);

      const cy = curveToScreen(row.xsum, L);
      ctx.fillStyle = "#ffffff";
      ctx.strokeStyle = colors.xsum;
      ctx.lineWidth = 2;
      ctx.beginPath();
      ctx.arc(x, cy, 4, 0, Math.PI * 2);
      ctx.fill();
      ctx.stroke();

      fnValue.value = String(row.fn);
      readout.textContent = `pred ${{row.pred_name}} · current ${{row.current_name}} · final ${{row.final_name}} · sum(x1..x6) ${{Math.round(row.xsum)}}`;
    }}

    function drawPointer(L) {{
      if (!pointer) return;
      const row = nearestRow(screenToX(pointer.x, L));
      const x = xToScreen(row.fn, L);
      const y = pointer.y < L.curveTop ? stateToScreen(row.final_name, L) : curveToScreen(row.xsum, L);
      ctx.fillStyle = "rgba(255,255,255,.94)";
      ctx.strokeStyle = "#b6c2ca";
      ctx.lineWidth = 1;
      const text = `fn ${{row.fn}}  pred ${{row.pred_name}}  current ${{row.current_name}}  final ${{row.final_name}}  sum ${{Math.round(row.xsum)}}`;
      ctx.font = "12px -apple-system, BlinkMacSystemFont, Segoe UI, Arial";
      const tw = ctx.measureText(text).width + 18;
      const boxX = Math.min(Math.max(L.pad.l, x + 12), L.w - L.pad.r - tw);
      const boxY = Math.max(8, y - 34);
      roundRect(boxX, boxY, tw, 25, 6);
      ctx.fill();
      ctx.stroke();
      ctx.fillStyle = colors.text;
      ctx.textAlign = "left";
      ctx.textBaseline = "middle";
      ctx.fillText(text, boxX + 9, boxY + 13);
    }}

    function roundRect(x, y, w, h, r) {{
      ctx.beginPath();
      ctx.moveTo(x + r, y);
      ctx.arcTo(x + w, y, x + w, y + h, r);
      ctx.arcTo(x + w, y + h, x, y + h, r);
      ctx.arcTo(x, y + h, x, y, r);
      ctx.arcTo(x, y, x + w, y, r);
      ctx.closePath();
    }}

    function draw() {{
      const L = layout();
      const data = visibleRows();
      drawGrid(L);
      drawShades(L, data);
      drawStepLine(L, data, "pred_name", colors.pred_name);
      drawStepLine(L, data, "current_name", colors.current_name);
      drawStepLine(L, data, "final_name", colors.final_name);
      drawKeepIbdMarkers(L, data);
      drawLowCloudNbdMarkers(L, data);
      drawAltEntryMarkers(L, data);
      drawCurve(L, data);
      drawCursor(L);
      drawPointer(L);
    }}

    function clampView() {{
      const minWidth = 20;
      if (view.xMax - view.xMin < minWidth) {{
        const c = (view.xMin + view.xMax) / 2;
        view.xMin = c - minWidth / 2;
        view.xMax = c + minWidth / 2;
      }}
      const width = view.xMax - view.xMin;
      if (view.xMin < minFn) {{
        view.xMin = minFn;
        view.xMax = minFn + width;
      }}
      if (view.xMax > maxFn) {{
        view.xMax = maxFn;
        view.xMin = maxFn - width;
      }}
      view.xMin = Math.max(minFn, view.xMin);
      view.xMax = Math.min(maxFn, view.xMax);
      if (view.curveYMax - view.curveYMin < 5) view.curveYMax = view.curveYMin + 5;
      view.curveYMin = Math.max(0, view.curveYMin);
    }}

    function centerOn(fn) {{
      const width = view.xMax - view.xMin;
      view.xMin = fn - width / 2;
      view.xMax = fn + width / 2;
      clampView();
    }}

    localPcBtn.addEventListener("click", () => {{
      csvFile.click();
    }});

    csvFile.addEventListener("change", async () => {{
      const file = csvFile.files && csvFile.files[0];
      if (!file) return;
      try {{
        const text = await file.text();
        const nextRows = rowsFromCsv(text);
        setDataset(nextRows, file.name);
      }} catch (error) {{
        readout.textContent = `CSV load error: ${{error.message}}`;
      }} finally {{
        csvFile.value = "";
      }}
    }});

    openFolderFileBtn.addEventListener("click", () => {{
      openWorkingFile(folderFileSelect.value);
    }});

    githubRepoBtn.addEventListener("click", () => {{
      openGithubFile(folderFileSelect.value);
    }});

    dropboxLinkBtn.addEventListener("click", () => {{
      const url = normalizeDropboxUrl(prompt("Paste Dropbox CSV shared link", "") || "");
      if (!url) return;
      fetchCsvUrl(url, "Dropbox CSV");
    }});

    folderFileSelect.addEventListener("change", () => {{
      if (folderFileSelect.value.toLowerCase().endsWith(".csv")) {{
        openWorkingFile(folderFileSelect.value);
      }}
    }});

    slider.addEventListener("input", () => {{
      cursorFn = Number(slider.value);
      if (followMode.value === "center") centerOn(cursorFn);
      draw();
    }});

    resetBtn.addEventListener("click", () => {{
      view = {{ xMin: minFn, xMax: maxFn, curveYMin: 0, curveYMax: Math.max(10, maxXsum * 1.06) }};
      cursorFn = minFn;
      slider.value = String(minFn);
      draw();
    }});

    exportBtn.addEventListener("click", () => {{
      const a = document.createElement("a");
      a.download = `bed_curve_fn_${{Math.round(cursorFn)}}.png`;
      a.href = canvas.toDataURL("image/png");
      a.click();
    }});

    canvas.addEventListener("mousedown", (e) => {{
      dragging = true;
      lastMouse = {{ x: e.offsetX, y: e.offsetY }};
      canvas.classList.add("dragging");
    }});

    window.addEventListener("mouseup", () => {{
      dragging = false;
      canvas.classList.remove("dragging");
    }});

    canvas.addEventListener("mousemove", (e) => {{
      pointer = {{ x: e.offsetX, y: e.offsetY }};
      if (dragging && lastMouse) {{
        const L = layout();
        const dx = e.offsetX - lastMouse.x;
        const dy = e.offsetY - lastMouse.y;
        const xSpan = view.xMax - view.xMin;
        const ySpan = view.curveYMax - view.curveYMin;
        view.xMin -= dx / L.plotW * xSpan;
        view.xMax -= dx / L.plotW * xSpan;
        if (e.offsetY > L.curveTop || lastMouse.y > L.curveTop) {{
          view.curveYMin += dy / L.curveH * ySpan;
          view.curveYMax += dy / L.curveH * ySpan;
        }}
        clampView();
        lastMouse = {{ x: e.offsetX, y: e.offsetY }};
      }}
      draw();
    }});

    canvas.addEventListener("mouseleave", () => {{
      pointer = null;
      draw();
    }});

    canvas.addEventListener("click", (e) => {{
      const L = layout();
      const row = nearestRow(screenToX(e.offsetX, L));
      cursorFn = row.fn;
      slider.value = String(row.fn);
      draw();
    }});

    canvas.addEventListener("wheel", (e) => {{
      e.preventDefault();
      const L = layout();
      const factor = e.deltaY < 0 ? 0.82 : 1.22;
      if (e.shiftKey) {{
        const y0 = screenToCurveValue(e.offsetY, L);
        view.curveYMin = y0 + (view.curveYMin - y0) * factor;
        view.curveYMax = y0 + (view.curveYMax - y0) * factor;
      }} else {{
        const x0 = screenToX(e.offsetX, L);
        view.xMin = x0 + (view.xMin - x0) * factor;
        view.xMax = x0 + (view.xMax - x0) * factor;
      }}
      clampView();
      draw();
    }}, {{ passive: false }});

    function screenToCurveValue(y, L) {{
      return view.curveYMin + (L.curveTop + L.curveH - y) / L.curveH * (view.curveYMax - view.curveYMin);
    }}

    window.addEventListener("resize", resizeCanvas);
    populateWorkingFiles();
    updateStatePercentages();
    resizeCanvas();
  </script>
</body>
</html>
"""
    html_path.write_text(html_text, encoding="utf-8")


def main():
    base = Path(__file__).resolve().parent
    csv_path = base / CSV_NAME
    rows = read_rows(csv_path)
    if not rows:
        raise SystemExit(f"No rows found in {csv_path}")
    make_overview_svg(rows, base / SVG_NAME)
    make_html(rows, base / HTML_NAME)
    print(f"wrote {base / HTML_NAME}")
    print(f"wrote {base / SVG_NAME}")


if __name__ == "__main__":
    main()
