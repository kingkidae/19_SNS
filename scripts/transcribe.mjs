// One-off: word timestamps for the lyric clip. Usage: node scripts/transcribe.mjs <pcm-f32le-16k> <out.json>
import { canUseWhisperWebGpu, downloadWhisperModel, loadWhisperModel, toCaptions, transcribe } from "@remotion/whisper-webgpu";
import { readFile, writeFile } from "node:fs/promises";

const [pcmPath, outPath] = process.argv.slice(2);
const support = await canUseWhisperWebGpu();
if (!support.supported) throw new Error(support.detailedReason);

const buf = await readFile(pcmPath);
const channelWaveform = new Float32Array(buf.buffer, buf.byteOffset, buf.byteLength / 4);
const model = "small";
await downloadWhisperModel({ model });
await using _h = await loadWhisperModel({ model });
const transcription = await transcribe({ channelWaveform, model, language: "ko" });
const { captions } = toCaptions({ whisperWebGpuOutput: transcription });
await writeFile(outPath, JSON.stringify(captions, null, 1));
for (const c of captions) console.log((c.startMs / 1000).toFixed(2), (c.endMs / 1000).toFixed(2), c.text);
