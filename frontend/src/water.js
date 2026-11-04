export function parseWaterBudget(value) {
  const text = value.trim();
  if (!text) return null;
  const budget = Number(text.replace(",", "."));
  if (!Number.isFinite(budget) || budget < 0) {
    throw new Error("Su bütçesi, sıfır veya daha büyük sonlu bir sayı olmalıdır.");
  }
  return budget;
}

export function formatWaterValue(value, unit) {
  return Number.isFinite(value)
    ? `${value.toLocaleString("tr-TR", { maximumFractionDigits: 2 })} ${unit}`
    : "Veri yok";
}

export function summarizeWaterPlan(field) {
  const rows = field?.plan || [];
  const rowWater = rows.length > 0 && rows.every(
    (row) => Number.isFinite(row.estimated_water_m3) && row.estimated_water_m3 >= 0
  ) ? rows.reduce((sum, row) => sum + row.estimated_water_m3, 0) : null;
  const water = Number.isFinite(field?.estimated_water_m3) && field.estimated_water_m3 >= 0
    ? field.estimated_water_m3 : rowWater;
  const profit = (rows.length > 0 || (field?.success === true && Array.isArray(field.plan)))
    && rows.every((row) => Number.isFinite(row.estimated_profit))
    ? rows.reduce((sum, row) => sum + row.estimated_profit, 0) : null;
  return {
    water: Number.isFinite(water) ? water : null,
    profit: Number.isFinite(profit) ? profit : null,
    efficiency: water > 0 && Number.isFinite(profit) && Number.isFinite(profit / water)
      ? profit / water : null,
  };
}

export function waterAssumptionText(assumptions) {
  if (typeof assumptions === "string") return assumptions;
  if (Array.isArray(assumptions)) return assumptions.map(waterAssumptionText).filter(Boolean).join("; ");
  if (assumptions && typeof assumptions === "object") {
    return Object.entries(assumptions)
      .map(([key, value]) => `${key}: ${typeof value === "object" ? waterAssumptionText(value) : value}`)
      .join("; ");
  }
  return "";
}

export const IRRIGATION_FIELDS = [
  { name: "latitude", label: "Enlem (−90 – 90)", min: -90, max: 90 },
  { name: "longitude", label: "Boylam (−180 – 180)", min: -180, max: 180 },
  { name: "area_decare", label: "Alan (dönüm, en fazla 1.000.000)", min: 0, max: 1_000_000, positive: true },
  { name: "kc", label: "Bitki katsayısı (Kc, 0 – 3)", min: 0, max: 3, positive: true },
  { name: "current_deficit_mm", label: "Başlangıç su açığı (mm, 0 – 1000)", min: 0, max: 1000 },
  { name: "allowed_deficit_mm", label: "Sulama eşiği (mm, 0 – 1000)", min: 0, max: 1000, positive: true },
  { name: "effective_rain_fraction", label: "Etkili yağış katsayısı (0 – 1)", min: 0, max: 1 },
];

export function buildIrrigationRequest(form, forecastText = null) {
  const payload = {};
  for (const field of IRRIGATION_FIELDS) {
    const text = String(form[field.name] ?? "").trim();
    const value = Number(text.replace(",", "."));
    if (!text || !Number.isFinite(value) || value < field.min || value > field.max || (field.positive && value === 0)) {
      throw new Error(`${field.label}: geçerli ${field.positive ? "ve sıfırdan büyük " : ""}bir sayı girin.`);
    }
    payload[field.name] = value;
  }
  if (!["damla", "yagmurlama", "salma"].includes(form.irrigation_method)) {
    throw new Error("Geçerli bir sulama yöntemi seçin.");
  }
  payload.irrigation_method = form.irrigation_method;
  if (forecastText !== null) {
    let forecast;
    try { forecast = JSON.parse(forecastText); } catch {
      throw new Error("Demo hava verisini geçerli bir JSON listesi olarak girin.");
    }
    if (!Array.isArray(forecast) || forecast.length < 1 || forecast.length > 7) {
      throw new Error("Demo hava verisi 1–7 ardışık gün içermelidir.");
    }
    let previousDate;
    for (const day of forecast) {
      const date = typeof day?.date === "string" && /^\d{4}-\d{2}-\d{2}$/.test(day.date)
        ? Date.parse(`${day.date}T00:00:00Z`) : NaN;
      if (!day || Object.keys(day).sort().join(",") !== "date,et0_mm,rain_mm"
        || !Number.isFinite(date) || new Date(date).toISOString().slice(0, 10) !== day.date
        || (previousDate !== undefined && date - previousDate !== 86400000)
        || !Number.isFinite(day.et0_mm) || day.et0_mm < 0 || day.et0_mm > 100
        || !Number.isFinite(day.rain_mm) || day.rain_mm < 0 || day.rain_mm > 1000) {
        throw new Error("Demo günleri ardışık YYYY-MM-DD tarihleri, ET₀ (0–100 mm) ve yağış (0–1000 mm) sayıları içermelidir.");
      }
      previousDate = date;
    }
    payload.forecast = forecast;
  }
  return payload;
}
