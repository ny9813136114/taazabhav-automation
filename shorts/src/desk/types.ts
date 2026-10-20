// Props written by engine/render.py (one props.json per video).
export type Word = { w: string; from: number }; // absolute frame the word is spoken

export type DeskScene = {
  kind: "number" | "move" | "compare" | "meter" | "stamp" | "claim" | "timeline" | "news" | "phone" | "cta" | "headline";
  from: number;
  frames: number;
  audio?: string | null;
  words?: Word[];
  tone?: string | null;
  label?: string | null;
  big?: string | null;
  sub?: string | null;
  count?: number | null;
  bars?: { label: string; value: number; text: string; tone?: string | null }[];
  pos?: number | null;
  left?: string | null;
  right?: string | null;
  items?: { label: string; value: string; tone?: string | null }[];
  n?: number | null;
  of?: number | null;
  video?: string | null;
};

export type DeskProps = {
  series: "A" | "B" | "C" | "D";
  clip?: string | null;
  clipFrames?: number | null;
  photo?: string | null;
  credit?: string | null;
  stamp?: string | null;
  stampTop?: string | null;
  scenes: DeskScene[];
  frames: number;
};
