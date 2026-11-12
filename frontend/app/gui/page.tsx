"use client";

import {useEffect, useState} from "react";
import {useRouter} from "next/navigation";

const KEY = "gui-token";

// Khách vào /gui là bắt đầu luôn: hệ thống tự mở phiếu, lần sau vào lại sẽ tiếp tục phiếu cũ.
export default function ClientStart() {
  const router = useRouter();
  const [state, setState] = useState<"check" | "ready" | "busy">("check");
  const [error, setError] = useState("");

  useEffect(() => {
    let saved = "";
    try {saved = localStorage.getItem(KEY) || "";} catch { /* bỏ qua */ }
    if (!saved) {setState("ready"); return;}
    fetch(`/api/v1/public/${saved}/project`, {cache: "no-store"}).then(r => {
      if (r.ok) router.replace(`/gui/${saved}`);
      else {try {localStorage.removeItem(KEY);} catch { /* bỏ qua */ } setState("ready");}
    }).catch(() => setState("ready"));
  }, [router]);

  async function start() {
    setState("busy"); setError("");
    try {
      const r = await fetch("/api/v1/public/start", {method: "POST"});
      const data = await r.json();
      if (!r.ok) throw new Error(data.error?.message || "Chưa mở được phiếu, anh chị thử lại nhé.");
      try {localStorage.setItem(KEY, data.token);} catch { /* bỏ qua */ }
      router.replace(`/gui/${data.token}`);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Chưa mở được phiếu, anh chị thử lại nhé.");
      setState("ready");
    }
  }

  if (state === "check") return <main className="gui-screen"><div className="gui-card"><p>Đang mở…</p></div></main>;
  return (
    <main className="gui-screen gui-skin">
      <div className="gui-card gui-start">
        <span className="gui-eyebrow">01 — XIN CHÀO</span>
        <h1>Chào anh chị! <em>Mời anh chị kể về video cần làm.</em></h1>
        <p>Bộ câu hỏi rất nhanh, khoảng 5–7 phút, mỗi câu đã có sẵn đáp án. Không cần tạo tài khoản, anh chị có thể dừng rồi quay lại tiếp bất cứ lúc nào.</p>
        {error && <p role="alert">{error}</p>}
        <button className="gui-cta" disabled={state === "busy"} onClick={start}>{state === "busy" ? "Đang mở phiếu…" : "Mời anh chị bắt đầu"} <span aria-hidden="true">↗</span></button>
      </div>
    </main>
  );
}
