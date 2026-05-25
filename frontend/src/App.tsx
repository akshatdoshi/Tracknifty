import { useEffect, useState } from "react";
import { api, clearToken, getToken, type Me } from "./api/client";
import { LoginView } from "./views/LoginView";
import { DashboardView } from "./views/DashboardView";

export default function App() {
  const [me, setMe] = useState<Me | null>(null);
  const [checked, setChecked] = useState(false);

  function loadMe() {
    api
      .me()
      .then(setMe)
      .catch(() => setMe(null))
      .finally(() => setChecked(true));
  }

  useEffect(() => {
    if (getToken()) loadMe();
    else setChecked(true);
  }, []);

  if (!checked) {
    return (
      <div className="flex min-h-screen items-center justify-center text-slate-400">
        Loading…
      </div>
    );
  }

  if (!me) return <LoginView onLogin={loadMe} />;

  return (
    <DashboardView
      me={me}
      onLogout={() => {
        clearToken();
        setMe(null);
      }}
    />
  );
}
