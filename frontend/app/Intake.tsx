"use client";

import {CSSProperties, ReactNode, useCallback, useEffect, useMemo, useRef, useState} from "react";

type Obj = Record<string, any>;
export type Opt = {id: string; label: string};
export type FieldDef = {id: string; type: string; label?: string; example?: string; required?: boolean; options?: Opt[]; other?: boolean; max_items?: number; exclusive?: string[]; unit?: string; min?: number; max?: number; integer?: boolean; rows?: Opt[]; cols?: Opt[]; scope_kinds?: Opt[]; objects?: Opt[]; actions?: Opt[]; max_length?: number};
export type QDef = {code: string; group: string; section: string; label: string; help_text?: string; note?: string; required: boolean; star?: boolean; allow_na?: boolean; audience?: string; fields: FieldDef[]};
export type SectionDef = {id: string; title: string; subtitle: string; part: string};
type SaveState = "saving" | "saved" | "error";
type Props = {project: Obj; setProject: (p: Obj) => void; questions: QDef[]; sections: SectionDef[]; api: (path: string, init?: RequestInit) => Promise<any>; editable: boolean; reviewer: boolean; onReview: () => void; onError: (message: string) => void; client?: boolean; attach?: (code: string) => ReactNode; finale?: ReactNode};

const STATUS: Record<string, string> = {CONFIRMED: "Đã xác nhận", ANSWERED_UNCONFIRMED: "Chờ xác nhận", PROPOSED_FROM_SOURCE: "Gợi ý từ tài liệu", NEEDS_CONSULTATION: "Cần tư vấn", CONFLICTED: "Có mâu thuẫn", UNKNOWN: "Chưa xác định", NOT_APPLICABLE: "Không áp dụng"};
const CLIENT_PART: Record<string, string> = {"Phần 0": "Phiếu câu hỏi", "Phần A": "Về video của bạn", "Phần B": "Về bạn và nhu cầu", "Phần C": "Chi tiết theo loại video", "Phần D": "Theo từng cảnh"};
const PART_NOTE: Record<string, string> = {"Phần 0": "Chọn đường đi", "Phần A": "Câu hỏi lõi", "Phần B": "Theo kiểu khách", "Phần C": "Theo loại video", "Phần D": "Theo cảnh", "Phần E": "Nội bộ"};
const SAVE_DELAY = 850;
const todayISO = () => {const d = new Date(); return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;};
const isObj = (v: any): v is Obj => !!v && typeof v === "object" && !Array.isArray(v);
const strList = (v: any): string[] => Array.isArray(v) ? v.filter((x): x is string => typeof x === "string") : [];
const norm = (t: any) => typeof t === "string" ? t.trim().toLowerCase().replace(/\s+/g, " ") : "";

function Check({on}: {on: boolean}) {
  return <svg className={`tick ${on ? "on" : ""}`} viewBox="0 0 16 16" aria-hidden="true"><path d="M3.5 8.5l3 3 6-7" /></svg>;
}

function Ring({value, size = 92}: {value: number; size?: number}) {
  const r = size / 2 - 7, len = 2 * Math.PI * r;
  return <svg className="ring" width={size} height={size} viewBox={`0 0 ${size} ${size}`} aria-hidden="true">
    <circle cx={size / 2} cy={size / 2} r={r} className="ring-track" />
    <circle cx={size / 2} cy={size / 2} r={r} className="ring-fill" style={{strokeDasharray: len, strokeDashoffset: len * (1 - Math.max(0, Math.min(1, value / 100)))}} />
  </svg>;
}

function CountUp({to}: {to: number}) {
  const [shown, setShown] = useState(to);
  const from = useRef(to);
  useEffect(() => {
    if (window.matchMedia?.("(prefers-reduced-motion: reduce)").matches) {setShown(to); from.current = to; return;}
    const start = performance.now(), a = from.current;
    let raf = 0;
    const tick = (t: number) => {const k = Math.min(1, (t - start) / 600); setShown(Math.round(a + (to - a) * (1 - Math.pow(1 - k, 3)))); if (k < 1) raf = requestAnimationFrame(tick); else from.current = to;};
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [to]);
  return <>{shown}</>;
}

function Chips({options, selected, multi, onToggle, disabled, name, exclusive = [], max}: {options: Opt[]; selected: string[]; multi: boolean; onToggle: (id: string) => void; disabled: boolean; name: string; exclusive?: string[]; max?: number}) {
  const full = !!max && selected.filter(s => !exclusive.includes(s)).length >= max;
  return <div className="chips" role={multi ? "group" : "radiogroup"} aria-label={name}>
    {options.map(o => {
      const on = selected.includes(o.id);
      return <button type="button" key={o.id} role={multi ? "checkbox" : "radio"} aria-checked={on} className={`chip ${on ? "on" : ""} ${exclusive.includes(o.id) ? "exclusive" : ""}`} disabled={disabled || (!on && full && !exclusive.includes(o.id))} onClick={() => onToggle(o.id)}>
        <span className="chip-box"><Check on={on} /></span>{o.label}
      </button>;
    })}
  </div>;
}

function Reveal({open, children}: {open: boolean; children: ReactNode}) {
  return <div className={`reveal ${open ? "open" : ""}`} aria-hidden={!open}><div>{children}</div></div>;
}

function toggleIn(list: string[], id: string, exclusive: string[]) {
  if (list.includes(id)) return list.filter(x => x !== id);
  if (exclusive.includes(id)) return [id];
  return [...list.filter(x => !exclusive.includes(x)), id];
}

function FieldInput({field, value, onChange, disabled, code}: {field: FieldDef; value: Obj; onChange: (v: Obj) => void; disabled: boolean; code: string}) {
  const raw = value[field.id];
  const otherKey = field.id + "__other";
  const set = (v: any, extra: Obj = {}) => onChange({...value, [field.id]: v, ...extra});
  const id = `${code}-${field.id}`;
  const label = field.label ? <label className="field-label" htmlFor={id}>{field.label}{field.required === false && <span className="optional"> · không bắt buộc</span>}</label> : null;
  const placeholder = field.example ? `Ví dụ: ${field.example}` : "";
  switch (field.type) {
    case "text":
      return <div className="field">{label}<input id={id} disabled={disabled} value={typeof raw === "string" ? raw : ""} maxLength={field.max_length} placeholder={placeholder} onChange={e => set(e.target.value)} /></div>;
    case "textarea":
      return <div className="field">{label}<textarea id={id} rows={3} disabled={disabled} value={typeof raw === "string" ? raw : ""} maxLength={field.max_length} placeholder={placeholder} onChange={e => set(e.target.value)} /></div>;
    case "number":
      return <div className="field">{label}<div className="number-input"><input id={id} type="number" inputMode="numeric" disabled={disabled} min={field.min} max={field.max} step={field.integer ? 1 : "any"} value={typeof raw === "number" ? raw : ""} onChange={e => set(e.target.value === "" ? null : Number(e.target.value))} />{field.unit && <span>{field.unit}</span>}</div></div>;
    case "date": {
      const past = typeof raw === "string" && raw && raw < todayISO();
      return <div className="field">{label}<input id={id} type="date" disabled={disabled} min={todayISO()} value={typeof raw === "string" ? raw : ""} onChange={e => set(e.target.value || null)} />{past && <small className="field-warn">Ngày này đã qua.</small>}</div>;
    }
    case "single": {
      const opts = [...(field.options || []), ...(field.other ? [{id: "OTHER", label: "Khác"}] : [])];
      return <div className="field">{field.label && <span className="field-label">{field.label}</span>}
        <Chips name={field.label || code} options={opts} selected={typeof raw === "string" ? [raw] : []} multi={false} disabled={disabled} onToggle={idv => set(raw === idv ? null : idv)} />
        {field.other && <input className="other-input" aria-label="Ý khác của bạn" disabled={disabled} value={typeof value[otherKey] === "string" ? value[otherKey] : ""} placeholder="Ý khác của bạn (nếu có), gõ vào đây" onChange={e => onChange({...value, [otherKey]: e.target.value, ...(e.target.value.trim() && raw !== "OTHER" ? {[field.id]: "OTHER"} : {})})} />}
      </div>;
    }
    case "multi": {
      const list = strList(raw);
      const opts = [...(field.options || []), ...(field.other ? [{id: "OTHER", label: "Khác"}] : [])];
      return <div className="field">{field.label && <span className="field-label">{field.label}{field.max_items && <span className="optional"> · tối đa {field.max_items}</span>}</span>}
        <Chips name={field.label || code} options={opts} selected={list} multi disabled={disabled} exclusive={field.exclusive} max={field.max_items} onToggle={idv => set(toggleIn(list, idv, field.exclusive || []))} />
        {field.other && <input className="other-input" aria-label="Ý khác của bạn" disabled={disabled} value={typeof value[otherKey] === "string" ? value[otherKey] : ""} placeholder="Ý khác của bạn (nếu có), gõ vào đây" onChange={e => onChange({...value, [otherKey]: e.target.value, ...(e.target.value.trim() && !list.includes("OTHER") ? {[field.id]: [...list, "OTHER"]} : {})})} />}
      </div>;
    }
    case "matrix_single":
    case "matrix_multi": {
      const grid: Obj = isObj(raw) ? raw : {};
      const multi = field.type === "matrix_multi";
      const cols = field.cols || [];
      return <div className="field matrix-wrap"><table className="matrix">
        <thead><tr><th scope="col"><span className="sr-only">Mục</span></th>{cols.map(c => <th scope="col" key={c.id}>{c.label}</th>)}</tr></thead>
        <tbody>{(field.rows || []).map(r => {
          const cell = grid[r.id];
          return <tr key={r.id}><th scope="row">{r.label}</th>{cols.map(c => {
            const on = multi ? strList(cell).includes(c.id) : cell === c.id;
            const next = multi ? toggleIn(strList(cell), c.id, field.exclusive || []) : (on ? undefined : c.id);
            return <td key={c.id}><button type="button" className={`cell ${multi ? "square" : "dot"} ${on ? "on" : ""}`} role={multi ? "checkbox" : "radio"} aria-checked={on} aria-label={`${r.label}: ${c.label}`} disabled={disabled} onClick={() => {const g = {...grid}; if (next === undefined || (Array.isArray(next) && !next.length)) delete g[r.id]; else g[r.id] = next; set(g);}}><Check on={on} /></button></td>;
          })}</tr>;
        })}</tbody>
      </table></div>;
    }
    case "scene_table":
      return <SceneTable field={field} rows={Array.isArray(raw) ? raw : []} disabled={disabled} onChange={rows => set(rows)} />;
    default:
      return null;
  }
}

function SceneTable({field, rows, onChange, disabled}: {field: FieldDef; rows: any[]; onChange: (rows: any[]) => void; disabled: boolean}) {
  const conflicts = useMemo(() => {
    const out = new Set<number>(), seen = new Map<string, number[]>();
    rows.forEach((r, i) => {
      if (!isObj(r)) return;
      const scope = r.scope === "TIME" ? `T${r.a}-${r.b}` : r.scope === "ALL" ? "ALL" : `${r.scope}${r.a}`;
      const key = `${scope}|${r.object}|${norm(r.detail)}`;
      for (const j of seen.get(key) || []) {
        const pair = new Set([rows[j].action, r.action]);
        const clash = (pair.has("ON") && pair.has("OFF")) || (pair.has("KEEP") && pair.has("CHANGE")) || (r.action === "CHANGE" && rows[j].action === "CHANGE" && norm(r.value) !== norm(rows[j].value));
        if (clash && norm(r.detail)) {out.add(i); out.add(j);}
      }
      seen.set(key, [...(seen.get(key) || []), i]);
    });
    return out;
  }, [rows]);
  const update = (i: number, patch: Obj) => onChange(rows.map((r, n) => n === i ? {...(isObj(r) ? r : {}), ...patch} : r));
  const blank = {scope: "SCENE", a: null, b: null, object: "", detail: "", action: "", value: "", note: ""};
  return <div className="scene-table">
    <div className="scene-head" aria-hidden="true"><span>Cảnh / thời gian</span><span>Đối tượng</span><span>Chi tiết</span><span>Yêu cầu</span><span>Giá trị / ghi chú</span><span /></div>
    {rows.map((row, i) => {
      const r: Obj = isObj(row) ? row : {};
      return <div className={`scene-row ${conflicts.has(i) ? "conflict" : ""}`} key={i} style={{"--i": i} as CSSProperties}>
        <div className="scene-scope">
          <select aria-label={`Dòng ${i + 1}: cảnh hoặc thời gian`} disabled={disabled} value={r.scope || ""} onChange={e => update(i, {scope: e.target.value, a: null, b: null})}>{(field.scope_kinds || []).map(k => <option key={k.id} value={k.id}>{k.label}</option>)}</select>
          {(r.scope === "SCENE" || r.scope === "FROM") && <input aria-label="Số cảnh" type="number" min={1} disabled={disabled} value={typeof r.a === "number" ? r.a : ""} placeholder="Số" onChange={e => update(i, {a: e.target.value === "" ? null : Number(e.target.value)})} />}
          {r.scope === "TIME" && <span className="time-pair"><input aria-label="Từ giây" type="number" min={0} disabled={disabled} value={typeof r.a === "number" ? r.a : ""} placeholder="từ" onChange={e => update(i, {a: e.target.value === "" ? null : Number(e.target.value)})} /><input aria-label="Đến giây" type="number" min={0} disabled={disabled} value={typeof r.b === "number" ? r.b : ""} placeholder="đến" onChange={e => update(i, {b: e.target.value === "" ? null : Number(e.target.value)})} /></span>}
        </div>
        <select aria-label={`Dòng ${i + 1}: đối tượng`} disabled={disabled} value={r.object || ""} onChange={e => update(i, {object: e.target.value})}><option value="">Chọn…</option>{(field.objects || []).map(o => <option key={o.id} value={o.id}>{o.label}</option>)}</select>
        <input aria-label={`Dòng ${i + 1}: chi tiết`} disabled={disabled} value={r.detail || ""} placeholder="Ví dụ: tiếng mưa" onChange={e => update(i, {detail: e.target.value})} />
        <select aria-label={`Dòng ${i + 1}: yêu cầu`} className={`action-${r.action || "none"}`} disabled={disabled} value={r.action || ""} onChange={e => update(i, {action: e.target.value})}><option value="">Chọn…</option>{(field.actions || []).map(o => <option key={o.id} value={o.id}>{o.label}</option>)}</select>
        <div className="scene-extra">
          {r.action === "CHANGE" && <input aria-label={`Dòng ${i + 1}: giá trị mong muốn`} disabled={disabled} value={r.value || ""} placeholder="Đổi thành…" onChange={e => update(i, {value: e.target.value})} />}
          <input aria-label={`Dòng ${i + 1}: ghi chú`} disabled={disabled} value={r.note || ""} placeholder="Ghi chú" onChange={e => update(i, {note: e.target.value})} />
        </div>
        <button type="button" className="row-remove" aria-label={`Xóa dòng ${i + 1}`} disabled={disabled} onClick={() => onChange(rows.filter((_, n) => n !== i))}>×</button>
        {conflicts.has(i) && <p className="row-alert">Mâu thuẫn với một dòng khác cùng cảnh và cùng chi tiết.</p>}
      </div>;
    })}
    {!rows.length && <p className="scene-empty">Chưa có dòng nào. Mỗi dòng là một đối tượng và một yêu cầu, ví dụ “Cảnh 4 · Âm thanh · Tiếng mưa · Bật”.</p>}
    <button type="button" className="add-row" disabled={disabled} onClick={() => onChange([...rows, {...blank}])}><span>+</span>Thêm dòng</button>
  </div>;
}

function QuestionCard({q, index, answer, draft, dirty, saveState, required, issues, notes, editable, reviewer, client, attach, onChange, onStatus, onConfirm}: {client?: boolean; attach?: ReactNode; q: QDef; index: number; answer?: Obj; draft: any; dirty: boolean; saveState?: SaveState; required: boolean; issues: string[]; notes: string[]; editable: boolean; reviewer: boolean; onChange: (v: any) => void; onStatus: (status: string, value: any) => void; onConfirm: () => void}) {
  const value: Obj = isObj(draft) ? draft : {};
  const na = value._na === true;
  const consult = answer?.status === "NEEDS_CONSULTATION";
  const status = dirty ? "EDITING" : answer?.status || "UNANSWERED";
  const confirmed = status === "CONFIRMED";
  const canConfirm = reviewer && !dirty && answer && ["ANSWERED_UNCONFIRMED", "PROPOSED_FROM_SOURCE"].includes(answer.status) && !issues.length;
  return <article className={`q-card ${confirmed ? "confirmed" : ""} ${issues.length && !dirty ? "has-issue" : ""} ${q.audience === "internal" ? "internal" : ""}`} style={{"--i": index} as CSSProperties} data-question-code={q.code}>
    <header className="q-head">
      {!client && <span className="q-code">{q.code}</span>}
      <div className="q-title"><h3>{q.label}{required && <span className="req" title={client ? "Câu này giúp mình báo giá chính xác" : "Bắt buộc"}> ★</span>}</h3>{q.help_text && <p className="q-help">{q.help_text}</p>}</div>
      {!client && <span className={`q-status s-${status}`}>{confirmed && <Check on />}{status === "EDITING" ? "Đang sửa" : STATUS[status] || "Chưa trả lời"}</span>}
    </header>
    <div className={`q-body ${na || consult ? "muted-body" : ""}`}>
      {na ? <p className="na-note">Đã đánh dấu “Không áp dụng”.</p> : q.fields.map(f => <FieldInput key={f.id} code={q.code} field={f} value={value} disabled={!editable} onChange={onChange} />)}
      {q.note && <p className="q-note">{q.note}</p>}
      {attach}
    </div>
    {(issues.length > 0 || notes.length > 0) && !dirty && <ul className="q-issues">{issues.map((m, i) => <li key={"b" + i} className="block">{m}</li>)}{notes.map((m, i) => <li key={"n" + i} className="note">{m}</li>)}</ul>}
    <footer className="q-foot">
      <div className="q-quick">
        {editable && <button type="button" className={`ghost-chip ${consult ? "on" : ""}`} aria-pressed={consult} onClick={() => onStatus(consult ? "ANSWERED_UNCONFIRMED" : "NEEDS_CONSULTATION", draft ?? null)}>Chưa biết – cần tư vấn</button>}
        {editable && q.allow_na && <button type="button" className={`ghost-chip ${na ? "on" : ""}`} aria-pressed={na} onClick={() => onChange(na ? {} : {_na: true})}>Không áp dụng</button>}
      </div>
      <span className={`save-state ${saveState || ""}`} aria-live="polite">{saveState === "saving" ? "Đang lưu…" : saveState === "saved" ? "Đã lưu" : saveState === "error" ? "Chưa lưu được" : ""}</span>
      {canConfirm && <button type="button" className="confirm-btn" onClick={onConfirm}><Check on />Xác nhận</button>}
    </footer>
  </article>;
}

export default function Intake({project, setProject, questions, sections, api, editable, reviewer, onReview, onError, client, attach, finale}: Props) {
  const validation: Obj = project.validation || {};
  const answers = useMemo(() => {
    const map: Record<string, Obj> = {};
    for (const a of project.answers || []) if (!a.scope_id) map[a.question_code] = a;
    return map;
  }, [project.answers]);
  const [drafts, setDrafts] = useState<Record<string, any>>(() => Object.fromEntries(Object.entries(answers).map(([c, a]) => [c, a.value])));
  const [saveState, setSaveState] = useState<Record<string, SaveState>>({});
  const [dirty, setDirty] = useState<Record<string, number>>({});
  const dirtyRef = useRef<Record<string, number>>({});
  const timers = useRef<Record<string, ReturnType<typeof setTimeout>>>({});
  const pending = useRef<Record<string, () => void>>({});
  const projectRef = useRef(project);
  const queue = useRef<Promise<void>>(Promise.resolve());
  const [active, setActive] = useState("P");
  const [toasts, setToasts] = useState<{id: number; text: string}[]>([]);
  const [fresh, setFresh] = useState<string[]>([]);
  const prevGroups = useRef<string[] | null>(null);
  const [laterOpen, setLaterOpen] = useState<Record<string, boolean>>({});
  const [brand, setBrand] = useState<Obj | null>(null);

  useEffect(() => {projectRef.current = project;}, [project]);
  useEffect(() => {api("/brand").then(setBrand).catch(() => undefined);}, [api]);
  useEffect(() => {
    setDrafts(prev => {
      const next = {...prev};
      for (const [code, a] of Object.entries(answers)) if (!dirtyRef.current[code]) next[code] = a.value;
      return next;
    });
  }, [answers]);
  useEffect(() => {
    const groups: string[] = validation.active_groups || [];
    if (prevGroups.current) {
      const added = groups.filter(g => !prevGroups.current!.includes(g) && /^[BC]/.test(g));
      if (added.length) {
        setFresh(f => [...f, ...added]);
        setToasts(t => [...t, ...added.map((g, i) => ({id: Date.now() + i, text: `Đã mở nhánh ${g} · ${sections.find(s => s.id === g)?.title || ""}`}))]);
        setTimeout(() => setFresh(f => f.filter(g => !added.includes(g))), 6000);
      }
    }
    prevGroups.current = groups;
  }, [validation.active_groups, sections]);
  useEffect(() => {
    if (!toasts.length) return;
    const timer = setTimeout(() => setToasts(t => t.slice(1)), 4200);
    return () => clearTimeout(timer);
  }, [toasts]);
  useEffect(() => () => {
    // Rời màn hình khi còn thay đổi chưa lưu: lưu ngay thay vì bỏ.
    Object.values(timers.current).forEach(clearTimeout);
    Object.values(pending.current).forEach(fn => fn());
  }, []);

  const persist = useCallback((code: string, body: Obj, version: number) => {
    setSaveState(s => ({...s, [code]: "saving"}));
    queue.current = queue.current.then(async () => {
      const p = projectRef.current;
      try {
        const data = await api(`/projects/${p.id}/answers/${encodeURIComponent(code)}`, {method: "PUT", body: JSON.stringify({expected_revision: p.revision, scope_id: "", ...body})});
        projectRef.current = data;
        if (dirtyRef.current[code] === version) {delete dirtyRef.current[code]; setDirty({...dirtyRef.current});}
        setProject(data);
        setSaveState(s => ({...s, [code]: "saved"}));
      } catch (e) {
        setSaveState(s => ({...s, [code]: "error"}));
        onError(e instanceof Error ? e.message : "Không lưu được câu trả lời.");
        try {const latest = await api(`/projects/${p.id}`); projectRef.current = latest; setProject(latest);} catch { /* giữ bản nháp */ }
      }
    });
    return queue.current;
  }, [api, onError, setProject]);

  const change = (code: string, value: any, status = "ANSWERED_UNCONFIRMED", delay = SAVE_DELAY) => {
    const version = (dirtyRef.current[code] || 0) + 1;
    dirtyRef.current[code] = version;
    setDirty({...dirtyRef.current});
    setDrafts(d => ({...d, [code]: value}));
    clearTimeout(timers.current[code]);
    const run = () => {delete pending.current[code]; persist(code, {value, status, raw_text: null}, version);};
    pending.current[code] = run;
    timers.current[code] = setTimeout(run, delay);
  };
  const confirm = async (codes: string[]) => {
    if (!codes.length) return;
    await queue.current;
    const p = projectRef.current;
    try {
      const data = await api(`/projects/${p.id}/confirm`, {method: "POST", body: JSON.stringify({expected_revision: p.revision, question_codes: codes, scope_id: ""})});
      projectRef.current = data; setProject(data);
    } catch (e) {onError(e instanceof Error ? e.message : "Không xác nhận được.");}
  };

  const secStats: Record<string, Obj> = useMemo(() => Object.fromEntries((validation.sections || []).map((s: Obj) => [s.id, s])), [validation.sections]);
  const visible = sections.filter(s => secStats[s.id]?.applicable);
  const visibleKey = visible.map(s => s.id).join(",");
  // Mục lục tự sáng theo chương đang ở giữa màn hình.
  useEffect(() => {
    const blocks = Array.from(document.querySelectorAll<HTMLElement>(".chapter-block"));
    if (!blocks.length || typeof IntersectionObserver === "undefined") return;
    const io = new IntersectionObserver(entries => {
      const hit = entries.filter(e => e.isIntersecting).sort((a, b) => b.intersectionRatio - a.intersectionRatio)[0];
      if (hit) setActive(hit.target.getAttribute("data-section") || "P");
    }, {rootMargin: "-45% 0px -50% 0px", threshold: [0, 0.01]});
    blocks.forEach(b => io.observe(b));
    return () => io.disconnect();
  }, [visibleKey]);
  useEffect(() => {
    if (client || matchMedia('(prefers-reduced-motion: reduce)').matches) return;
    const stages = document.querySelectorAll<HTMLElement>('.app-shell .intake .chapter-stage');
    const observer = new IntersectionObserver(entries => {
      for (const entry of entries) if (entry.isIntersecting) {
        (entry.target as HTMLElement).dataset.artArrival = 'true';
        observer.unobserve(entry.target);
      }
    }, {threshold: .08});
    stages.forEach(stage => observer.observe(stage));
    return () => observer.disconnect();
  }, [visibleKey, client]);
  const current = visible.find(s => s.id === active) || visible[0];
  const required = new Set<string>(validation.required_codes || []);
  const blockers: Obj[] = validation.blockers || [];
  const notesAll: Obj[] = validation.clarifications || [];
  const reqTotal = required.size;
  const reqAnswered = [...required].filter(c => answers[c] && answers[c].value != null).length;
  const reqConfirmed = [...required].filter(c => answers[c]?.status === "CONFIRMED").length;
  const parts = visible.reduce<Record<string, SectionDef[]>>((acc, s) => {(acc[s.part] = acc[s.part] || []).push(s); return acc;}, {});
  const go = (id: string) => {setActive(id); document.getElementById(`ch-${id}`)?.scrollIntoView({behavior: "smooth", block: "start"});};
  const issuesFor = (code: string) => blockers.filter(b => b.question_code === code && !["ANSWER_REQUIRED", "NEEDS_CONFIRMATION", "NEEDS_CONSULTATION"].includes(b.code)).map(b => b.message);
  const notesFor = (code: string) => notesAll.filter(b => b.question_code === code).map(b => b.message);
  const confirmableIn = (list: QDef[]) => list.filter(q => answers[q.code] && ["ANSWERED_UNCONFIRMED", "PROPOSED_FROM_SOURCE"].includes(answers[q.code].status) && !dirty[q.code] && !issuesFor(q.code).length).map(q => q.code);
  const colors: Obj = brand?.colors || {};
  const themeVars = Object.fromEntries(Object.entries(colors).map(([k, v]) => [`--b-${k.replace(/_/g, "-")}`, v])) as CSSProperties;
  const card = (q: QDef, i: number) => <QuestionCard key={q.code} q={q} index={i} answer={answers[q.code]} draft={drafts[q.code]} dirty={!!dirty[q.code]} saveState={saveState[q.code]} required={required.has(q.code)} issues={issuesFor(q.code)} notes={notesFor(q.code)} editable={editable} reviewer={reviewer} client={client} attach={attach ? attach(q.code) : undefined}
    onChange={v => change(q.code, v)} onStatus={(status, v) => change(q.code, v, status, 0)} onConfirm={() => confirm([q.code])} />;

  return <div className="intake" style={themeVars} id="intake-top">
    <section className="intake-hero">
      <div className="scene" aria-hidden="true"><span className="orb o1" /><span className="orb o2" /><span className="orb o3" /><span className="grain" /></div>
      <div className="hero-copy">
        {client ? <>
          <span className="eyebrow">{(brand?.studio_name || "Studio").toUpperCase()}</span>
          <h1>Kể cho mình nghe video bạn cần</h1>
          <p>Dự án: {project.name}. Bạn có thể dừng bất cứ lúc nào, câu trả lời được lưu tự động và bạn quay lại bằng đúng đường link này.</p>
        </> : <>
          <span className="eyebrow">{(brand?.tagline || "Phiếu tiếp nhận yêu cầu video").toUpperCase()}{brand?.studio_name ? ` · ${brand.studio_name}` : ""}</span>
          <h1>{project.name}</h1>
          <div className="branch-chips">{(validation.active_groups || []).filter((g: string) => /^[BC]/.test(g)).map((g: string) => <button type="button" key={g} className={`branch ${fresh.includes(g) ? "fresh" : ""}`} onClick={() => go(g)}>{g} · {sections.find(s => s.id === g)?.title}</button>)}</div>
        </>}
      </div>
      {client ? <div className="hero-stats">
        <div className="ring-box"><Ring value={reqTotal ? Math.round(reqAnswered / reqTotal * 100) : 0} /><strong><CountUp to={reqTotal ? Math.round(reqAnswered / reqTotal * 100) : 0} />%</strong><span>đã trả lời</span></div>
        <dl><div><dt>Câu cần trả lời</dt><dd><CountUp to={reqAnswered} /><small>/{reqTotal}</small></dd></div>
        <div><dt>Còn lại</dt><dd><CountUp to={Math.max(reqTotal - reqAnswered, 0)} /><small> câu</small></dd></div></dl>
      </div> : <div className="hero-stats">
        <div className="ring-box"><Ring value={validation.completion || 0} /><strong><CountUp to={validation.completion || 0} />%</strong><span>đã xác nhận</span></div>
        <dl>
          <div><dt>Câu bắt buộc đã trả lời</dt><dd><CountUp to={reqAnswered} /><small>/{reqTotal}</small></dd></div>
          <div><dt>Đã xác nhận</dt><dd><CountUp to={reqConfirmed} /><small>/{reqTotal}</small></dd></div>
          <div><dt>Việc còn mở</dt><dd className={blockers.length ? "hot" : ""}><CountUp to={blockers.length} /></dd></div>
        </dl>
      </div>}
    </section>

    <div className="intake-body">
      <nav className="rail" aria-label="Các phần của phiếu">
        {Object.entries(parts).map(([part, list]) => <div className="rail-part" key={part}>
          <span className="rail-part-name">{client ? (CLIENT_PART[part] || part) : part}{!client && <small>{PART_NOTE[part]}</small>}</span>
          {list.map(s => {
            const no = String(visible.findIndex(v => v.id === s.id) + 1).padStart(2, "0");
            const st = secStats[s.id] || {};
            const ratio = st.total ? st.answered / st.total : 0;
            const done = st.required ? st.confirmed >= st.required && !st.issues : st.answered === st.total && st.total > 0;
            return <button type="button" key={s.id} className={`rail-item ${s.id === current?.id ? "active" : ""} ${fresh.includes(s.id) ? "fresh" : ""} ${done ? "done" : ""}`} aria-current={s.id === current?.id ? "step" : undefined} onClick={() => go(s.id)}>
              <span className={`rail-dot ${st.issues ? "issue" : ""}`}>{done ? <Check on /> : <em>{no}</em>}</span>
              <span className="rail-text"><b>{s.title}</b><span className="rail-bar"><i style={{transform: `scaleX(${ratio})`}} /></span></span>
              {fresh.includes(s.id) && <span className="new-badge">Mới</span>}
            </button>;
          })}
        </div>)}
      </nav>

      <div className="chapters">
        {visible.map((sec, idx) => {
          const qs = questions.filter(q => q.section === sec.id);
          const mainQs = qs.filter(q => required.has(q.code) || q.group !== "A");
          const laterQs = qs.filter(q => !required.has(q.code) && q.group === "A");
          const confirmable = confirmableIn(qs);
          const st = secStats[sec.id] || {};
          return <section className={`chapter-block part-${sec.part.slice(-1)}`} id={`ch-${sec.id}`} data-section={sec.id} key={sec.id} aria-labelledby={`title-${sec.id}`}>
            <div className="chapter-stage">
              <div className="scene" aria-hidden="true"><span className="orb o1" /><span className="orb o2" /><span className="orb o3" /><span className="grain" /></div>
              <span className="chapter-no" aria-hidden="true">{String(idx + 1).padStart(2, "0")}</span>
              <div className="chapter-copy">
                <span className="eyebrow">{client ? `Phần ${idx + 1} / ${visible.length}` : `${sec.part}${/^[BC]/.test(sec.id) ? ` · ${sec.id}` : ""} · Chương ${idx + 1}/${visible.length}`}</span>
                <h2 id={`title-${sec.id}`}>{sec.title}</h2>
                <p>{sec.subtitle}</p>
                <div className="chapter-meta">
                  <span>{st.answered || 0}/{st.total || 0} câu đã trả lời</span>
                  {!client && sec.id === "E" && <span className="internal-tag">Nội bộ – khách không thấy</span>}
                  {fresh.includes(sec.id) && <span className="new-badge">Vừa mở</span>}
                </div>
              </div>
              <span className="scroll-cue" aria-hidden="true">Cuộn xuống để trả lời</span>
            </div>
            <div className="chapter-content">
              {reviewer && confirmable.length > 1 && <div className="chapter-tools"><button type="button" className="confirm-btn outline" onClick={() => confirm(confirmable)}><Check on />Xác nhận cả phần ({confirmable.length})</button></div>}
              <div className="cards">{mainQs.map(card)}</div>
              {laterQs.length > 0 && <div className="later">
                <button type="button" className="later-toggle" aria-expanded={laterOpen[sec.id] !== false} onClick={() => setLaterOpen(o => ({...o, [sec.id]: o[sec.id] === false}))}><span>{laterOpen[sec.id] !== false ? "−" : "+"}</span>Có thể bổ sung sau · {laterQs.length} câu</button>
                <Reveal open={laterOpen[sec.id] !== false}><div className="cards">{laterQs.map(card)}</div></Reveal>
              </div>}
            </div>
          </section>;
        })}
        {client ? (finale || null) : <div className="finale">
          <span className="eyebrow">Hết phiếu</span>
          <h2>Kiểm tra và gửi duyệt</h2>
          <p>{blockers.length ? `Còn ${blockers.length} việc cần xử lý trước khi gửi.` : "Không còn việc chặn. Có thể gửi duyệt."}</p>
          <button type="button" className="nav-btn primary" onClick={onReview}>Kiểm tra & gửi →</button>
        </div>}
      </div>
    </div>

    <div className="toasts" aria-live="polite">{toasts.map(t => <div className="toast" key={t.id}><span className="toast-dot" />{t.text}</div>)}</div>
  </div>;
}
