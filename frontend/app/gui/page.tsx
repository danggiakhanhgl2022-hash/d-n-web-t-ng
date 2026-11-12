"use client";

import {useCallback, useEffect, useState} from "react";
import {useRouter} from "next/navigation";

const KEY = "gui-token";

// Link /gui chỉ làm một việc: mở phiếu mới hoặc tiếp tục phiếu đang làm dở. Lời chào nằm ở trang chủ, không chào lại ở đây.
export default function ClientStart() {
  const router = useRouter();
  const [error, setError] = useState("");

  const open = useCallback(async () => {
    setError("");
    try {
      let saved = "";
      try {saved = localStorage.getItem(KEY) || "";} catch { /* bỏ qua */ }
      if (saved) {
        const r = await fetch(`/api/v1/public/${saved}/project`, {cache: "no-store"});
        if (r.ok) {router.replace(`/gui/${saved}`); return;}
        try {localStorage.removeItem(KEY);} catch { /* bỏ qua */ }
      }
      const r = await fetch("/api/v1/public/start", {method: "POST"});
      const data = await r.json();
      if (!r.ok) throw new Error(data.error?.message || "Chưa mở được phiếu, anh chị thử lại giúp chúng tôi nhé.");
      try {localStorage.setItem(KEY, data.token);} catch { /* bỏ qua */ }
      router.replace(`/gui/${data.token}`);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Chưa mở được phiếu, anh chị thử lại giúp chúng tôi nhé.");
    }
  }, [router]);

  useEffect(() => {void open();}, [open]);

  return (
    <main className="gui-screen gui-skin">
      <div className="gui-card">
        <span className="gui-eyebrow">B PRODUCTIONS</span>
        {error
          ? <><p role="alert">{error}</p><button className="gui-cta" onClick={open}>Thử lại ↗</button></>
          : <p>Đang chuẩn bị phiếu cho anh chị, vui lòng chờ vài giây…</p>}
      </div>
    </main>
  );
}
