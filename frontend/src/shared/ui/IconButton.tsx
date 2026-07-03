import type { ButtonHTMLAttributes } from "react";
import type { LucideIcon } from "lucide-react";

interface IconButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  icon: LucideIcon;
  /** Обязательная доступная подпись: aria-label + нативный тултип. */
  label: string;
  tone?: "default" | "success" | "danger";
}

/** Icon-кнопка строчных действий: компактная, с aria-label и тултипом. */
export function IconButton({
  icon: Icon,
  label,
  tone = "default",
  type = "button",
  ...rest
}: IconButtonProps) {
  const toneClass =
    tone === "success" ? " icon-btn--success" : tone === "danger" ? " icon-btn--danger" : "";
  return (
    <button
      type={type}
      className={`icon-btn${toneClass}`}
      aria-label={label}
      title={label}
      {...rest}
    >
      <Icon size={16} aria-hidden />
    </button>
  );
}
