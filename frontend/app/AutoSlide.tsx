"use client";
import {useEffect} from "react";

// Sau phần mở đầu, trang tự cuộn liên tục qua các slide như video mẫu.
// Người dùng cuộn/chạm/bấm phím thì dừng, rồi tự chạy tiếp sau vài giây yên lặng.
const TOTAL_SECONDS = 75;   // thời gian chạy hết trang
const RESUME_AFTER_MS = 6000;
// Đặt true để bật lại tự cuộn. Hiện tắt: người dùng cuộn tay.
const ENABLED = false;

export default function AutoSlide() {
  useEffect(() => {
    if (!ENABLED || matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    let raf = 0, last = 0, pos = 0, paused = true, resumeTimer = 0, ended = false;
    const root = () => document.querySelector<HTMLElement>(".login-shell .renaissance-cinema");
    const introDone = () => root()?.dataset.introDone === "true";
    // Lưu đệm các giá trị tốn kém (đọc bố cục/DOM) để mỗi khung hình chỉ làm việc nhẹ.
    let max = 0, dlg = false;
    const refresh = () => { max = document.documentElement.scrollHeight - innerHeight; dlg = !!document.querySelector("dialog[open]"); };
    refresh();
    const cache = window.setInterval(refresh, 400);
    addEventListener("resize", refresh);

    const stop = () => {
      paused = true;
      clearTimeout(resumeTimer);
      resumeTimer = window.setTimeout(() => { if (!ended) { pos = scrollY; paused = false; last = 0; } }, RESUME_AFTER_MS);
    };
    const events: [string, AddEventListenerOptions][] = [["wheel", {passive: true}], ["touchstart", {passive: true}], ["keydown", {}], ["pointerdown", {}]];
    events.forEach(([n, o]) => window.addEventListener(n, stop, o));

    const frame = (now: number) => {
      raf = requestAnimationFrame(frame);
      if (paused || document.hidden || dlg) { last = 0; return; }
      if (!last) { last = now; pos = scrollY; return; }
      const dt = Math.min(64, now - last); last = now;
      if (max <= 0) return;
      // Nếu người dùng đã kéo thanh cuộn (không qua sự kiện trên), đồng bộ lại vị trí.
      if (Math.abs(scrollY - pos) > 4) pos = scrollY;
      pos = Math.min(max, pos + (max / TOTAL_SECONDS) * dt / 1000);
      scrollTo({top: pos, left: 0, behavior: "instant" as ScrollBehavior});
      if (pos >= max - 1) { ended = true; paused = true; }
    };

    // Chờ phần mở đầu chạy xong rồi mới bắt đầu.
    const wait = window.setInterval(() => {
      if (introDone()) {
        clearInterval(wait);
        window.setTimeout(() => { pos = scrollY; paused = false; last = 0; }, 1200);
      }
    }, 400);
    raf = requestAnimationFrame(frame);

    return () => {
      clearInterval(wait); clearInterval(cache); removeEventListener("resize", refresh); clearTimeout(resumeTimer); cancelAnimationFrame(raf);
      events.forEach(([n, o]) => window.removeEventListener(n, stop));
    };
  }, []);
  return null;
}
