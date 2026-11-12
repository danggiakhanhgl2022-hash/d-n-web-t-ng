"use client";

import {useRef, useState} from "react";

type Obj = Record<string, any>;
export type Uploader = (file: File | Blob, name: string, code: string | null, onProgress: (ratio: number) => void) => Promise<void>;
type Limits = {image: number; audio: number; video: number};

const ACCEPT = ".png,.jpg,.jpeg,.webp,.gif,.mp3,.wav,.m4a,.ogg,.aac,.mp4,.mov,.webm,.m4v,.pdf,.docx,.txt";
const KIND: Record<string, "image" | "audio" | "video"> = {png: "image", jpg: "image", jpeg: "image", webp: "image", gif: "image", mp3: "audio", wav: "audio", m4a: "audio", ogg: "audio", aac: "audio", mp4: "video", mov: "video", webm: "video", m4v: "video"};
const KIND_NAME = {image: "Ảnh", audio: "Ghi âm", video: "Video"};

export function sizeText(n: number) {
  if (n < 1024 * 1024) return `${Math.max(1, Math.round(n / 1024))} KB`;
  return `${(n / 1024 / 1024).toFixed(n > 100 * 1024 * 1024 ? 0 : 1)} MB`;
}
function mb(n: number) {return `${Math.round(n / 1024 / 1024)} MB`;}

/** Kiểm tra trước khi gửi để khách biết ngay, không phải chờ tải xong mới báo lỗi. */
function precheck(file: File, limits: Limits): string | null {
  const ext = file.name.split(".").pop()?.toLowerCase() || "";
  const kind = KIND[ext];
  if (kind && file.size > limits[kind]) return `${KIND_NAME[kind]} “${file.name}” nặng ${sizeText(file.size)}, tối đa ${mb(limits[kind])}. Anh chị có thể dán link Google Drive vào câu trả lời thay vì tải lên.`;
  if (!kind && !["pdf", "docx", "txt", "md"].includes(ext)) return `Chúng tôi chưa nhận loại tệp “.${ext}”. Hãy gửi ảnh, ghi âm, video hoặc PDF.`;
  if (!kind && file.size > 10 * 1024 * 1024) return `Tệp “${file.name}” nặng ${sizeText(file.size)}, tài liệu tối đa 10 MB.`;
  return null;
}

type Item = {key: string; name: string; ratio: number; error?: string};

export default function Attach({code, files, limits, upload, remove, label, hint}: {code: string | null; files: Obj[]; limits: Limits; upload: Uploader; remove: (id: string) => Promise<void>; label?: string; hint?: string}) {
  const input = useRef<HTMLInputElement>(null);
  const [items, setItems] = useState<Item[]>([]);
  const [drag, setDrag] = useState(false);
  const [rec, setRec] = useState<{recorder: MediaRecorder; started: number} | null>(null);
  const [seconds, setSeconds] = useState(0);
  const timer = useRef<ReturnType<typeof setInterval> | null>(null);
  const mine = files.filter(f => (f.question_code || null) === code);
  const canRecord = typeof window !== "undefined" && !!navigator.mediaDevices?.getUserMedia && typeof MediaRecorder !== "undefined";

  const send = async (file: File | Blob, name: string) => {
    const key = `${Date.now()}-${Math.random()}`;
    if (file instanceof File) {
      const problem = precheck(file, limits);
      if (problem) {setItems(list => [...list, {key, name, ratio: 0, error: problem}]); return;}
    }
    setItems(list => [...list, {key, name, ratio: 0}]);
    try {
      await upload(file, name, code, ratio => setItems(list => list.map(i => i.key === key ? {...i, ratio} : i)));
      setItems(list => list.filter(i => i.key !== key));
    } catch (e) {
      setItems(list => list.map(i => i.key === key ? {...i, error: e instanceof Error ? e.message : "Chưa gửi được, thử lại nhé."} : i));
    }
  };
  const pick = (list: FileList | null) => {if (list) Array.from(list).forEach(f => send(f, f.name));};

  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({audio: true});
      const recorder = new MediaRecorder(stream);
      const chunks: Blob[] = [];
      recorder.ondataavailable = e => {if (e.data.size) chunks.push(e.data);};
      recorder.onstop = () => {
        stream.getTracks().forEach(t => t.stop());
        const type = recorder.mimeType || "audio/webm";
        const ext = type.includes("mp4") ? "m4a" : type.includes("ogg") ? "ogg" : "webm";
        const stamp = new Date().toLocaleTimeString("vi-VN", {hour: "2-digit", minute: "2-digit"}).replace(":", "h");
        send(new Blob(chunks, {type}), `ghi-am-${stamp}.${ext}`);
      };
      recorder.start();
      setRec({recorder, started: Date.now()}); setSeconds(0);
      timer.current = setInterval(() => setSeconds(s => {
        if (s + 1 >= 180) stopRecording(recorder);
        return s + 1;
      }), 1000);
    } catch {
      setItems(list => [...list, {key: `${Date.now()}`, name: "Ghi âm", ratio: 0, error: "Trình duyệt chưa được cho phép dùng micro. Anh chị bấm vào biểu tượng khóa cạnh thanh địa chỉ để bật, hoặc chọn tệp ghi âm có sẵn."}]);
    }
  };
  const stopRecording = (recorder?: MediaRecorder) => {
    if (timer.current) clearInterval(timer.current);
    const r = recorder || rec?.recorder;
    if (r && r.state !== "inactive") r.stop();
    setRec(null);
  };

  return <div className={`attach ${drag ? "drag" : ""}`} onDragOver={e => {e.preventDefault(); setDrag(true);}} onDragLeave={() => setDrag(false)} onDrop={e => {e.preventDefault(); setDrag(false); pick(e.dataTransfer.files);}}>
    <div className="attach-bar">
      <button type="button" className="attach-btn" onClick={() => input.current?.click()}><span aria-hidden="true">＋</span>{label || "Chọn ảnh, video từ máy"}</button>
      {canRecord && (rec
        ? <button type="button" className="attach-btn rec on" onClick={() => stopRecording()}><span className="rec-dot" aria-hidden="true" />Đang ghi {Math.floor(seconds / 60)}:{String(seconds % 60).padStart(2, "0")} · bấm để dừng</button>
        : <button type="button" className="attach-btn rec" onClick={startRecording}><span className="rec-dot" aria-hidden="true" />Ghi âm</button>)}
      <input ref={input} type="file" multiple accept={ACCEPT} hidden onChange={e => {pick(e.target.files); e.target.value = "";}} aria-label="Chọn tệp đính kèm" />
    </div>
    <p className="attach-hint">{hint || "Hoặc kéo thả tệp vào khung này. Ảnh tối đa 25 MB, ghi âm 60 MB, video 200 MB."}</p>
    {(mine.length > 0 || items.length > 0) && <ul className="attach-list">
      {mine.map(f => <li key={f.id}><span className="attach-name">{f.filename}</span><small>{sizeText(f.size)}</small><button type="button" className="attach-x" aria-label={`Bỏ tệp ${f.filename}`} onClick={() => remove(f.id).catch(() => undefined)}>Bỏ</button></li>)}
      {items.map(i => <li key={i.key} className={i.error ? "bad" : ""}>
        <span className="attach-name">{i.name}</span>
        {i.error ? <><small>{i.error}</small><button type="button" className="attach-x" onClick={() => setItems(list => list.filter(x => x.key !== i.key))}>Đóng</button></>
          : <span className="attach-bar-wrap" role="progressbar" aria-valuenow={Math.round(i.ratio * 100)}><i style={{transform: `scaleX(${i.ratio})`}} /></span>}
      </li>)}
    </ul>}
  </div>;
}
