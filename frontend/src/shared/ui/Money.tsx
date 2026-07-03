import { ArrowDownRight, ArrowUpRight } from "lucide-react";

import {
  directionOf,
  formatMoney,
  moneyColor,
  type MoneyDirection,
} from "@/shared/lib/money";

interface MoneyProps {
  value: string | number;
  /** in/out — операция; не указано — по знаку значения (балансы, прибыль). */
  direction?: MoneyDirection;
  /** Стрелка-иконка рядом с суммой (для операций). */
  withIcon?: boolean;
  /** Явный знак +/− перед суммой. */
  withSign?: boolean;
}

/** Деньги: иконка + цвет + знак — цвет не единственный носитель смысла. */
export function Money({ value, direction, withIcon = false, withSign = false }: MoneyProps) {
  const dir = direction ?? directionOf(value);
  const color = moneyColor(dir);
  const Icon = dir === "in" ? ArrowUpRight : dir === "out" ? ArrowDownRight : null;
  return (
    <span className="money" style={{ color }} data-direction={dir}>
      {withIcon && Icon && <Icon size={15} aria-hidden />}
      {formatMoney(value, { sign: withSign && dir !== "zero" ? dir : undefined })}
    </span>
  );
}
