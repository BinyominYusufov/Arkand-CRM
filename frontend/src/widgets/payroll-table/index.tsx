import { Fragment, useState } from "react";
import { useTranslation } from "react-i18next";
import { ChevronDown, ChevronUp } from "lucide-react";

import type { PayrollItem } from "@/entities/payroll";
import { formatMoney } from "@/shared/lib/money";
import { EmptyState, IconButton, Money } from "@/shared/ui";

const COLS = 7;

/** Ключи breakdown, значения которых — деньги (формат только через formatMoney). */
const MONEY_KEYS = new Set(["base", "bonus", "total", "sales_amount"]);

const INPUT_LABEL_KEYS: Record<string, string> = {
  sales_amount: "payroll.salesAmount",
  units: "payroll.units",
};

function formatValue(key: string, value: unknown): string {
  if (value == null) return "—";
  if (MONEY_KEYS.has(key) && (typeof value === "string" || typeof value === "number")) {
    return formatMoney(value);
  }
  if (typeof value === "object") return JSON.stringify(value);
  return String(value);
}

/** Разбивка расчёта: scheme_type, inputs (значение + источник auto/manual),
 *  остальные поля (percent, tiers_applied, tier_mode, …) — как есть. */
function BreakdownView({ data }: { data: Record<string, unknown> }) {
  const { t } = useTranslation();
  const schemeType = data.scheme_type;
  const inputs =
    data.inputs && typeof data.inputs === "object" && !Array.isArray(data.inputs)
      ? (data.inputs as Record<string, unknown>)
      : null;
  const rest = Object.entries(data).filter(([k]) => k !== "scheme_type" && k !== "inputs");
  const labelStyle = { color: "var(--text-muted)" } as const;

  return (
    <div style={{ display: "grid", gap: 3, fontSize: 12.5, padding: "4px 2px" }}>
      {typeof schemeType === "string" && (
        <div>
          <span style={labelStyle}>{t("payroll.schemeType")}: </span>
          <span>{t(`payroll.${schemeType}`, schemeType)}</span>
        </div>
      )}
      {inputs &&
        Object.entries(inputs).map(([key, raw]) => {
          const labelKey = INPUT_LABEL_KEYS[key];
          const label = labelKey ? t(labelKey) : key;
          const obj =
            raw && typeof raw === "object" && !Array.isArray(raw)
              ? (raw as { value?: unknown; source?: unknown })
              : null;
          const value = obj && "value" in obj ? obj.value : raw;
          const source = obj && typeof obj.source === "string" ? obj.source : null;
          return (
            <div key={key}>
              <span style={labelStyle}>{label}: </span>
              <span>{formatValue(key, value)}</span>{" "}
              {source && (
                <span style={{ color: "var(--text-faint)" }}>
                  ({t("payroll.inputsSource")}:{" "}
                  {source === "auto"
                    ? t("payroll.auto")
                    : source === "manual"
                      ? t("payroll.manual")
                      : source}
                  )
                </span>
              )}
            </div>
          );
        })}
      {rest.map(([key, value]) => (
        <div key={key} style={{ fontFamily: "ui-monospace, SFMono-Regular, Consolas, monospace" }}>
          <span style={labelStyle}>{key}: </span>
          <span>{formatValue(key, value)}</span>
        </div>
      ))}
    </div>
  );
}

/** Таблица строк расчёта зарплаты: сотрудник, бизнес, тип, оклад/бонус/итого,
 *  раскрывающаяся разбивка по каждой строке. */
export function PayrollTable({ items }: { items: PayrollItem[] }) {
  const { t } = useTranslation();
  const [openId, setOpenId] = useState<number | null>(null);

  if (!items.length) return <EmptyState />;

  return (
    <div className="tbl-wrap">
      <table className="tbl">
        <thead>
          <tr>
            <th>{t("payroll.employee")}</th>
            <th>{t("common.business")}</th>
            <th>{t("payroll.salaryType")}</th>
            <th className="num">{t("payroll.base")}</th>
            <th className="num">{t("payroll.bonus")}</th>
            <th className="num">{t("payroll.totalPay")}</th>
            <th />
          </tr>
        </thead>
        <tbody>
          {items.map((item) => {
            const expanded = openId === item.id;
            return (
              <Fragment key={item.id}>
                <tr>
                  <td>{item.employee_name}</td>
                  <td>{item.business_name ?? t("payroll.headOffice")}</td>
                  <td>{t(`payroll.${item.salary_type}`, item.salary_type)}</td>
                  <td className="num">
                    <Money value={item.base} direction="zero" />
                  </td>
                  <td className="num">
                    <Money value={item.bonus} direction="zero" />
                  </td>
                  <td className="num" style={{ fontWeight: 600 }}>
                    <Money value={item.total} direction="zero" />
                  </td>
                  <td>
                    <div className="row-actions">
                      <IconButton
                        icon={expanded ? ChevronUp : ChevronDown}
                        label={t("payroll.breakdown")}
                        aria-expanded={expanded}
                        onClick={() => setOpenId(expanded ? null : item.id)}
                      />
                    </div>
                  </td>
                </tr>
                {expanded && (
                  <tr>
                    <td colSpan={COLS} style={{ background: "var(--n-50)" }}>
                      <BreakdownView data={item.breakdown} />
                    </td>
                  </tr>
                )}
              </Fragment>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
