// SPDX-License-Identifier: MIT
// The chatter model in the browser: the same tokenizer, guard and rebuild as slopdam.chatter in
// Python, run on the int8 ONNX export of slopdam/chatter-tagger with onnxruntime-web.
// hf/model/js_parity.py checks this file against the Python version.
// Positions are code point indexes, as in Python, so emoji and other astral characters count once.

export const KEEP = 0, DELETE = 1, UPPER = 2;
export const MAX_PIECES = 256;

const W = "[\\p{L}\\p{N}_]"; // Python's \w
const LINE_START = /[ \t]*(?:[-*+•][ \t]+|#{1,6}[ \t]+|\p{Nd}+[.)][ \t]+)?/uy;
const UNSAFE = new RegExp(`[0-9/\\\\_=@]|\\.${W}|${W}\\.${W}`, "u");
const CJK_PUNCT = "、，！？：。";
const OPENER_END = /(?:[,:!?.…、，！？。]|[가-힣]*[면로히도피대럼과만데])$/u;
const LOG_LABEL_I = new RegExp(
  "^(?:panic|fatal|error|err|warn|warning|info|debug|trace|note|hint|caution|caused by|exception|traceback" +
  "|경고|오류|에러|참고|주의|치명적 오류|알림|警告|エラー|注意|情報|致命的エラー|错误|提示|信息|严重|致命错误)" +
  `(?![\\p{L}\\p{N}_-])`, "iu");
const LOG_LABEL = new RegExp(`^${W}*(?:Error|Exception|Warning)(?![\\p{L}\\p{N}_-])`, "u");
const CJK = "가-힣\\u3040-\\u30ff\\u3400-\\u4dbf\\u4e00-\\u9fff";
const MIXED = new RegExp(`[A-Za-z][\\s\\S]*[${CJK}]|[${CJK}][\\s\\S]*[A-Za-z]`, "u");

// --- tokenizer: BERT normalizer and pre-tokenizer, then WordPiece (distilbert-base-multilingual-cased) ---

const isChinese = (c) =>
  (c >= 0x4e00 && c <= 0x9fff) || (c >= 0x3400 && c <= 0x4dbf) || (c >= 0x20000 && c <= 0x2a6df) ||
  (c >= 0x2a700 && c <= 0x2b73f) || (c >= 0x2b740 && c <= 0x2b81f) || (c >= 0x2b820 && c <= 0x2ceaf) ||
  (c >= 0xf900 && c <= 0xfaff) || (c >= 0x2f800 && c <= 0x2fa1f);
const isSpace = (ch) => ch === " " || ch === "\t" || ch === "\n" || ch === "\r" || /\p{Z}/u.test(ch);
const isControl = (ch) => ch !== "\t" && ch !== "\n" && ch !== "\r" && /\p{C}/u.test(ch);
const isPunct = (ch, c) => (c >= 33 && c <= 47) || (c >= 58 && c <= 64) || (c >= 91 && c <= 96) || (c >= 123 && c <= 126) || /\p{P}/u.test(ch);

/** Pieces of `chars` (an array of code points as strings): [{start, end, id}], start and end in code points. */
export function tokenize(vocab, chars) {
  // A word is the code point indexes it keeps. Control and format characters (U+200B, U+FEFF) are
  // dropped without ending the word, so a piece's span can enclose one, as in Hugging Face tokenizers.
  const words = [];
  let cur = null;
  const flush = () => { if (cur) { words.push(cur); cur = null; } };
  chars.forEach((ch, i) => {
    const c = ch.codePointAt(0);
    if (c === 0 || c === 0xfffd || isControl(ch)) return;
    if (isSpace(ch)) return flush();
    if (isChinese(c) || isPunct(ch, c)) { flush(); words.push([i]); return; }
    if (!cur) cur = [i]; else cur.push(i);
  });
  flush();
  const unk = vocab.get("[UNK]");
  const out = [];
  for (const w of words) {
    const word = w.map((i) => chars[i]);
    if (word.length > 100) { out.push({ start: w[0], end: w[w.length - 1] + 1, id: unk }); continue; }
    const pieces = [];
    let s = 0, bad = false;
    while (s < word.length) {
      let e = word.length, id;
      for (; e > s; e--) {
        id = vocab.get((s > 0 ? "##" : "") + word.slice(s, e).join(""));
        if (id !== undefined) break;
      }
      if (e === s) { bad = true; break; }
      pieces.push({ start: w[s], end: w[e - 1] + 1, id });
      s = e;
    }
    if (bad) out.push({ start: w[0], end: w[w.length - 1] + 1, id: unk }); else out.push(...pieces);
  }
  return out.slice(0, MAX_PIECES);
}

// --- the guard, as in slopdam/chatter.py ---

export function wholeWords(chars, offsets, labels) {
  const out = [];
  let first = KEEP;
  offsets.forEach(([s], i) => {
    if (i === 0 || s !== offsets[i - 1][1] || (s > 0 && CJK_PUNCT.includes(chars[s - 1]))) { first = labels[i]; out.push(labels[i]); }
    else out.push(first === DELETE ? DELETE : KEEP);
  });
  return out;
}

export function guard(chars, offsets, labels) {
  const text = (a, b) => chars.slice(a, b).join("");
  const out = labels.slice();
  const lines = [];
  let pos = 0;
  for (let i = 0; i <= chars.length; i++) {
    if (i === chars.length || chars[i] === "\n") { lines.push([pos, i]); pos = i + 1; }
  }
  for (const [a, b] of lines) {
    const idx = offsets.map(([s], i) => (a <= s && s < b ? i : -1)).filter((i) => i >= 0);
    if (!idx.length || idx.every((i) => labels[i] === KEEP)) continue;
    LINE_START.lastIndex = 0;
    const start = a + [...LINE_START.exec(text(a, b))[0]].length;
    const run = idx.filter((i) => labels[i] === DELETE);
    const kept = idx.find((i) => labels[i] !== DELETE && offsets[i][0] >= start);
    const firstKept = kept === undefined ? null : kept;
    const span = run.length ? text(offsets[run[0]][0], offsets[run[run.length - 1]][1]) : "";
    let ok = !run.length || (
      offsets[run[0]][0] === start &&
      run.every((v, k) => v === run[0] + k) &&
      firstKept !== null && firstKept === run[run.length - 1] + 1 &&
      !UNSAFE.test(span) && OPENER_END.test(span) && !MIXED.test(span) &&
      !LOG_LABEL_I.test(span) && !LOG_LABEL.test(span));
    ok = ok && idx.filter((i) => labels[i] === UPPER).every((i) => i === firstKept && run.length > 0);
    if (!ok) for (const i of idx) out[i] = KEEP;
  }
  return out;
}

export function rebuild(chars, offsets, labels) {
  const out = [];
  let pos = 0, deleted = false;
  offsets.forEach(([s, e], i) => {
    const gap = chars.slice(pos, s).join("");
    out.push(!deleted || pos === 0 ? gap : "\n".repeat((gap.match(/\n/g) || []).length));
    if (labels[i] !== DELETE) {
      const piece = chars.slice(s, e);
      out.push(labels[i] === UPPER ? piece[0].toUpperCase() + piece.slice(1).join("") : piece.join(""));
    }
    deleted = labels[i] === DELETE;
    pos = e;
  });
  if (!deleted) out.push(chars.slice(pos).join(""));
  return out.join("");
}

/** Labels to final text: whole words, then the guard, then rebuild. */
export function apply(text, offsets, labels) {
  const chars = [...text];
  return rebuild(chars, offsets, guard(chars, offsets, wholeWords(chars, offsets, labels)));
}

// --- running the model ---

export async function loadVocab(url) {
  const tok = await (await fetch(url)).json();
  return new Map(Object.entries(tok.model.vocab));
}

/** Strip the opener of one line of slopdam output; `ort` is the onnxruntime-web module. */
export async function stripOpener(ort, session, vocab, text) {
  const pieces = tokenize(vocab, [...text]);
  if (!pieces.length) return text;
  const n = pieces.length;
  const ids = new ort.Tensor("int64", BigInt64Array.from(pieces, (p) => BigInt(p.id)), [1, n]);
  const mask = new ort.Tensor("int64", new BigInt64Array(n).fill(1n), [1, n]);
  const { logits } = await session.run({ input_ids: ids, attention_mask: mask });
  const labels = [];
  for (let i = 0; i < n; i++) {
    const row = logits.data.slice(i * 3, i * 3 + 3);
    labels.push(row.indexOf(Math.max(...row)));
  }
  return apply(text, pieces.map((p) => [p.start, p.end]), labels);
}
