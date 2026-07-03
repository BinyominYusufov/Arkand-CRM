import { setupServer } from "msw/node";

/** MSW-сервер для компонентных тестов; хэндлеры добавляются per-test
 *  через server.use(http.get("/api/v1/...", ...)). */
export const server = setupServer();
