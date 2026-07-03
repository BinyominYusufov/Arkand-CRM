import logoFullSvg from "@/shared/assets/brand/logo-full.svg";
import logoMarkSvg from "@/shared/assets/brand/logo-mark.svg";

// Оригинальный вордмарк arkand_logo.png добавляет разработчик в
// shared/assets/brand/ — glob подхватит его без правок кода.
const pngCandidates = import.meta.glob("@/shared/assets/brand/arkand_logo.png", {
  eager: true,
  query: "?url",
  import: "default",
}) as Record<string, string>;
const logoFullPng = Object.values(pngCandidates)[0];

interface BrandLogoProps {
  /** full — вордмарк (сайдбар, вход); mark — компактный знак. */
  variant?: "full" | "mark";
  height?: number;
}

/** Логотип ARKAND: не искажать, не перекрашивать, только на --paper/--white/--ink. */
export function BrandLogo({ variant = "full", height = 28 }: BrandLogoProps) {
  const src = variant === "mark" ? logoMarkSvg : (logoFullPng ?? logoFullSvg);
  return (
    <img
      src={src}
      alt="ARKAND"
      style={{ height, width: "auto", display: "block" }}
      draggable={false}
    />
  );
}
