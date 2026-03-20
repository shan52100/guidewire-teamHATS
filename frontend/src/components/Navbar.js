import React from "react";
import { NavLink } from "react-router-dom";

const navItems = [
  { to: "/", label: "Dashboard" },
  { to: "/claims", label: "Claims" },
  { to: "/fraud", label: "Fraud Queue" },
  { to: "/zones", label: "Zones" },
];

export default function Navbar() {
  return (
    <nav className="navbar">
      <div className="navbar-brand">
        <span className="navbar-logo">IF</span>
        <span className="navbar-title">InsureFlow AI</span>
      </div>
      <ul className="navbar-links">
        {navItems.map((item) => (
          <li key={item.to}>
            <NavLink
              to={item.to}
              end={item.to === "/"}
              className={({ isActive }) =>
                `navbar-link ${isActive ? "navbar-link--active" : ""}`
              }
            >
              {item.label}
            </NavLink>
          </li>
        ))}
      </ul>
      <div className="navbar-actions">
        <span className="navbar-role">Admin</span>
      </div>
    </nav>
  );
}
