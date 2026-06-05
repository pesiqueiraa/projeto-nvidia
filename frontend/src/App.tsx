import { Navigate, Route, Routes } from "react-router-dom";
import Sidebar from "./components/Sidebar";
import Topbar from "./components/Topbar";
import Placeholder from "./pages/Placeholder";

// Shell da aplicação (ux.md §3.1): sidebar fixa + topbar + conteúdo.
// As 5 rotas do ux.md §6.5. Por ora todas usam o Placeholder; cada uma
// será substituída pela página real na semana correspondente do roadmap.
export default function App() {
  return (
    <div className="app-shell">
      <Sidebar />
      <div className="main">
        <Topbar />
        <Routes>
          <Route path="/" element={<Navigate to="/pipeline" replace />} />
          <Route path="/pipeline" element={<Placeholder titulo="Pipeline" />} />
          <Route path="/qualificadas" element={<Placeholder titulo="Qualificadas" />} />
          <Route path="/analytics" element={<Placeholder titulo="Analytics" />} />
          <Route path="/fit-score" element={<Placeholder titulo="Score de Fit" />} />
          <Route path="/sinais" element={<Placeholder titulo="Sinais de Evolução" />} />
        </Routes>
      </div>
    </div>
  );
}
