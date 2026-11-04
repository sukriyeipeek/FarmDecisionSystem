const API_URL = (import.meta.env.VITE_API_URL || "http://localhost:8000").replace(/\/+$/, "");

export function kullaniciyiOku() {
  try {
    return JSON.parse(localStorage.getItem("kullanici"));
  } catch {
    return null;
  }
}

export function oturumuKapat() {
  localStorage.removeItem("kullanici");
  window.location.href = "/login";
}

// fetch ile ayni imza; oturum token'ini Authorization basligina ekler.
// Sunucu 401 donerse oturum kapatilir ve giris sayfasina yonlendirilir.
export async function authFetch(url, options = {}) {
  const kullanici = kullaniciyiOku();
  const headers = { ...(options.headers || {}) };
  if (kullanici?.token) {
    headers.Authorization = `Bearer ${kullanici.token}`;
  }

  const res = await fetch(url, { ...options, headers });
  if (res.status === 401) {
    oturumuKapat();
  }
  return res;
}

export { API_URL };
