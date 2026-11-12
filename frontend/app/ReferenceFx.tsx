"use client";
import {useEffect} from "react";

// Hiệu ứng nhẹ theo mẫu: thẻ câu hỏi hiện dần khi cuộn + thanh tiến độ. Không đụng vào logic form.
const SEL = ".q-card, .chapter-block, .cinema-feature, .cinema-document-preview";

export default function ReferenceFx() {
  useEffect(() => {
    const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    const root = document.documentElement;
    const bar = document.createElement("div");
    bar.className = "rs-progress";
    document.body.appendChild(bar);

    let ticking = false;
    const onScroll = () => {
      if (ticking) return; ticking = true;
      requestAnimationFrame(() => {
        ticking = false;
        const el = document.scrollingElement as HTMLElement | null;
        if (!el || el.scrollHeight <= el.clientHeight + 40) return;
        bar.style.transform = `scaleX(${Math.min(1, el.scrollTop / (el.scrollHeight - el.clientHeight))})`;
      });
    };
    document.addEventListener("scroll", onScroll, {capture: true, passive: true});

    let io: IntersectionObserver | null = null;
    const seen = new WeakSet<Element>();
    const watch = () => {
      document.querySelectorAll(SEL).forEach((el) => {
        if (seen.has(el)) return;
        seen.add(el);
        el.classList.add("rs-reveal");
        (el as HTMLElement).style.setProperty("--rs-d", `${(seen.has(el) ? Array.from(el.parentElement?.children || []).indexOf(el) % 4 : 0) * 70}ms`);
        io?.observe(el);
      });
    };
    if (!reduce && "IntersectionObserver" in window) {
      io = new IntersectionObserver((entries) => entries.forEach((en) => {
        if (en.isIntersecting) { en.target.classList.add("rs-in"); io?.unobserve(en.target); }
      }), {threshold: 0.08, rootMargin: "0px 0px -6% 0px"});
      root.classList.add("rs-fx");
      watch();
    }
    let moT = 0;
    const mo = new MutationObserver(() => { clearTimeout(moT); moT = window.setTimeout(() => { if (io) watch(); }, 200); });
    mo.observe(document.body, {childList: true, subtree: true});
    // an toàn: nếu có thẻ nào chưa hiện sau 2,5s (ví dụ nằm ngoài khung nhìn lạ) thì hiện luôn
    const safety = window.setTimeout(() => document.querySelectorAll(".rs-reveal:not(.rs-in)").forEach((e) => {
      const r = e.getBoundingClientRect(); if (r.top < innerHeight && r.bottom > 0) e.classList.add("rs-in");
    }), 2500);

    return () => {
      document.removeEventListener("scroll", onScroll, {capture: true} as EventListenerOptions);
      mo.disconnect(); io?.disconnect(); clearTimeout(safety); bar.remove(); root.classList.remove("rs-fx");
    };
  }, []);
  return null;
}
