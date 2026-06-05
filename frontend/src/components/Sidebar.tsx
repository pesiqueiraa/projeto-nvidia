import { NavLink } from "react-router-dom";
import { NAV } from "../nav";

// Sidebar fixa de 200px (ux.md §3.1). Agrupa as páginas em
// "operacional" e "inteligência" conforme o ux.md §1.
export default function Sidebar() {
  const operacionais = NAV.filter((n) => n.group === "operacional");
  const inteligencia = NAV.filter((n) => n.group === "inteligencia");

  return (
    <aside className="sidebar">
      <div className="logo">
        NV<span>ISION</span>
      </div>

      <div className="sec-lbl">Operacional</div>
      {operacionais.map((n) => (
        <NavLink key={n.path} to={n.path} className="nav-item">
          {n.label}
        </NavLink>
      ))}

      <div className="sec-lbl">Inteligência</div>
      {inteligencia.map((n) => (
        <NavLink key={n.path} to={n.path} className="nav-item">
          {n.label}
        </NavLink>
      ))}

      <div className="status-live">
        <span className="dot" />
        sistema online
      </div>
    </aside>
  );
}
