import { useState } from "react";
import { NavLink } from "react-router-dom";
import { useTranslation } from "react-i18next";
import {
  ArrowLeftRight,
  Banknote,
  BarChart3,
  Building2,
  LogOut,
  PanelLeftClose,
  PanelLeftOpen,
  Users,
  Wallet,
} from "lucide-react";

import { hasPerm, logout, type Me } from "@/entities/session";
import { LanguageSwitcher } from "@/features/language-switcher";
import { BrandLogo, IconButton } from "@/shared/ui";

import "./sidebar.css";

const NAV_ITEMS = [
  { to: "/finance", perm: "finance.view", icon: Wallet, key: "nav.finance" },
  { to: "/cash", perm: "cash.view", icon: Banknote, key: "nav.cash" },
  { to: "/settlements", perm: "settlements.view", icon: ArrowLeftRight, key: "nav.settlements" },
  { to: "/payroll", perm: "payroll.view", icon: Users, key: "nav.payroll" },
  { to: "/reports", perm: "reports.view", icon: BarChart3, key: "nav.reports" },
  { to: "/overlay", perm: "overlay.view", icon: Building2, key: "nav.overlay" },
] as const;

export function Sidebar({ me }: { me: Me }) {
  const { t } = useTranslation();
  const [collapsed, setCollapsed] = useState(false);

  return (
    <aside className={`sidebar${collapsed ? " sidebar--collapsed" : ""}`}>
      <div className="sidebar__logo">
        <BrandLogo variant={collapsed ? "mark" : "full"} height={26} />
      </div>
      <nav className="sidebar__nav" aria-label="Main">
        {NAV_ITEMS.filter((item) => hasPerm(me, item.perm)).map((item) => {
          const Icon = item.icon;
          const label = t(item.key);
          return (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) =>
                `sidebar__link${isActive ? " sidebar__link--active" : ""}`
              }
              title={collapsed ? label : undefined}
              aria-label={label}
            >
              <Icon size={18} aria-hidden />
              {!collapsed && <span>{label}</span>}
            </NavLink>
          );
        })}
      </nav>
      <div className="sidebar__footer">
        {!collapsed && (
          <div className="sidebar__user">
            <div className="sidebar__user-name">{me.full_name}</div>
            <div className="sidebar__user-role">{me.email}</div>
          </div>
        )}
        {!collapsed && <LanguageSwitcher />}
        <div className="sidebar__footer-actions">
          <IconButton
            icon={collapsed ? PanelLeftOpen : PanelLeftClose}
            label={collapsed ? t("nav.expand") : t("nav.collapse")}
            onClick={() => setCollapsed((v) => !v)}
          />
          <IconButton icon={LogOut} label={t("auth.logout")} onClick={logout} tone="danger" />
        </div>
      </div>
    </aside>
  );
}
