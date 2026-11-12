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
    if (!saved) {void start(); return;}
    fetch(`/api/v1/public/${saved}/project`, {cache: "no-store"}).then(r => {
      if (r.ok) router.replace(`/gui/${saved}`);
      else {try {localStorage.removeItem(KEY);} catch { /* bỏ qua */ } setState("ready");}
    }).catch(() => setState("ready"));
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [router]);

  async function start() {
    setState("busy"); setError("");
    try {
      const r = await fetch("/api/v1/public/start", {method: "POST"});
      const data = await r.json();
      if (!r.ok) throw new Error(data.error?.message || "Chưa mở được phiếu, bạn thử lại nhé.");
      try {localStorage.setItem(KEY, data.token);} catch { /* bỏ qua */ }
      router.replace(`/gui/${data.token}`);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Chưa mở được phiếu, bạn thử lại nhé.");
      setState("ready");
    }
  }

  if (state === "check") return <main className="gui-screen"><div className="gui-card"><p>Đang mở…</p></div></main>;
  return (
    <main className="gui-screen">
      <div className="gui-card gui-start">
        <h1>Chào anh chị, cảm ơn đã quan tâm đến dịch vụ làm video</h1>
        <p>Chỉ cần trả lời vài câu hỏi ngắn. Không cần tạo tài khoản, và anh chị có thể dừng rồi quay lại tiếp bất cứ lúc nào.</p>
        {error && <p role="alert">{error}</p>}
        <button className="btn" disabled={state === "busy"} onClick={start}>{state === "busy" ? "Đang mở phiếu…" : "Bắt đầu"}</button>
      </div>
    </main>
  );
}
