import { useEffect, useState } from "react";
import { api } from "./api.js";

const MYDU = "https://astanait.edu.kz", LEARN = "https://astanait.edu.kz"; // R1: replace with real myDU / Learn URLs
const mask = (e) => e.slice(0, 2) + "*****" + e.slice(e.indexOf("@"));

function Login({ onAuth }) {
  const [err, setErr] = useState("");
  const go = (email) => api("/login/oidc", "POST", { email }).then((d) => onAuth(d.token, d.user)).catch((e) => setErr(e.message));
  return (
    <div className="login"><div className="logo">ASTANA IT UNIVERSITY</div>
      <div className="box">
        <button className="oidc" onClick={() => go("ansar@astanait.edu.kz")}><span className="ms" />Connect with OpenID Connect</button>
        {err && <p className="error">{err}</p>}
        <button className="link" onClick={() => go("teacher@astanait.edu.kz")}>Demo: sign in as teacher</button>
        <p className="muted small">Prototype: sign-in is simulated. Production uses the university Microsoft account.</p>
      </div></div>
  );
}

const Bar = ({ v, max = 100 }) => <div className="bar"><div style={{ width: Math.min(100, (v / max) * 100) + "%" }} /></div>;

function Dashboard() {
  const [d, setD] = useState(null); const [inv, setInv] = useState([]);
  const load = () => { api("/dashboard").then(setD); api("/invitations").then(setInv); };
  useEffect(load, []);
  if (!d) return null;
  return (<>
    <h2>Dashboard</h2>
    {inv.map((t) => (<div className="card note" key={t.id}>
      <span>Invitation to team <b>{t.name}</b> ({t.course})</span>
      <button onClick={() => api(`/teams/${t.id}/accept`, "POST").then(load)}>Accept</button></div>))}
    <h3>Upcoming deadlines</h3>
    {d.deadlines.length ? d.deadlines.map((x, i) => (<div className="card row" key={i}><span><b>{x.title}</b> · {x.course}</span><span className="tag">{x.due}</span></div>))
      : <p className="muted">No deadlines. Nice.</p>}
  </>);
}

function Courses({ open }) {
  const [l, setL] = useState([]); useEffect(() => { api("/courses").then(setL); }, []);
  return (<><h2>My courses</h2><div className="grid">
    {l.map((c) => (<button key={c.id} className="card course" onClick={() => open(c.id)}>
      <span className="tag">{c.code}</span><h3>{c.title}</h3><span className="muted small">{c.teacher}</span>
      <Bar v={c.current} /><span className="small">Current: {c.current} / 100</span></button>))}</div></>);
}

function Course({ id, back, user }) {
  const [c, setC] = useState(null); const [name, setName] = useState(""); const [emails, setEmails] = useState("");
  const [proj, setProj] = useState(""); const [msg, setMsg] = useState(""); const [max, setMax] = useState(0);
  const load = () => api("/courses/" + id).then((x) => { setC(x); setMax(x.group_max); });
  useEffect(() => { load(); }, [id]);
  const run = (p) => p.then(() => { setMsg(""); load(); }).catch((e) => setMsg(e.message));
  if (!c) return null;
  return (<>
    <button className="link" onClick={back}>← My courses</button>
    <h2>{c.title}</h2>
    <h3>Syllabus</h3>
    <table><tbody>{c.items.map((i) => (<tr key={i.id}><td>{i.title}</td><td>{i.weight}%</td><td>{i.due || ""}</td></tr>))}</tbody></table>
    <h3>Project group</h3>
    {user.role === "teacher" ? (
      <div className="card row"><label>Max students per group (0 = off)
        <input type="number" min="0" max="8" value={max} onChange={(e) => setMax(e.target.value)} /></label>
        <button onClick={() => run(api(`/courses/${id}/groups`, "PUT", { max: +max }))}>Save</button></div>
    ) : !c.group_max ? <p className="muted">Project groups are not enabled for this course.</p>
      : c.teams.length ? c.teams.map((t) => (<div className="card" key={t.id}>
          <b>{t.name}</b>
          <ul>{t.members.map((m, i) => <li key={i}>{m.name} — {m.accepted ? "accepted" : "waiting"}</li>)}</ul>
          {t.project ? <p>Project: <b>{t.project}</b></p> : (<div className="row2">
            <input placeholder="Project title" value={proj} onChange={(e) => setProj(e.target.value)} />
            <button onClick={() => run(api(`/teams/${t.id}/project`, "POST", { project: proj }))}>Add project</button></div>)}
        </div>))
      : (<div className="card col">
          <input placeholder="Team name" value={name} onChange={(e) => setName(e.target.value)} />
          <input placeholder={`Teammate emails, comma separated (max ${c.group_max - 1})`} value={emails} onChange={(e) => setEmails(e.target.value)} />
          <button onClick={() => run(api(`/courses/${id}/teams`, "POST", { name, emails: emails.split(",").filter(Boolean) }))}>Send invitations</button>
        </div>)}
    {msg && <p className="error">{msg}</p>}
  </>);
}

function Calc({ course }) {
  const [target, setTarget] = useState(80);
  const done = course.items.filter((i) => i.score !== null), left = course.items.filter((i) => i.score === null);
  const earned = done.reduce((s, i) => s + (i.weight * i.score) / 100, 0), w = left.reduce((s, i) => s + i.weight, 0);
  const need = w ? ((target - earned) / w) * 100 : null;
  return (<div className="card">
    <h3>{course.title}</h3>
    <table><tbody>{course.items.map((i) => (<tr key={i.id}><td>{i.title} ({i.weight}%)</td><td>{i.score ?? "—"}</td></tr>))}</tbody></table>
    <p>Current total: <b>{earned.toFixed(1)}</b> / {100 - w}</p>
    <label>Desired final score <input type="number" min="0" max="100" value={target} onChange={(e) => setTarget(+e.target.value)} /></label>
    <p className="result">{need === null ? "Course is complete." : need > 100 ? "Not reachable with the remaining assessments."
      : need <= 0 ? "Already achieved." : <>Average needed on the remaining {w}%: <b>{need.toFixed(1)}</b> / 100</>}</p>
  </div>);
}
function Grades() { const [g, setG] = useState([]); useEffect(() => { api("/grades").then(setG); }, []); return <><h2>Grades</h2><div className="grid">{g.map((c) => <Calc key={c.id} course={c} />)}</div></>; }

function Attendance() {
  const [a, setA] = useState([]); useEffect(() => { api("/attendance").then(setA); }, []);
  return (<><h2>Attendance</h2>{a.map((x, i) => (<div className="card" key={i}><div className="row"><b>{x.course}</b><span>{x.attended} / {x.total}</span></div><Bar v={x.attended} max={x.total} /></div>))}</>);
}

function Teams() {
  const [t, setT] = useState([]); useEffect(() => { api("/teacher/teams").then(setT); }, []);
  return (<><h2>Teams</h2>{!t.length && <p className="muted">No teams yet.</p>}
    {t.map((x) => (<div className="card" key={x.id}><b>{x.name}</b> <span className="tag">{x.course}</span>
      <ul>{x.members.map((m, i) => <li key={i}>{m.name} — {m.accepted ? "accepted" : "waiting"}</li>)}</ul>
      <p className="muted">{x.project ? "Project: " + x.project : "No project yet"}</p></div>))}</>);
}

export default function App() {
  const [user, setUser] = useState(null); const [ready, setReady] = useState(false);
  const [page, setPage] = useState("dashboard"); const [cid, setCid] = useState(null); const [menu, setMenu] = useState(false);
  const [dark, setDark] = useState(localStorage.getItem("dark") === "1");
  useEffect(() => { document.documentElement.dataset.theme = dark ? "dark" : "light"; localStorage.setItem("dark", dark ? "1" : "0"); }, [dark]);
  useEffect(() => { api("/me").then(setUser).catch(() => {}).finally(() => setReady(true)); }, []);
  if (!ready) return null;
  if (!user) return <Login onAuth={(t, u) => { localStorage.setItem("token", t); setUser(u); }} />;
  const nav = [["dashboard", "◎", "Dashboard"], ["courses", "▤", "My courses"], ["attendance", "✓", "Attendance"],
    ...(user.role === "teacher" ? [["teams", "☰", "Teams"]] : [["grades", "▦", "Grades"]])];
  const go = (p) => { setPage(p); setCid(null); };
  return (
    <div className="shell">
      <aside className="rail">
        <button className="ic" aria-label="Home" onClick={() => go("dashboard")}>⌂</button>
        <a className="ic" href={LEARN} target="_blank" rel="noreferrer" aria-label="Learn">L</a>
        <a className="ic" href={MYDU} target="_blank" rel="noreferrer" aria-label="myDU">M</a>
        <button className="ic bottom" aria-label="Dark mode" onClick={() => setDark(!dark)}>{dark ? "☀" : "☾"}</button>
      </aside>
      <nav className="side">
        <button className="user" onClick={() => setMenu(!menu)}><b>{user.name}</b><span className="small">{mask(user.email)} ▾</span></button>
        {menu && <button className="link" onClick={() => { localStorage.removeItem("token"); setUser(null); }}>Log out</button>}
        <div className="items">{nav.map(([k, i, l]) => (<button key={k} className={page === k ? "on" : ""} onClick={() => go(k)}><span>{i}</span>{l}</button>))}</div>
      </nav>
      <main>
        {page === "dashboard" && <Dashboard />}
        {page === "courses" && (cid ? <Course id={cid} user={user} back={() => setCid(null)} /> : <Courses open={setCid} />)}
        {page === "attendance" && <Attendance />}
        {page === "grades" && <Grades />}
        {page === "teams" && <Teams />}
      </main>
    </div>
  );
}
