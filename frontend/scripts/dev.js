import { spawn } from "node:child_process";
import { request } from "node:http";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const frontendRoot = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const projectRoot = resolve(frontendRoot, "..");
const python = process.env.PYTHON || "python";
let stopping = false;
let apiProcess;
let viteProcess;

function stop(code = 0) {
  if (stopping) return;
  stopping = true;
  process.exitCode = code;
  for (const child of [viteProcess, apiProcess]) {
    if (child && child.exitCode === null) child.kill();
  }
}

function start(command, args, cwd, label) {
  const child = spawn(command, args, { cwd, stdio: "inherit", env: process.env });
  child.on("error", (error) => {
    console.error(`[dev] Could not start ${label}: ${error.message}`);
    stop(1);
  });
  child.on("exit", (code, signal) => {
    if (!stopping) {
      console.error(`[dev] ${label} exited (${signal || code}). Stopping the other service.`);
      stop(code || 1);
    }
  });
  return child;
}

function apiIsReady() {
  return new Promise((resolveRequest) => {
    const req = request("http://127.0.0.1:8000/api/health", { timeout: 1000 }, (res) => {
      res.resume();
      resolveRequest(res.statusCode === 200);
    });
    req.on("timeout", () => req.destroy());
    req.on("error", () => resolveRequest(false));
    req.end();
  });
}

async function main() {
  process.on("SIGINT", () => stop());
  process.on("SIGTERM", () => stop());

  if (!(await apiIsReady())) {
    console.log("[dev] Starting FastAPI on http://127.0.0.1:8000");
    apiProcess = start(
      python,
      ["-m", "uvicorn", "backend.main:app", "--host", "127.0.0.1", "--port", "8000"],
      projectRoot,
      "API",
    );

    const deadline = Date.now() + 60_000;
    while (!stopping && Date.now() < deadline) {
      if (apiProcess.exitCode !== null) return;
      if (await apiIsReady()) break;
      await new Promise((resolveDelay) => setTimeout(resolveDelay, 500));
    }

    if (stopping) return;
    if (!(await apiIsReady())) {
      console.error("[dev] API did not become ready. Check Python dependencies and port 8000.");
      stop(1);
      return;
    }
  } else {
    console.log("[dev] Reusing API already available on port 8000.");
  }

  console.log("[dev] API ready. Starting Vite.");
  viteProcess = start(
    process.execPath,
    [resolve(frontendRoot, "node_modules", "vite", "bin", "vite.js")],
    frontendRoot,
    "Vite",
  );
}

main().catch((error) => {
  console.error(`[dev] Startup failed: ${error.message}`);
  stop(1);
});
