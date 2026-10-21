import { onRequestGet as __api_anket_js_onRequestGet } from "/opt/hh-izleyici/site/functions/api/anket.js"
import { onRequestPost as __api_anket_js_onRequestPost } from "/opt/hh-izleyici/site/functions/api/anket.js"

export const routes = [
    {
      routePath: "/api/anket",
      mountPath: "/api",
      method: "GET",
      middlewares: [],
      modules: [__api_anket_js_onRequestGet],
    },
  {
      routePath: "/api/anket",
      mountPath: "/api",
      method: "POST",
      middlewares: [],
      modules: [__api_anket_js_onRequestPost],
    },
  ]