/* Dokun & Dinle - ses katmanı
 *
 * Görme engelli kullanıcılar için sitenin sesli çalışan kısmı:
 *  1. Sesli rehber: odaklanılan alanı ve yapılacak işi sesli söyler, durum mesajlarını okur.
 *  2. Sesli komut: mikrofonla verilen Türkçe komutları anlar (Chrome / Edge).
 *  3. Sayfayı sesli okuma: sayfa içeriğini okur; duraklat, devam et, durdur, hız.
 *  4. Haritayı sesli anlatma: uygulama.js üretilen haritanın anlatımını Ses.konus() ile okutur.
 *
 * Tarayıcılar, kullanıcı bir tuşa basmadan ya da tıklamadan konuşmaya izin vermez.
 * Bu yüzden rehber "Sesli rehberi başlat" düğmesiyle (ya da daha önce açıldıysa ilk tuşta) başlar.
 */
"use strict";

const Ses = (() => {
  const sentezVar = "speechSynthesis" in window && "SpeechSynthesisUtterance" in window;
  const TanimaSinifi = window.SpeechRecognition || window.webkitSpeechRecognition;

  const el = (id) => document.getElementById(id);
  const durumKutusu = () => el("ses-durum");

  let rehberAcik = false;
  let sonMesaj = "";
  let turkceSes = null;
  let odakZamanlayici = null;
  const komutlar = [];          // uygulama.js tarafından eklenir: { kalip: RegExp, calistir: fn, aciklama }

  // ---------- Konuşma ----------

  function sesSec() {
    if (!sentezVar) return;
    const sesler = window.speechSynthesis.getVoices();
    turkceSes = sesler.find((s) => s.lang && s.lang.toLowerCase().startsWith("tr")) || null;
  }
  if (sentezVar) {
    sesSec();
    window.speechSynthesis.onvoiceschanged = sesSec;
  }

  function hiz() {
    const s = el("okuma-hizi");
    return s ? Number(s.value) : 1;
  }

  /** Metni sesli okur. Varsayılan olarak o an süren konuşmayı keser. */
  function konus(metin, { kes = true, bitince } = {}) {
    if (!metin) return;
    sonMesaj = metin;
    if (!sentezVar) { if (bitince) bitince(); return; }
    if (kes) window.speechSynthesis.cancel();
    const s = new SpeechSynthesisUtterance(metin);
    s.lang = "tr-TR";
    if (turkceSes) s.voice = turkceSes;
    s.rate = hiz();
    s.onstart = () => okumaDugmeleri(true);
    s.onend = () => { okumaDugmeleri(window.speechSynthesis.pending); if (bitince) bitince(); };
    s.onerror = () => { okumaDugmeleri(false); if (bitince) bitince(); };
    window.speechSynthesis.speak(s);
  }

  function sustur() {
    if (sentezVar) window.speechSynthesis.cancel();
    okumaDugmeleri(false);
  }

  /**
   * Bir durumu bildirir: ekranda (ve ekran okuyucuya) gösterir, rehber açıksa sesli okur.
   * hedef: mesajın yazılacağı role="status" öğesi (verilmezse araç çubuğundaki durum satırı).
   */
  function duyur(metin, hedef) {
    const kutu = hedef || durumKutusu();
    if (kutu) kutu.textContent = metin;
    if (rehberAcik) konus(metin);
    else sonMesaj = metin;
  }

  // ---------- Sesli rehber ----------

  const KARSILAMA =
    "Dokun ve Dinle'ye hoş geldiniz. Bu site, görme engelli bireyler için 3D yazıcıda basılabilen " +
    "kabartma harita hazırlar. Size her adımda sesli yol göstereceğim. " +
    "Sekme tuşuyla alanlar arasında gezinebilirsiniz; her alana geldiğinizde ne yapmanız gerektiğini söyleyeceğim. " +
    "Alt ve K tuşlarına birlikte basarak sesli komut verebilirsiniz; örneğin, yer Yozgat Bozok Üniversitesi, diyebilirsiniz. " +
    "Alt ve T son mesajı tekrarlar, Escape konuşmayı durdurur. " +
    "Ekran okuyucu kullanıyorsanız sesli rehberi kapatabilirsiniz. Şimdi haritası çıkarılacak yerin adını yazın.";

  function rehberDugmesiniGuncelle() {
    const d = el("rehber-dugme");
    if (!d) return;
    d.setAttribute("aria-pressed", String(rehberAcik));
    d.textContent = rehberAcik ? "Sesli rehberi kapat" : "Sesli rehberi başlat";
  }

  function rehberiAc({ karsila = true } = {}) {
    rehberAcik = true;
    kaydet("rehber", "acik");
    rehberDugmesiniGuncelle();
    if (karsila) {
      duyur(KARSILAMA);
      const ilk = el("yer");
      if (ilk) { odakSessiz = true; ilk.focus(); }
    }
  }

  function rehberiKapat() {
    rehberAcik = false;
    kaydet("rehber", "kapali");
    sustur();
    rehberDugmesiniGuncelle();
    const kutu = durumKutusu();
    if (kutu) kutu.textContent = "Sesli rehber kapatıldı.";
  }

  // Odaklanılan alanın etiketi ve ipucu okunur.
  let odakSessiz = false;   // programla odak verilirken bir kerelik susmak için
  function odakMetni(hedef) {
    const ipucu = hedef.getAttribute("data-rehber");
    if (!ipucu) return "";
    let etiket = "";
    if (hedef.labels && hedef.labels.length) etiket = hedef.labels[0].innerText.split("\n")[0].trim();
    else if (hedef.tagName === "BUTTON" || hedef.tagName === "A") etiket = hedef.innerText.trim();
    let deger = "";
    if (hedef.tagName === "SELECT") deger = "Seçili: " + hedef.options[hedef.selectedIndex].text + ".";
    else if (hedef.type === "checkbox") deger = hedef.checked ? "İşaretli." : "İşaretli değil.";
    else if (hedef.value && hedef.tagName === "INPUT") deger = "Yazılı: " + hedef.value + ".";
    return [etiket && etiket + ".", deger, ipucu].filter(Boolean).join(" ");
  }

  document.addEventListener("focusin", (e) => {
    if (!rehberAcik) return;
    if (odakSessiz) { odakSessiz = false; return; }
    const metin = odakMetni(e.target);
    if (!metin) return;
    clearTimeout(odakZamanlayici);
    odakZamanlayici = setTimeout(() => konus(metin), 120);
  });

  // ---------- Sesli komut ----------

  let tanima = null;
  let dinliyor = false;

  function kucuk(m) {
    return (m || "").replace(/I/g, "ı").replace(/İ/g, "i").toLowerCase().trim();
  }

  function komutEkle(kalip, calistir, aciklama) {
    komutlar.push({ kalip, calistir, aciklama });
  }

  function komutuIsle(soylenen) {
    const metin = kucuk(soylenen).replace(/[.!?]+$/, "");
    for (const k of komutlar) {
      const m = metin.match(k.kalip);
      if (m) { k.calistir(m, soylenen); return; }
    }
    // Komut değilse ve bir yazı alanındaysak söyleneni oraya yaz.
    const aktif = document.activeElement;
    if (aktif && aktif.tagName === "INPUT" && /^(text|search|)$/.test(aktif.type)) {
      aktif.value = soylenen.replace(/[.!?]+$/, "");
      aktif.dispatchEvent(new Event("input", { bubbles: true }));
      duyur("Yazıldı: " + aktif.value);
      return;
    }
    duyur("Söylediğinizi anlayamadım: " + soylenen + ". Komutları duymak için, yardım, deyin.");
  }

  function komutDugmesi(durum) {
    const d = el("komut-dugme");
    if (!d) return;
    d.setAttribute("aria-pressed", String(durum));
    d.textContent = durum ? "Dinliyorum… (durdur)" : "Sesli komut ver";
  }

  function dinle() {
    if (!TanimaSinifi) {
      duyur("Bu tarayıcı sesli komutu desteklemiyor. Google Chrome ya da Microsoft Edge kullanabilirsiniz.");
      return;
    }
    if (dinliyor) { tanima && tanima.stop(); return; }
    sustur();
    tanima = new TanimaSinifi();
    tanima.lang = "tr-TR";
    tanima.interimResults = false;
    tanima.maxAlternatives = 1;
    tanima.onresult = (e) => {
      const soylenen = e.results[0][0].transcript;
      komutuIsle(soylenen);
    };
    tanima.onerror = (e) => {
      const nedenler = {
        "not-allowed": "Mikrofon izni verilmedi. Tarayıcının adres çubuğundaki mikrofon simgesinden izin verebilirsiniz.",
        "no-speech": "Bir şey duyamadım. Tekrar denemek için Alt ve K tuşlarına basın.",
        "network": "Sesli komut için internet bağlantısı gerekiyor.",
        "audio-capture": "Mikrofon bulunamadı.",
      };
      duyur(nedenler[e.error] || "Sesli komut alınamadı.");
    };
    tanima.onend = () => { dinliyor = false; komutDugmesi(false); };
    // "Dinliyorum" sözü bittikten sonra mikrofon açılır; yoksa kendi sesini duyar.
    const baslat = () => {
      try { tanima.start(); dinliyor = true; komutDugmesi(true); }
      catch (_) { duyur("Sesli komut başlatılamadı."); }
    };
    const kutu = durumKutusu();
    if (kutu) kutu.textContent = "Dinliyorum…";
    if (sentezVar) konus("Dinliyorum", { bitince: baslat }); else baslat();
  }

  // ---------- Sayfayı sesli okuma ----------

  function okumaDugmeleri(okuyor) {
    ["okuma-duraklat", "okuma-devam", "okuma-durdur"].forEach((id) => {
      const d = el(id);
      if (d) d.disabled = !okuyor;
    });
  }

  function sayfayiOku() {
    const ana = el("main");
    if (!ana) return;
    // Gizli ve yalnızca süs amaçlı öğeler okunmaz.
    const kopya = ana.cloneNode(true);
    kopya.querySelectorAll("[aria-hidden='true'], script, style, svg, .gorsel-gizli-degil").forEach((n) => n.remove());
    const metin = kopya.innerText.replace(/\s+\n/g, "\n").replace(/\n{2,}/g, "\n").trim();
    konus(metin);
    const kutu = durumKutusu();
    if (kutu) kutu.textContent = "Sayfa sesli okunuyor.";
  }

  // ---------- Kalıcı tercih ----------

  function kaydet(anahtar, deger) {
    try { localStorage.setItem("dokun-" + anahtar, deger); } catch (_) { /* özel pencere vb. */ }
  }
  function oku(anahtar) {
    try { return localStorage.getItem("dokun-" + anahtar); } catch (_) { return null; }
  }

  // ---------- Kurulum ----------

  function kur() {
    const rehberDugme = el("rehber-dugme");
    const komutD = el("komut-dugme");

    if (!sentezVar) {
      if (rehberDugme) rehberDugme.disabled = true;
      ["sayfayi-oku"].forEach((id) => el(id) && (el(id).disabled = true));
      const kutu = durumKutusu();
      if (kutu) kutu.textContent = "Bu tarayıcı sesli okumayı desteklemiyor. NVDA veya VoiceOver gibi bir ekran okuyucu kullanabilirsiniz.";
    }
    if (!TanimaSinifi && komutD) {
      komutD.disabled = true;
      komutD.title = "Sesli komut Chrome ve Edge tarayıcılarında çalışır.";
    }

    rehberDugme && rehberDugme.addEventListener("click", () => (rehberAcik ? rehberiKapat() : rehberiAc()));
    komutD && komutD.addEventListener("click", dinle);
    el("tekrarla") && el("tekrarla").addEventListener("click", () => konus(sonMesaj || "Henüz bir mesaj yok."));
    el("sayfayi-oku") && el("sayfayi-oku").addEventListener("click", sayfayiOku);
    el("okuma-duraklat") && el("okuma-duraklat").addEventListener("click", () => sentezVar && window.speechSynthesis.pause());
    el("okuma-devam") && el("okuma-devam").addEventListener("click", () => sentezVar && window.speechSynthesis.resume());
    el("okuma-durdur") && el("okuma-durdur").addEventListener("click", sustur);

    // Kısayollar: Alt+K sesli komut, Alt+T tekrarla, Escape sustur.
    document.addEventListener("keydown", (e) => {
      if (e.altKey && !e.ctrlKey && (e.key === "k" || e.key === "K")) { e.preventDefault(); dinle(); }
      else if (e.altKey && !e.ctrlKey && (e.key === "t" || e.key === "T")) { e.preventDefault(); konus(sonMesaj || "Henüz bir mesaj yok."); }
      else if (e.key === "Escape") { sustur(); }
    });

    // Daha önce rehberi açmış kullanıcı için: ilk tuş ya da tıklamada rehber kendiliğinden açılır.
    if (sentezVar && oku("rehber") === "acik") {
      rehberAcik = true;
      rehberDugmesiniGuncelle();
      const ilkEtkilesim = () => {
        konus("Sesli rehber açık. Komutlar için Alt ve K tuşlarına basıp, yardım, deyin.");
        document.removeEventListener("keydown", ilkEtkilesim, true);
        document.removeEventListener("pointerdown", ilkEtkilesim, true);
      };
      document.addEventListener("keydown", ilkEtkilesim, true);
      document.addEventListener("pointerdown", ilkEtkilesim, true);
    }
  }

  document.addEventListener("DOMContentLoaded", kur);

  return {
    konus, sustur, duyur, komutEkle, dinle, sayfayiOku,
    get rehberAcik() { return rehberAcik; },
    sessizOdakla(oge) { odakSessiz = true; oge.focus(); },
    komutListesi: () => komutlar.filter((k) => k.aciklama).map((k) => k.aciklama),
  };
})();
