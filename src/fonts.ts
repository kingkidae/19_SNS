import { loadFont as loadLocalFont } from "@remotion/fonts";
import * as AstaSans from "@remotion/google-fonts/AstaSans";
import * as BagelFatOne from "@remotion/google-fonts/BagelFatOne";
import * as BlackAndWhitePicture from "@remotion/google-fonts/BlackAndWhitePicture";
import * as BlackHanSans from "@remotion/google-fonts/BlackHanSans";
import * as CuteFont from "@remotion/google-fonts/CuteFont";
import * as Diphylleia from "@remotion/google-fonts/Diphylleia";
import * as DoHyeon from "@remotion/google-fonts/DoHyeon";
import * as Dokdo from "@remotion/google-fonts/Dokdo";
import * as Dongle from "@remotion/google-fonts/Dongle";
import * as EastSeaDokdo from "@remotion/google-fonts/EastSeaDokdo";
import * as Gaegu from "@remotion/google-fonts/Gaegu";
import * as GamjaFlower from "@remotion/google-fonts/GamjaFlower";
import * as GasoekOne from "@remotion/google-fonts/GasoekOne";
import * as GothicA1 from "@remotion/google-fonts/GothicA1";
import * as GowunBatang from "@remotion/google-fonts/GowunBatang";
import * as GowunDodum from "@remotion/google-fonts/GowunDodum";
import * as Gugi from "@remotion/google-fonts/Gugi";
import * as Hahmlet from "@remotion/google-fonts/Hahmlet";
import * as HiMelody from "@remotion/google-fonts/HiMelody";
import * as IBMPlexSansKR from "@remotion/google-fonts/IBMPlexSansKR";
import * as Jua from "@remotion/google-fonts/Jua";
import * as KirangHaerang from "@remotion/google-fonts/KirangHaerang";
import * as MoiraiOne from "@remotion/google-fonts/MoiraiOne";
import * as NanumBrushScript from "@remotion/google-fonts/NanumBrushScript";
import * as NanumGothic from "@remotion/google-fonts/NanumGothic";
import * as NanumMyeongjo from "@remotion/google-fonts/NanumMyeongjo";
import * as NanumPenScript from "@remotion/google-fonts/NanumPenScript";
import * as NotoSansKR from "@remotion/google-fonts/NotoSansKR";
import * as NotoSerifKR from "@remotion/google-fonts/NotoSerifKR";
import * as Orbit from "@remotion/google-fonts/Orbit";
import * as PoorStory from "@remotion/google-fonts/PoorStory";
import * as SingleDay from "@remotion/google-fonts/SingleDay";
import * as SongMyung from "@remotion/google-fonts/SongMyung";
import * as Stylish from "@remotion/google-fonts/Stylish";
import * as Sunflower from "@remotion/google-fonts/Sunflower";
import * as YeonSung from "@remotion/google-fonts/YeonSung";
import { staticFile } from "remotion";

type GoogleModule = {
  fontFamily: string;
  getInfo: () => { unicodeRanges: Record<string, string> };
  loadFont: (style: "normal", opts: { weights: string[]; subsets: never }) => unknown;
};
type Entry = { mod?: GoogleModule; weights: number[]; scale?: number };

/**
 * Every font the Short composition may use. Keys are what scenarios name (keep in sync with
 * FONTS in scripts/content.py). `scale` corrects fonts that look small at the same px (handwriting).
 * All Google Fonts are SIL OFL; Pretendard (public/fonts) is SIL OFL too.
 */
const g = (m: unknown) => m as GoogleModule;
const REGISTRY: Record<string, Entry> = {
  // Sans
  Pretendard: { weights: [300, 400, 600, 800, 900] },
  "Noto Sans KR": { mod: g(NotoSansKR), weights: [300, 500, 900] },
  "IBM Plex Sans KR": { mod: g(IBMPlexSansKR), weights: [300, 500, 700] },
  "Gothic A1": { mod: g(GothicA1), weights: [100, 400, 900] },
  "Asta Sans": { mod: g(AstaSans), weights: [300, 500, 800] },
  "Nanum Gothic": { mod: g(NanumGothic), weights: [400, 800] },
  // Display
  "Black Han Sans": { mod: g(BlackHanSans), weights: [400] },
  "Do Hyeon": { mod: g(DoHyeon), weights: [400] },
  "Bagel Fat One": { mod: g(BagelFatOne), weights: [400] },
  "Gasoek One": { mod: g(GasoekOne), weights: [400] },
  Dongle: { mod: g(Dongle), weights: [300, 700], scale: 1.6 },
  Orbit: { mod: g(Orbit), weights: [400] },
  "Black And White Picture": { mod: g(BlackAndWhitePicture), weights: [400], scale: 1.15 },
  Gugi: { mod: g(Gugi), weights: [400] },
  "Moirai One": { mod: g(MoiraiOne), weights: [400] },
  // Serif
  "Noto Serif KR": { mod: g(NotoSerifKR), weights: [300, 500, 900] },
  "Nanum Myeongjo": { mod: g(NanumMyeongjo), weights: [400, 800] },
  "Gowun Batang": { mod: g(GowunBatang), weights: [400, 700] },
  Hahmlet: { mod: g(Hahmlet), weights: [300, 500, 800] },
  "Song Myung": { mod: g(SongMyung), weights: [400] },
  Diphylleia: { mod: g(Diphylleia), weights: [400] },
  // Rounded / cute
  Jua: { mod: g(Jua), weights: [400] },
  "Gowun Dodum": { mod: g(GowunDodum), weights: [400] },
  Sunflower: { mod: g(Sunflower), weights: [300, 700] },
  "Cute Font": { mod: g(CuteFont), weights: [400], scale: 1.35 },
  "Poor Story": { mod: g(PoorStory), weights: [400], scale: 1.1 },
  // Handwriting / brush
  "Nanum Pen Script": { mod: g(NanumPenScript), weights: [400], scale: 1.4 },
  Gaegu: { mod: g(Gaegu), weights: [300, 700], scale: 1.15 },
  "Hi Melody": { mod: g(HiMelody), weights: [400], scale: 1.3 },
  "Gamja Flower": { mod: g(GamjaFlower), weights: [400], scale: 1.15 },
  "Single Day": { mod: g(SingleDay), weights: [400], scale: 1.1 },
  "Yeon Sung": { mod: g(YeonSung), weights: [400], scale: 1.1 },
  "Kirang Haerang": { mod: g(KirangHaerang), weights: [400], scale: 1.2 },
  Stylish: { mod: g(Stylish), weights: [400], scale: 1.1 },
  "East Sea Dokdo": { mod: g(EastSeaDokdo), weights: [400], scale: 1.45 },
  Dokdo: { mod: g(Dokdo), weights: [400], scale: 1.2 },
  "Nanum Brush Script": { mod: g(NanumBrushScript), weights: [400], scale: 1.4 },
};
export const FONT_NAMES = Object.keys(REGISTRY);

const PRETENDARD_FILES: Record<number, string> = {
  300: "Light", 400: "Regular", 600: "SemiBold", 800: "ExtraBold", 900: "Black",
};

// Korean Google Fonts are split into ~100 unicode slices; load only those the given text needs.
const subsetsFor = (info: { unicodeRanges: Record<string, string> }, text: string) =>
  Object.entries(info.unicodeRanges)
    .filter(
      ([name, ranges]) =>
        name === "latin" ||
        Array.from(text).some((ch) => {
          const c = ch.codePointAt(0)!;
          return ranges.split(",").some((r) => {
            const [a, b] = r.trim().slice(2).split("-");
            return c >= parseInt(a, 16) && c <= parseInt(b ?? a, 16);
          });
        }),
    )
    .map(([name]) => name) as never;

const loaded = new Set<string>();

/** Loads the glyphs `text` uses for each family (once per family+text). Safe to call during render. */
export const loadFontsFor = (text: string, families: string[] = ["Black Han Sans", "Gothic A1"]) => {
  for (const fam of families) {
    const entry = REGISTRY[fam];
    if (!entry) continue;
    const key = entry.mod ? `${fam}|${text}` : fam; // local files load whole, once
    if (loaded.has(key)) continue;
    loaded.add(key);
    if (entry.mod) {
      entry.mod.loadFont("normal", { weights: entry.weights.map(String), subsets: subsetsFor(entry.mod.getInfo(), text) });
    } else {
      for (const w of entry.weights) {
        loadLocalFont({ family: fam, url: staticFile(`fonts/Pretendard-${PRETENDARD_FILES[w]}.woff2`), weight: String(w) });
      }
    }
  }
};

/** CSS family, heaviest/lightest/regular weight and size correction for a registry name. */
export const fontOf = (name: string) => {
  const e = REGISTRY[name] ?? REGISTRY["Noto Sans KR"];
  const w = e.weights;
  return {
    family: e.mod ? e.mod.fontFamily : name,
    heavy: w[w.length - 1],
    light: w[0],
    regular: w.includes(400) ? 400 : w[Math.floor(w.length / 2)],
    scale: e.scale ?? 1,
  };
};
export const family = (name: string) => fontOf(name).family;
export const HEAVY = BlackHanSans.fontFamily;
export const THIN = GothicA1.fontFamily;

// Glyphs of the SeoulMoon composition.
loadFontsFor("서울의달오늘밤바라본저달이너무처량해너도나처럼외로운텅빈가슴안고사는구나슬픈추억“”");
