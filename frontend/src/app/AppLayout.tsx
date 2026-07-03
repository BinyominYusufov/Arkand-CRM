import { Outlet } from "react-router-dom";

import { useMe } from "@/entities/session";
import { Sidebar } from "@/widgets/sidebar";
import { Loading } from "@/shared/ui";

export function AppLayout() {
  const { data: me } = useMe();
  if (!me) return <Loading />;
  return (
    <div style={{ display: "flex", minHeight: "100%" }}>
      <div className="no-print" style={{ display: "contents" }}>
        <Sidebar me={me} />
      </div>
      <main style={{ flex: 1, padding: "18px 22px", minWidth: 0 }}>
        <Outlet />
      </main>
    </div>
  );
}
