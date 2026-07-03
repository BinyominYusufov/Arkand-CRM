import { useState } from "react";
import { useTranslation } from "react-i18next";
import {
  ArrowDownRight,
  ArrowUpRight,
  ChevronLeft,
  ChevronRight,
  Coins,
  CreditCard,
  Plus,
} from "lucide-react";

import { CashCard } from "@/widgets/cash-card";
import { CashOperationModal } from "@/features/cash-operation";
import {
  useCashOperations,
  useCashRegisters,
  type CashOperation,
} from "@/entities/cash-register";
import { apiErrorOf } from "@/shared/api";
import { moneyColor } from "@/shared/lib/money";
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
} from "@/shared/ui";

function DirectionCell({ direction }: { direction: CashOperation["direction"] }) {
  const { t } = useTranslation();
  const Icon = direction === "in" ? ArrowUpRight : ArrowDownRight;
  return (
    <span
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: 4,
        color: moneyColor(direction),
      }}
    >
      <Icon size={15} aria-hidden />
      {direction === "in" ? t("cash.in") : t("cash.out")}
    </span>
  );
}

function MethodCell({ method }: { method: CashOperation["method"] }) {
  const { t } = useTranslation();
  const Icon = method === "cash" ? Coins : CreditCard;
  return (
    <span style={{ display: "inline-flex", alignItems: "center", gap: 4 }}>
      <Icon size={16} aria-hidden style={{ color: "var(--text-muted)" }} />
      {method === "cash" ? t("method.cash") : t("method.transfer")}
    </span>
  );
}

export function CashPage() {
  const { t } = useTranslation();
  const registers = useCashRegisters();
  const [registerFilter, setRegisterFilter] = useState<number | "">("");
  const [directionFilter, setDirectionFilter] = useState("");
  const [page, setPage] = useState(1);
  const [modalOpen, setModalOpen] = useState(false);
  const operations = useCashOperations({
    register: registerFilter,
    direction: directionFilter || undefined,
    page,
  });

  return (
    <div>
      <PageHeader
        title={t("cash.title")}
        actions={
          <Button
            variant="primary"
            icon={Plus}
            onClick={() => setModalOpen(true)}
          >
            {t("cash.addOperation")}
          </Button>
        }
      />

      {registers.isPending && <Loading />}
      {registers.isError && <ErrorBanner error={apiErrorOf(registers.error)} />}
      {registers.data &&
        (registers.data.length === 0 ? (
          <EmptyState />
        ) : (
          <div className="kpi-grid">
            {registers.data.map((register) => (
              <CashCard key={register.id} register={register} />
            ))}
          </div>
        ))}

      <h2 className="section-title">{t("cash.operations")}</h2>
      <div className="filters-bar">
        <Field label={t("cash.register")}>
          <Select
            value={registerFilter}
            onChange={(e) => {
              setRegisterFilter(e.target.value === "" ? "" : Number(e.target.value));
              setPage(1);
            }}
          >
            <option value="">{t("common.all")}</option>
            {(registers.data ?? []).map((r) => (
              <option key={r.id} value={r.id}>
                {r.name} · {r.business_name}
              </option>
            ))}
          </Select>
        </Field>
        <Field label={t("cash.direction")}>
          <Select
            value={directionFilter}
            onChange={(e) => {
              setDirectionFilter(e.target.value);
              setPage(1);
            }}
          >
            <option value="">{t("common.all")}</option>
            <option value="in">{t("cash.in")}</option>
            <option value="out">{t("cash.out")}</option>
          </Select>
        </Field>
      </div>

      {operations.isPending && <Loading />}
      {operations.isError && (
        <ErrorBanner error={apiErrorOf(operations.error)} />
      )}
      {operations.data &&
        (operations.data.results.length === 0 ? (
          <EmptyState />
        ) : (
          <>
            <div className="tbl-wrap">
              <table className="tbl">
                <thead>
                  <tr>
                    <th>{t("common.date")}</th>
                    <th>{t("cash.register")}</th>
                    <th>{t("cash.direction")}</th>
                    <th>{t("common.method")}</th>
                    <th className="num">{t("common.amount")}</th>
                    <th>{t("audit.actor")}</th>
                  </tr>
                </thead>
                <tbody>
                  {operations.data.results.map((op) => (
                    <tr key={op.id}>
                      <td>
                        {new Date(op.occurred_at).toLocaleString("ru-RU", {
                          dateStyle: "short",
                          timeStyle: "short",
                        })}
                      </td>
                      <td>
                        {op.register_name} · {op.business_name}
                      </td>
                      <td>
                        <DirectionCell direction={op.direction} />
                      </td>
                      <td>
                        <MethodCell method={op.method} />
                      </td>
                      <td className="num">
                        <Money
                          value={op.amount}
                          direction={op.direction}
                          withIcon
                          withSign
                        />
                      </td>
                      <td>{op.created_by_name}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div className="pagination">
              <IconButton
                icon={ChevronLeft}
                label={t("common.prev")}
                disabled={!operations.data.previous}
                onClick={() => setPage((p) => Math.max(1, p - 1))}
              />
              <span>
                {t("common.page")} {page}
              </span>
              <IconButton
                icon={ChevronRight}
                label={t("common.next")}
                disabled={!operations.data.next}
                onClick={() => setPage((p) => p + 1)}
              />
            </div>
          </>
        ))}

      <CashOperationModal
        open={modalOpen}
        onClose={() => setModalOpen(false)}
        registers={registers.data ?? []}
      />
    </div>
  );
}
