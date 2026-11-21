// Local-only HTTP signature fixture for the Windows deployment process test.
// Does not load application code or connect to a database.
const http = require("node:http");
const port = Number(process.argv[2] || 5173);
const server = http.createServer((request, response) => {
  if (request.url === "/@vite/client") {
    response.writeHead(200, {"Content-Type": "application/javascript"});
    response.end("/* vite client smoke fixture */\nexport const vite = true;\n");
    return;
  }
  if (request.url === "/") {
    response.writeHead(200, {"Content-Type": "text/html"});
    response.end("<!doctype html><title>NutriFlow AI</title><div>smoke fixture</div>");
    return;
  }
  response.writeHead(404);
  response.end("Not found");
});
server.listen(port, "127.0.0.1");
