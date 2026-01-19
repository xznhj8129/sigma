import { Link } from 'react-router-dom';

function LandingPage() {
  return (
    <div className="page-shell">
      <header className="glass-panel">
        <h1>σ Frontend</h1>
        <p>
          React + Vite rewrite of the legacy Flask UI. GoldenLayout and WinBox are wired for
          modular windows, FastAPI contracts are ready to flow into typed clients, and blueprint
          YAML drives previewable window definitions.
        </p>
      </header>

      <section className="glass-panel">
        <h2>Entry points</h2>
        <ul>
          <li>
            <Link to="/workspace">Workspace</Link> — WinBox powered desktop with Start menu.
          </li>
          <li>
            <Link to="/test">GoldenLayout Test</Link> — mirrors the legacy twin pane sandbox.
          </li>
        </ul>
      </section>
    </div>
  );
}

export default LandingPage;
