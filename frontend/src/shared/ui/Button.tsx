import type { ButtonHTMLAttributes, ReactNode } from "react";
import type { LucideIcon } from "lucide-react";

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "primary" | "secondary" | "ghost" | "danger";
  icon?: LucideIcon;
  children?: ReactNode;
}

/** Кнопка: первичные действия — иконка слева от подписи (size=16). */
export function Button({
  variant = "secondary",
  icon: Icon,
  children,
  type = "button",
  ...rest
}: ButtonProps) {
  return (
    <button type={type} className={`btn btn--${variant}`} {...rest}>
      {Icon && <Icon size={16} aria-hidden />}
      {children}
    </button>
  );
}
