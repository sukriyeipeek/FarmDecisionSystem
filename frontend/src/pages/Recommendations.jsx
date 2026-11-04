import { useEffect, useRef, useState } from "react";
import "../App.css";
import { URUN_GORUNEN_ADLAR } from "../constants/urunler";
import { API_URL, authFetch } from "../api";
import { tl, yuzde } from "../belirsizlik";
import { formatWaterValue, parseWaterBudget, summarizeWaterPlan, waterAssumptionText } from "../water";

const ILCELER = ["Bayındır", "Bergama", "Menderes", "Tire", "Torbalı", "Ödemiş"];
const SEZONLAR = ["İlkbahar", "Yaz", "Sonbahar", "Kış"];

function Recommendations() {
  const kayit = localStorage.getItem("kullanici");
  const aktifKullanici = kayit ? JSON.parse(kayit) : null;

  const [mod, setMod] = useState(aktifKullanici ? "tarlalarim" : "manuel");
  const [tarlalar, setTarlalar] = useState([]);
  const [secilenTarla, setSecilenTarla] = useState(null);
  const [manuelForm, setManuelForm] = useState({ ilce: "", donum: "" });
  const [sonuc, setSonuc] = useState(null);
  const [yukleniyor, setYukleniyor] = useState(false);
  const [hata, setHata] = useState("");
  const [sezon, setSezon] = useState("");
  const [secilenUrunler, setSecilenUrunler] = useState([]);
  const [onaylaniyor, setOnaylaniyor] = useState(false);
  const [basariMesaji, setBasariMesaji] = useState("");
  const [urunler, setUrunler] = useState([]);
  const [strateji, setStrateji] = useState("dengeli");
  const [ekMaliyet, setEkMaliyet] = useState("");
  const [suButcesi, setSuButcesi] = useState("");
  const [sulamaYontemi, setSulamaYontemi] = useState("damla");
  const [optimizasyonModu, setOptimizasyonModu] = useState("dengeli");
  const [karsilastirma, setKarsilastirma] = useState(null);
  const istekSurumu = useRef(0);

  const girdileriDegistir = (guncelle) => {
    istekSurumu.current += 1;
    setSonuc(null);
    setKarsilastirma(null);
    setHata("");
    setBasariMesaji("");
    guncelle();
  };

  useEffect(() => {
    if (aktifKullanici?.id) {
      authFetch(`${API_URL}/tarla/liste`)
        .then((res) => res.json())
        .then((data) => setTarlalar(Array.isArray(data) ? data : []))
        .catch(() => setTarlalar([]));
    }
  }, [aktifKullanici?.id]);

  useEffect(() => {
    authFetch(`${API_URL}/urun/liste`)
      .then((res) => res.json())
      .then((data) => setUrunler(Array.isArray(data)
        ? data.filter((urun) => urun.aktif).map((urun) => urun.urun_adi) : []))
      .catch(() => setUrunler([]));
    return () => { istekSurumu.current += 1; };
  }, []);

  const tarlaSec = (tarlaId) => {
    girdileriDegistir(() => setSecilenTarla(tarlaId));
  };

  const urunSecimiDegistir = (urun) => {
    girdileriDegistir(() => setSecilenUrunler((prev) =>
      prev.includes(urun) ? prev.filter((u) => u !== urun) : [...prev, urun]
    ));
  };

  const uygunTarlalar = tarlalar.filter((t) => t.bos_donum > 0);

  const toplamDonum = secilenTarla
    ? uygunTarlalar.find((t) => t.tarla_id === secilenTarla)?.bos_donum || 0
    : 0;

  const handleManuelChange = (e) => {
    girdileriDegistir(() => setManuelForm((prev) => ({ ...prev, [e.target.name]: e.target.value })));
  };

  const ilkPlan = sonuc?.[0];
  const urunListesi = ilkPlan?.plan || [];
  const toplamGelir = urunListesi.reduce(
    (toplam, urun) => toplam + urun.estimated_revenue,
    0
  );
  const toplamKar = urunListesi.reduce((toplam, urun) => toplam + urun.estimated_profit, 0);
  const toplamKarDusuk = urunListesi.every((u) => u.estimated_profit_low !== null)
    ? urunListesi.reduce((toplam, urun) => toplam + urun.estimated_profit_low, 0)
    : null;
  const maliyetlerEksik = urunListesi.some((u) => u.costs_incomplete);
  const suOzeti = summarizeWaterPlan(ilkPlan);
  const karsilastirmaTam = karsilastirma && [
    karsilastirma.dengeli.water, karsilastirma.dengeli.profit,
    karsilastirma.suTasarruflu.water, karsilastirma.suTasarruflu.profit,
  ].every(Number.isFinite);

  const ekimiOnayla = async () => {
    if (yukleniyor || onaylaniyor || !ilkPlan || !ilkPlan.success || urunListesi.length === 0) return;
    const surum = istekSurumu.current;

    setOnaylaniyor(true);
    setHata("");
    setBasariMesaji("");

    try {
      const res = await authFetch(`${API_URL}/oneri/onayla`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          kullanici_id: aktifKullanici.id,
          tarla_id: secilenTarla,
          hesaplanan_toplam_kar: Math.round(toplamKar),
          urunler: urunListesi.map((o) => ({
            urun_adi: o.product_name,
            donum: o.recommended_area,
          })),
        }),
      });
      const data = await res.json();
      if (res.ok) {
        setBasariMesaji("✅ Ekim planı başarıyla onaylandı. Tarlanız güncellendi.");
        // Tarla listesini tazele (boş dönüm güncellensin)
        authFetch(`${API_URL}/tarla/liste`)
          .then((r) => r.json())
          .then((d) => setTarlalar(Array.isArray(d) ? d : []));
        setTimeout(() => {
            if (surum !== istekSurumu.current) return;
            setSonuc(null);
            setKarsilastirma(null);
            setBasariMesaji("");
            }, 5000);
      } else {
        const mesaj =
          typeof data.detail === "string" ? data.detail : "Onaylanamadı.";
        setHata(mesaj);
      }
    } catch {
      setHata("Sunucuya bağlanılamadı.");
    } finally {
      setOnaylaniyor(false);
    }
  };

  const oneriAl = async (karsilastir = false) => {
    if (yukleniyor || onaylaniyor) return;
    setHata("");

    if (!sezon) {
      setHata("Lütfen Sezon Seçiniz!");
      return;
    }

    let suButcesiM3;
    try {
      suButcesiM3 = parseWaterBudget(suButcesi);
    } catch (error) {
      setHata(error.message);
      return;
    }

    let endpoint;
    let payload = {
      sezon,
      secilen_urunler: secilenUrunler.length > 0 ? secilenUrunler : null,
      strateji,
      ek_maliyet_donum: Number(ekMaliyet) || 0,
      su_butcesi_m3: suButcesiM3,
      sulama_yontemi: sulamaYontemi,
      optimizasyon_modu: optimizasyonModu,
    };

    if (mod === "tarlalarim") {
      if (!aktifKullanici || !secilenTarla) {
        setHata("Lütfen bir tarla seç.");
        return;
      }
      endpoint = `${API_URL}/oneri/tarla_getir`;

      payload = {
        ...payload,
        kullanici_id: aktifKullanici.id,
        tarla_id: secilenTarla,
        bos_donum: toplamDonum,
      };
    } else {
      if (!manuelForm.ilce || !manuelForm.donum) {
        setHata("Lütfen ilçe ve dönüm gir.");
        return;
      }
      endpoint = `${API_URL}/oneri/manual`;

      payload = {
        ...payload,
        ilce_adi: manuelForm.ilce,
        donum: Number(manuelForm.donum),
      };
    }

    setYukleniyor(true);
    setSonuc(null);
    setKarsilastirma(null);
    setBasariMesaji("");
    const surum = ++istekSurumu.current;
    const planiGetir = async (istek) => {
      const res = await authFetch(endpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(istek),
      });
      const data = await res.json();
      if (!res.ok) {
        throw new Error(typeof data.detail === "string" ? data.detail : "Öneri alınamadı.");
      }
      if (!Array.isArray(data) || data.length !== 1 || !data[0]?.success || !Array.isArray(data[0].plan)) {
        throw new Error(typeof data?.[0]?.error === "string" ? data[0].error : "Geçerli bir ekim planı alınamadı.");
      }
      return data;
    };
    try {
      if (karsilastir) {
        const cevaplar = await Promise.allSettled([
          planiGetir({ ...payload, optimizasyon_modu: "dengeli" }),
          planiGetir({ ...payload, optimizasyon_modu: "su_tasarruflu" }),
        ]);
        if (surum !== istekSurumu.current) return;
        const basarisiz = cevaplar.find((cevap) => cevap.status === "rejected");
        if (basarisiz) throw new Error(`Karşılaştırma tamamlanamadı: ${basarisiz.reason.message}`);
        const dengeli = cevaplar[0].value;
        const suTasarruflu = cevaplar[1].value;
        setKarsilastirma({ dengeli: summarizeWaterPlan(dengeli[0]), suTasarruflu: summarizeWaterPlan(suTasarruflu[0]) });
        setSonuc(optimizasyonModu === "su_tasarruflu" ? suTasarruflu : dengeli);
      } else {
        const data = await planiGetir(payload);
        if (surum !== istekSurumu.current) return;
        setSonuc(data);
      }
    } catch (err) {
      if (surum === istekSurumu.current) setHata(err.message || "Sunucuya bağlanılamadı.");
    } finally {
      setYukleniyor(false);
    }
  };

  return (
    <div className="page-container">
      <div className="analysis-header">
        <span className="eyebrow">Öneri Sistemi</span>
        <h2>Ekim Planı Önerisi</h2>
      </div>

      <div className="analysis-grid">
        <div className="panel">
          <h3>Kaynak Seç</h3>

          <div className="source-toggle">
            <button
              type="button"
              className={mod === "tarlalarim" ? "active" : ""}
              onClick={() => girdileriDegistir(() => setMod("tarlalarim"))}
            >
              Tarlalarımdan Seç
            </button>
            <button
              type="button"
              className={mod === "manuel" ? "active" : ""}
              onClick={() => girdileriDegistir(() => setMod("manuel"))}
            >
              Kendim Girmek İstiyorum
            </button>
          </div>

          {mod === "tarlalarim" ? (
            !aktifKullanici ? (
              <div className="empty-state">
                Kayıtlı tarlalarını kullanabilmek için önce giriş yapmalısın.
              </div>
            ) : uygunTarlalar.length === 0 ? (
              <div className="empty-state">Boş dönümü olan bir tarlan yok. "Tarlalarım" sayfasından tarladüzenleyebilirsin. </div>
            ) : (
              <>
                <div className="tarla-picklist">
                  {uygunTarlalar.map((t) => (
                    <label className="tarla-pick-item" key={t.tarla_id}>
                      <input
                        type="radio"
                        name="tarla-secimi"
                        checked={secilenTarla === t.tarla_id}
                        onChange={() => tarlaSec(t.tarla_id)}
                      />
                      <div className="info">
                        <strong>{t.tarla_adi}</strong>
                        <span>{t.ilce_adi} · {t.bos_donum} dönüm boş</span>
                      </div>
                    </label>
                  ))}
                </div>
                <div className="toplam-donum-box">Seçilen Tarlanın Boş Dönümü: {toplamDonum || 0}</div>
              </>
            )
          ) : (
            <>
              <div className="field">
                <label>İlçe</label>
                <select name="ilce"
                  value={manuelForm.ilce}
                  onChange={handleManuelChange}
                >
                  <option value="">İlçe seç</option>
                  {ILCELER.map((i) => (
                    <option key={i} value={i}>{i}</option>
                  ))}
                </select>
              </div>
              <div className="field">
                <label>Dönüm</label>
                <input
                  type="number"
                  min="0"
                  step="0.1"
                  name="donum"
                  placeholder="Örn. 10"
                  value={manuelForm.donum}
                  onChange={handleManuelChange}
                >
                </input>
              </div>
            </>
          )}

          <div className="field">
            <label>Sezon</label>
            <select value={sezon} onChange={(e) => girdileriDegistir(() => setSezon(e.target.value))}>
              <option value="">Sezon Seç</option>
              {SEZONLAR.map((s) => (
                <option key={s} value={s}>{s}</option>
              ))}
            </select>
          </div>

<div className="field">
  <label>Ürün Seç</label>

  <select
    value=""
    onChange={(e) => {
      const urun = e.target.value;

      if (!urun) return;

      girdileriDegistir(() => setSecilenUrunler((prev) =>
        prev.includes(urun) ? prev : [...prev, urun]
      ));
    }}
  >
    <option value="">Ürün Seç</option>
    {urunler.map((u) => (
      <option key={u} value={u}>
        {URUN_GORUNEN_ADLAR[u]}
      </option>
    ))}
  </select>

  {secilenUrunler.length > 0 && (
    <div className="selected-products-box">
      <div className="selected-products-title">Seçilen Ürünler</div>

      <div className="selected-products-list">
        {secilenUrunler.map((u) => (
          <button
            type="button"
            key={u}
            className="selected-product-pill"
            onClick={() => urunSecimiDegistir(u)}
          >
            {URUN_GORUNEN_ADLAR[u]} ×
          </button>
        ))}
      </div>
    </div>
  )}
</div>

          <div className="field">
            <label>Planlama Yaklaşımı</label>
            <div className="source-toggle">
              <button
                type="button"
                className={strateji === "dengeli" ? "active" : ""}
                onClick={() => girdileriDegistir(() => setStrateji("dengeli"))}
              >
                Dengeli
              </button>
              <button
                type="button"
                className={strateji === "temkinli" ? "active" : ""}
                onClick={() => girdileriDegistir(() => setStrateji("temkinli"))}
              >
                Temkinli
              </button>
            </div>
            <p className="hint">
              {strateji === "dengeli"
                ? "Beklenen kârı en yüksek planı arar."
                : "Fiyat düşerse en az zarar edecek planı arar; fiyatı çok oynak ürünlerden kaçınır."}
            </p>
          </div>

          <div className="field">
            <label htmlFor="su-butcesi">Su bütçesi (m³)</label>
            <input
              id="su-butcesi"
              type="text"
              inputMode="decimal"
              aria-describedby="su-butcesi-aciklama"
              placeholder="İsteğe bağlı, örn. 5000"
              value={suButcesi}
              onChange={(e) => girdileriDegistir(() => setSuButcesi(e.target.value))}
            />
            <p id="su-butcesi-aciklama" className="hint">
              Seçilen alanın sezonluk toplam bütçesi. Boş bırakırsanız su bütçesi sınırı uygulanmaz; 0 geçerli bir sınırdır.
            </p>
          </div>

          <div className="field">
            <label htmlFor="sulama-yontemi">Sulama yöntemi</label>
            <select id="sulama-yontemi" value={sulamaYontemi}
              onChange={(e) => girdileriDegistir(() => setSulamaYontemi(e.target.value))}>
              <option value="damla">Damla</option>
              <option value="yagmurlama">Yağmurlama</option>
              <option value="salma">Salma</option>
            </select>
          </div>

          <div className="field">
            <label htmlFor="optimizasyon-modu">Optimizasyon modu</label>
            <select id="optimizasyon-modu" value={optimizasyonModu}
              onChange={(e) => girdileriDegistir(() => setOptimizasyonModu(e.target.value))}>
              <option value="dengeli">Dengeli</option>
              <option value="su_tasarruflu">Su tasarruflu</option>
            </select>
            <p className="hint">Planlama yaklaşımı (Dengeli / Temkinli) ayrıca korunur.</p>
          </div>

          <div className="field">
            <label>Diğer Giderler (₺/dönüm)</label>
            <input
              type="number"
              min="0"
              placeholder="İşçilik, tohum, sulama, kira… bilinmiyorsa boş bırak"
              value={ekMaliyet}
              onChange={(e) => girdileriDegistir(() => setEkMaliyet(e.target.value))}
            />
          </div>

          {hata && <div className="form-message error">{hata}</div>}

          <button type="button" className="run-btn" onClick={() => oneriAl()} disabled={yukleniyor || onaylaniyor}>
            {yukleniyor ? "Hesaplanıyor..." : "Öneri Al"}
          </button>
          <button type="button" className="run-btn" style={{ marginTop: 12 }}
            onClick={() => oneriAl(true)} disabled={yukleniyor || onaylaniyor}>
            Modları Karşılaştır (isteğe bağlı)
          </button>
          <p className="hint">Karşılaştırma, aynı girdilerle her mod için bir kez hesaplama yapar.</p>
        </div>

        <div className="results-column">
            {basariMesaji && (
                <div className="form-message succes">
                    {basariMesaji}
                </div>
                )}
          {sonuc ? (
            <>
              {karsilastirma && (
                <section className="panel" aria-label="Mod karşılaştırması">
                  <h3>Dengeli / Su tasarruflu karşılaştırması</h3>
                  <p>Dengeli: {formatWaterValue(karsilastirma.dengeli.water, "m³")} su,
                    {" "}{formatWaterValue(karsilastirma.dengeli.profit, "TL")} tahmini kâr.</p>
                  <p>Su tasarruflu: {formatWaterValue(karsilastirma.suTasarruflu.water, "m³")} su,
                    {" "}{formatWaterValue(karsilastirma.suTasarruflu.profit, "TL")} tahmini kâr.</p>
                  {karsilastirmaTam ? (
                    <>
                      <p className="hint">Tahmini fark = Su tasarruflu − Dengeli; negatif değer azalmayı gösterir.</p>
                      <div className="result-row">
                        <div className="result-card">
                          <div className="label">Tahmini Su Farkı</div>
                          <div className="value">{formatWaterValue(karsilastirma.suTasarruflu.water - karsilastirma.dengeli.water, "m³")}</div>
                        </div>
                        <div className="result-card">
                          <div className="label">Tahmini Kâr Farkı</div>
                          <div className="value">{formatWaterValue(karsilastirma.suTasarruflu.profit - karsilastirma.dengeli.profit, "TL")}</div>
                        </div>
                      </div>
                    </>
                  ) : <p className="hint">Su veya kâr verisi eksik olduğundan fark hesaplanamadı.</p>}
                  <p className="hint">Aşağıdaki ekim planı seçili {optimizasyonModu === "su_tasarruflu" ? "Su tasarruflu" : "Dengeli"} moduna aittir.</p>
                </section>
              )}
              {ilkPlan && !ilkPlan.success && (
                <div className="form-message error">{ilkPlan.error}</div>
              )}
              <div className="oneri-grid">{urunListesi.map((o, idx) => (
                  <div className="oneri-cell" key={idx}>
                    <div className="donum">{o.recommended_area} dönüm</div>
                    <div className="urun">{URUN_GORUNEN_ADLAR[o.product_name] || o.product_name}</div>
                    <div className="Meta">Tahmini Üretim:{" "}{(o.estimated_production ?? 0).toLocaleString("tr-TR")}{" "}ton</div>
                    <div className="Meta">Tahmini Gelir:{" "}{(o.estimated_revenue ?? 0).toLocaleString("tr-TR")} ₺</div>
                    <div className="Meta">Tahmini Kâr:{" "}{(o.estimated_profit ?? 0).toLocaleString("tr-TR")} ₺</div>
                    <div className="Meta">Dönüm Başına Tahmini Su: {formatWaterValue(o.water_per_decare_m3, "m³/dönüm")}</div>
                    <div className="Meta">Tahmini Toplam Su: {formatWaterValue(o.estimated_water_m3, "m³")}</div>
                    <div className="Meta">Tahmini Su Başına Kâr: {formatWaterValue(o.water_efficiency_tl_m3, "TL/m³")}</div>
                    {waterAssumptionText(o.water_assumptions) && (
                      <details>
                        <summary>Su hesabı varsayımları</summary>
                        <p className="hint">{waterAssumptionText(o.water_assumptions)}</p>
                      </details>
                    )}
                    {o.estimated_profit_low !== null && (
                      <div className="Meta">Kötü senaryoda kâr: {tl(o.estimated_profit_low)}</div>
                    )}
                    {o.loss_probability !== null && (
                      <div className="Meta">Zarar olasılığı: {yuzde(o.loss_probability)}</div>
                    )}
                  </div>
                ))}
              </div>
              <div className="result-row">
                <div className="result-card highlight">
                  <div className="label">Tahmini Toplam Gelir</div>
                  <div className="value">{toplamGelir.toLocaleString("tr-TR")} ₺</div>
                </div>
                <div className="result-card">
                  <div className="label">Tahmini Toplam Kâr</div>
                  <div className="value">{tl(toplamKar)}</div>
                </div>
              </div>

              <div className="result-row">
                <div className="result-card">
                  <div className="label">Tahmini Toplam Su</div>
                  <div className="value">{formatWaterValue(suOzeti.water, "m³")}</div>
                  <div className="hint">Su bütçesi: {ilkPlan?.water_budget_m3 === null
                    ? "Belirtilmedi" : formatWaterValue(ilkPlan?.water_budget_m3, "m³")}</div>
                </div>
                <div className="result-card">
                  <div className="label">Tahmini Su Başına Kâr</div>
                  <div className="value">{formatWaterValue(suOzeti.efficiency, "TL/m³")}</div>
                  <div className="hint">Toplam tahmini kâr / toplam tahmini su</div>
                </div>
              </div>
              <p className="hint">
                Su değerleri, ürün ve sulama yöntemi varsayımlarına dayalı geçici tahminlerdir;
                ölçülmüş tüketim veya tasarruf değildir.
              </p>

              {toplamKarDusuk !== null && (
                <div className="form-message info">
                  Fiyatlar kötü giderse toplam kâr {tl(toplamKarDusuk)} olur.
                  {urunListesi[0]?.interval_coverage != null &&
                    ` Geçmiş testlerde gerçek fiyat tahmin aralığında ${yuzde(urunListesi[0].interval_coverage)} oranında kaldı.`}
                </div>
              )}
              {ilkPlan?.unallocated_area > 0 && (
                <div className="form-message info">
                  {ilkPlan.unallocated_area} dönüm plan kısıtları nedeniyle boş bırakılıyor (kârlılık, kota veya su bütçesi).
                </div>
              )}
              {maliyetlerEksik && (
                <div className="form-message info">
                  Diğer giderler girilmedi; kâr olduğundan yüksek, zarar olasılığı olduğundan düşük görünebilir.
                </div>
              )}

              {basariMesaji && (
                <div className="form-message success">{basariMesaji}</div>
              )}

              {mod === "tarlalarim" && ilkPlan?.success && (
                <button
                  className="run-btn"
                  onClick={ekimiOnayla}
                  disabled={onaylaniyor || yukleniyor}
                  style={{ marginTop: 12 }}
                >
                  {onaylaniyor ? "Kaydediliyor..." : "Bu Ekimi Onaylıyorum"}
                </button>
              )}
            </>
          ) : (
            <div className="panel">
              <div className="empty-state">
                  {basariMesaji
                    ? "✔ Ekim planı kaydedildi. Yeni bir öneri oluşturmak için tarla veya sezon seçebilirsiniz."
                    : 'Bir kaynak seç ve "Öneri Al" butonuna bas — tarlan için önerilen ekim dağılımı burada görünecek.'}</div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default Recommendations;
