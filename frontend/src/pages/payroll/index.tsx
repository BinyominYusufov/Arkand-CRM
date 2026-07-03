import { useState } from "react";
import { useTranslation } from "react-i18next";
import { isAxiosError } from "axios";
import { ArrowLeft, CheckCircle2, Eye } from "lucide-react";

import {
  useEmployees,
  useFinalizeRun,
  usePayrollRun,
  usePayrollRuns,
  useSchemes,
  type SalaryScheme,
} from "@/entities/payroll";
import { hasPerm, useMe } from "@/entities/session";
import { RunPayrollButton } from "@/features/run-payroll";
import { PayrollTable } from "@/widgets/payroll-table";
import { apiErrorOf } from "@/shared/api";
import {
  Button,
  EmptyState,
  ErrorBanner,
  Field,
  IconButton,
  Loading,
  Money,
  PageHeader,
  Select,
  StatusBadge,
  Tabs,
} from "@/shared/ui";

function periodOf(run: { year: number; month: number }): string {
  return `${String(run.month).padStart(2, "0")}.${run.year}`;
}

/** Список расчётов: период, статус, фонд, число сотрудников. */
function RunsTab({ onOpen }: { onOpen: (id: number) => void }) {
  const { t } = useTranslation();
  const runs = usePayrollRuns();

  if (runs.isPending) return <Loading />;
  if (runs.isError) return <ErrorBanner error={apiErrorOf(runs.error)} />;
  const rows = runs.data.results;
  if (!rows.length) return <EmptyState />;

  return (
    <div className="tbl-wrap">
      <table className="tbl">
        <thead>
          <tr>
            <th>{t("common.period")}</th>
            <th>{t("common.status")}</th>
            <th className="num">{t("payroll.fund")}</th>
            <th className="num">{t("payroll.employees")}</th>
            <th />
          </tr>
        </thead>
        <tbody>
          {rows.map((run) => (
            <tr key={run.id} onClick={() => onOpen(run.id)} style={{ cursor: "pointer" }}>
              <td>{periodOf(run)}</td>
              <td>
                <StatusBadge status={run.status} />
              </td>
              <td className="num">
                <Money value={run.total_fund} direction="zero" />
              </td>
              <td className="num">{run.items_count}</td>
              <td>
                <div className="row-actions">
                  <IconButton
                    icon={Eye}
                    label={t("common.view")}
                    onClick={(e) => {
                      e.stopPropagation();
                      onOpen(run.id);
                    }}
                  />
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

/** Детали расчёта: шапка (период, статус, фонд), утверждение, таблица строк. */
function RunDetails({
  id,
  canManage,
  onBack,
}: {
  id: number;
  canManage: boolean;
  onBack: () => void;
}) {
  const { t } = useTranslation();
  const runQuery = usePayrollRun(id);
  const finalize = useFinalizeRun();
  const [finalizeError, setFinalizeError] = useState<string | null>(null);

  if (runQuery.isPending) return <Loading />;
  if (runQuery.isError) return <ErrorBanner error={apiErrorOf(runQuery.error)} />;
  const run = runQuery.data;

  const onFinalize = () => {
    setFinalizeError(null);
    finalize.mutate(run.id, {
      onError: (err) => {
        setFinalizeError(
          isAxiosError(err) && err.response?.status === 409
            ? t("payroll.alreadyFinalized")
            : apiErrorOf(err).message,
        );
      },
    });
  };

  return (
    <>
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: 10,
          flexWrap: "wrap",
          marginBottom: 12,
        }}
      >
        <Button variant="ghost" icon={ArrowLeft} onClick={onBack}>
          {t("common.prev")}
        </Button>
        <span style={{ fontSize: 15, fontWeight: 600 }}>
          {t("payroll.run")} {periodOf(run)}
        </span>
        <StatusBadge status={run.status} />
        <span style={{ color: "var(--text-muted)", fontSize: 13 }}>
          {t("payroll.fund")}:
        </span>
        <Money value={run.total_fund} direction="zero" />
        <span style={{ flex: 1 }} />
        {canManage && run.status === "draft" && (
          <Button
            variant="primary"
            icon={CheckCircle2}
            onClick={onFinalize}
            disabled={finalize.isPending}
          >
            {t("payroll.finalize")}
          </Button>
        )}
      </div>
      <ErrorBanner error={finalizeError} />
      <PayrollTable items={run.items ?? []} />
    </>
  );
}

/** Сотрудники: ФИО (+бейдж продажника), бизнес, должность, тип, активность. */
function EmployeesTab() {
  const { t } = useTranslation();
  const [active, setActive] = useState("");
  const employees = useEmployees(active === "" ? {} : { is_active: active === "1" });

  return (
    <>
      <div className="filters-bar">
        <Field label={t("status.active")}>
          <Select value={active} onChange={(e) => setActive(e.target.value)}>
            <option value="">{t("common.all")}</option>
            <option value="1">{t("common.yes")}</option>
            <option value="0">{t("common.no")}</option>
          </Select>
        </Field>
      </div>
      {employees.isPending ? (
        <Loading />
      ) : employees.isError ? (
        <ErrorBanner error={apiErrorOf(employees.error)} />
      ) : !employees.data.results.length ? (
        <EmptyState />
      ) : (
        <div className="tbl-wrap">
          <table className="tbl">
            <thead>
              <tr>
                <th>{t("payroll.fullName")}</th>
                <th>{t("common.business")}</th>
                <th>{t("payroll.position")}</th>
                <th>{t("payroll.salaryType")}</th>
                <th>{t("status.active")}</th>
              </tr>
            </thead>
            <tbody>
              {employees.data.results.map((emp) => (
                <tr key={emp.id}>
                  <td>
                    <span style={{ display: "inline-flex", alignItems: "center", gap: 6 }}>
                      {emp.full_name}
                      {emp.is_salesperson && (
                        <span className="badge badge--info">{t("payroll.salesperson")}</span>
                      )}
                    </span>
                  </td>
                  <td>{emp.business_name ?? t("payroll.headOffice")}</td>
                  <td>{emp.position}</td>
                  <td>{t(`payroll.${emp.salary_type}`, emp.salary_type)}</td>
                  <td>{emp.is_active ? t("common.yes") : t("common.no")}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </>
  );
}

/** Краткое описание config схемы: base / percent / tiers + tier_mode. */
function SchemeConfig({ scheme }: { scheme: SalaryScheme }) {
  const cfg = scheme.config ?? {};
  if (scheme.scheme_type === "fixed") {
    const base = cfg["base"];
    return typeof base === "string" || typeof base === "number" ? (
      <Money value={base} direction="zero" />
    ) : (
      <>—</>
    );
  }
  if (scheme.scheme_type === "percent_of_sales") {
    const percent = cfg["percent"];
    return <>{percent == null ? "—" : `${String(percent)}%`}</>;
  }
  const tiers = Array.isArray(cfg["tiers"]) ? (cfg["tiers"] as unknown[]) : [];
  const mode = typeof cfg["tier_mode"] === "string" ? (cfg["tier_mode"] as string) : null;
  return (
    <span style={{ fontFamily: "ui-monospace, SFMono-Regular, Consolas, monospace", fontSize: 12 }}>
      {JSON.stringify(tiers)}
      {mode ? ` · ${mode}` : ""}
    </span>
  );
}

/** Схемы оплаты: сотрудник, тип схемы, config кратко. */
function SchemesTab() {
  const { t } = useTranslation();
  const schemes = useSchemes();

  if (schemes.isPending) return <Loading />;
  if (schemes.isError) return <ErrorBanner error={apiErrorOf(schemes.error)} />;
  const rows = schemes.data.results;
  if (!rows.length) return <EmptyState />;

  return (
    <div className="tbl-wrap">
      <table className="tbl">
        <thead>
          <tr>
            <th>{t("payroll.employee")}</th>
            <th>{t("payroll.schemeType")}</th>
            <th>{t("payroll.scheme")}</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((scheme) => (
            <tr key={scheme.id}>
              <td>{scheme.employee_name}</td>
              <td>{t(`payroll.${scheme.scheme_type}`, scheme.scheme_type)}</td>
              <td>
                <SchemeConfig scheme={scheme} />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function PayrollPage() {
  const { t } = useTranslation();
  const { data: me } = useMe();
  const canManage = hasPerm(me, "payroll.manage");
  const [tab, setTab] = useState("runs");
  const [runId, setRunId] = useState<number | null>(null);

  return (
    <div>
      <PageHeader
        title={t("payroll.title")}
        actions={
          canManage ? (
            <RunPayrollButton
              onCreated={(run) => {
                setTab("runs");
                setRunId(run.id);
              }}
            />
          ) : undefined
        }
      />
      <Tabs
        tabs={[
          { key: "runs", label: t("payroll.runs") },
          { key: "employees", label: t("payroll.employees") },
          { key: "schemes", label: t("payroll.schemes") },
        ]}
        active={tab}
        onChange={(key) => {
          setTab(key);
          setRunId(null);
        }}
      />
      {tab === "runs" &&
        (runId != null ? (
          <RunDetails id={runId} canManage={canManage} onBack={() => setRunId(null)} />
        ) : (
          <RunsTab onOpen={setRunId} />
        ))}
      {tab === "employees" && <EmployeesTab />}
      {tab === "schemes" && <SchemesTab />}
    </div>
  );
}
