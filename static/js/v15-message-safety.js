(() => {
  const normalize = (value) => String(value || "")
    .toLocaleLowerCase("tr-TR")
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .replaceAll("ı", "i");

  const rules = [
    { score: 78, reason: "Şifre veya doğrulama kodu talebi içeriyor", terms: ["dogrulama kodu", "sms kodu", "onay kodu", "otp kodu", "kart sifresi", "e-devlet sifresi", "cvv kodu", "sifreni gonder"] },
    { score: 68, reason: "Cihaza uzaktan erişim veya ekran paylaşımı istiyor", terms: ["anydesk", "teamviewer", "uzak masaustu", "uzaktan baglan", "ekran paylas"] },
    { score: 52, reason: "Kimlik veya kart görüntüsü paylaşımı istiyor", terms: ["tc kimlik", "kimlik fotograf", "kart fotograf", "selfie ile kimlik"] },
    { score: 42, reason: "Takibi zor bir ödeme yöntemi öneriyor", terms: ["kripto ile ode", "usdt gonder", "bitcoin gonder", "hediye karti al", "gift card"] },
    { score: 24, reason: "Ön ödeme, havale veya kapora ifadesi içeriyor", terms: ["kapora", "on odeme", "havale yap", "eft yap", "ibana gonder", "odeme linki", "parayi gonder"] },
    { score: 18, reason: "Acele ödeme veya baskı ifadesi içeriyor", terms: ["hemen gonder", "simdi gonder", "bugun yatir", "acele et", "yalnizca bugun"] },
    { score: 14, reason: "Görüşmeyi platform dışına taşıma isteği içeriyor", terms: ["whatsapptan", "whatsappa gec", "telegramdan", "instagramdan yaz", "buradan yazma"] },
  ];
  const shortLink = /(?:bit\.ly|tinyurl\.com|t\.co|cutt\.ly|shorturl\.at|is\.gd|rb\.gy|rebrand\.ly)\//i;
  const anyLink = /(?:https?:\/\/|www\.)\S+/i;

  const analyze = (value) => {
    const text = normalize(value);
    let score = 0;
    const reasons = [];
    rules.forEach((rule) => {
      if (rule.terms.some((term) => text.includes(term))) {
        score += rule.score;
        if (!reasons.includes(rule.reason)) reasons.push(rule.reason);
      }
    });
    if (shortLink.test(value)) {
      score += 48;
      reasons.push("Kısaltılmış ve hedefi görünmeyen bağlantı içeriyor");
    } else if (anyLink.test(value)) {
      score += 16;
      reasons.push("Harici internet bağlantısı içeriyor");
    }
    score = Math.min(100, score);
    const level = score >= 70 ? "critical" : score >= 45 ? "high" : score >= 20 ? "medium" : "safe";
    return { score, level, reasons: [...new Set(reasons)].slice(0, 4) };
  };

  document.querySelectorAll("[data-message-safety-form]").forEach((form) => {
    const input = form.querySelector("[data-message-safety-input]");
    const preview = form.querySelector("[data-message-safety-preview]");
    const title = form.querySelector("[data-message-safety-title]");
    const advice = form.querySelector("[data-message-safety-advice]");
    const list = form.querySelector("[data-message-safety-reasons]");
    const confirmWrap = form.querySelector("[data-message-safety-confirm]");
    const confirmBox = form.querySelector("[data-safety-confirm-checkbox]");
    const count = form.querySelector("[data-message-character-count]");
    if (!input || !preview) return;

    const render = () => {
      const result = analyze(input.value);
      if (count) count.textContent = String(input.value.length);
      preview.classList.remove("tone-medium", "tone-high", "tone-critical");
      if (result.level === "safe") {
        preview.hidden = true;
        if (confirmWrap && !confirmWrap.querySelector(".errorlist")) confirmWrap.hidden = true;
        if (confirmBox) confirmBox.checked = false;
        return;
      }
      preview.hidden = false;
      preview.classList.add(`tone-${result.level}`);
      title.textContent = result.level === "critical" ? "Kritik güvenlik uyarısı" : result.level === "high" ? "Yüksek risk uyarısı" : "Dikkat gerektiren mesaj";
      advice.textContent = result.level === "medium"
        ? "Platform dışına çıkarken, kapora gönderirken veya bağlantı açarken dikkatli ol."
        : "Şifre, doğrulama kodu, kart bilgisi ve kimlik fotoğrafı paylaşma; ödeme yapmadan önce karşı tarafı doğrula.";
      list.innerHTML = result.reasons.map((reason) => `<li>${reason}</li>`).join("");
      if (confirmWrap) confirmWrap.hidden = !["high", "critical"].includes(result.level);
    };

    input.addEventListener("input", render);
    render();
  });
})();
