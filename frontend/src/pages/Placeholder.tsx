// Stub reutilizável para as páginas ainda não implementadas.
// O layout real (dois painéis — ux.md §3.2) entra conforme o roadmap.
export default function Placeholder({ titulo }: { titulo: string }) {
  return (
    <div className="page">
      <div className="placeholder">
        Página <strong>{titulo}</strong> — esqueleto. Layout e dados reais entram
        conforme o roadmap (ux.md §10).
      </div>
    </div>
  );
}
