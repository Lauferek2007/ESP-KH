(function () {
  const API = "";
  const style = `
  :root{--bg:#0b1822;--panel:#112838;--line:#29495c;--tx:#e9f5ff;--mut:#9ec1d7;--ac:#36d7ff}
  *{box-sizing:border-box} body{margin:0;font-family:Segoe UI,Arial,sans-serif;background:linear-gradient(130deg,#0b1822,#113346);color:var(--tx)}
  .wrap{max-width:1200px;margin:0 auto;padding:14px}.h{display:flex;justify-content:space-between;align-items:center;gap:12px}
  .ttl{font-size:24px;font-weight:800}.grid{display:grid;grid-template-columns:repeat(12,minmax(0,1fr));gap:10px;margin-top:12px}
  .c{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:12px}.k{grid-column:span 3}.w{grid-column:span 6}.f{grid-column:span 12}
  .mut{color:var(--mut);font-size:12px}.v{font-size:28px;font-weight:700}.row{display:flex;justify-content:space-between;gap:8px;align-items:center;margin:8px 0}
  .btn{border:1px solid var(--line);background:#17394d;color:var(--tx);padding:8px 10px;border-radius:10px;cursor:pointer;font-weight:700}
  .btn:hover{filter:brightness(1.1)} input[type=range]{width:100%}
  .hint{font-size:12px;color:var(--mut);margin:4px 0 8px}.switch{width:46px;height:26px;border-radius:999px;background:#2d4252;position:relative;cursor:pointer}
  .switch i{position:absolute;left:2px;top:2px;width:22px;height:22px;border-radius:50%;background:#fff;transition:.2s}
  .switch.on{background:#2b7a63}.switch.on i{left:22px}.log{max-height:180px;overflow:auto;font-size:12px}
  @media(max-width:1000px){.k,.w,.f{grid-column:1/-1}}
  `;

  const html = `
  <div class="wrap">
    <div class="h">
      <div class="ttl">KH Keeper - Nowe UI</div>
      <button class="btn" id="btnStop">KH STOP</button>
    </div>
    <div class="grid">
      <div class="c k"><div class="mut">Main pH</div><div class="v" id="phMain">NA</div><div class="mut">A1: <span id="a1v">NA</span></div></div>
      <div class="c k"><div class="mut">Last KH</div><div class="v" id="khLast">NA</div><div class="mut">Ostatni wynik</div></div>
      <div class="c k"><div class="mut">WiFi RSSI</div><div class="v" id="rssi">NA</div><div class="mut">SSID: <span id="ssid">NA</span></div></div>
      <div class="c k"><div class="mut">Tryb</div><div class="v" id="mode">Idle</div><div class="mut">Status: <span id="status">-</span></div></div>

      <div class="c w">
        <h3>Kalibracja pH (2 punkty)</h3>
        <div class="row"><span>Punkt 1 [pH]</span><span id="p1lbl">6.89</span></div>
        <input id="p1" type="range" min="3" max="9.5" step="0.01" value="6.89">
        <div class="hint">Ustaw bufor dla punktu 1 i kliknij "Przechwyć P1".</div>
        <div class="row"><button class="btn" id="cap1">Przechwyć P1</button><span id="p1v">V1: NA</span></div>
        <div class="row"><span>Punkt 2 [pH]</span><span id="p2lbl">9.12</span></div>
        <input id="p2" type="range" min="3" max="9.5" step="0.01" value="9.12">
        <div class="hint">Przełóż sondę do 2 buforu, ustaw wartość i kliknij "Przechwyć P2".</div>
        <div class="row"><button class="btn" id="cap2">Przechwyć P2</button><span id="p2v">V2: NA</span></div>
        <div class="row"><button class="btn" id="saveph">Zapisz kalibrację 2-punktową</button><span id="slope">slope: NA</span></div>
      </div>

      <div class="c w">
        <h3>Kalibracje pomp</h3>
        <div class="row"><button class="btn" id="calp1run">Uruchom P1 60s</button><span id="p1mlps">P1: 0.000 ml/s</span></div>
        <div class="row"><span>P1 objętość [ml]</span><span id="p1mlLbl">0</span></div>
        <input id="p1ml" type="range" min="0" max="1000" step="1" value="0">
        <div class="hint">Po 60s wpisz objętość z wagi i kliknij "Zapisz P1".</div>
        <button class="btn" id="calp1save">Zapisz P1</button>
        <hr style="border-color:#29495c;opacity:.4">
        <div class="row"><button class="btn" id="calp2run">Uruchom P2 60s</button><span id="p2mlps">P2: 0.000 ml/s</span></div>
        <div class="row"><span>P2 objętość [ml]</span><span id="p2mlLbl">0</span></div>
        <input id="p2ml" type="range" min="0" max="1000" step="1" value="0">
        <div class="hint">Po 60s wpisz objętość z pomiaru i kliknij "Zapisz P2".</div>
        <button class="btn" id="calp2save">Zapisz P2</button>
      </div>

      <div class="c f">
        <h3>Testy ręczne</h3>
        <div class="row"><span>Manual hold P1</span><div class="switch" id="sw1"><i></i></div></div>
        <div class="hint">Włącza P1 ciągle do czasu ręcznego wyłączenia.</div>
        <div class="row"><span>Manual hold P2</span><div class="switch" id="sw2"><i></i></div></div>
        <div class="hint">Włącza P2 ciągle do testu odpompowania.</div>
        <div class="row"><span>Manual hold Air</span><div class="switch" id="sw3"><i></i></div></div>
        <div class="hint">Włącza aerację ciągłą.</div>
        <div class="row"><button class="btn" id="mp1">Manual test P1</button><button class="btn" id="mp2">Manual test P2</button><button class="btn" id="mair">Manual test Air</button></div>
      </div>

      <div class="c f">
        <h3>Log</h3>
        <div id="log" class="log"></div>
      </div>
    </div>
  </div>`;

  document.head.insertAdjacentHTML("beforeend", `<style>${style}</style>`);
  document.body.innerHTML = html;
  const app = document.querySelector("esp-app"); if (app) app.remove();

  const ids = {
    phMain: "sensor-main_ph",
    a1: "sensor-a1_ph_voltage__v_",
    kh: "sensor-last_kh__dkh_",
    rssi: "sensor-wifi_rssi",
    ssid: "text_sensor-wifi_ssid",
    mode: "text_sensor-kh_mode",
    status: "text_sensor-kh_status",
    p1v: "sensor-ph_cal_point_1_voltage__v_",
    p2v: "sensor-ph_cal_point_2_voltage__v_",
    slope: "sensor-ph_slope__ph_per_v_",
    p1mlps: "sensor-p1_calibration__ml_per_s_",
    p2mlps: "sensor-p2_calibration__ml_per_s_",
    sw1: "switch-manual_hold_p1",
    sw2: "switch-manual_hold_p2",
    sw3: "switch-manual_hold_air",
  };

  const mapButton = {
    cap1: "capture_ph_point_1",
    cap2: "capture_ph_point_2",
    saveph: "save_ph_2-point_calibration",
    calp1run: "calibrate_p1__60s_",
    calp1save: "save_p1_calibration",
    calp2run: "calibrate_p2__60s_",
    calp2save: "save_p2_calibration",
    mp1: "manual_test_p1",
    mp2: "manual_test_p2",
    mair: "manual_test_air",
    btnStop: "kh_stop",
  };
  const mapSwitch = { sw1: "manual_hold_p1", sw2: "manual_hold_p2", sw3: "manual_hold_air" };
  const mapNumber = { p1: "ph_cal_point_1_target", p2: "ph_cal_point_2_target", p1ml: "p1_measured_volume__ml_", p2ml: "p2_measured_volume__ml_" };

  function log(t) { const n = document.createElement("div"); n.textContent = `[${new Date().toLocaleTimeString()}] ${t}`; const box = document.getElementById("log"); box.prepend(n); while (box.children.length > 40) box.removeChild(box.lastChild); }
  async function post(path) { const r = await fetch(`${API}${path}`, { method: "POST", headers: { "Content-Type": "application/x-www-form-urlencoded" }, body: "x=" }); if (!r.ok) throw new Error(r.status); }
  const debounce = (fn, d=200)=>{let t;return(...a)=>{clearTimeout(t);t=setTimeout(()=>fn(...a),d)}};

  Object.keys(mapButton).forEach((id) => document.getElementById(id).addEventListener("click", async () => {
    try { await post(`/button/${mapButton[id]}/press`); log(`Wywołano: ${id}`); } catch (e) { log(`Błąd: ${id} (${e.message})`); }
  }));
  Object.keys(mapSwitch).forEach((id) => document.getElementById(id).addEventListener("click", async () => {
    const on = !document.getElementById(id).classList.contains("on");
    try { await post(`/switch/${mapSwitch[id]}/${on ? "turn_on" : "turn_off"}`); } catch (e) { log(`Błąd switch ${id}`); }
  }));
  Object.keys(mapNumber).forEach((id) => {
    const el = document.getElementById(id);
    el.addEventListener("input", () => {
      if (id === "p1") document.getElementById("p1lbl").textContent = Number(el.value).toFixed(2);
      if (id === "p2") document.getElementById("p2lbl").textContent = Number(el.value).toFixed(2);
      if (id === "p1ml") document.getElementById("p1mlLbl").textContent = Math.round(el.value);
      if (id === "p2ml") document.getElementById("p2mlLbl").textContent = Math.round(el.value);
    });
    el.addEventListener("change", debounce(async () => {
      try { await post(`/number/${mapNumber[id]}/set?value=${encodeURIComponent(el.value)}`); } catch (e) { log(`Błąd number ${id}`); }
    }));
  });

  const es = new EventSource("/events");
  es.addEventListener("state", (ev) => {
    try {
      const d = JSON.parse(ev.data);
      if (d.id === ids.phMain) document.getElementById("phMain").textContent = d.state || "NA";
      if (d.id === ids.a1) document.getElementById("a1v").textContent = d.state || "NA";
      if (d.id === ids.kh) document.getElementById("khLast").textContent = d.state || "NA";
      if (d.id === ids.rssi) document.getElementById("rssi").textContent = d.state || "NA";
      if (d.id === ids.ssid) document.getElementById("ssid").textContent = d.state || "NA";
      if (d.id === ids.mode) document.getElementById("mode").textContent = d.state || "Idle";
      if (d.id === ids.status) document.getElementById("status").textContent = d.state || "-";
      if (d.id === ids.p1v) document.getElementById("p1v").textContent = `V1: ${d.state || "NA"}`;
      if (d.id === ids.p2v) document.getElementById("p2v").textContent = `V2: ${d.state || "NA"}`;
      if (d.id === ids.slope) document.getElementById("slope").textContent = `slope: ${d.state || "NA"}`;
      if (d.id === ids.p1mlps) document.getElementById("p1mlps").textContent = `P1: ${d.state || "NA"}`;
      if (d.id === ids.p2mlps) document.getElementById("p2mlps").textContent = `P2: ${d.state || "NA"}`;
      if (d.id === ids.sw1) document.getElementById("sw1").classList.toggle("on", !!d.value);
      if (d.id === ids.sw2) document.getElementById("sw2").classList.toggle("on", !!d.value);
      if (d.id === ids.sw3) document.getElementById("sw3").classList.toggle("on", !!d.value);
      if (d.id === "number-ph_cal_point_1_target") { document.getElementById("p1").value = d.value; document.getElementById("p1lbl").textContent = Number(d.value).toFixed(2); }
      if (d.id === "number-ph_cal_point_2_target") { document.getElementById("p2").value = d.value; document.getElementById("p2lbl").textContent = Number(d.value).toFixed(2); }
      if (d.id === "number-p1_measured_volume__ml_") { document.getElementById("p1ml").value = d.value; document.getElementById("p1mlLbl").textContent = Math.round(d.value); }
      if (d.id === "number-p2_measured_volume__ml_") { document.getElementById("p2ml").value = d.value; document.getElementById("p2mlLbl").textContent = Math.round(d.value); }
    } catch {}
  });
  es.onerror = () => log("Utrata połączenia SSE /events");
})();
