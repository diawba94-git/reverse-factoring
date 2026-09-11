export function ComingSoonAcheteurScreen({ title }: { title: string }) {
  return (
    <>
      <div className="generic-topbar">
        <h1>{title}</h1>
      </div>
      <main>
        <div className="empty-state">Cet écran n'est pas encore branché sur des données réelles.</div>
      </main>
    </>
  );
}
