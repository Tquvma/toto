// Telegram /hava komutuna cevap veren Cloudflare Worker.
//
// Telegram her mesajı webhook olarak bu Worker'a gönderir; cevap doğrudan
// webhook yanıtında döner, bu yüzden Worker'ın bot token'ına ihtiyacı yoktur.
//
// Ortam değişkenleri (Cloudflare → Worker → Settings → Variables and Secrets):
//   WEBHOOK_SECRET   (zorunlu) setWebhook'ta verilen secret_token ile aynı olmalı
//   ALLOWED_CHAT_ID  (isteğe bağlı) Verilirse bot sadece bu sohbete cevap verir
//   CITY             (isteğe bağlı) /hava için varsayılan şehirler, "Bursa, Pattaya"

const GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search";
const FORECAST_URL = "https://api.open-meteo.com/v1/forecast";

// WMO hava durumu kodları: https://open-meteo.com/en/docs
const WEATHER_CODES = {
  0: ["☀️", "Açık"],
  1: ["🌤️", "Çoğunlukla açık"],
  2: ["⛅", "Parçalı bulutlu"],
  3: ["☁️", "Kapalı"],
  45: ["🌫️", "Sisli"],
  48: ["🌫️", "Kırağılı sis"],
  51: ["🌦️", "Hafif çisenti"],
  53: ["🌦️", "Çisenti"],
  55: ["🌦️", "Yoğun çisenti"],
  56: ["🌧️", "Hafif dondurucu çisenti"],
  57: ["🌧️", "Dondurucu çisenti"],
  61: ["🌧️", "Hafif yağmur"],
  63: ["🌧️", "Yağmur"],
  65: ["🌧️", "Kuvvetli yağmur"],
  66: ["🌧️", "Hafif dondurucu yağmur"],
  67: ["🌧️", "Dondurucu yağmur"],
  71: ["🌨️", "Hafif kar"],
  73: ["🌨️", "Kar"],
  75: ["❄️", "Yoğun kar"],
  77: ["🌨️", "Kar taneleri"],
  80: ["🌦️", "Hafif sağanak"],
  81: ["🌧️", "Sağanak"],
  82: ["⛈️", "Şiddetli sağanak"],
  85: ["🌨️", "Hafif kar sağanağı"],
  86: ["❄️", "Yoğun kar sağanağı"],
  95: ["⛈️", "Gök gürültülü fırtına"],
  96: ["⛈️", "Hafif dolulu fırtına"],
  99: ["⛈️", "Şiddetli dolulu fırtına"],
};

const HELP = [
  "Merhaba! Komutlar:",
  "/hava – varsayılan şehirlerin hava durumu",
  "/hava İzmir – istediğin şehrin hava durumu",
  "/hava Bursa, Pattaya – birden fazla şehir",
].join("\n");

async function getJson(url, params, attempts = 2) {
  for (let attempt = 1; ; attempt++) {
    try {
      const resp = await fetch(`${url}?${new URLSearchParams(params)}`);
      if (!resp.ok) throw new Error(`${url} → HTTP ${resp.status}`);
      return await resp.json();
    } catch (err) {
      if (attempt >= attempts) throw err;
    }
  }
}

async function findCity(name) {
  const data = await getJson(GEOCODING_URL, { name, count: 1, language: "tr" });
  const city = data.results?.[0];
  if (!city) return null;
  return { name: city.name, lat: city.latitude, lon: city.longitude, tz: city.timezone || "auto" };
}

function getForecast(city) {
  return getJson(FORECAST_URL, {
    latitude: city.lat,
    longitude: city.lon,
    timezone: city.tz,
    forecast_days: 1,
    current: "temperature_2m,apparent_temperature,weather_code",
    daily: [
      "weather_code",
      "temperature_2m_max",
      "temperature_2m_min",
      "precipitation_probability_max",
      "precipitation_sum",
      "wind_speed_10m_max",
      "sunrise",
      "sunset",
    ].join(","),
  });
}

const describe = (code) => WEATHER_CODES[code] || ["🌡️", "Bilinmiyor"];
const round = (n) => Math.round(n);

function advice(daily) {
  const tips = [];
  if ((daily.precipitation_probability_max[0] || 0) >= 50) tips.push("☂️ Şemsiyeni almayı unutma.");
  if (daily.temperature_2m_min[0] <= 5) tips.push("🧥 Sıkı giyin, hava soğuk.");
  else if (daily.temperature_2m_max[0] >= 30) tips.push("🧴 Sıcak bir gün, bol su iç.");
  if (daily.wind_speed_10m_max[0] >= 40) tips.push("💨 Kuvvetli rüzgar bekleniyor.");
  return tips;
}

function cityReport(name, forecast) {
  const { current, daily } = forecast;
  const [emoji, text] = describe(daily.weather_code[0]);
  const [nowEmoji, nowText] = describe(current.weather_code);
  return [
    `📍 ${name}`,
    `${emoji} ${text}`,
    `🌡️ En düşük ${round(daily.temperature_2m_min[0])}°C / en yüksek ${round(daily.temperature_2m_max[0])}°C`,
    `${nowEmoji} Şu an ${round(current.temperature_2m)}°C, hissedilen ${round(current.apparent_temperature)}°C (${nowText.toLocaleLowerCase("tr")})`,
    `💧 Yağış ihtimali %${daily.precipitation_probability_max[0] || 0} (${daily.precipitation_sum[0].toFixed(1)} mm)`,
    `💨 Rüzgar en fazla ${round(daily.wind_speed_10m_max[0])} km/s`,
    `🌄 Gün doğumu ${daily.sunrise[0].slice(-5)}, gün batımı ${daily.sunset[0].slice(-5)}`,
    ...advice(daily),
  ].join("\n");
}

export async function weatherReply(names) {
  const reports = await Promise.all(
    names.map(async (name) => {
      const city = await findCity(name);
      if (!city) return `📍 ${name}\n❓ Şehir bulunamadı.`;
      return cityReport(city.name, await getForecast(city));
    }),
  );
  return reports.join("\n\n");
}

const splitCities = (s) =>
  s
    .split(",")
    .map((n) => n.trim())
    .filter(Boolean);

export async function replyFor(text, env) {
  // "/hava@BotAdi İzmir" → komut "/hava", argüman "İzmir"
  const match = text.trim().match(/^(\/\S+?)(?:@\S+)?(?:\s+([\s\S]*))?$/);
  if (!match) return null;
  const [, command, args = ""] = match;
  if (command === "/start" || command === "/yardim") return HELP;
  if (command !== "/hava") return null;
  const names = splitCities(args).length ? splitCities(args) : splitCities(env.CITY || "Bursa, Pattaya");
  return weatherReply(names.slice(0, 5));
}

export default {
  async fetch(request, env) {
    if (request.method !== "POST") return new Response("Hava durumu botu çalışıyor.");
    if (!env.WEBHOOK_SECRET || request.headers.get("X-Telegram-Bot-Api-Secret-Token") !== env.WEBHOOK_SECRET) {
      return new Response("Yetkisiz", { status: 401 });
    }

    const update = await request.json();
    const message = update.message;
    if (!message?.text) return new Response("ok");

    const chatId = message.chat.id;
    if (env.ALLOWED_CHAT_ID && String(chatId) !== env.ALLOWED_CHAT_ID.trim()) {
      return new Response("ok");
    }

    let text;
    try {
      text = await replyFor(message.text, env);
    } catch (err) {
      console.error(err);
      text = "⚠️ Hava durumu alınamadı, biraz sonra tekrar dene.";
    }
    if (!text) return new Response("ok");

    // Cevabı webhook yanıtında gönder: Telegram bunu sendMessage çağrısı olarak işler
    return Response.json({ method: "sendMessage", chat_id: chatId, text });
  },
};
