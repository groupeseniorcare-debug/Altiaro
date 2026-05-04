/**
 * SEO bot routing — CRA setupProxy hook.
 *
 * Problématique : le pod Emergent expose un ingress qui dispatch par path :
 *   /api/* → backend FastAPI (port 8001)
 *   tout le reste → frontend CRA (port 3000)
 *
 * Or le `prerender_routing_middleware` côté backend ne peut intercepter
 * Googlebot/Bingbot que sur les paths /api/*. Quand un bot tape
 * `https://altea-home.com/blog/comment-installer-...`, l'ingress envoie
 * la requête au CRA qui retourne `index.html` générique (sans hreflang,
 * sans JSON-LD, sans contenu rendu) → catastrophe SEO.
 *
 * Fix :
 *   - On hook le dev-server CRA via `setupProxy.js` (pattern officiel CRA).
 *   - On détecte les User-Agents de SEO bots (Google/Bing/Yandex/Apple/etc.)
 *   - Sur tout path qui n'est PAS technique (/static, /uploads, /api, etc.),
 *     on PROXY (pas redirect) la requête vers le backend
 *     `/api/seo/prerender/?path=<path>` avec son host original.
 *   - Le backend sert alors le HTML prerender enrichi (h1, hreflang ×6,
 *     JSON-LD Article+FAQ+Breadcrumb, body article, OG tags Altea).
 *
 * Pourquoi proxy plutôt que 302 :
 *   - Googlebot suit les 302 mais préfère 200 direct (≤1 hop).
 *   - Le path original reste visible dans `request.url` côté backend
 *     pour l'audit, et l'URL canonique reste dans le `<link rel="canonical">`.
 *
 * Activation :
 *   - Ce fichier est auto-chargé par react-scripts si présent dans `src/`.
 *   - En dev (yarn start) ET en preview Emergent (craco start) : actif.
 *   - En prod build statique (CRA build + static server) : non-actif → il
 *     faudra un middleware équivalent dans le serveur statique de prod
 *     (Caddy/Nginx) ou activer le routing UA côté Approximated/Cloudflare.
 *
 * Logs : préfixe `[seo-proxy]` pour grep.
 */
const { createProxyMiddleware } = require("http-proxy-middleware");

// Backend interne (FastAPI uvicorn) — TOUJOURS localhost:8001 dans le pod
const BACKEND_INTERNAL = process.env.BACKEND_INTERNAL_URL || "http://localhost:8001";

// User-Agents SEO/AI bots qui doivent voir le prerender enrichi.
// On reste large : tout ce qui contient ces tokens.
const BOT_UA_REGEX = /(googlebot|bingbot|adsbot-google|google-extended|yandex(bot)?|duckduckbot|baiduspider|applebot|facebookexternalhit|twitterbot|slurp|linkedinbot|whatsapp|telegrambot|petalbot|claudebot|gptbot|chatgpt|perplexitybot|youbot|ccbot|amazonbot)/i;

// Paths techniques qui doivent rester sur le frontend CRA même pour bots
// (assets JS/CSS/images, manifestes, fichiers de vérification, etc.)
const PASSTHROUGH_PATHS = [
  /^\/static\//,
  /^\/uploads\//,
  /^\/assets\//,
  /^\/api\//,
  /^\/sockjs-node\//,
  /^\/_next\//,            // safety, pas notre cas
  /^\/__\//,
  /^\/favicon/,
  /^\/manifest\.json$/,
  /^\/robots\.txt$/,
  /^\/sitemap.*\.xml$/,
  /^\/sitemaps?\//,
  /^\/.*\.(?:js|css|png|jpe?g|gif|webp|avif|svg|ico|woff2?|ttf|eot|map|json|xml|txt|pdf)$/i,
  /^\/BingSiteAuth\.xml$/,
  /^\/.well-known\//,
];

function isPassthrough(url) {
  return PASSTHROUGH_PATHS.some((re) => re.test(url));
}

function looksLikeBot(req) {
  const ua = req.headers["user-agent"] || "";
  return BOT_UA_REGEX.test(ua);
}

module.exports = function (app) {
  // Middleware ordre 1 : intercepter les bots AVANT le webpack-dev-server.
  app.use((req, res, next) => {
    try {
      const url = req.url.split("?")[0];
      if (isPassthrough(url)) return next();
      if (!looksLikeBot(req)) return next();

      // On laisse les paths /api/seo/prerender/* passer en direct si déjà préfixés
      if (url.startsWith("/api/")) return next();

      // Hostname original — Approximated met `Apx-Incoming-Host` en source
      // de vérité. L'ingress Emergent en aval réécrit `X-Forwarded-Host`
      // avec le hostname interne (`commerce-builder-21.preview.emergentagent.com`)
      // donc on lit Apx-Incoming-Host EN PREMIER.
      const incomingHost =
        req.headers["apx-incoming-host"] ||
        req.headers["x-forwarded-host"] ||
        req.headers["x-original-host"] ||
        req.headers["host"] ||
        "";

      console.log(
        `[seo-proxy] BOT ${req.headers["user-agent"]?.slice(0, 60)}... ` +
        `host=${incomingHost} ${req.url} → backend (prerender_routing_middleware)`
      );

      // Proxy vers backend SANS pathRewrite : on forward le path original
      // (ex. /blog/comment-installer-...). Le backend a déjà
      // `prerender_routing_middleware.py` qui :
      //   1. détecte UA bot
      //   2. résout custom domain via X-Forwarded-Host / Apx-Incoming-Host
      //   3. matche path indexable (/blog/, /products/, /collections/, ...)
      //   4. génère le HTML enrichi via prerender_html()
      //   5. retourne avec headers X-Prerender: 1 + Cache-Control 5min.
      // On lui forwarde la requête telle quelle. Aucune duplication de logique.
      const proxy = createProxyMiddleware({
        target: BACKEND_INTERNAL,
        changeOrigin: false,   // on garde le Host original pour le backend middleware
        onProxyReq: (proxyReq) => {
          // Forward le host original explicitement, au cas où.
          if (incomingHost) {
            proxyReq.setHeader("X-Forwarded-Host", incomingHost);
            proxyReq.setHeader("Apx-Incoming-Host", incomingHost);
          }
          proxyReq.setHeader("X-Seo-Proxy", "1");
        },
        onError: (err, req, res) => {
          console.error(`[seo-proxy] ERROR proxying ${req.url}: ${err.message}`);
          res.status(502).end("SEO proxy error");
        },
        logLevel: "warn",
      });
      return proxy(req, res, next);
    } catch (e) {
      console.error("[seo-proxy] middleware exception:", e);
      return next();
    }
  });
};
