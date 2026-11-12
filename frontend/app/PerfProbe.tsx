"use client";
import {useEffect} from "react";

// Công cụ đo độ mượt, CHỈ chạy khi mở trang với ?perf=1 (khách bình thường không thấy).
// Hiện khung nhỏ góc trái dưới: số khung/giây hiện tại, khung chậm nhất, và bảng tổng hợp theo từng chương.
export default function PerfProbe() {
  useEffect(() => {
    if (!new URLSearchParams(location.search).has("perf")) return;
    const box = document.createElement("pre");
    box.style.cssText = "position:fixed;left:8px;bottom:8px;z-index:2147483647;margin:0;padding:8px 10px;max-height:46vh;overflow:auto;background:#000c;color:#9f9;font:11px/1.35 monospace;border-radius:6px;pointer-events:none;white-space:pre";
    document.body.appendChild(box);
    const stats: Record<string, {frames: number; time: number; worst: number; slow: number; long: number}> = {};
    const chapter = () => {
      const el = document.querySelector<HTMLElement>(".renaissance-cinema");
      const label = document.querySelector<HTMLElement>(".cinema-chapter[data-active=true]");
      return (label?.dataset.chapter || el?.dataset.chapter || "?") + "";
    };
    const key = () => "chuong " + (document.querySelector(".renaissance-cinema")?.getAttribute("data-chapter") ?? "?") + (scrollY < 10 ? " (dau trang)" : "");
    let last = performance.now(), raf = 0, fps = 0, acc = 0, n = 0;
    const frame = (now: number) => {
      raf = requestAnimationFrame(frame);
      const dt = now - last; last = now;
      if (dt > 500) return; // bỏ qua lúc tab bị ẩn
      const k = key();
      const s = (stats[k] ||= {frames: 0, time: 0, worst: 0, slow: 0, long: 0});
      s.frames++; s.time += dt; s.worst = Math.max(s.worst, dt); if (dt > 33.4) s.slow++;
      acc += dt; n++;
      if (acc >= 500) { fps = Math.round(1000 * n / acc); acc = 0; n = 0; render(); }
    };
    let po: PerformanceObserver | null = null;
    try {
      po = new PerformanceObserver(list => list.getEntries().forEach(e => { (stats[key()] ||= {frames: 0, time: 0, worst: 0, slow: 0, long: 0}).long++; }));
      po.observe({entryTypes: ["longtask"]});
    } catch {}
    const render = () => {
      const rows = Object.entries(stats).map(([k, s]) => {
        const avg = s.frames ? Math.round(1000 * s.frames / s.time) : 0;
        return `${k.padEnd(18)} ${String(avg).padStart(3)} fps  cham nhat ${String(Math.round(s.worst)).padStart(4)}ms  khung>33ms ${String(s.slow).padStart(3)}  tac vu dai ${s.long}`;
      });
      box.textContent = `DO DO MUOT  |  hien tai ${fps} fps\n` + rows.join("\n");
    };
    raf = requestAnimationFrame(frame);
    void chapter;
    return () => { cancelAnimationFrame(raf); po?.disconnect(); box.remove(); };
  }, []);
  return null;
}
