import React from "react";
import { Audio } from "@remotion/media";
import {
  AbsoluteFill, CalculateMetadataFunction, Easing, Sequence, interpolate, staticFile, useCurrentFrame, useVideoConfig,
} from "remotion";
import { fontOf, loadFontsFor } from "./fonts";
import { Element, Grain, Rays, Rings } from "./SeoulMoon";

// Scenario-driven vertical short. Claude (scripts/content.py) picks the theme, music and scene types per topic.

type Palette = { bg: string; fg: string; accent: string; sub: string };
type Theme = {
  palettes: Palette[]; // cycled per scene
  head: string; headWeight: number;
  body: string; bodyWeight: number;
  grain: boolean; blobs: boolean; glow: boolean; whip: boolean; marker: boolean;
};

const THEMES = {
  retro: {
    palettes: [
      { bg: "#2b1d33", fg: "#f3e6cc", accent: "#c8323a", sub: "#7cc6c2" },
      { bg: "#c8323a", fg: "#f3e6cc", accent: "#2b1d33", sub: "#f3e6cc" },
      { bg: "#f3e6cc", fg: "#2b1d33", accent: "#c8323a", sub: "#2b1d33" },
      { bg: "#e8822a", fg: "#2b1d33", accent: "#f3e6cc", sub: "#2b1d33" },
    ],
    head: "Black Han Sans", headWeight: 400, body: "Gothic A1", bodyWeight: 900,
    grain: true, blobs: false, glow: false, whip: true, marker: false,
  },
  minimal: {
    palettes: [{ bg: "#f4f3ef", fg: "#141414", accent: "#ff4d2e", sub: "#6b6b6b" }],
    head: "Pretendard", headWeight: 900, body: "Pretendard", bodyWeight: 300,
    grain: false, blobs: false, glow: false, whip: false, marker: true,
  },
  night: {
    palettes: [{ bg: "#0e1430", fg: "#f1ece2", accent: "#ffd27a", sub: "#9aa3c0" }],
    head: "Nanum Myeongjo", headWeight: 800, body: "Nanum Myeongjo", bodyWeight: 400,
    grain: false, blobs: true, glow: true, whip: false, marker: false,
  },
  pastel: {
    palettes: [
      { bg: "#fde4e1", fg: "#3b3150", accent: "#ff6f9c", sub: "#8b7f9c" },
      { bg: "#e1ecfd", fg: "#2f3a55", accent: "#4f7cff", sub: "#7d88a3" },
      { bg: "#e6f6e9", fg: "#2f4a3a", accent: "#2fae6a", sub: "#7b9686" },
    ],
    head: "Jua", headWeight: 400, body: "Gowun Dodum", bodyWeight: 400,
    grain: false, blobs: true, glow: false, whip: false, marker: true,
  },
  paper: {
    palettes: [{ bg: "#efe6d6", fg: "#2a2622", accent: "#b2392a", sub: "#7d7166" }],
    head: "Gowun Batang", headWeight: 700, body: "Gowun Batang", bodyWeight: 400,
    grain: true, blobs: false, glow: false, whip: false, marker: true,
  },
  neon: {
    palettes: [
      { bg: "#08080d", fg: "#f4f4f8", accent: "#39ff88", sub: "#8d8da6" },
      { bg: "#08080d", fg: "#f4f4f8", accent: "#ff2d95", sub: "#8d8da6" },
    ],
    head: "Do Hyeon", headWeight: 400, body: "Noto Sans KR", bodyWeight: 300,
    grain: false, blobs: true, glow: true, whip: true, marker: false,
  },
} satisfies Record<string, Theme>;

export type ThemeName = keyof typeof THEMES;
export type Music = "none" | "calm" | "emotional" | "upbeat" | "energetic" | "epic" | "comedic" | "jazzy" | "chill";
export type Scene = {
  type: "title" | "text" | "typo" | "chat" | "list" | "stat" | "quote" | "outro";
  seconds: number;
  heading: string;
  body: string; // lines separated by \n
  emphasis: string; // word to highlight
  items: string[]; // list items
  messages: { side: "left" | "right"; text: string }[]; // chat
  number: string; // stat, e.g. "73%"
};
/** headFont/bodyFont: names from src/fonts.ts REGISTRY; omitted or unknown -> the theme's defaults. */
export type ShortProps = { theme: ThemeName; music: Music; scenes: Scene[]; headFont?: string; bodyFont?: string };

const secondsOf = (s: Scene) => Math.min(8, Math.max(1.5, s.seconds || 3));
export const calculateShortMetadata: CalculateMetadataFunction<ShortProps> = ({ props }) => ({
  durationInFrames: Math.round((props.scenes.reduce((a, s) => a + secondsOf(s), 0) + 0.5) * 30),
});

const clamp = { extrapolateLeft: "clamp", extrapolateRight: "clamp" } as const;
const easeOut = { ...clamp, easing: Easing.bezier(0.16, 1, 0.3, 1) };
/** 0 -> 1 entrance progress starting at `delay` frames. */
const useIn = (delay = 0, dur = 14) => interpolate(useCurrentFrame() - delay, [0, dur], [0, 1], easeOut);
/** Font size that fits the longest line in `width` px (Korean glyphs are ~1em wide). */
const fit = (text: string, max: number, min: number, width = 920) => {
  const longest = Math.max(1, ...text.split("\n").map((l) => Array.from(l).length));
  return Math.round(Math.max(min, Math.min(max, width / (longest * 0.98))));
};

type Face = { family: string; weight: number; regular: number; scale: number };
type Ctx = { t: Theme; p: Palette; index: number; head: Face; body: Face };

const Rise: React.FC<{ delay?: number; children: React.ReactNode; style?: React.CSSProperties }> = ({ delay = 0, children, style }) => {
  const k = useIn(delay);
  return <div style={{ opacity: k, translate: `0px ${(1 - k) * 40}px`, ...style }}>{children}</div>;
};

/** Text with the emphasis word highlighted (marker sweep or accent color). */
const Emph: React.FC<{ text: string; emphasis: string; c: Ctx; delay: number }> = ({ text, emphasis, c, delay }) => {
  const sweep = useIn(delay + 10, 16);
  const i = emphasis ? text.indexOf(emphasis) : -1;
  if (i < 0) return <>{text}</>;
  const word = text.slice(i, i + emphasis.length);
  const style: React.CSSProperties = c.t.marker
    ? { backgroundImage: `linear-gradient(${c.p.accent}55, ${c.p.accent}55)`, backgroundSize: `${sweep * 100}% 42%`, backgroundPosition: "0 88%", backgroundRepeat: "no-repeat" }
    : { color: c.p.accent, textShadow: c.t.glow ? `0 0 28px ${c.p.accent}aa` : undefined };
  return <>{text.slice(0, i)}<span style={style}>{word}</span>{text.slice(i + emphasis.length)}</>;
};

const headStyle = (c: Ctx, size: number): React.CSSProperties => ({
  fontFamily: c.head.family, fontWeight: c.head.weight, fontSize: Math.round(size * c.head.scale), lineHeight: 1.25, color: c.p.fg,
  textAlign: "center", wordBreak: "keep-all", whiteSpace: "pre-line", textShadow: c.t.glow ? `0 0 30px ${c.p.fg}44` : undefined,
});
const bodyStyle = (c: Ctx, size: number): React.CSSProperties => ({
  fontFamily: c.body.family, fontWeight: c.body.weight, fontSize: Math.round(size * c.body.scale), lineHeight: 1.45, color: c.p.fg,
  textAlign: "center", wordBreak: "keep-all", whiteSpace: "pre-line",
});
const Center: React.FC<{ children: React.ReactNode; gap?: number }> = ({ children, gap = 36 }) => (
  <AbsoluteFill style={{ justifyContent: "center", alignItems: "center", flexDirection: "column", gap, padding: "0 80px" }}>{children}</AbsoluteFill>
);

const TitleScene: React.FC<{ s: Scene; c: Ctx; outro?: boolean }> = ({ s, c, outro }) => {
  const bar = useIn(12, 20);
  const frame = useCurrentFrame();
  const pulse = outro ? 1 + Math.sin(frame / 8) * 0.015 : 1;
  return (
    <Center gap={40}>
      <Rise style={{ scale: pulse }}>
        <div style={headStyle(c, fit(s.heading, 150, 76))}><Emph text={s.heading} emphasis={s.emphasis} c={c} delay={0} /></div>
      </Rise>
      <div style={{ width: 260 * bar, height: 8, borderRadius: 4, background: c.p.accent }} />
      {s.body ? <Rise delay={14}><div style={{ ...bodyStyle(c, 60), color: c.p.sub }}>{s.body}</div></Rise> : null}
    </Center>
  );
};

const TextScene: React.FC<{ s: Scene; c: Ctx }> = ({ s, c }) => {
  const lines = s.body.split("\n").filter(Boolean);
  const size = fit(s.body, 100, 66);
  return (
    <Center gap={18}>
      {s.heading ? <Rise><div style={{ ...bodyStyle(c, 50), color: c.p.sub, marginBottom: 24 }}>{s.heading}</div></Rise> : null}
      {lines.map((l, i) => (
        <Rise key={i} delay={8 + i * 16}>
          <div style={{ ...headStyle(c, size), lineHeight: 1.4 }}>
            <Emph text={l} emphasis={s.emphasis} c={c} delay={8 + i * 16} />
          </div>
        </Rise>
      ))}
    </Center>
  );
};

const TypoScene: React.FC<{ s: Scene; c: Ctx }> = ({ s, c }) => {
  const lines = (s.body || s.heading).split("\n").filter(Boolean).slice(0, 4);
  let n = 0;
  return (
    <>
      {c.t.whip ? (c.index % 2 ? <Rays /> : null) : null}
      <Center gap={20}>
        {lines.map((line, li) => {
          const words = line.split(" ").filter(Boolean);
          const est = words.reduce((a, w) => a + Array.from(w).length, 0) + words.length;
          const base = Math.round(Math.max(90, Math.min(220, 920 / Math.max(1, est))));
          return (
            <div key={li} style={{ display: "flex", gap: 28, alignItems: "baseline", justifyContent: "center", flexWrap: "wrap" }}>
              {words.map((w, wi) => {
                const i = n++;
                const hot = s.emphasis && w.includes(s.emphasis);
                return (
                  <Element
                    key={wi}
                    at={4 + i * 6}
                    el={{
                      text: w, t: 0, size: hot ? Math.min(300, Math.round(base * 1.45)) : base,
                      font: hot || i % 2 === 0 ? "heavy" : "thin", color: hot ? c.p.accent : c.p.fg,
                      fx: hot ? "slam" : i % 2 ? "slide" : "pop", shadow: hot ? c.p.sub : undefined,
                    }}
                  />
                );
              })}
            </div>
          );
        })}
      </Center>
    </>
  );
};

const ChatScene: React.FC<{ s: Scene; c: Ctx }> = ({ s, c }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const msgs = s.messages.slice(0, 7);
  const per = Math.max(18, Math.min(40, (secondsOf(s) * fps - 30) / Math.max(1, msgs.length)));
  const shown = msgs.filter((_, i) => frame >= 12 + i * per);
  const typing = shown.length < msgs.length && frame >= 12 + shown.length * per - 14;
  const typingRight = msgs[shown.length]?.side === "right";
  const bubble = (right: boolean): React.CSSProperties => ({
    maxWidth: 780, padding: "26px 36px", borderRadius: 38, fontSize: Math.round(56 * c.body.scale), lineHeight: 1.4, wordBreak: "keep-all",
    fontFamily: c.body.family, fontWeight: c.body.regular,
    background: right ? c.p.accent : `color-mix(in srgb, ${c.p.fg} 10%, ${c.p.bg})`,
    color: right ? (c.t.glow ? "#08080d" : "#ffffff") : c.p.fg,
    alignSelf: right ? "flex-end" : "flex-start",
    borderBottomRightRadius: right ? 8 : 34, borderBottomLeftRadius: right ? 34 : 8,
  });
  return (
    <AbsoluteFill style={{ padding: "220px 70px 160px", flexDirection: "column", justifyContent: "flex-end", gap: 22 }}>
      {s.heading ? (
        <div style={{ position: "absolute", top: 120, left: 0, right: 0, ...bodyStyle(c, 52), color: c.p.sub }}>{s.heading}</div>
      ) : null}
      {shown.map((m, i) => (
        <Rise key={i} delay={12 + i * per} style={{ display: "flex", flexDirection: "column" }}>
          <div style={bubble(m.side === "right")}>{m.text}</div>
        </Rise>
      ))}
      {typing ? (
        <div style={{ ...bubble(typingRight), display: "flex", gap: 12 }}>
          {[0, 1, 2].map((d) => (
            <span key={d} style={{ width: 16, height: 16, borderRadius: 8, background: "currentColor", opacity: 0.35 + 0.65 * Math.abs(Math.sin((frame + d * 5) / 6)) }} />
          ))}
        </div>
      ) : null}
    </AbsoluteFill>
  );
};

const ListScene: React.FC<{ s: Scene; c: Ctx }> = ({ s, c }) => {
  const items = s.items.slice(0, 5);
  const size = fit(items.join("\n"), 72, 50, 760);
  return (
    <AbsoluteFill style={{ padding: "0 80px", justifyContent: "center", gap: 48 }}>
      <Rise><div style={{ ...headStyle(c, fit(s.heading, 110, 70)), textAlign: "left" }}><Emph text={s.heading} emphasis={s.emphasis} c={c} delay={0} /></div></Rise>
      {items.map((it, i) => (
        <Rise key={i} delay={16 + i * 14} style={{ display: "flex", gap: 30, alignItems: "center" }}>
          <div style={{
            flex: "0 0 88px", height: 88, borderRadius: 44, background: c.p.accent, display: "grid", placeItems: "center",
            fontFamily: c.head.family, fontWeight: c.head.weight, fontSize: Math.round(48 * c.head.scale), color: c.t.glow ? "#08080d" : c.p.bg,
          }}>{i + 1}</div>
          <div style={{ ...bodyStyle(c, size), textAlign: "left", fontWeight: c.body.regular }}>{it}</div>
        </Rise>
      ))}
    </AbsoluteFill>
  );
};

const StatScene: React.FC<{ s: Scene; c: Ctx }> = ({ s, c }) => {
  const k = useIn(4, 40);
  const m = s.number.match(/^(\D*)([\d.,]+)(.*)$/);
  let shown = s.number;
  if (m) {
    const target = parseFloat(m[2].replace(/,/g, ""));
    const dec = (m[2].split(".")[1] ?? "").length;
    const v = (target * k).toFixed(dec);
    shown = m[1] + (m[2].includes(",") ? Number(v).toLocaleString("en-US") : v) + m[3];
  }
  return (
    <Center gap={30}>
      {s.heading ? <Rise><div style={{ ...bodyStyle(c, 62), color: c.p.sub }}>{s.heading}</div></Rise> : null}
      <div style={{
        ...headStyle(c, fit(s.number, 280, 140, 900)), color: c.p.accent, fontVariantNumeric: "tabular-nums",
        textShadow: c.t.glow ? `0 0 40px ${c.p.accent}` : undefined, scale: interpolate(k, [0, 1], [0.8, 1]),
      }}>{shown}</div>
      {s.body ? <Rise delay={30}><div style={bodyStyle(c, fit(s.body, 72, 54))}>{s.body}</div></Rise> : null}
    </Center>
  );
};

const QuoteScene: React.FC<{ s: Scene; c: Ctx }> = ({ s, c }) => (
  <Center gap={30}>
    <div style={{ fontFamily: "Georgia, serif", fontSize: 300, lineHeight: 0.6, color: c.p.accent, opacity: useIn(0, 20) * 0.5 }}>“</div>
    <Rise delay={6}>
      <div style={{ ...headStyle(c, fit(s.body, 92, 62)), lineHeight: 1.4 }}>
        <Emph text={s.body} emphasis={s.emphasis} c={c} delay={6} />
      </div>
    </Rise>
    {s.heading ? <Rise delay={24}><div style={{ ...bodyStyle(c, 50), color: c.p.sub }}>— {s.heading}</div></Rise> : null}
  </Center>
);

const Backdrop: React.FC<{ c: Ctx }> = ({ c }) => {
  const frame = useCurrentFrame();
  return (
    <AbsoluteFill style={{ background: `radial-gradient(ellipse at 50% 40%, ${c.p.bg} 35%, color-mix(in srgb, ${c.p.bg} 70%, black) 120%)` }}>
      {c.t.blobs ? (
        <AbsoluteFill style={{ filter: "blur(120px)", opacity: c.t.glow ? 0.35 : 0.55 }}>
          {[0, 1, 2].map((i) => (
            <div key={i} style={{
              position: "absolute", width: 700, height: 700, borderRadius: "50%",
              background: i === 1 ? c.p.sub : c.p.accent, opacity: i === 1 ? 0.5 : 0.35,
              left: -200 + i * 380 + Math.sin(frame / 90 + i * 2) * 140,
              top: 200 + i * 520 + Math.cos(frame / 110 + i) * 160,
            }} />
          ))}
        </AbsoluteFill>
      ) : null}
      {c.t.whip && c.index % 3 === 1 && c.t.grain ? <Rings /> : null}
    </AbsoluteFill>
  );
};

const SceneView: React.FC<{ s: Scene; c: Ctx }> = ({ s, c }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const dur = secondsOf(s) * fps;
  const whip = c.t.whip ? interpolate(frame, [0, 6], [1, 0], easeOut) : 0;
  const out = c.t.whip ? 0 : interpolate(frame, [dur - 8, dur], [0, 1], clamp);
  const drift = interpolate(frame, [0, dur], [1.04, 1], clamp);
  const body = {
    title: <TitleScene s={s} c={c} />, outro: <TitleScene s={s} c={c} outro />, text: <TextScene s={s} c={c} />,
    typo: <TypoScene s={s} c={c} />, chat: <ChatScene s={s} c={c} />, list: <ListScene s={s} c={c} />,
    stat: <StatScene s={s} c={c} />, quote: <QuoteScene s={s} c={c} />,
  }[s.type] ?? <TextScene s={s} c={c} />;
  return (
    <AbsoluteFill>
      <Backdrop c={c} />
      <AbsoluteFill style={{
        opacity: 1 - out, scale: s.type === "chat" || s.type === "list" ? 1 : drift,
        translate: `${(c.index % 2 ? 1 : -1) * 360 * whip}px 0px`, filter: whip > 0.01 ? `blur(${whip * 28}px)` : undefined,
      }}>
        {body}
      </AbsoluteFill>
    </AbsoluteFill>
  );
};

const Progress: React.FC<{ color: string }> = ({ color }) => {
  const frame = useCurrentFrame();
  const { durationInFrames } = useVideoConfig();
  return <div style={{ position: "absolute", top: 0, left: 0, height: 10, width: `${(frame / durationInFrames) * 100}%`, background: color, opacity: 0.85 }} />;
};

const Music: React.FC<{ track: Music }> = ({ track }) => {
  const frame = useCurrentFrame();
  const { fps, durationInFrames } = useVideoConfig();
  if (track === "none") return null;
  return (
    <Audio
      src={staticFile(`music/${track}.mp3`)}
      volume={interpolate(frame, [0, 0.6 * fps, durationInFrames - 1.5 * fps, durationInFrames], [0, 0.45, 0.45, 0], clamp)}
    />
  );
};

const Fade: React.FC = () => {
  const frame = useCurrentFrame();
  const { durationInFrames } = useVideoConfig();
  return <AbsoluteFill style={{ background: "black", opacity: interpolate(frame, [0, 6, durationInFrames - 12, durationInFrames], [1, 0, 0, 1], clamp) }} />;
};

export const Short: React.FC<ShortProps> = ({ theme, music, scenes, headFont, bodyFont }) => {
  const { fps } = useVideoConfig();
  const t: Theme = THEMES[theme] ?? THEMES.minimal;
  const headName = headFont || t.head;
  const bodyName = bodyFont || t.body;
  const hf = fontOf(headName);
  const bf = fontOf(bodyName);
  const head: Face = { family: hf.family, weight: hf.heavy, regular: hf.regular, scale: hf.scale };
  const body: Face = { family: bf.family, weight: t.bodyWeight <= 300 ? bf.light : bf.regular, regular: bf.regular, scale: bf.scale };
  const text = scenes.map((s) => [s.heading, s.body, s.number, ...s.items, ...s.messages.map((m) => m.text)].join("")).join("");
  loadFontsFor(text, [headName, bodyName, ...(scenes.some((s) => s.type === "typo") ? ["Black Han Sans", "Gothic A1"] : [])]);
  let from = 0;
  return (
    <AbsoluteFill style={{ background: t.palettes[0].bg }}>
      <Music track={music} />
      {scenes.map((s, i) => {
        const start = Math.round(from * fps);
        from += secondsOf(s);
        const end = i === scenes.length - 1 ? Math.round((from + 0.5) * fps) : Math.round(from * fps);
        const c = { t, p: t.palettes[i % t.palettes.length], index: i, head, body };
        return (
          <Sequence key={i} name={`${i + 1}. ${s.type}`} from={start} durationInFrames={end - start}>
            <SceneView s={s} c={c} />
          </Sequence>
        );
      })}
      <Progress color={t.palettes[0].accent} />
      {t.grain ? <Grain /> : null}
      <Fade />
    </AbsoluteFill>
  );
};
