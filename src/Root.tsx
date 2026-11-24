import { Composition, Still } from "remotion";
import { FontSpecimen } from "./FontSpecimen";
import { SeoulMoon } from "./SeoulMoon";
import { Short, calculateShortMetadata } from "./Short";

export const RemotionRoot: React.FC = () => {
  return (
    <>
      <Composition
        id="SeoulMoon"
        component={SeoulMoon}
        durationInFrames={1500}
        fps={30}
        width={1920}
        height={1080}
      />
      <Composition
        id="SeoulMoonShorts"
        component={SeoulMoon}
        durationInFrames={1500}
        fps={30}
        width={1080}
        height={1920}
      />
      <Still id="FontSpecimen" component={FontSpecimen} width={1600} height={2700} />
      {/* Rendered by the Telegram bot with --props=<scenario>; defaults are a preview sample. */}
      <Composition
        id="Short"
        component={Short}
        durationInFrames={300}
        fps={30}
        width={1080}
        height={1920}
        calculateMetadata={calculateShortMetadata}
        defaultProps={{
          theme: "pastel" as const,
          music: "comedic" as const,
          scenes: [
            { type: "title" as const, seconds: 2.5, heading: "엄마의 카톡 특징", body: "공감 100%", emphasis: "카톡", items: [], messages: [], number: "" },
            {
              type: "chat" as const, seconds: 5, heading: "엄마", body: "", emphasis: "", items: [], number: "",
              messages: [
                { side: "left" as const, text: "밥은 먹었니" },
                { side: "right" as const, text: "응 먹었어" },
                { side: "left" as const, text: "뭐 먹었는데 사진 보내봐" },
              ],
            },
            { type: "stat" as const, seconds: 3, heading: "답장까지 걸린 시간", body: "엄마는 기다리고 있었다", emphasis: "", items: [], messages: [], number: "3초" },
          ],
        }}
      />
    </>
  );
};
