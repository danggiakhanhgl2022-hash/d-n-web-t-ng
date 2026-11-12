"use client";

import {useState} from "react";

type Obj = Record<string, any>;

/** Hộp cho nhân viên: tạo, sao chép, ngừng link cho khách điền và gửi tệp. */
export default function ShareBox({project, api, reload, editable}: {project: Obj; api: (path: string, init?: RequestInit) => Promise<any>; reload: () => Promise<void>; editable: boolean}) {
  const [busy, setBusy] = useState(false);
  const [copied, setCopied] = useState(false);
  const [error, setError] = useState("");
  if (!editable) return null;
  const link: Obj = project.client_link || {};
  const url = link.active && link.path ? `${window.location.origin}${link.path}` : "";
  const run = async (fn: () => Promise<unknown>) => {
    setBusy(true); setError("");
    try {await fn(); await reload();} catch (e) {setError(e instanceof Error ? e.message : "Không thực hiện được.");} finally {setBusy(false);}
  };
  const when = (iso?: string) => iso ? new Date(iso).toLocaleString("vi-VN", {day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit"}) : "";
  const clientFiles = (project.sources || []).filter((s: Obj) => s.via === "CLIENT_LINK").length;
  return <section className="share-box" aria-label="Link cho khách">
    <div>
      <b>Cho khách tự điền trên web</b>
      <p>{url
        ? link.submitted_at ? `Khách đã gửi lúc ${when(link.submitted_at)}. Khách đã gửi ${clientFiles} tệp. Link hết hạn ${when(link.expires_at)}.` : `Khách chưa gửi. Đã có ${clientFiles} tệp. Link hết hạn ${when(link.expires_at)}.`
        : "Khách đã có thể tự bắt đầu từ link chung. Chỉ tạo link riêng khi muốn gửi đúng một khách này tiếp tục phiếu của họ."}</p>
      {url && <input readOnly value={url} onFocus={e => e.currentTarget.select()} aria-label="Link cho khách" />}
      {error && <p className="share-error" role="alert">{error}</p>}
    </div>
    <div className="share-actions">
      {url && <button type="button" disabled={busy} onClick={async () => {await navigator.clipboard.writeText(url); setCopied(true); setTimeout(() => setCopied(false), 2500);}}>{copied ? "Đã chép" : "Sao chép link"}</button>}
      <button type="button" disabled={busy} className={url ? "secondary" : ""} onClick={() => run(() => api(`/projects/${project.id}/share-link`, {method: "POST", body: JSON.stringify({days: 14})}))}>{url ? "Tạo link mới" : "Tạo link cho khách"}</button>
      {url && <button type="button" disabled={busy} className="secondary" onClick={() => run(() => api(`/projects/${project.id}/share-link`, {method: "DELETE"}))}>Ngừng link</button>}
    </div>
  </section>;
}
