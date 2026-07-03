/** Единый хелпер форматирования денег (сомони, TJS) — ТЗ, раздел 9.
 *  Цвет по знаку/направлению — только через CSS-переменные --money-in/out/zero. */

export const CURRENCY_SYMBOL = "с.";

const fmt = new Intl.NumberFormat("ru-RU", {
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});

export type MoneyDirection = "in" | "out" | "zero";

/** "12345.67" → "12 345,67 с." (опц. со знаком +/−). */
export function formatMoney(
  value: string | number,
  opts: { sign?: MoneyDirection } = {},
): string {
  const num = typeof value === "number" ? value : Number.parseFloat(value);
  if (Number.isNaN(num)) return `— ${CURRENCY_SYMBOL}`;
  const formatted = `${fmt.format(Math.abs(num))} ${CURRENCY_SYMBOL}`;
  if (opts.sign === "in") return `+${formatted}`;
  if (opts.sign === "out") return `−${formatted}`;
  return num < 0 ? `−${formatted}` : formatted;
}

/** CSS-цвет для направления денег. Никогда не бренд-вишнёвый. */
export function moneyColor(direction: MoneyDirection): string {
  if (direction === "in") return "var(--money-in)";
  if (direction === "out") return "var(--money-out)";
  return "var(--money-zero)";
}

/** Направление по знаку числа (для балансов/прибыли). */
export function directionOf(value: string | number): MoneyDirection {
  const num = typeof value === "number" ? value : Number.parseFloat(value);
  if (Number.isNaN(num) || num === 0) return "zero";
  return num > 0 ? "in" : "out";
}
