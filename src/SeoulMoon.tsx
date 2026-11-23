import React from "react";
import { Audio } from "@remotion/media";
import {
  AbsoluteFill,
  Easing,
  Sequence,
  interpolate,
  spring,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import { HEAVY, THIN } from "./fonts";

// Retro circus palette (ref: 산이 'Rap Circus' typo motion).
const PLUM = "#2b1d33";
const RED = "#c8323a";
const CREAM = "#f3e6cc";
const ORANGE = "#e8822a";
const TEAL = "#7cc6c2";

// Measured tempo of the clip: ~122 BPM, first beat at 0.45s.
const BEAT = 0.49;
const BEAT0 = 0.45;

type Fx = "slam" | "slide" | "pop" | "rise" | "type";
type El = {
  text: string;
  t: number; // seconds into the clip (Whisper word stamps)
  x: number;
  y: number;
  size: number;
  font: "heavy" | "thin" | "bold";
  color: string;
  fx: Fx;
  step?: number; // frames between letters for "type"
  outline?: boolean;
  shadow?: string;
  box?: boolean;
};
type Range = [number, number];
type Shot = {
  from: number;
  to: number;
  bg: string;
  cam: { s?: Range; x?: Range; y?: Range; r?: Range };
  deco?: "rings" | "rays" | "ghost";
  ghost?: string;
  els: El[];
};

const SHOTS: Shot[] = [
  {
    from: 0, to: 2.3, bg: PLUM, deco: "rays", cam: { s: [1, 1.08] },
    els: [{ text: "서울의", t: 0.3, x: 960, y: 540, size: 380, font: "heavy", color: CREAM, fx: "slam", shadow: RED }],
  },
  {
    from: 2.3, to: 6.6, bg: CREAM, deco: "rings", cam: { s: [1.5, 1], r: [-10, 0] },
    els: [{ text: "달", t: 2.5, x: 960, y: 550, size: 360, font: "heavy", color: CREAM, fx: "slam", shadow: RED }],
  },
  {
    from: 6.6, to: 7.8, bg: RED, cam: { s: [1, 1.12] },
    els: [
      { text: "오늘", t: 6.78, x: 720, y: 540, size: 420, font: "heavy", color: CREAM, fx: "slam", shadow: PLUM },
      { text: "밤", t: 7.06, x: 1400, y: 560, size: 420, font: "thin", color: CREAM, fx: "slide" },
    ],
  },
  {
    from: 7.8, to: 12.1, bg: PLUM, deco: "ghost", ghost: "바라본", cam: { s: [1.15, 0.95], r: [3, -2] },
    els: [
      { text: "바라본", t: 7.84, x: 960, y: 290, size: 250, font: "heavy", color: CREAM, fx: "type", step: 4 },
      { text: "바라본", t: 9.3, x: 960, y: 545, size: 250, font: "thin", color: CREAM, fx: "slide" },
      { text: "바라본", t: 10.7, x: 960, y: 800, size: 250, font: "heavy", color: RED, fx: "slam", shadow: TEAL },
    ],
  },
  {
    from: 12.1, to: 13.5, bg: CREAM, deco: "rings", cam: { s: [1.7, 1], r: [-12, 0] },
    els: [
      { text: "저", t: 12.26, x: 960, y: 330, size: 130, font: "thin", color: CREAM, fx: "pop" },
      { text: "달이", t: 12.8, x: 960, y: 600, size: 290, font: "heavy", color: CREAM, fx: "slam", shadow: RED },
    ],
  },
  {
    from: 13.5, to: 18.3, bg: PLUM, deco: "ghost", ghost: "처량해", cam: { s: [1, 1.35], r: [0, 4] },
    els: [
      { text: "너무", t: 13.58, x: 960, y: 260, size: 200, font: "thin", color: CREAM, fx: "slide" },
      { text: "처량해", t: 14.3, x: 960, y: 610, size: 400, font: "heavy", color: RED, fx: "type", step: 10, shadow: CREAM },
    ],
  },
  {
    from: 18.3, to: 20.3, bg: ORANGE, cam: { x: [60, -60], s: [1.05, 1.1] },
    els: [
      { text: "너도", t: 18.42, x: 640, y: 540, size: 360, font: "heavy", color: RED, fx: "slam", shadow: PLUM },
      { text: "나처럼", t: 18.8, x: 1360, y: 560, size: 280, font: "thin", color: PLUM, fx: "type", step: 5 },
    ],
  },
  {
    // Lonely: one small word swallowed by empty space.
    from: 20.3, to: 22.9, bg: PLUM, cam: { s: [1.3, 0.7] },
    els: [{ text: "외로운", t: 20.36, x: 960, y: 540, size: 110, font: "bold", color: CREAM, fx: "rise" }],
  },
  {
    from: 22.9, to: 24.9, bg: RED, cam: { s: [1.2, 1], r: [-4, 2] },
    els: [
      { text: "텅", t: 22.98, x: 540, y: 500, size: 700, font: "heavy", color: CREAM, fx: "slam", outline: true },
      { text: "빈", t: 23.3, x: 1380, y: 580, size: 700, font: "heavy", color: CREAM, fx: "slam", outline: true },
      { text: "가슴", t: 23.64, x: 960, y: 540, size: 230, font: "heavy", color: CREAM, fx: "pop", shadow: PLUM },
      { text: "안고", t: 24.3, x: 960, y: 800, size: 160, font: "thin", color: CREAM, fx: "slide" },
    ],
  },
  {
    from: 24.9, to: 28.5, bg: PLUM, deco: "ghost", ghost: "사는구나", cam: { x: [260, -260], s: [1.1, 1.15] },
    els: [{ text: "사는구나", t: 24.98, x: 960, y: 540, size: 380, font: "heavy", color: CREAM, fx: "type", step: 8, shadow: RED }],
  },
  {
    from: 28.5, to: 30.2, bg: CREAM, cam: { s: [1.15, 1] },
    els: [
      { text: "슬픈", t: 28.74, x: 960, y: 270, size: 200, font: "thin", color: PLUM, fx: "slide" },
      { text: "“", t: 29.42, x: 470, y: 520, size: 300, font: "heavy", color: RED, fx: "pop" },
      { text: "추억", t: 29.42, x: 960, y: 650, size: 460, font: "heavy", color: RED, fx: "slam", shadow: TEAL },
      { text: "”", t: 29.6, x: 1450, y: 520, size: 300, font: "heavy", color: RED, fx: "pop" },
    ],
  },
  {
    from: 30.2, to: 34.6, bg: ORANGE, deco: "rays", cam: { s: [1, 1.25], r: [0, -3] },
    els: [
      { text: "안고", t: 30.22, x: 960, y: 330, size: 200, font: "thin", color: PLUM, fx: "slide" },
      { text: "사는구나", t: 30.88, x: 960, y: 640, size: 260, font: "heavy", color: CREAM, fx: "type", step: 6, shadow: RED, box: true },
    ],
  },
  {
    from: 34.6, to: 35.55, bg: RED, cam: { s: [1.12, 1] },
    els: [
      { text: "텅", t: 34.76, x: 680, y: 540, size: 520, font: "heavy", color: CREAM, fx: "slam", shadow: PLUM },
      { text: "빈", t: 35.2, x: 1260, y: 540, size: 520, font: "heavy", color: CREAM, fx: "slam", shadow: PLUM },
    ],
  },
  {
    from: 35.55, to: 39.8, bg: PLUM, deco: "ghost", ghost: "텅 빈 가슴", cam: { s: [1, 1.4], r: [0, 3] },
    els: [
      { text: "가슴", t: 35.6, x: 960, y: 470, size: 500, font: "heavy", color: CREAM, fx: "slam", shadow: RED },
      { text: "안고", t: 36.18, x: 960, y: 830, size: 220, font: "thin", color: TEAL, fx: "slide" },
    ],
  },
  {
    from: 39.8, to: 50, bg: CREAM, deco: "rings", cam: { s: [1.8, 1], r: [-15, 0] },
    els: [
      { text: "서울의", t: 40.2, x: 960, y: 420, size: 120, font: "thin", color: CREAM, fx: "slide" },
      { text: "달", t: 40.6, x: 960, y: 610, size: 300, font: "heavy", color: CREAM, fx: "slam", shadow: RED },
    ],
  },
];

const clamp = { extrapolateLeft: "clamp", extrapolateRight: "clamp" } as const;
const out = (e: (t: number) => number = Easing.cubic) => ({ ...clamp, easing: Easing.out(e) });

const Element: React.FC<{ el: El; at: number }> = ({ el, at }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const f = frame - at;
  if (f < 0) return null;

  const off = Math.round(el.size * 0.035);
  const text: React.CSSProperties = {
    fontFamily: el.font === "heavy" ? HEAVY : THIN,
    fontWeight: el.font === "thin" ? 100 : el.font === "bold" ? 900 : 400,
    fontSize: el.size,
    lineHeight: 1,
    whiteSpace: "nowrap",
    color: el.outline ? "transparent" : el.color,
    WebkitTextStroke: el.outline ? `${Math.round(el.size / 120)}px ${el.color}` : undefined,
    textShadow: el.shadow ? `${off}px ${off}px 0 ${el.shadow}` : undefined,
    display: "inline-block",
  };

  let inner: React.ReactNode;
  if (el.fx === "type") {
    inner = (
      <span style={text}>
        {Array.from(el.text).map((ch, i) => {
          const lf = f - i * (el.step ?? 5);
          return (
            <span
              key={i}
              style={{
                display: "inline-block",
                opacity: lf < 0 ? 0 : 1,
                scale: interpolate(lf, [0, 4], [1.8, 1], out()),
              }}
            >
              {ch}
            </span>
          );
        })}
      </span>
    );
  } else {
    const s: React.CSSProperties = { ...text };
    if (el.fx === "slam") {
      s.scale = interpolate(f, [0, 5], [2.4, 1], out());
      s.opacity = interpolate(f, [0, 2], [0, 1], clamp);
    } else if (el.fx === "slide") {
      s.translate = `${interpolate(f, [0, 7], [-260, 0], out())}px 0px`;
      s.filter = `blur(${interpolate(f, [0, 7], [18, 0], clamp)}px)`;
      s.opacity = interpolate(f, [0, 3], [0, 1], clamp);
    } else if (el.fx === "pop") {
      s.scale = spring({ frame: f, fps, config: { damping: 10, stiffness: 180 } });
    } else if (el.fx === "rise") {
      s.translate = `0px ${interpolate(f, [0, 9], [130, 0], out())}px`;
    }
    inner = <span style={s}>{el.text}</span>;
  }

  return (
    <div
      style={{
        position: "absolute",
        left: el.x,
        top: el.y,
        translate: "-50% -50%",
        overflow: el.fx === "rise" ? "hidden" : undefined,
        padding: el.box ? "24px 56px" : undefined,
      }}
    >
      {el.box ? (
        <div
          style={{
            position: "absolute",
            inset: 0,
            border: `8px solid ${el.color}`,
            scale: `${interpolate(f, [0, 8], [0, 1], out())} 1`,
          }}
        />
      ) : null}
      {inner}
    </div>
  );
};

const Rings: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const rings: [number, string, boolean][] = [
    [2600, TEAL, false],
    [2100, RED, false],
    [1700, CREAM, false],
    [1480, RED, false],
    [1160, CREAM, true],
    [940, RED, false],
    [740, PLUM, true],
  ];
  return (
    <AbsoluteFill>
      {rings.map(([d, c, dashed], i) => (
        <div
          key={i}
          style={{
            position: "absolute",
            left: 960 - d / 2,
            top: 540 - d / 2,
            width: d,
            height: d,
            borderRadius: "50%",
            background: c,
            outline: dashed ? `3px dashed ${CREAM}` : undefined,
            outlineOffset: -18,
            scale: spring({ frame: frame - i * 2, fps, config: { damping: 14 } }),
            rotate: `${frame * (i % 2 ? 0.4 : -0.4)}deg`,
          }}
        />
      ))}
    </AbsoluteFill>
  );
};

const Rays: React.FC = () => {
  const frame = useCurrentFrame();
  return (
    <AbsoluteFill style={{ rotate: `${frame * 0.15}deg`, opacity: 0.35 }}>
      <svg width="1920" height="1080" viewBox="-960 -540 1920 1080" style={{ overflow: "visible" }}>
        {new Array(36).fill(0).map((_, i) => {
          const a = (i / 36) * Math.PI * 2;
          return <line key={i} x1={0} y1={0} x2={Math.cos(a) * 2000} y2={Math.sin(a) * 2000} stroke={RED} strokeWidth={2} />;
        })}
      </svg>
    </AbsoluteFill>
  );
};

const Ghost: React.FC<{ text: string }> = ({ text }) => {
  const frame = useCurrentFrame();
  return (
    <AbsoluteFill style={{ justifyContent: "center", gap: 0, opacity: 0.07 }}>
      {[0, 1, 2, 3, 4, 5, 6, 7, 8, 9].map((r) => (
        <div
          key={r}
          style={{
            fontFamily: THIN,
            fontWeight: 100,
            fontSize: 250,
            lineHeight: 1.05,
            color: CREAM,
            whiteSpace: "nowrap",
            translate: `${(r % 2 ? -1 : 1) * frame * 3 - 400}px 0px`,
          }}
        >
          {`${text} `.repeat(6)}
        </div>
      ))}
    </AbsoluteFill>
  );
};

const ShotView: React.FC<{ shot: Shot; index: number }> = ({ shot, index }) => {
  const frame = useCurrentFrame();
  const { fps, width, height } = useVideoConfig();
  // Layouts are authored on a 1920x1080 board; vertical (Shorts) shrinks it and lets edges crop.
  const fit = height > width ? 0.75 : 1;
  const dur = (shot.to - shot.from) * fps;
  const ease = { ...clamp, easing: Easing.bezier(0.2, 0.8, 0.2, 1) };
  const cam = (r: Range | undefined, d: number) => (r ? interpolate(frame, [0, dur], r, ease) : d);
  // Camera kick on every beat, decaying within the beat.
  const tAbs = shot.from + frame / fps;
  const phase = (((tAbs - BEAT0) % BEAT) + BEAT) % BEAT / BEAT;
  const kick = 1 + 0.03 * Math.exp(-phase * 6);
  // Whip-pan in from alternating sides.
  const dir = index % 2 ? 1 : -1;
  const whip = interpolate(frame, [0, 5], [1, 0], out());

  return (
    <AbsoluteFill
      style={{ background: `radial-gradient(ellipse at 50% 45%, ${shot.bg} 30%, color-mix(in srgb, ${shot.bg} 55%, black) 110%)` }}
    >
      <div
        style={{
          position: "absolute",
          width: 1920,
          height: 1080,
          left: (width - 1920) / 2,
          top: (height - 1080) / 2,
          scale: cam(shot.cam.s, 1) * kick * fit,
          translate: `${cam(shot.cam.x, 0) + dir * 420 * whip}px ${cam(shot.cam.y, 0)}px`,
          rotate: `${cam(shot.cam.r, 0)}deg`,
          filter: whip > 0.01 ? `blur(${whip * 30}px)` : undefined,
        }}
      >
        {shot.deco === "rings" ? <Rings /> : null}
        {shot.deco === "rays" ? <Rays /> : null}
        {shot.deco === "ghost" ? <Ghost text={shot.ghost ?? ""} /> : null}
        {shot.els.map((el, i) => (
          <Element key={i} el={el} at={(el.t - shot.from) * fps} />
        ))}
      </div>
    </AbsoluteFill>
  );
};

const Grain: React.FC = () => {
  const frame = useCurrentFrame();
  return (
    <AbsoluteFill style={{ mixBlendMode: "overlay", opacity: 0.3 }}>
      <svg width="100%" height="100%">
        <filter id="g">
          <feTurbulence type="fractalNoise" baseFrequency="0.8" numOctaves="2" seed={frame % 12} />
        </filter>
        <rect width="100%" height="100%" filter="url(#g)" />
      </svg>
    </AbsoluteFill>
  );
};

const Fades: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps, durationInFrames } = useVideoConfig();
  return (
    <AbsoluteFill
      style={{
        background: "black",
        opacity: interpolate(frame, [0, 0.3 * fps, durationInFrames - 1.5 * fps, durationInFrames], [1, 0, 0, 1], clamp),
      }}
    />
  );
};

const Music: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps, durationInFrames } = useVideoConfig();
  return (
    <Audio
      src={staticFile("seoul-moon.mp3")}
      volume={interpolate(frame, [0, 0.3 * fps, durationInFrames - 2 * fps, durationInFrames], [0, 1, 1, 0], clamp)}
    />
  );
};

export const SeoulMoon: React.FC = () => {
  const { fps } = useVideoConfig();
  return (
    <AbsoluteFill style={{ background: PLUM }}>
      <Music />
      {SHOTS.map((shot, i) => (
        <Sequence
          key={shot.from}
          name={shot.els.map((e) => e.text).join(" ")}
          from={Math.round(shot.from * fps)}
          durationInFrames={Math.round(shot.to * fps) - Math.round(shot.from * fps)}
        >
          <ShotView shot={shot} index={i} />
        </Sequence>
      ))}
      <Grain />
      <Fades />
    </AbsoluteFill>
  );
};
