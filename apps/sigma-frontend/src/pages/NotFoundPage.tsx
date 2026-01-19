import { Link, useLocation } from 'react-router-dom';

function NotFoundPage() {
  const location = useLocation();

  return (
    <div className="page-shell">
      <section className="glass-panel">
        <h2>Route not found</h2>
        <p>
          No view is registered for <code>{location.pathname}</code>. Use the navigation below to
          return to a known layout.
        </p>
        <p>
          <Link to="/">Return to landing</Link>
        </p>
      </section>
    </div>
  );
}

export default NotFoundPage;
