import { useMemo } from "react";
import { useTranslation } from "react-i18next";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import type { CashflowRow, ExpenseCategoryRow, MonthlyRow } from "@/entities/report";
import { formatMoney } from "@/shared/lib/money";

/** Фиксированный мап business_id -> var(--cat-N) по отсортированным id.
 *  Цвет следует за сущностью и не перекрашивается при фильтрации:
 *  мап строится по полному списку бизнесов, а не по отфильтрованным данным. */
export function businessColorMap(
  ids: (number | null | undefined)[],
): Map<number, string> {
  const sorted = [...new Set(ids.filter((v): v is number => typeof v === "number"))].sort(
    (a, b) => a - b,
  );
  return new Map(sorted.map((id, i) => [id, `var(--cat-${(i % 6) + 1})`]));
}

const CHART_HEIGHT = 260;
/* Тик-текст 12px var(--text-muted); подписи НЕ цветом серии. */
const AXIS_TICK = { fontSize: 12, fill: "var(--text-muted)" } as const;
const TOOLTIP_STYLE = {
  fontSize: 12,
  background: "var(--surface)",
  border: "1px solid var(--border)",
  borderRadius: 6,
} as const;
const CURSOR_FILL = { fill: "var(--n-100)" } as const;

const compact = new Intl.NumberFormat("ru-RU", {
  notation: "compact",
  maximumFractionDigits: 1,
});

const axisMoney = (v: number) => compact.format(v);

/* Деньги в тултипах — только через formatMoney. */
const moneyFormatter = (value: number | string | (number | string)[]) =>
  formatMoney(Array.isArray(value) ? Number(value[0]) : Number(value));

/* "2026-01" -> "01.26" */
const monthLabel = (m: string) =>
  m.length >= 7 ? `${m.slice(5, 7)}.${m.slice(2, 4)}` : m;

const legendText = (value: string) => (
  <span style={{ color: "var(--text-muted)", fontSize: 12 }}>{value}</span>
);

/** Динамика доходов по месяцам: линия на бизнес, цвет фиксирован по business_id. */
export function MonthlyIncomeLineChart({
  rows,
  colorOf,
}: {
  rows: MonthlyRow[];
  colorOf: Map<number, string>;
}) {
  const { data, series } = useMemo(() => {
    const byMonth = new Map<string, Record<string, number | string>>();
    const names = new Map<number, string>();
    for (const r of rows) {
      names.set(r.business_id, r.business_name);
      const rec = byMonth.get(r.month) ?? { month: r.month };
      rec[`b${r.business_id}`] = Number.parseFloat(r.income);
      byMonth.set(r.month, rec);
    }
    return {
      data: [...byMonth.values()].sort((a, b) =>
        String(a.month).localeCompare(String(b.month)),
      ),
      series: [...names.entries()]
        .sort((a, b) => a[0] - b[0])
        .map(([id, name]) => ({ id, name })),
    };
  }, [rows]);

  return (
    <ResponsiveContainer width="100%" height={CHART_HEIGHT}>
      <LineChart data={data} margin={{ top: 8, right: 12, left: 4, bottom: 0 }}>
        <CartesianGrid stroke="var(--n-200)" vertical={false} />
        <XAxis
          dataKey="month"
          tick={AXIS_TICK}
          tickFormatter={monthLabel}
          axisLine={false}
          tickLine={false}
        />
        <YAxis
          tick={AXIS_TICK}
          tickFormatter={axisMoney}
          axisLine={false}
          tickLine={false}
          width={56}
        />
        <Tooltip
          formatter={moneyFormatter}
          labelFormatter={(m) => monthLabel(String(m))}
          contentStyle={TOOLTIP_STYLE}
        />
        {series.length >= 2 && <Legend formatter={legendText} iconSize={10} />}
        {series.map((s) => (
          <Line
            key={s.id}
            type="monotone"
            dataKey={`b${s.id}`}
            name={s.name}
            stroke={colorOf.get(s.id) ?? "var(--cat-1)"}
            strokeWidth={2}
            dot={false}
            activeDot={{ r: 4 }}
          />
        ))}
      </LineChart>
    </ResponsiveContainer>
  );
}

/** Доход/расход по бизнесам: 2 серии в семантических цветах денег. */
export function IncomeExpenseBarChart({ rows }: { rows: CashflowRow[] }) {
  const { t } = useTranslation();
  const data = useMemo(
    () =>
      rows.map((r) => ({
        name: r.business_name,
        income: Number.parseFloat(r.income),
        expense: Number.parseFloat(r.expense),
      })),
    [rows],
  );

  return (
    <ResponsiveContainer width="100%" height={CHART_HEIGHT}>
      <BarChart data={data} margin={{ top: 8, right: 12, left: 4, bottom: 0 }} barGap={2}>
        <CartesianGrid stroke="var(--n-200)" vertical={false} />
        <XAxis dataKey="name" tick={AXIS_TICK} axisLine={false} tickLine={false} />
        <YAxis
          tick={AXIS_TICK}
          tickFormatter={axisMoney}
          axisLine={false}
          tickLine={false}
          width={56}
        />
        <Tooltip formatter={moneyFormatter} cursor={CURSOR_FILL} contentStyle={TOOLTIP_STYLE} />
        <Legend formatter={legendText} iconSize={10} />
        <Bar
          dataKey="income"
          name={t("reports.income")}
          fill="var(--money-in)"
          radius={[4, 4, 0, 0]}
          maxBarSize={20}
        />
        <Bar
          dataKey="expense"
          name={t("reports.expense")}
          fill="var(--money-out)"
          radius={[4, 4, 0, 0]}
          maxBarSize={20}
        />
      </BarChart>
    </ResponsiveContainer>
  );
}

/** Расходы по категориям: горизонтальный BarChart (не pie), одна серия --money-out. */
export function ExpenseCategoryBarChart({ rows }: { rows: ExpenseCategoryRow[] }) {
  const { t } = useTranslation();
  const data = useMemo(
    () =>
      rows.map((r) => ({
        name: r.category_name,
        total: Number.parseFloat(r.total),
      })),
    [rows],
  );
  const height = Math.max(CHART_HEIGHT, data.length * 34 + 40);

  return (
    <ResponsiveContainer width="100%" height={height}>
      <BarChart data={data} layout="vertical" margin={{ top: 8, right: 12, left: 4, bottom: 0 }}>
        <CartesianGrid stroke="var(--n-200)" horizontal={false} />
        <XAxis
          type="number"
          tick={AXIS_TICK}
          tickFormatter={axisMoney}
          axisLine={false}
          tickLine={false}
        />
        <YAxis
          type="category"
          dataKey="name"
          tick={AXIS_TICK}
          width={150}
          axisLine={false}
          tickLine={false}
        />
        <Tooltip formatter={moneyFormatter} cursor={CURSOR_FILL} contentStyle={TOOLTIP_STYLE} />
        <Bar
          dataKey="total"
          name={t("reports.expense")}
          fill="var(--money-out)"
          radius={[0, 4, 4, 0]}
          maxBarSize={16}
        />
      </BarChart>
    </ResponsiveContainer>
  );
}

export interface BusinessBarDatum {
  id: number | null;
  name: string;
  value: number;
}

/** Одна метрика по бизнесам, категориальные цвета фиксированы за business_id. */
export function BusinessBarChart({
  rows,
  colorOf,
  name,
}: {
  rows: BusinessBarDatum[];
  colorOf: Map<number, string>;
  name: string;
}) {
  return (
    <ResponsiveContainer width="100%" height={CHART_HEIGHT}>
      <BarChart data={rows} margin={{ top: 8, right: 12, left: 4, bottom: 0 }}>
        <CartesianGrid stroke="var(--n-200)" vertical={false} />
        <XAxis dataKey="name" tick={AXIS_TICK} axisLine={false} tickLine={false} />
        <YAxis
          tick={AXIS_TICK}
          tickFormatter={axisMoney}
          axisLine={false}
          tickLine={false}
          width={56}
        />
        <Tooltip formatter={moneyFormatter} cursor={CURSOR_FILL} contentStyle={TOOLTIP_STYLE} />
        <Bar dataKey="value" name={name} radius={[4, 4, 0, 0]} maxBarSize={20}>
          {rows.map((d, i) => (
            <Cell
              key={d.id ?? `hq-${i}`}
              fill={d.id != null ? (colorOf.get(d.id) ?? "var(--n-400)") : "var(--n-400)"}
            />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}
