/* Dokun & Dinle - backend bağlantısı
 *
 * Arayüz backend ile aynı adresten açıldığı için istekler göreli adreslerle (/api/...) yapılır.
 * Uç noktaların ayrıntıları: backend/API_BELGESI.docx
 */
"use strict";

(() => {
  const SUNUCU = "";  // arayüz başka bir adresten açılırsa ör. "http://127.0.0.1:8000"
  const el = (id) => document.getElementById(id);

  const form = el("harita-formu");
  const formDurum = el("form-durum");
  const uretDugme = el("uret-dugme");
  const sonucAlani = el("sonuc");
  let sonHarita = null;          // en son gösterilen haritanın bilgileri
  let bekleZamanlayici = null;

  // ---------- Yardımcılar ----------

  async function istek(yol, ayar = {}) {
    let cevap;
    try {
      cevap = await fetch(SUNUCU + yol, {
        ...ayar,
        headers: { "Content-Type": "application/json", ...(ayar.headers || {}) },
      });
    } catch (_) {
      throw { kod: "baglanti", mesaj: "Sunucuya bağlanılamadı. Sunucunun çalıştığından emin olun." };
    }
    const veri = await cevap.json().catch(() => ({}));
    if (!cevap.ok) throw (veri.detail || { kod: "bilinmeyen", mesaj: "Beklenmeyen bir hata oluştu." });
    return veri;
  }

  function sayi(metin) {
    const m = metin == null ? "" : String(metin).trim().replace(",", ".");
    return m === "" ? NaN : Number(m);
  }

  function yeni(etiket, ozellikler = {}, ...cocuklar) {
    const e = document.createElement(etiket);
    for (const [k, v] of Object.entries(ozellikler)) {
      if (k === "text") e.textContent = v;
      else if (k.startsWith("on")) e.addEventListener(k.slice(2), v);
      else if (v !== false && v != null) e.setAttribute(k, v === true ? "" : v);
    }
    cocuklar.flat().forEach((c) => c && e.append(c));
    return e;
  }

  function tarihYaz(iso) {
    if (!iso) return "";
    const t = new Date(iso);
    return t.toLocaleDateString("tr-TR", { day: "numeric", month: "long", year: "numeric" }) +
      " " + t.toLocaleTimeString("tr-TR", { hour: "2-digit", minute: "2-digit" });
  }

  // ---------- Form hataları ----------

  const ALAN_KIMLIKLERI = {
    "yer": "yer", "merkez": "enlem", "merkez.enlem": "enlem", "merkez.boylam": "boylam",
    "alan_m": "alan", "baslik": "baslik",
  };

  function hatalariTemizle() {
    form.querySelectorAll("[aria-invalid='true']").forEach((g) => {
      g.removeAttribute("aria-invalid");
      const h = el(g.id + "-hata");
      if (h) h.textContent = "";
    });
  }

  function alanHatasi(id, mesaj) {
    const g = el(id);
    if (!g) return null;
    g.setAttribute("aria-invalid", "true");
    const h = el(id + "-hata");
    if (h) h.textContent = mesaj;
    return g;
  }

  // ---------- 1. Konum ----------

  async function konumuBul({ sessiz = false } = {}) {
    const yer = el("yer").value.trim();
    hatalariTemizle();
    if (!yer) {
      const g = alanHatasi("yer", "Yer adı yazın.");
      Ses.duyur("Önce yer adını yazın.", formDurum);
      g && g.focus();
      return false;
    }
    Ses.duyur("Konum aranıyor: " + yer, formDurum);
    try {
      const k = await istek("/api/konum?yer=" + encodeURIComponent(yer));
      el("enlem").value = k.enlem.toFixed(6);
      el("boylam").value = k.boylam.toFixed(6);
      const bulunan = k.bulunan || yer;
      el("bulunan-yer").textContent = "Bulunan yer: " + bulunan;
      if (!sessiz) Ses.duyur("Bulunan yer: " + bulunan + ". Doğru değilse adı daha ayrıntılı yazın, örneğin ilçe ve şehir ekleyin.", formDurum);
      return true;
    } catch (h) {
      const g = alanHatasi("yer", h.mesaj);
      Ses.duyur(h.mesaj, formDurum);
      g && g.focus();
      return false;
    }
  }

  el("konum-bul").addEventListener("click", () => konumuBul());
  el("yer").addEventListener("input", () => {
    // Yer değişince eski koordinatlar geçersiz olur.
    el("enlem").value = "";
    el("boylam").value = "";
    el("bulunan-yer").textContent = "";
  });

  // ---------- 2. Başlık ve Braille önizlemesi ----------

  let brailleZamanlayici = null;
  el("baslik").addEventListener("input", () => {
    clearTimeout(brailleZamanlayici);
    brailleZamanlayici = setTimeout(brailleOnizle, 400);
  });

  async function brailleOnizle() {
    const metin = el("baslik").value.trim();
    const cikti = el("baslik-braille");
    if (!metin) { cikti.textContent = ""; return null; }
    try {
      const b = await istek("/api/braille", { method: "POST", body: JSON.stringify({ metin }) });
      let aciklama = `Braille: ${b.braille} (${b.hucre_sayisi} hücre). `;
      aciklama += b.baslik_olarak_sigar ? "Başlık banda sığıyor." : "Başlık banda sığmıyor, kısaltın.";
      if (b.cevrilemeyen_karakterler.length) aciklama += " Haritada yer almayacak karakterler: " + b.cevrilemeyen_karakterler.join(" ");
      cikti.textContent = aciklama;
      return b;
    } catch (_) {
      cikti.textContent = "";
      return null;
    }
  }

  el("baslik").addEventListener("blur", async () => {
    const b = await brailleOnizle();
    if (b && !b.baslik_olarak_sigar) Ses.duyur("Başlık plakaya sığmıyor. Lütfen kısaltın.", formDurum);
  });

  // ---------- 3. Bina adları ----------

  let binaSayaci = 0;
  function binaSatiriEkle(deger = {}) {
    binaSayaci += 1;
    const n = binaSayaci;
    const liste = el("bina-listesi");
    const sira = liste.children.length + 1;
    const satir = yeni("li", { class: "bina-satiri" },
      yeni("label", { class: "field", for: `bina-ad-${n}` }, `${sira}. bina adı`,
        yeni("input", { id: `bina-ad-${n}`, class: "bina-ad", maxlength: "80", value: deger.ad || "",
          "data-rehber": "Haritada bu binanın anahtarıyla gösterilecek kısa adı yazın." })),
      yeni("label", { class: "field", for: `bina-enlem-${n}` }, "Enlem",
        yeni("input", { id: `bina-enlem-${n}`, class: "bina-enlem", inputmode: "decimal", value: deger.enlem || "",
          "data-rehber": "Binanın içindeki bir noktanın enlemini yazın. Google Haritalar'da binaya sağ tıklayınca çıkan ilk sayıdır." })),
      yeni("label", { class: "field", for: `bina-boylam-${n}` }, "Boylam",
        yeni("input", { id: `bina-boylam-${n}`, class: "bina-boylam", inputmode: "decimal", value: deger.boylam || "",
          "data-rehber": "Aynı noktanın boylamını yazın." })),
      yeni("button", { type: "button", class: "button button-outline bina-sil", "data-rehber": "Bu binayı listeden çıkarır.",
        onclick: () => { satir.remove(); binaSiralariniYaz(); Ses.duyur("Bina listeden çıkarıldı.", formDurum); el("bina-ekle").focus(); } },
        "Bu binayı sil"),
    );
    liste.append(satir);
    satir.querySelector(".bina-ad").focus();
  }

  function binaSiralariniYaz() {
    [...el("bina-listesi").children].forEach((li, i) => {
      const lab = li.querySelector("label");
      lab.firstChild.textContent = `${i + 1}. bina adı`;
    });
  }

  el("bina-ekle").addEventListener("click", () => binaSatiriEkle());

  function binaAdlariniTopla() {
    const adlar = [];
    for (const li of el("bina-listesi").children) {
      const ad = li.querySelector(".bina-ad").value.trim();
      const en = sayi(li.querySelector(".bina-enlem").value);
      const boy = sayi(li.querySelector(".bina-boylam").value);
      if (!ad && !li.querySelector(".bina-enlem").value) continue;   // boş satır
      if (!ad || isNaN(en) || isNaN(boy)) {
        throw { alan: li.querySelector(!ad ? ".bina-ad" : ".bina-enlem"), mesaj: "Bina adı satırında ad, enlem ve boylam birlikte yazılmalı." };
      }
      adlar.push({ enlem: en, boylam: boy, ad });
    }
    return adlar;
  }

  // ---------- 4. Harita üretme ----------

  const KABARTMA = { standart: 3.0, belirgin: 3.5, yuksek: 4.0 };

  async function haritaUret({ yeniden = false } = {}) {
    hatalariTemizle();
    const yer = el("yer").value.trim();
    let enlem = sayi(el("enlem").value);
    let boylam = sayi(el("boylam").value);
    const ornek = el("ornek-veri").checked;

    if (!ornek && (isNaN(enlem) || isNaN(boylam))) {
      if (!yer && (el("enlem").value || el("boylam").value)) {
        const g = alanHatasi(isNaN(enlem) ? "enlem" : "boylam", "Enlem ve boylam sayı olmalı.");
        Ses.duyur("Enlem ve boylam sayı olmalı.", formDurum);
        g && g.focus();
        return;
      }
      if (!yer) {
        const g = alanHatasi("yer", "Yer adı yazın ya da enlem ve boylam girin.");
        Ses.duyur("Haritası çıkarılacak yerin adını yazın ya da enlem ve boylam girin.", formDurum);
        g && g.focus();
        return;
      }
      if (!(await konumuBul({ sessiz: true }))) return;
      enlem = sayi(el("enlem").value);
      boylam = sayi(el("boylam").value);
    }

    let binaAdlari;
    try { binaAdlari = binaAdlariniTopla(); }
    catch (h) {
      h.alan.setAttribute("aria-invalid", "true");
      Ses.duyur(h.mesaj, formDurum);
      h.alan.focus();
      return;
    }

    const govde = {
      alan_m: Number(el("alan").value),
      baslik: el("baslik").value.trim() || null,
      bina_adlari: binaAdlari,
      ayarlar: {
        bina_yukseklik_mm: KABARTMA[el("kabartma").value],
        bina_anahtarlari: el("braille-anahtar").checked,
      },
      ornek_veri: ornek,
      yeniden_uret: yeniden || el("yeniden-uret").checked,
    };
    if (!ornek) { govde.merkez = { enlem, boylam }; govde.yer = yer || null; }

    // Bekleme durumu
    form.setAttribute("aria-busy", "true");
    uretDugme.disabled = true;
    uretDugme.textContent = "Harita hazırlanıyor…";
    const bulunan = el("bulunan-yer").textContent.replace("Bulunan yer: ", "");
    Ses.duyur((bulunan ? bulunan + " için " : "") +
      "harita hazırlanıyor. Bu işlem bir ile beş dakika sürebilir. Hazır olduğunda size haber vereceğim.", formDurum);
    let gecen = 0;
    bekleZamanlayici = setInterval(() => {
      gecen += 30;
      Ses.duyur(`Harita hâlâ hazırlanıyor, ${gecen} saniye geçti. Lütfen bekleyin.`, formDurum);
    }, 30000);

    try {
      const sonuc = await istek("/api/harita", { method: "POST", body: JSON.stringify(govde) });
      sonucuGoster(sonuc, { yeniUretildi: true });
      oncekileriYukle();
    } catch (h) {
      hatayiGoster(h);
    } finally {
      clearInterval(bekleZamanlayici);
      form.removeAttribute("aria-busy");
      uretDugme.disabled = false;
      uretDugme.textContent = "Haritayı üret";
    }
  }

  function hatayiGoster(h) {
    let odak = null;
    if (h.alanlar) {
      for (const a of h.alanlar) {
        const g = alanHatasi(ALAN_KIMLIKLERI[a.alan] || a.alan, a.sorun);
        odak = odak || g;
      }
    }
    const tekrar = el("tekrar-dene");
    tekrar.hidden = !(h.kod === "veri_alinamadi" || h.kod === "baglanti");
    Ses.duyur(h.mesaj + (tekrar.hidden ? "" : " Tekrar denemek için Tekrar dene düğmesini kullanın."), formDurum);
    (odak || (tekrar.hidden ? uretDugme : tekrar)).focus();
  }

  form.addEventListener("submit", (e) => { e.preventDefault(); haritaUret(); });
  el("tekrar-dene").addEventListener("click", () => { el("tekrar-dene").hidden = true; haritaUret(); });

  // ---------- 5. Sonuç ve sesli anlatım ----------

  function haritaAnlatimi(h) {
    const parcalar = [h.aciklama];
    if (h.uyarilar && h.uyarilar.length) parcalar.push("Uyarılar: " + h.uyarilar.join(" "));
    if (h.ozet && h.ozet.basilabilir === false) parcalar.push("Dikkat: model baskıya uygun görünmüyor.");
    return parcalar.join(" ");
  }

  function sonucuGoster(h, { yeniUretildi = false } = {}) {
    sonHarita = h;
    const o = h.ozet;
    const dosyaBaglantisi = (tur, metin) => h.dosyalar[tur]
      ? yeni("li", {}, yeni("a", { class: "button button-outline indir", href: SUNUCU + h.dosyalar[tur], download: "" }, metin))
      : null;

    const baslik = yeni("h3", { id: "sonuc-baslik", tabindex: "-1" },
      h.onceden_uretildi ? "Bu harita daha önce hazırlanmış" : "Harita hazır");

    const anahtarTablosu = h.anahtarlar && h.anahtarlar.length
      ? yeni("table", { class: "anahtar-tablosu" },
          yeni("caption", { text: "Haritadaki Braille anahtarları" }),
          yeni("thead", {}, yeni("tr", {}, yeni("th", { scope: "col", text: "Anahtar" }), yeni("th", { scope: "col", text: "Bina adı" }))),
          yeni("tbody", {}, h.anahtarlar.map((k) => yeni("tr", {}, yeni("td", { text: k.anahtar }), yeni("td", { text: k.ad })))))
      : yeni("p", { class: "muted", text: "Bu haritada Braille anahtarlı bina yok." });

    sonucAlani.replaceChildren(...[
      baslik,
      yeni("p", { class: "sonuc-aciklama", text: h.aciklama }),
      h.onceden_uretildi ? yeni("p", { class: "muted" },
        `Bu harita ${tarihYaz(h.olusturma)} tarihinde aynı ayarlarla hazırlanmıştı, kayıttan getirildi. `,
        yeni("button", { type: "button", class: "metin-dugme", "data-rehber": "Haritayı baştan, güncel veriyle üretir.",
          onclick: () => haritaUret({ yeniden: true }) }, "Baştan üret")) : null,
      yeni("dl", { class: "ozet-listesi" },
        yeni("dt", { text: "Alan" }), yeni("dd", { text: `${Math.round(o.alan_m)} m × ${Math.round(o.alan_m)} m` }),
        yeni("dt", { text: "Plaka" }), yeni("dd", { text: `${Math.round(o.plaka_mm[0])} × ${Math.round(o.plaka_mm[1])} mm` }),
        yeni("dt", { text: "Ölçek" }), yeni("dd", { text: o.olcek }),
        yeni("dt", { text: "Bina sayısı" }), yeni("dd", { text: String(o.bina_sayisi) }),
        yeni("dt", { text: "Baskıya uygun" }), yeni("dd", { text: o.basilabilir ? "Evet" : "Hayır" })),
      anahtarTablosu,
      h.uyarilar && h.uyarilar.length
        ? yeni("div", { class: "uyarilar" }, yeni("h4", { text: "Uyarılar" }), yeni("ul", {}, h.uyarilar.map((u) => yeni("li", { text: u }))))
        : null,
      yeni("button", { type: "button", class: "button button-primary", id: "haritayi-anlat",
        "data-rehber": "Haritada nelerin olduğunu sesli anlatır.",
        onclick: () => Ses.konus(haritaAnlatimi(h)) }, "Haritayı sesli dinle"),
      yeni("h4", { text: "Dosyaları indir" }),
      yeni("ul", { class: "indirme-listesi" },
        dosyaBaglantisi("harita_stl", "Harita modelini indir (STL, 3D yazıcı için)"),
        dosyaBaglantisi("lejant_stl", "Braille lejant plakasını indir (STL)"),
        dosyaBaglantisi("onizleme_png", "Önizleme resmini indir (PNG)"),
        dosyaBaglantisi("lejant_txt", "Anahtar listesini indir (metin)")),
    ].filter(Boolean));

    // Önizleme resmi: alt metni haritanın açıklamasıdır.
    const resim = yeni("img", { src: SUNUCU + h.dosyalar.onizleme_png + "?t=" + Date.now(), alt: h.aciklama, class: "onizleme-resmi" });
    el("onizleme-kutusu").replaceChildren(resim);
    el("onizleme-yazi").textContent = "Üretilen haritanın katman önizlemesi. Lacivert: bina, gri: araç yolu kanalı, turuncu: yaya yolu, harfler: Braille anahtarları.";

    Ses.sessizOdakla(baslik);
    const ilk = h.onceden_uretildi ? "Bu harita daha önce hazırlanmış, kayıttan getirildi. " : (yeniUretildi ? "Harita hazır. " : "Harita açıldı. ");
    // Ekranda kısa bilgi; sesli rehber açıksa haritanın tamamı anlatılır.
    // (Ekran okuyucu kullanıcısının odağı sonuç başlığına taşındığı için ayrıntıyı oradan okur.)
    formDurum.textContent = ilk.trim();
    if (Ses.rehberAcik) Ses.konus(ilk + haritaAnlatimi(h) + " Dosyaları indirmek için, indir, deyin ya da indirme bağlantılarına gidin.");
  }

  // ---------- 6. Önceki haritalar ----------

  async function oncekileriYukle(ara = el("onceki-ara").value.trim()) {
    const liste = el("onceki-liste");
    const durum = el("onceki-durum");
    try {
      const v = await istek("/api/haritalar?adet=50" + (ara ? "&ara=" + encodeURIComponent(ara) : ""));
      liste.replaceChildren(...v.haritalar.map(oncekiKarti));
      durum.textContent = v.toplam === 0
        ? (ara ? `"${ara}" için kayıtlı harita bulunamadı.` : "Henüz kayıtlı harita yok.")
        : `${v.toplam} kayıtlı harita` + (ara ? ` ("${ara}" araması)` : "") + ".";
      return v;
    } catch (h) {
      durum.textContent = h.mesaj;
      return null;
    }
  }

  function oncekiAdi(h) {
    return h.baslik || h.yer || `${h.merkez.enlem.toFixed(4)}, ${h.merkez.boylam.toFixed(4)}`;
  }

  function oncekiKarti(h) {
    const ad = oncekiAdi(h);
    const li = yeni("li", { class: "onceki-kart" },
      yeni("h3", { text: ad }),
      yeni("p", { class: "muted" },
        [h.yer && h.baslik ? h.yer : null, tarihYaz(h.olusturma), `${Math.round(h.alan_m)} m`, `${h.bina_sayisi} bina`,
          h.anahtarlar.length ? "Anahtarlar: " + h.anahtarlar.map((k) => `${k.anahtar} ${k.ad}`).join(", ") : null]
          .filter(Boolean).join(" · ")),
      yeni("div", { class: "onceki-dugmeler" },
        yeni("button", { type: "button", class: "button button-primary", "aria-label": `${ad} haritasını aç`,
          "data-rehber": "Haritanın bilgilerini ve indirme bağlantılarını gösterir.", onclick: () => haritayiAc(h.id) }, "Aç"),
        yeni("a", { class: "button button-outline", href: SUNUCU + h.dosyalar.harita_stl, download: "", "aria-label": `${ad} harita modelini indir (STL)` }, "STL indir"),
        yeni("button", { type: "button", class: "button button-outline", "aria-label": `${ad} haritasını sil`,
          "data-rehber": "Haritayı ve dosyalarını kalıcı olarak siler. Onay istenir.", onclick: () => haritayiSil(h.id, ad) }, "Sil")));
    return li;
  }

  async function haritayiAc(id) {
    try {
      const h = await istek("/api/harita/" + id);
      el("olustur").scrollIntoView();
      sonucuGoster({ ...h, onceden_uretildi: false });
    } catch (h) { Ses.duyur(h.mesaj, el("onceki-durum")); }
  }

  async function haritayiSil(id, ad) {
    if (!window.confirm(`"${ad}" haritası ve dosyaları silinsin mi? Bu işlem geri alınamaz.`)) return;
    try {
      await istek("/api/harita/" + id, { method: "DELETE" });
      await oncekileriYukle();
      Ses.duyur(`"${ad}" haritası silindi.`, el("onceki-durum"));
      el("onceki-ara").focus();
    } catch (h) { Ses.duyur(h.mesaj, el("onceki-durum")); }
  }

  el("onceki-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const v = await oncekileriYukle();
    if (v) Ses.duyur(el("onceki-durum").textContent, el("onceki-durum"));
  });

  // ---------- 7. Sesli komutlar ----------

  const SAYI_KELIMELERI = { "yüz": 100, "iki yüz": 200, "üç yüz": 300, "dört yüz": 400, "beş yüz": 500, "altı yüz": 600,
    "yedi yüz": 700, "sekiz yüz": 800, "dokuz yüz": 900, "bin": 1000, "bin beş yüz": 1500, "iki bin": 2000 };

  function alaniSec(metin) {
    let n = parseInt(metin.replace(/\./g, ""), 10);
    if (isNaN(n)) n = SAYI_KELIMELERI[metin.replace(/\s*metre.*$/, "").trim()];
    if (!n) return null;
    const secenekler = [...el("alan").options].map((o) => Number(o.value));
    const enYakin = secenekler.reduce((a, b) => (Math.abs(b - n) < Math.abs(a - n) ? b : a));
    el("alan").value = String(enYakin);
    return enYakin;
  }

  function yardim() {
    Ses.konus("Kullanabileceğiniz komutlar: " + Ses.komutListesi().join(". ") +
      ". Bir yazı alanındayken komut dışında söylediğiniz her şey o alana yazılır.");
  }

  const K = Ses.komutEkle;
  K(/^(yardım|komutlar|ne diyebilirim)/, yardim, "yardım: komutları dinlersiniz");
  K(/^(dur|sus|sessiz|yeter)$/, () => Ses.sustur(), "sus: konuşmayı durdurur");
  K(/^(tekrar|tekrarla|tekrar et)$/, () => Ses.konus(sonHarita ? haritaAnlatimi(sonHarita) : (formDurum.textContent || "Henüz bir mesaj yok.")), "tekrarla: son bilgiyi yeniden okur");
  K(/^(?:yer|konum|adres)\s+(.+)/, (m, ham) => {
    el("yer").value = ham.replace(/^\s*(yer|konum|adres)\s+/i, "").replace(/[.!?]+$/, "");
    el("yer").dispatchEvent(new Event("input", { bubbles: true }));
    konumuBul();
  }, "yer, ardından yer adı: örneğin, yer Yozgat Bozok Üniversitesi");
  K(/^alan\s+(.+)/, (m) => {
    const n = alaniSec(m[1]);
    Ses.duyur(n ? `Alan ${n} metre olarak seçildi.` : "Alanı anlayamadım. Örneğin, alan altı yüz, deyin.", formDurum);
  }, "alan, ardından metre: örneğin, alan altı yüz");
  K(/^başlık\s+(.+)/, (m, ham) => {
    el("baslik").value = ham.replace(/^\s*başlık\s+/i, "").replace(/[.!?]+$/, "").slice(0, 40);
    brailleOnizle().then((b) => Ses.duyur(`Başlık: ${el("baslik").value}.` + (b && !b.baslik_olarak_sigar ? " Bu başlık banda sığmıyor, kısaltın." : ""), formDurum));
  }, "başlık, ardından metin: haritanın üstüne Braille ile yazılır");
  K(/^kabartma\s+(standart|normal|belirgin|yüksek)/, (m) => {
    el("kabartma").value = { standart: "standart", normal: "standart", belirgin: "belirgin", "yüksek": "yuksek" }[m[1]];
    Ses.duyur("Kabartma seviyesi: " + el("kabartma").options[el("kabartma").selectedIndex].text, formDurum);
  }, "kabartma standart, belirgin ya da yüksek");
  K(/^(haritayı )?(üret|oluştur|hazırla|başlat)|^harita(yı)? (üret|oluştur|hazırla)/, () => haritaUret(), "haritayı üret: haritayı hazırlar");
  K(/(anlat|dinle|haritada ne var)/, () => Ses.konus(sonHarita ? haritaAnlatimi(sonHarita) : "Henüz bir harita yok. Önce haritayı üretin."), "haritayı anlat: hazırlanan haritayı sesli anlatır");
  K(/^(indir|modeli indir|dosyayı indir)/, () => {
    const a = sonucAlani.querySelector("a.indir");
    if (!a) { Ses.duyur("İndirilecek bir harita yok. Önce haritayı üretin.", formDurum); return; }
    a.click();
    Ses.duyur("Harita modeli indiriliyor.", formDurum);
  }, "indir: harita modelini indirir");
  K(/^(önceki haritalar|geçmiş|kayıtlı haritalar|önceki)/, async () => {
    el("onceki").scrollIntoView();
    const v = await oncekileriYukle("");
    if (!v) return;
    const ilkler = v.haritalar.slice(0, 5).map(oncekiAdi).join(", ");
    Ses.duyur(el("onceki-durum").textContent + (ilkler ? " En yeniler: " + ilkler + "." : ""), el("onceki-durum"));
    Ses.sessizOdakla(el("onceki-ara"));
  }, "önceki haritalar: kayıtlı haritaları okur");
  K(/^ara\s+(.+)/, async (m) => {
    el("onceki-ara").value = m[1];
    el("onceki").scrollIntoView();
    const v = await oncekileriYukle(m[1]);
    if (v) Ses.duyur(el("onceki-durum").textContent + (v.haritalar.length ? " İlki: " + oncekiAdi(v.haritalar[0]) + "." : ""), el("onceki-durum"));
  }, "ara, ardından kelime: önceki haritalarda arar");
  K(/^(sayfayı oku|sayfayı sesli oku|oku)$/, () => Ses.sayfayiOku(), "sayfayı oku: sayfanın tamamını okur");
  K(/^(bina ekle|yeni bina)$/, () => binaSatiriEkle(), "bina ekle: bina adı satırı ekler");

  // ---------- Başlangıç ----------
  oncekileriYukle();
})();
