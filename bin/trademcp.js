#!/usr/bin/env node
"use strict";

/* TradeMCP launcher.
 *
 * The npm package carries the Python server. On first run it builds a small
 * virtualenv with the only two runtime dependencies (mcp, httpx) and then runs
 * the server on stdio, so an MCP client can point at it with one command:
 *
 *     npx -y @aswathas/trademcp
 *
 * Everything this script says goes to stderr. stdout belongs to the MCP
 * protocol, and a stray line there corrupts the session.
 */

const { spawn, spawnSync } = require("node:child_process");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");

const PKG_ROOT = path.resolve(__dirname, "..");
const SRC_DIR = path.join(PKG_ROOT, "src");
const CACHE_DIR = path.join(os.homedir(), ".cache", "trademcp-npm");
const VENV_DIR = path.join(CACHE_DIR, "venv");
const STAMP_FILE = path.join(CACHE_DIR, "deps.ok");
const LOCK_FILE = path.join(CACHE_DIR, "setup.lock");
const DEPS = ["mcp>=2.3", "httpx>=0.27"];

const say = (message) => process.stderr.write(`${message}\n`);

function venvPython() {
  return process.platform === "win32"
    ? path.join(VENV_DIR, "Scripts", "python.exe")
    : path.join(VENV_DIR, "bin", "python");
}

function findPython() {
  const wanted = process.env.TRADEMCP_PYTHON
    ? [process.env.TRADEMCP_PYTHON]
    : process.platform === "win32"
      ? ["py", "python", "python3"]
      : ["python3", "python"];
  for (const candidate of wanted) {
    const probe = spawnSync(candidate, ["--version"], { encoding: "utf8" });
    if (!probe.error && probe.status === 0) return candidate;
  }
  return null;
}

function sleep(ms) {
  Atomics.wait(new Int32Array(new SharedArrayBuffer(4)), 0, 0, ms);
}

/* Two `npx` invocations can race on the first run. One takes the lock and
   builds the environment; the other waits for the stamp. */
function takeLock() {
  fs.mkdirSync(CACHE_DIR, { recursive: true });
  for (let attempt = 0; attempt < 600; attempt += 1) {
    try {
      const handle = fs.openSync(LOCK_FILE, "wx");
      fs.closeSync(handle);
      return true;
    } catch {
      if (fs.existsSync(STAMP_FILE)) return false;
      sleep(1000);
    }
  }
  return false;
}

function releaseLock() {
  try {
    fs.unlinkSync(LOCK_FILE);
  } catch {
    /* already gone */
  }
}

function buildEnvironment() {
  const python = findPython();
  if (!python) {
    say(
      "trademcp: no Python 3.11+ found. Install Python from https://www.python.org/downloads/\n" +
        "trademcp: or point TRADEMCP_PYTHON at an interpreter and try again."
    );
    process.exit(1);
  }

  const created = spawnSync(python, ["-m", "venv", VENV_DIR], { encoding: "utf8" });
  if (created.status !== 0) {
    say(
      "trademcp: could not create a virtualenv. On Debian/Ubuntu install python3-venv.\n" +
        (created.stderr || "").trim()
    );
    process.exit(1);
  }

  const target = venvPython();
  const upgraded = spawnSync(target, ["-m", "pip", "install", "--quiet", "--upgrade", "pip"], {
    encoding: "utf8",
  });
  if (upgraded.status !== 0) {
    say("trademcp: pip could not be upgraded. Continuing with the bundled pip.");
  }

  const installed = spawnSync(target, ["-m", "pip", "install", "--quiet", ...DEPS], {
    encoding: "utf8",
  });
  if (installed.status !== 0) {
    say(`trademcp: dependency install failed.\n${(installed.stderr || "").trim()}`);
    process.exit(1);
  }

  fs.writeFileSync(STAMP_FILE, new Date().toISOString());
}

function ensureEnvironment() {
  if (fs.existsSync(STAMP_FILE) && fs.existsSync(venvPython())) return;
  if (!takeLock()) {
    if (fs.existsSync(STAMP_FILE) && fs.existsSync(venvPython())) return;
    say("trademcp: timed out waiting for the first-run setup. Try again.");
    process.exit(1);
  }
  try {
    buildEnvironment();
  } finally {
    releaseLock();
  }
}

function main() {
  if (process.argv.includes("--version")) {
    process.stdout.write(`${require("../package.json").version}\n`);
    return;
  }
  if (process.argv.includes("--selftest")) {
    ensureEnvironment();
    const probe = spawnSync(venvPython(), ["-c", "import trademcp; print(trademcp.__name__)"], {
      encoding: "utf8",
      env: { ...process.env, PYTHONPATH: SRC_DIR },
    });
    say(probe.status === 0 ? `ok: ${probe.stdout.trim()}` : `failed: ${probe.stderr.trim()}`);
    process.exit(probe.status === 0 ? 0 : 1);
  }

  ensureEnvironment();

  const child = spawn(venvPython(), ["-m", "trademcp"], {
    env: { ...process.env, PYTHONPATH: SRC_DIR },
    stdio: "inherit",
  });
  child.on("error", (error) => {
    say(`trademcp: could not start the server: ${error.message}`);
    process.exit(1);
  });
  child.on("exit", (code, signal) => {
    if (signal) process.exit(1);
    process.exit(code === null ? 1 : code);
  });
}

main();
