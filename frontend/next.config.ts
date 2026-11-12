import type { NextConfig } from "next";
const isProd = process.env.NODE_ENV === "production";
// Backend address for the same-origin /api proxy (set BACKEND_URL when deploying; defaults to local dev).
const rawBackend = process.env.BACKEND_URL || "http://127.0.0.1:8100";
const backendUrl = (/^https?:\/\//.test(rawBackend) ? rawBackend : `http://${rawBackend}`).replace(/\/+$/, "");

// Header an toàn áp dụng cho mọi trang. CSP để chế độ Report-Only trước vì cảnh 3D dùng worker/WebAssembly/blob:
// nên cần theo dõi vi phạm trước khi chuyển sang chặn thật (xem SECURITY.md).
const csp = [
  "default-src 'self'",
  "script-src 'self' 'unsafe-inline' 'wasm-unsafe-eval'" + (isProd ? "" : " 'unsafe-eval'"),
  "style-src 'self' 'unsafe-inline'",
  "img-src 'self' data: blob:",
  "media-src 'self' blob:",
  "font-src 'self' data:",
  "connect-src 'self' blob: data:",
  "worker-src 'self' blob:",
  "object-src 'none'",
  "base-uri 'self'",
  "form-action 'self'",
  "frame-ancestors 'none'",
].join("; ");

const securityHeaders = [
  {key: "X-Content-Type-Options", value: "nosniff"},
  {key: "X-Frame-Options", value: "DENY"},
  {key: "Referrer-Policy", value: "strict-origin-when-cross-origin"},
  {key: "Permissions-Policy", value: "camera=(), microphone=(), geolocation=(), payment=(), usb=()"},
  {key: "Cross-Origin-Opener-Policy", value: "same-origin"},
  {key: "Content-Security-Policy-Report-Only", value: csp},
  ...(isProd ? [{key: "Strict-Transport-Security", value: "max-age=63072000; includeSubDomains"}] : []),
];

const config: NextConfig = {
  poweredByHeader: false,
  // Khách gửi video tới 200 MB qua trang /gui; mặc định chỉ cho 10 MB khi chuyển tiếp.
  experimental: {proxyClientMaxBodySize: "250mb", proxyTimeout: 600000},
  // The launcher builds into a fresh directory before switching the server.
  // Direct npm commands keep the legacy default unless explicitly configured.
  distDir: process.env.VIDEO_OS_NEXT_DIST_DIR || ".next-v6",
  typescript: { tsconfigPath: process.env.VIDEO_OS_NEXT_TSCONFIG || "tsconfig.json" },
  async headers() { return [{source: "/:path*", headers: securityHeaders}]; },
  async rewrites() { return [{source: "/api/v1/:path*", destination: `${backendUrl}/api/v1/:path*`}]; },
};
export default config;
