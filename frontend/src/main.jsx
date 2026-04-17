import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import { ThemeProvider, CssBaseline } from "@mui/material";
import { registerSW } from "virtual:pwa-register";
import App from "./App";
import theme from "./theme";

// Регистрация Service Worker (авто-обновление)
registerSW({
  onNeedRefresh() {
    if (confirm("Доступна новая версия. Обновить?")) {
      window.location.reload();
    }
  },
  onOfflineReady() {
    console.log("Приложение готово к работе офлайн");
  },
});

ReactDOM.createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <BrowserRouter>
      <ThemeProvider theme={theme}>
        <CssBaseline />
        <App />
      </ThemeProvider>
    </BrowserRouter>
  </React.StrictMode>
);
