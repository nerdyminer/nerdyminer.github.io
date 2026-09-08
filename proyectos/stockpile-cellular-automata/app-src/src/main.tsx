/** Punto de entrada del reporte. */

import { StrictMode } from "react";
import { createRoot } from "react-dom/client";

import App from "./App";
import "./styles.css";

const container = document.getElementById("root");

if (!container) {
  throw new Error("no se encontro el contenedor raiz del reporte");
}

createRoot(container).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
