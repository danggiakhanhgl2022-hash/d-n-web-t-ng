"use client";

import {useCallback, useEffect, useMemo, useState} from "react";
import {useParams} from "next/navigation";
import Intake, {QDef} from "../../Intake";
import Attach, {Uploader} from "../../Attach";
import {ATTACH_HINT} from "../../attachHints";

type Obj = Record<string, any>;
type SectionDef = {id: string; title: string; subtitle: string; part: string};

export default function ClientPage() {
  const {token} = useParams<{token: string}>();
  const [project, setProject] = useState<Obj | null>(null);
  const [questions, setQuestions] = useState<QDef[]>([]);
  const [sections, setSections] = useState<SectionDef[]>([]);
  const [brand, setBrand] = useState<Obj | null>(null);
  const [phase, setPhase] = useState<"loading" | "invalid" | "welcome" | "form" | "thanks">("loading");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [missing, setMissing] = useState<Obj[]>([]);

  const api = useCallback(async (path: string, init: RequestInit = {}) => {
    let url: string;
    const answer = path.match(/^\/projects\/[^/]+\/answers\/(.+)$/);
    if (path === "/brand") url = "/brand";
    else if (answer) url = `/public/${token}/answers/${answer[1]}`;
    else if (/^\/projects\/[^/]+$/.test(path)) url = `/public/${token}/project`;
    else throw new Error("Thao tác này không dùng được ở trang khách.");
    const headers = new Headers(init.headers);
    if (init.body) headers.set("Content-Type", "application/json");
    const response = await fetch("/api/v1" + url, {...init, headers, cache: "no-store"});
    if (!response.ok) {
      let data: Obj = {};
      try {data = await response.json();} catch { /* bỏ qua */ }
      const err: Error & {code?: string; details?: Obj[]} = new Error(data.error?.message || "Có lỗi xảy ra, bạn thử lại nhé.");
      err.code = data.error?.code; err.details = data.error?.details;
      throw err;
    }
    return response.json();
  }, [token]);

  useEffect(() => {
    let alive = true;
    (async () => {
      try {
        const [view, qs, b] = await Promise.all([
          fetch(`/api/v1/public/${token}/project`, {cache: "no-store"}).then(async r => {if (!r.ok) throw new Error("invalid"); return r.json();}),
          fetch(`/api/v1/public/${token}/questions`, {cache: "no-store"}).then(r => r.json()),
          fetch("/api/v1/brand").then(r => r.json()).catch(() => null),
        ]);
        if (!alive) return;
        setProject(view); setQuestions(qs.questions || []); setSections(qs.sections || []); setBrand(b);
        const started = view.answers.length > 0 || view.sources.length > 0 || sessionStorage.getItem(`gui-${token}`);
        setPhase(view.submitted_at ? "thanks" : started ? "form" : "welcome");
      } catch {
        if (alive) setPhase("invalid");
      }
    })();
    return () => {alive = false;};
  }, [token]);

  const upload: Uploader = useCallback((file, name, code, onProgress) => new Promise((resolve, reject) => {
    const form = new FormData();
    form.append("file", file, name);
    if (code) form.append("question_code", code);
    const xhr = new XMLHttpRequest();
    xhr.open("POST", `/api/v1/public/${token}/files`);
    xhr.upload.onprogress = e => {if (e.lengthComputable) onProgress(e.loaded / e.total);};
    xhr.onload = () => {
      let data: Obj = {};
      try {data = JSON.parse(xhr.responseText);} catch { /* bỏ qua */ }
      if (xhr.status >= 200 && xhr.status < 300) {setProject(data); resolve();}
      else reject(new Error(data.error?.message || "Chưa gửi được tệp, bạn thử lại nhé."));
    };
    xhr.onerror = () => reject(new Error("Mất kết nối giữa chừng. Bạn kiểm tra mạng rồi thử lại, tệp chưa bị mất."));
    xhr.send(form);
  }), [token]);

  const remove = useCallback(async (id: string) => {
    const response = await fetch(`/api/v1/public/${token}/files/${id}`, {method: "DELETE"});
    const data = await response.json();
    if (!response.ok) {setError(data.error?.message || "Chưa bỏ được tệp."); throw new Error("x");}
    setProject(data);
  }, [token]);

  const themeVars = useMemo(() => Object.fromEntries(Object.entries(brand?.colors || {}).map(([k, v]) => [`--b-${k.replace(/_/g, "-")}`, v as string])) as React.CSSProperties, [brand]);
  const studio = brand?.studio_name || "Studio";
  const label = useCallback((code: string) => questions.find(q => q.code === code)?.label || code, [questions]);
  const limits = project?.limits || {image: 25 * 1048576, audio: 60 * 1048576, video: 200 * 1048576};
  const open = useMemo(() => (project?.validation?.blockers || []).filter((b: Obj) => b.code === "ANSWER_REQUIRED"), [project]);
  const files: Obj[] = project?.sources || [];

  const submit = async () => {
    setBusy(true); setError("");
    try {
      const view = await fetch(`/api/v1/public/${token}/submit`, {method: "POST"});
      const data = await view.json();
      if (!view.ok) {
        setMissing(data.error?.details || []);
        throw new Error(data.error?.message || "Chưa gửi được.");
      }
      setProject(data); setMissing([]); setPhase("thanks");
      window.scrollTo({top: 0});
    } catch (e) {
      setError(e instanceof Error ? e.message : "Chưa gửi được, bạn thử lại nhé.");
    } finally {setBusy(false);}
  };
  const jump = (code: string) => {
    const el = document.querySelector(`[data-question-code="${code}"]`);
    el?.scrollIntoView({behavior: "smooth", block: "center"});
  };

  if (phase === "loading") return <main className="gui-screen" style={themeVars}><p className="gui-quiet">Đang mở phiếu của bạn…</p></main>;
  if (phase === "invalid") return <main className="gui-screen" style={themeVars}><div className="gui-card"><span className="gui-eyebrow">{studio.toUpperCase()}</span><h1>Đường link này không dùng được nữa</h1><p>Link có thể đã hết hạn hoặc được thay bằng link mới. Bạn nhắn cho {studio} để nhận link mới nhé, mọi thứ bạn đã điền trước đó vẫn còn.</p></div></main>;
  if (phase === "welcome") return <main className="gui-screen welcome" style={themeVars}>
    <div className="gui-card hero">
      <span className="gui-eyebrow">{studio.toUpperCase()}</span>
      <h1>Kể cho mình nghe video bạn cần</h1>
      <p>Mình hỏi từng chút một, bạn chỉ cần trả lời những gì bạn biết. Chỗ nào chưa chắc cứ bấm “Chưa biết”, mình sẽ tư vấn thêm.</p>
      <ul className="gui-points">
        <li><b>Khoảng 5–8 phút</b><span>Phần lớn là bấm chọn</span></li>
        <li><b>Dừng lúc nào cũng được</b><span>Tự lưu, quay lại bằng link này</span></li>
        <li><b>Gửi ảnh, video, ghi âm</b><span>Ngay trong từng câu hỏi</span></li>
      </ul>
      <button type="button" className="gui-start" onClick={() => {sessionStorage.setItem(`gui-${token}`, "1"); setPhase("form");}}>Bắt đầu</button>
      <small>Dự án: {project?.name}</small>
    </div>
  </main>;
  if (phase === "thanks") return <main className="gui-screen" style={themeVars}>
    <div className="gui-card">
      <span className="gui-eyebrow">{studio.toUpperCase()}</span>
      <h1>Cảm ơn bạn, {studio} đã nhận được rồi</h1>
      <p>Mình đã nhận {project?.answers.length || 0} câu trả lời và {files.length} tệp của bạn. Mình sẽ đọc kỹ rồi liên hệ lại qua kênh bạn đã ghi, nếu cần hỏi thêm thì mình hỏi đúng chỗ còn thiếu.</p>
      <button type="button" className="gui-ghost" onClick={() => setPhase("form")}>Bổ sung thêm thông tin hoặc tệp</button>
    </div>
  </main>;

  const finale = <section className="gui-finale" id="gui-finale">
    <span className="gui-eyebrow">GẦN XONG RỒI</span>
    <h2>Bạn còn tư liệu nào muốn gửi không?</h2>
    <p>Logo, ảnh sản phẩm, video mẫu, hoặc ghi âm vài câu bạn muốn nói thêm. Phần này không bắt buộc.</p>
    <Attach code={null} files={files} limits={limits} upload={upload} remove={remove} label="Thêm tư liệu chung" hint="Tư liệu ở đây áp dụng cho cả video. Tư liệu riêng cho từng câu thì gửi ngay trong câu đó." />
    {open.length > 0
      ? <div className="gui-todo"><b>Còn {open.length} câu cần trả lời để mình báo giá được:</b><ul>{open.slice(0, 8).map((b: Obj) => <li key={b.question_code}><button type="button" onClick={() => jump(b.question_code)}>{label(b.question_code)}</button></li>)}</ul>{open.length > 8 && <small>và {open.length - 8} câu nữa</small>}</div>
      : <p className="gui-ready">Bạn đã trả lời đủ phần cần thiết.</p>}
    {missing.length > 0 && <p className="gui-error" role="alert">Mình chưa gửi được vì còn thiếu câu, bạn bấm vào câu ở trên để điền nhé.</p>}
    <button type="button" className="gui-start" disabled={busy || open.length > 0} onClick={submit}>{busy ? "Đang gửi…" : `Gửi cho ${studio}`}</button>
    <small>Gửi rồi vẫn sửa được: bạn mở lại link này bất cứ lúc nào.</small>
  </section>;

  return <>
    {error && <div className="gui-banner" role="alert">{error}<button type="button" onClick={() => setError("")}>Đóng</button></div>}
    {project && <Intake client editable reviewer={false} project={project} setProject={p => setProject(p)} questions={questions} sections={sections} api={api} onReview={() => document.getElementById("gui-finale")?.scrollIntoView({behavior: "smooth"})} onError={setError}
      attach={code => ATTACH_HINT[code] ? <Attach code={code} files={files} limits={limits} upload={upload} remove={remove} hint={ATTACH_HINT[code]} /> : null}
      finale={finale} />}
  </>;
}
