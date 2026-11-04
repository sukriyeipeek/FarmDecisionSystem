import { useEffect, useRef, useState } from "react";
import { Navigate } from "react-router-dom";
import { API_URL, authFetch, kullaniciyiOku } from "../api";
import { buildIrrigationRequest, formatWaterValue, IRRIGATION_FIELDS } from "../water";

function Irrigation() {
  const kullanici = kullaniciyiOku();
  const [form, setForm] = useState({
    latitude: "", longitude: "", area_decare: "", kc: "",
    current_deficit_mm: "", allowed_deficit_mm: "",
    effective_rain_fraction: "1", irrigation_method: "damla",
  });
  const [havaModu, setHavaModu] = useState("online");
  const [demoHava, setDemoHava] = useState("");
  const [sonuc, setSonuc] = useState(null);
  const [hata, setHata] = useState("");
  const [yukleniyor, setYukleniyor] = useState(false);
  const istekSurumu = useRef(0);

  useEffect(() => () => { istekSurumu.current += 1; }, []);

  const girdiyiDegistir = (guncelle) => {
    istekSurumu.current += 1;
    setSonuc(null);
    setHata("");
    guncelle();
  };

  const hesapla = async (event) => {
    event.preventDefault();
    if (yukleniyor || !kullanici?.token) return;
    setHata("");
    setSonuc(null);
    let payload;
    try {
      payload = buildIrrigationRequest(form, havaModu === "demo" ? demoHava : null);
    } catch (error) {
      setHata(error.message);
      return;
    }
    const surum = ++istekSurumu.current;
    setYukleniyor(true);
    try {
      const res = await authFetch(`${API_URL}/sulama/oneri`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const data = await res.json();
      if (surum !== istekSurumu.current) return;
      if (!res.ok) {
        throw new Error(typeof data.detail === "string" ? data.detail : "Sulama tahmini alınamadı; girdileri kontrol edin.");
      }
      if (!Array.isArray(data.days) || !Number.isFinite(data.total_irrigation_volume_m3)
        || !["user", "open-meteo"].includes(data.source)) {
        throw new Error("Geçerli bir sulama tahmini alınamadı.");
      }
      setSonuc(data);
    } catch (error) {
      if (surum === istekSurumu.current) setHata(error.message || "Sunucuya bağlanılamadı.");
    } finally {
      setYukleniyor(false);
    }
  };

  if (!kullanici?.token) return <Navigate to="/login" replace />;

  return (
    <div className="page-container">
      <div className="analysis-header">
        <span className="eyebrow">Su Planlama</span>
        <h2>Günlük Sulama Tahmini</h2>
        <p className="hint">Kc, başlangıç su açığı ve sulama eşiğini kendi tarla koşullarınıza göre girin.</p>
      </div>
      <div className="analysis-grid">
        <form className="panel" onSubmit={hesapla}>
          <h3>Tarla ve Su Dengesi</h3>
          {IRRIGATION_FIELDS.map((field) => (
            <div className="field" key={field.name}>
              <label htmlFor={`sulama-${field.name}`}>{field.label}</label>
              <input id={`sulama-${field.name}`} type="number" step="any" required
                min={field.min} max={field.max} value={form[field.name]}
                onChange={(event) => {
                  const value = event.target.value;
                  girdiyiDegistir(() => setForm((prev) => ({ ...prev, [field.name]: value })));
                }} />
            </div>
          ))}
          <div className="field">
            <label htmlFor="sulama-method">Sulama yöntemi</label>
            <select id="sulama-method" value={form.irrigation_method}
              onChange={(event) => {
                const value = event.target.value;
                girdiyiDegistir(() => setForm((prev) => ({ ...prev, irrigation_method: value })));
              }}>
              <option value="damla">Damla</option>
              <option value="yagmurlama">Yağmurlama</option>
              <option value="salma">Salma</option>
            </select>
          </div>
          <div className="field">
            <label htmlFor="sulama-hava">Hava verisi</label>
            <select id="sulama-hava" value={havaModu}
              onChange={(event) => girdiyiDegistir(() => setHavaModu(event.target.value))}>
              <option value="online">Çevrimiçi tahmin (Open-Meteo)</option>
              <option value="demo">Demo senaryo — hava verisini kendim sağlayacağım</option>
            </select>
            <p className="hint">Çevrimiçi tahmin alınamazsa hata gösterilir. Demo için ayrıca seçim yapmanız gerekir.</p>
          </div>
          {havaModu === "demo" && (
            <div className="field">
              <label htmlFor="sulama-demo">Demo hava verisi (JSON, 1–7 ardışık gün)</label>
              <textarea id="sulama-demo" required value={demoHava}
                aria-describedby="sulama-demo-hint"
                style={{ width: "100%", minHeight: 150, padding: 12, borderRadius: 10 }}
                placeholder={'[{"date":"2026-06-01","et0_mm":4,"rain_mm":0}]'}
                onChange={(event) => girdiyiDegistir(() => setDemoHava(event.target.value))} />
              <p id="sulama-demo-hint" className="hint">Her gün için tarih, ET₀ (mm) ve yağış (mm) girin. Bunlar doğrulanmış hava tahmini değildir.</p>
            </div>
          )}
          {hata && <div className="form-message error" role="alert">{hata}</div>}
          <button type="submit" className="run-btn" disabled={yukleniyor}>
            {yukleniyor ? "Hesaplanıyor..." : "Sulama Tahmini Al"}
          </button>
        </form>
        <div className="results-column" aria-live="polite">
          <p className="hint">Geçici su dengesi tahminidir; ölçülmüş tasarruf veya kesin sulama talimatı değildir.</p>
          {sonuc ? (
            <>
              <div className="panel">
                <h3>{sonuc.source === "user" ? "Demo senaryo — kullanıcı verisi" : "Çevrimiçi tahmin — Open-Meteo"}</h3>
                <p className="hint">Saat dilimi: {sonuc.timezone}. Otomatik sulama işlemi yapılmaz.</p>
                <div className="result-row">
                  <div className="result-card">
                    <div className="label">Tahmini Toplam Sulama Suyu</div>
                    <div className="value">{formatWaterValue(sonuc.total_irrigation_volume_m3, "m³")}</div>
                  </div>
                  <div className="result-card">
                    <div className="label">Dönem Sonu Su Açığı</div>
                    <div className="value">{formatWaterValue(sonuc.final_deficit_mm, "mm")}</div>
                  </div>
                </div>
              </div>
              <div className="oneri-grid">
                {sonuc.days.map((day) => (
                  <div className="oneri-cell" key={day.date}>
                    <h3>{day.date}</h3>
                    <p>{day.irrigation_needed ? "Sulama eşiğine ulaşılıyor" : "Sulama eşiğine ulaşılmıyor"}</p>
                    <p>Tahmini sulama: {formatWaterValue(day.irrigation_volume_m3, "m³")}</p>
                    <p>ET₀: {formatWaterValue(day.et0_mm, "mm")} · Yağış: {formatWaterValue(day.rain_mm, "mm")}</p>
                    <p>Gün sonu açığı: {formatWaterValue(day.end_deficit_mm, "mm")}</p>
                  </div>
                ))}
              </div>
              {Array.isArray(sonuc.warnings) && (
                <div className="panel">
                  <h3>Varsayımlar</h3>
                  {sonuc.warnings.map((warning, index) => <p className="hint" key={index}>{warning}</p>)}
                </div>
              )}
            </>
          ) : <div className="panel empty-state">Girdileri doldurup “Sulama Tahmini Al” düğmesine basın.</div>}
        </div>
      </div>
    </div>
  );
}

export default Irrigation;
