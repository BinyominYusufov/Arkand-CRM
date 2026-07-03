import { describe, expect, it } from "vitest";

import {
  CURRENCY_SYMBOL,
  directionOf,
  formatMoney,
  moneyColor,
} from "./money";

/** Разделитель групп разрядов Intl ru-RU (NBSP/узкий пробел — зависит от ICU). */
const SEP = new Intl.NumberFormat("ru-RU", {
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
}).format(1234.5).charAt(1);

describe("formatMoney", () => {
  it("форматирует разряды и запятую, добавляет символ 'с.'", () => {
    expect(formatMoney("12345.67")).toBe(`12${SEP}345,67 ${CURRENCY_SYMBOL}`);
    expect(formatMoney(12345.67)).toBe(`12${SEP}345,67 ${CURRENCY_SYMBOL}`);
    expect(formatMoney(0)).toBe(`0,00 ${CURRENCY_SYMBOL}`);
    expect(formatMoney("1000000")).toBe(`1${SEP}000${SEP}000,00 ${CURRENCY_SYMBOL}`);
  });

  it("добавляет явный знак + для прихода", () => {
    expect(formatMoney("12345.67", { sign: "in" })).toBe(
      `+12${SEP}345,67 ${CURRENCY_SYMBOL}`,
    );
  });

  it("добавляет явный знак − для расхода (минус U+2212)", () => {
    expect(formatMoney("500", { sign: "out" })).toBe(`−500,00 ${CURRENCY_SYMBOL}`);
  });

  it("отрицательное значение без opts.sign — со знаком −", () => {
    expect(formatMoney(-42.5)).toBe(`−42,50 ${CURRENCY_SYMBOL}`);
  });

  it("NaN и нечисловые строки — прочерк с символом валюты", () => {
    expect(formatMoney(Number.NaN)).toBe(`— ${CURRENCY_SYMBOL}`);
    expect(formatMoney("abc")).toBe(`— ${CURRENCY_SYMBOL}`);
  });
});

describe("directionOf", () => {
  it("положительное — in, отрицательное — out", () => {
    expect(directionOf(10)).toBe("in");
    expect(directionOf("15.50")).toBe("in");
    expect(directionOf(-3)).toBe("out");
    expect(directionOf("-0.01")).toBe("out");
  });

  it("ноль и NaN — zero", () => {
    expect(directionOf(0)).toBe("zero");
    expect(directionOf("0.00")).toBe("zero");
    expect(directionOf("abc")).toBe("zero");
  });
});

describe("moneyColor", () => {
  it("возвращает CSS-переменные направлений (не бренд)", () => {
    expect(moneyColor("in")).toBe("var(--money-in)");
    expect(moneyColor("out")).toBe("var(--money-out)");
    expect(moneyColor("zero")).toBe("var(--money-zero)");
  });
});
