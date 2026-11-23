import * as BlackHan from "@remotion/google-fonts/BlackHanSans";
import * as GothicA1 from "@remotion/google-fonts/GothicA1";

// Every glyph on screen. Update when lyrics change, or missing glyphs fall back to a system font.
const KO = "서울의달오늘밤바라본저달이너무처량해너도나처럼외로운텅빈가슴안고사는구나슬픈추억“”";

// Korean Google Fonts are split into ~100 unicode slices; load only those our text needs.
const subsetsFor = (info: { unicodeRanges: Record<string, string> }) =>
  Object.entries(info.unicodeRanges)
    .filter(([, ranges]) =>
      Array.from(KO).some((ch) => {
        const c = ch.codePointAt(0)!;
        return ranges.split(",").some((r) => {
          const [a, b] = r.trim().slice(2).split("-");
          return c >= parseInt(a, 16) && c <= parseInt(b ?? a, 16);
        });
      }),
    )
    .map(([name]) => name) as never;

export const HEAVY = BlackHan.loadFont("normal", {
  weights: ["400"],
  subsets: subsetsFor(BlackHan.getInfo()),
}).fontFamily;

export const THIN = GothicA1.loadFont("normal", {
  weights: ["100", "900"],
  subsets: subsetsFor(GothicA1.getInfo()),
}).fontFamily;
