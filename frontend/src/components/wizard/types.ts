import type { ReviewMode } from "@/lib/api";

export interface WizardState {
  category: string;
  genre: string;
  audience: string;
  content_rating: string;
  pov: string;
  tense: string;
  title: string;
  subtitle: string;
  author_name: string;
  premise: string;
  tone: string;
  style_notes: string;
  target_word_count: number;
  target_chapter_count: number;
  review_mode: ReviewMode;
  writer_model: string;
  editor_model: string;
}

export type SetField = <K extends keyof WizardState>(key: K, value: WizardState[K]) => void;

export const INITIAL: WizardState = {
  category: "",
  genre: "",
  audience: "adult",
  content_rating: "moderate",
  pov: "third_limited",
  tense: "past",
  title: "",
  subtitle: "",
  author_name: "",
  premise: "",
  tone: "",
  style_notes: "",
  target_word_count: 0,
  target_chapter_count: 0,
  review_mode: "manual",
  writer_model: "",
  editor_model: "",
};
