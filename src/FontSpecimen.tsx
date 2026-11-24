import React from "react";
import { AbsoluteFill } from "remotion";
import { FONT_NAMES, fontOf, loadFontsFor } from "./fonts";

// Still: every font the Short composition can use, to compare and to check they all load.
const SAMPLE = "오늘도 수고했어요 1,234%";

export const FontSpecimen: React.FC = () => {
  for (const name of FONT_NAMES) loadFontsFor(SAMPLE + name, [name]);
  return (
    <AbsoluteFill style={{ background: "#f4f3ef", padding: 60, display: "grid", gridTemplateColumns: "1fr 1fr", gap: "18px 40px", alignContent: "start" }}>
      {FONT_NAMES.map((name) => {
        const f = fontOf(name);
        return (
          <div key={name} style={{ borderBottom: "1px solid #d8d4cc", paddingBottom: 10 }}>
            <div style={{ fontFamily: "monospace", fontSize: 20, color: "#8a857c" }}>{name}</div>
            <div style={{ fontFamily: f.family, fontWeight: f.heavy, fontSize: Math.round(56 * f.scale), color: "#141414", lineHeight: 1.25, whiteSpace: "nowrap" }}>
              {SAMPLE}
            </div>
          </div>
        );
      })}
    </AbsoluteFill>
  );
};
