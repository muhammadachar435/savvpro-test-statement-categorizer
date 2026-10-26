import { useState } from 'react';
import { NavLink, Link } from 'react-router-dom';
import { Menu, X, Zap, Shield } from 'lucide-react';

/**
 * Navbar — sticky professional navbar with React Router navigation.
 * Uses NavLink for active link highlighting with URL updates and history support.
 * Do not add icons to nav links.
 */
export default function Header() {
  const [mobileOpen, setMobileOpen] = useState(false);

  // Active state styling helper for desktop navigation links
  const getNavClass = ({ isActive }) => (isActive ? 'active' : '');

  return (
    <>
      <nav className="navbar" aria-label="Main navigation">
        <div className="navbar-inner">
          {/* Brand */}
          <Link to="/" className="navbar-brand" aria-label="SAVV Pro home">
            <div className="navbar-logo-icon" aria-hidden="true">SP</div>
            SAVV Pro
          </Link>

          {/* Desktop nav links */}
          <div className="navbar-nav" role="navigation" aria-label="Primary links">
            <NavLink
              to="/"
              end
              className={getNavClass}
            >
              Dashboard
            </NavLink>
            <NavLink
              to="/schedule-c"
              className={getNavClass}
            >
              Schedule C
            </NavLink>
            <NavLink
              to="/settings"
              className={getNavClass}
            >
              Settings
            </NavLink>
          </div>

          {/* Desktop right-side meta */}
          <div className="navbar-actions">
            <span className="navbar-badge" title="100% deterministic — no LLM API calls">
              <Zap size={12} strokeWidth={1.75} aria-hidden="true" />
              Zero-LLM
            </span>
            <span className="navbar-badge" title="All processing is local — data never leaves your machine">
              <Shield size={12} strokeWidth={1.75} aria-hidden="true" />
              Private
            </span>

            {/* Hamburger */}
            <button
              type="button"
              className="navbar-hamburger"
              onClick={() => setMobileOpen((o) => !o)}
              aria-label={mobileOpen ? 'Close menu' : 'Open menu'}
              aria-expanded={mobileOpen}
            >
              {mobileOpen
                ? <X size={20} strokeWidth={1.75} />
                : <Menu size={20} strokeWidth={1.75} />}
            </button>
          </div>
        </div>
      </nav>

      {/* Mobile menu */}
      {mobileOpen && (
        <div className="navbar-mobile" role="navigation" aria-label="Mobile navigation">
          <NavLink
            to="/"
            end
            className={getNavClass}
            onClick={() => setMobileOpen(false)}
          >
            Dashboard
          </NavLink>
          <NavLink
            to="/schedule-c"
            className={getNavClass}
            onClick={() => setMobileOpen(false)}
          >
            Schedule C
          </NavLink>
          <NavLink
            to="/settings"
            className={getNavClass}
            onClick={() => setMobileOpen(false)}
          >
            Settings
          </NavLink>
        </div>
      )}
    </>
  );
}
