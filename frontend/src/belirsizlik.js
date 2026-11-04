// Tahmin belirsizligini gostermek icin ortak yardimcilar.

export const tl = (deger) =>
  deger === null || deger === undefined ? "—" : `${Math.round(deger).toLocaleString("tr-TR")} ₺`;

export const yuzde = (oran) =>
  oran === null || oran === undefined ? "—" : `%${Math.round(oran * 100)}`;

// "5.5, 6, 7" veya "5,5; 6" -> sayilar; ayirici: noktali virgul, bosluk ya da ", " ("5,5" ondalik kalir)
export function verimleriAyikla(metin) {
  if (!metin || !metin.trim()) return null;
  const degerler = metin
    .split(/[;\s]+|,(?=\s)/)
    .map((v) => Number(v.replace(",", ".")))
    .filter((v) => Number.isFinite(v) && v > 0);
  return degerler.length ? degerler : null;
}

// Bos metin alanlarini null'a cevirir (API sayisal alanlarda "" kabul etmez)
export function bosluklariTemizle(nesne) {
  return Object.fromEntries(
    Object.entries(nesne).map(([k, v]) => [k, v === "" ? null : v])
  );
}
