import { useState } from "react";
import {
  ArrowDownRight,
  ArrowUpRight,
  Coins,
  CreditCard,
  Trash2,
  X,
} from "lucide-react";
import { useTranslation } from "react-i18next";

import { useBusinesses } from "@/entities/business";
import { hasPerm, useMe } from "@/entities/session";
import {
  useDeleteTransaction,
  useTransactions,
  useVoidTransaction,
  type Transaction,
} from "@/entities/transaction";
import { ConfirmIncomeButton } from "@/features/confirm-income";
import { apiErrorOf } from "@/shared/api";
import { moneyColor } from "@/shared/lib/money";
import {
  Button,
  EmptyState,
  ErrorBanner,
  Field,
  IconButton,
  Input,
  Loading,
  Money,
  Select,
  StatusBadge,
} from "@/shared/ui";

interface FiltersState {
  business: string;
  kind: string;
  status: string;
  method: string;
  date_from: string;
  date_to: string;
}

const EMPTY_FILTERS: FiltersState = {
  business: "",
  kind: "",
  status: "",
  method: "",
  date_from: "",
  date_to: "",
};

function KindCell({ kind }: { kind: Transaction["kind"] }) {
  const { t } = useTranslation();
  const dir = kind === "income" ? "in" : "out";
  const Icon = kind === "income" ? ArrowUpRight : ArrowDownRight;
  return (
    <span
      style={{
        color: moneyColor(dir),
        display: "inline-flex",
        alignItems: "center",
        gap: 4,
      }}
    >
      <Icon size={15} aria-hidden />
      {t(kind === "income" ? "finance.income" : "finance.expense")}
    </span>
  );
}

function MethodCell({ method }: { method: Transaction["method"] }) {
  const { t } = useTranslation();
  const Icon = method === "cash" ? Coins : CreditCard;
  return (
    <span style={{ display: "inline-flex", alignItems: "center", gap: 4 }}>
      <Icon size={15} aria-hidden style={{ color: "var(--text-muted)" }} />
      {t(`method.${method}`)}
    </span>
  );
}

/** Таблица операций (ФНС-01…03): фильтры, пагинация, строчные действия. */
export function TxTable() {
  const { t } = useTranslation();
  const { data: me } = useMe();
  const businesses = useBusinesses();

  const [filters, setFilters] = useState<FiltersState>(EMPTY_FILTERS);
  const [page, setPage] = useState(1);
  const [actionError, setActionError] = useState<string | null>(null);

  const query = useTransactions({
    page,
    business: filters.business ? Number(filters.business) : "",
    kind: filters.kind,
    status: filters.status,
    method: filters.method,
    date_from: filters.date_from,
    date_to: filters.date_to,
  });

  const voidTx = useVoidTransaction();
  const deleteTx = useDeleteTransaction();

  const canManage = hasPerm(me, "finance.manage");
  const canApprove = hasPerm(me, "finance.approve");

  const update = (patch: Partial<FiltersState>) => {
    setFilters((f) => ({ ...f, ...patch }));
    setPage(1);
  };

  const onMutationError = (err: unknown) => setActionError(apiErrorOf(err).message);

  return (
    <div>
      <div className="filters-bar">
        <Field label={t("common.business")}>
          <Select
            value={filters.business}
            onChange={(e) => update({ business: e.target.value })}
          >
            <option value="">{t("common.all")}</option>
            {(businesses.data ?? []).map((b) => (
              <option key={b.id} value={b.id}>
                {b.name}
              </option>
            ))}
          </Select>
        </Field>
        <Field label={t("finance.kind")}>
          <Select value={filters.kind} onChange={(e) => update({ kind: e.target.value })}>
            <option value="">{t("common.all")}</option>
            <option value="income">{t("finance.income")}</option>
            <option value="expense">{t("finance.expense")}</option>
          </Select>
        </Field>
        <Field label={t("common.status")}>
          <Select
            value={filters.status}
            onChange={(e) => update({ status: e.target.value })}
          >
            <option value="">{t("common.all")}</option>
            <option value="pending">{t("status.pending")}</option>
            <option value="confirmed">{t("status.confirmed")}</option>
            <option value="void">{t("status.void")}</option>
          </Select>
        </Field>
        <Field label={t("common.method")}>
          <Select
            value={filters.method}
            onChange={(e) => update({ method: e.target.value })}
          >
            <option value="">{t("common.all")}</option>
            <option value="cash">{t("method.cash")}</option>
            <option value="transfer">{t("method.transfer")}</option>
          </Select>
        </Field>
        <Field label={t("common.from")}>
          <Input
            type="date"
            value={filters.date_from}
            onChange={(e) => update({ date_from: e.target.value })}
          />
        </Field>
        <Field label={t("common.to")}>
          <Input
            type="date"
            value={filters.date_to}
            onChange={(e) => update({ date_to: e.target.value })}
          />
        </Field>
      </div>

      <ErrorBanner error={actionError} />

      {query.isLoading ? (
        <Loading />
      ) : query.isError ? (
        <div>
          <ErrorBanner error={apiErrorOf(query.error)} />
          <Button onClick={() => void query.refetch()}>{t("common.retry")}</Button>
        </div>
      ) : !query.data || query.data.results.length === 0 ? (
        <EmptyState />
      ) : (
        <>
          <div className="tbl-wrap">
            <table className="tbl">
              <thead>
                <tr>
                  <th>{t("common.date")}</th>
                  <th>{t("common.business")}</th>
                  <th>{t("finance.kind")}</th>
                  <th>{t("common.category")}</th>
                  <th className="num">{t("common.amount")}</th>
                  <th>{t("common.method")}</th>
                  <th>{t("common.status")}</th>
                  <th>{t("audit.actor")}</th>
                  <th className="num">{t("common.actions")}</th>
                </tr>
              </thead>
              <tbody>
                {query.data.results.map((tx) => (
                  <tr key={tx.id}>
                    <td>{new Date(tx.occurred_at).toLocaleDateString("ru-RU")}</td>
                    <td>{tx.business_name}</td>
                    <td>
                      <KindCell kind={tx.kind} />
                    </td>
                    <td>{tx.category_name ?? "—"}</td>
                    <td className="num">
                      <Money
                        value={tx.amount}
                        direction={tx.kind === "income" ? "in" : "out"}
                        withIcon
                        withSign
                      />
                    </td>
                    <td>
                      <MethodCell method={tx.method} />
                    </td>
                    <td>
                      <StatusBadge status={tx.status} />
                    </td>
                    <td>{tx.created_by_name}</td>
                    <td>
                      <div className="row-actions">
                        {tx.kind === "income" &&
                          tx.status === "pending" &&
                          canApprove && (
                            <ConfirmIncomeButton
                              transactionId={tx.id}
                              onApiError={setActionError}
                            />
                          )}
                        {tx.status !== "void" && canManage && (
                          <IconButton
                            icon={X}
                            label={t("finance.voidTx")}
                            tone="danger"
                            disabled={voidTx.isPending}
                            onClick={() => {
                              setActionError(null);
                              voidTx.mutate(tx.id, { onError: onMutationError });
                            }}
                          />
                        )}
                        {canManage && (
                          <IconButton
                            icon={Trash2}
                            label={t("common.delete")}
                            tone="danger"
                            disabled={deleteTx.isPending}
                            onClick={() => {
                              setActionError(null);
                              deleteTx.mutate(tx.id, { onError: onMutationError });
                            }}
                          />
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="pagination">
            <span>
              {t("common.total")}: {query.data.count}
            </span>
            <Button
              variant="ghost"
              disabled={!query.data.previous}
              onClick={() => setPage((p) => Math.max(1, p - 1))}
            >
              {t("common.prev")}
            </Button>
            <span>
              {t("common.page")} {page}
            </span>
            <Button
              variant="ghost"
              disabled={!query.data.next}
              onClick={() => setPage((p) => p + 1)}
            >
              {t("common.next")}
            </Button>
          </div>
        </>
      )}
    </div>
  );
}
