export const DEMO_PASSWORD = "arkand2026";
export const EMAIL_DOMAIN = "@arkand.tj";

export type DemoGroup = "acc" | "cash" | "own" | "sys";

export interface DemoAccount {
  user: string;
  group: DemoGroup;
  /** Подпись роли из i18n login.roles. */
  roleKey?: "chief" | "manager" | "admin";
  /** Предприятие (для кассиров), выводится как есть. */
  unit?: string;
}

export const demoAccounts: DemoAccount[] = [
  { user: "nigina", group: "acc", roleKey: "chief" },
  { user: "firuz", group: "acc" },
  { user: "manizha", group: "acc" },
  { user: "jamshed", group: "cash", unit: "Строй-Инвест" },
  { user: "farrukh", group: "cash", unit: "Проект-Бюро" },
  { user: "sino", group: "cash", unit: "Завод Алмосӣ" },
  { user: "dilnoza", group: "cash", unit: "Завод Сомон" },
  { user: "owner", group: "own" },
  { user: "umed", group: "own" },
  { user: "rustam", group: "sys", roleKey: "manager" },
  { user: "admin", group: "sys", roleKey: "admin" },
];

/** Порядок групп в UI. */
export const DEMO_GROUPS: DemoGroup[] = ["acc", "cash", "own", "sys"];

/** В панели показываем по одному представителю на отдел. */
export const FEATURED_USERS = ["nigina", "jamshed", "owner", "admin"] as const;

export const featuredAccounts: DemoAccount[] = DEMO_GROUPS.map(
  (group) =>
    demoAccounts.find(
      (a) => a.group === group && (FEATURED_USERS as readonly string[]).includes(a.user),
    ) ?? demoAccounts.find((a) => a.group === group)!,
);
