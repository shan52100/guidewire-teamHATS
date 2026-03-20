import React from "react";
import { Routes, Route } from "react-router-dom";
import Navbar from "./components/Navbar";
import Dashboard from "./pages/Dashboard";
import Claims from "./pages/Claims";
import FraudQueue from "./pages/FraudQueue";
import ZoneMap from "./pages/ZoneMap";

function App() {
  return (
    <div className="app-layout">
      <Navbar />
      <main className="main-content">
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/claims" element={<Claims />} />
          <Route path="/fraud" element={<FraudQueue />} />
          <Route path="/zones" element={<ZoneMap />} />
        </Routes>
      </main>
    </div>
  );
}

export default App;
