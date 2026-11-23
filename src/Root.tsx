import { Composition } from "remotion";
import { SeoulMoon } from "./SeoulMoon";

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
    </>
  );
};
