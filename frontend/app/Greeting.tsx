"use client";

import {useEffect, useState} from "react";

const KEY = "gui-token";

// Lời chào duy nhất của khách. Khách mới bấm là vào thẳng phiếu; khách đang làm dở thấy nút "Tiếp tục", không phải đọc lại lời chào.
export default function Greeting() {
  const [saved, setSaved] = useState<{token: string; count: number} | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    let token = "";
    try {token = localStorage.getItem(KEY) || "";} catch { /* bỏ qua */ }
    if (!token) return;
    fetch(`/api/v1/public/${token}/project`, {cache: "no-store"}).then(async r => {
      if (!r.ok) {try {localStorage.removeItem(KEY);} catch { /* bỏ qua */ } return;}
      const view = await r.json();
      if (!view.submitted_at) setSaved({token, count: (view.answers || []).length});
    }).catch(() => { /* mất mạng thì coi như khách mới */ });
  }, []);

  async function begin() {
    setBusy(true); setError("");
    try {
      let token = saved?.token || "";
      if (!token) {
        const r = await fetch("/api/v1/public/start", {method: "POST"});
        const data = await r.json();
        if (!r.ok) throw new Error(data.error?.message || "Chưa mở được phiếu, anh chị thử lại giúp chúng tôi nhé.");
        token = data.token;
        try {localStorage.setItem(KEY, token);} catch { /* bỏ qua */ }
      }
      window.location.assign(`/gui/${token}`);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Chưa mở được phiếu, anh chị thử lại giúp chúng tôi nhé.");
      setBusy(false);
    }
  }

  const resume = !!saved && saved.count > 0;
  return <div className="login-panel" id="login-form"><div className="login-box">
    <span className="eyebrow">{resume ? "CHÀO MỪNG ANH CHỊ QUAY LẠI" : "XIN CHÀO"}</span>
    {resume ? <>
      <h2>Anh chị đang làm dở phiếu</h2>
      <p className="muted">Chúng tôi đã lưu {saved!.count} câu trả lời của anh chị. Anh chị làm tiếp từ chỗ đang dừng nhé.</p>
    </> : <>
      <h2>Chào anh chị</h2>
      <p className="muted">Đây là nơi thu thập thông tin từ khách hàng để hiểu được yêu cầu của anh chị. Từ đó phía chúng tôi sẽ đề xuất phương án hợp lý cho anh chị. Anh chị vui lòng phối hợp trả lời giúp những câu hỏi này nhé. Câu hỏi rất nhanh, trả lời hết bộ này khoảng năm, bảy phút. Mỗi câu hỏi đều có sẵn câu trả lời, anh chị chỉ cần vài cú click chuột là xong. Mời anh chị bắt đầu.</p>
    </>}
    {error && <div role="alert" className="alert error">{error}</div>}
    <button type="button" className="btn full" disabled={busy} onClick={begin}>{busy ? "Đang chuẩn bị phiếu, vui lòng chờ vài giây…" : resume ? "Tiếp tục điền phiếu" : "Mời anh chị bắt đầu"} ↗</button>
    {resume && <button type="button" className="text-btn" disabled={busy} onClick={() => {try {localStorage.removeItem(KEY);} catch { /* bỏ qua */ } setSaved(null);}}>Bắt đầu một phiếu mới</button>}
  </div></div>;
}
