import { StrictMode } from "react";
import { createRoot } from "react-dom/client";

import App from "./App";
import { I18nProvider } from "./i18n";
import "./styles.css";
import "./bootstrap.css";
import "./shell.css";
import "./person-overview.css";
import "./family-meals.css";
import "./ingredient-catalogue.css";
import "./core-planning.css";
import "./pantry-shopping.css";
import "./recommendation-planner.css";
import { ThemeProvider } from "./theme";

const root = document.getElementById("root");
if (root === null) {
  throw new Error("NutriFlow web root element was not found.");
}

createRoot(root).render(
  <StrictMode>
    <ThemeProvider>
      <I18nProvider>
        <App />
      </I18nProvider>
    </ThemeProvider>
  </StrictMode>,
);