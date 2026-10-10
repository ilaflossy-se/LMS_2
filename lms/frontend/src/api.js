const API = import.meta.env.VITE_API || "http://localhost:5000";
export async function api(path, method = "GET", body) {
  const t = localStorage.getItem("token");
  const r = await fetch(API + "/api" + path, {
    method,
    headers: { "Content-Type": "application/json", ...(t ? { Authorization: "Bearer " + t } : {}) },
    body: body ? JSON.stringify(body) : undefined,
  });
  const d = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(d.error || "Ошибка запроса");
  return d;
}
