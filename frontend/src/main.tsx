import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import WebFont from "webfontloader";
import { AppRoutes } from "./App";
import "./styles.css";

WebFont.load({
  google: {
    families: ["Merriweather:400,700", "Public Sans:400,500,600,700"]
  }
});

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <BrowserRouter>
      <AppRoutes />
    </BrowserRouter>
  </React.StrictMode>,
);
