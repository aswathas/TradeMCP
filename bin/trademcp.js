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
 *
 * The build also runs from the package's postinstall hook, so a global
 * install is already warm by the time a client starts the server:
 *
 *     npm i -g @aswathas/trademcp
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
const MIN_PYTHON = [3, 11];

const say = (message) => process.stderr.write(`${message}\n`);

function venvPython() {
  return process.platform === "win32"
    ? path.join(VENV_DIR, "Scripts", "python.exe")
    : path.join(VENV_DIR, "bin", "python");
}

function pythonVersion(candidate) {
  const probe = spawnSync(
    candidate,
    ["-c", "import sys; print('%d.%d' % sys.version_info[:2])"],
    { encoding: "utf8" }
  );
  if (probe.error || probe.status !== 0) return null;
  const match = /(\d+)\.(\d+)/.exec(probe.stdout || "");
  if (!match) return null;
  return [Number(match[1]), Number(match[2])];
}

function atLeast(version, floor) {
  return version[0] > floor[0] || (version[0] === floor[0] && version[1] >= floor[1]);
}

/* Every interpreter on PATH, so the best one wins. `py` on Windows picks
   whatever the launcher considers current, which may be Python 2. */
function findPython() {
  const wanted = process.env.TRADEMCP_PYTHON
    ? [process.env.TRADEMCP_PYTHON]
    : process.platform === "win32"
      ? ["py", "python", "python3"]
      : ["python3", "python"];

  const found = [];
  for (const candidate of wanted) {
    const version = pythonVersion(candidate);
    if (version) found.push({ candidate, version });
  }
  if (!found.length) return null;

  const usable = found.filter((entry) => atLeast(entry.version, MIN_PYTHON));
  const pool = usable.length ? usable : found;
  pool.sort((a, b) => b.version[0] - a.version[0] || b.version[1] - a.version[1]);
  return pool[0];
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

function environmentReady() {
  return fs.existsSync(STAMP_FILE) && fs.existsSync(venvPython());
}

function buildEnvironment(python) {
  const created = spawnSync(python.candidate, ["-m", "venv", VENV_DIR], { encoding: "utf8" });
  if (created.status !== 0) {
    say(
      "trademcp: could not create a virtualenv. On Debian/Ubuntu install python3-venv.\n" +
        (created.stderr || "").trim()
    );
    return false;
  }

  const target = venvPython();
  const installed = spawnSync(
    target,
    ["-m", "pip", "install", "--quiet", "--no-input", "--disable-pip-version-check", ...DEPS],
    { encoding: "utf8" }
  );
  if (installed.status !== 0) {
    say(
      "trademcp: dependency install failed. Check your network and proxy settings.\n" +
        (installed.stderr || "").trim()
    );
    return false;
  }

  fs.writeFileSync(STAMP_FILE, new Date().toISOString());
  return true;
}

function ensureEnvironment(quiet) {
  if (environmentReady()) return true;

  const python = findPython();
  if (!python) {
    say(
      "trademcp: no Python found on this machine.\n" +
        "trademcp: install Python 3.11 or newer from https://www.python.org/downloads/\n" +
        "trademcp: or set TRADEMCP_PYTHON to the interpreter and try again."
    );
    return false;
  }
  if (!atLeast(python.version, MIN_PYTHON)) {
    say(
      `trademcp: ${python.candidate} is Python ${python.version.join(".")}.\n` +
        `trademcp: TradeMCP needs Python ${MIN_PYTHON.join(".")} or newer.\n` +
        "trademcp: set TRADEMCP_PYTHON to a newer interpreter and try again."
    );
    return false;
  }

  if (!takeLock()) {
    if (environmentReady()) return true;
    say("trademcp: timed out waiting for the first-run setup. Try again.");
    return false;
  }
  try {
    if (!quiet) {
      say(
        `trademcp: first run - building the Python environment with ${python.candidate} ` +
          `(Python ${python.version.join(".")}). This happens once and takes about half a minute.`
      );
    }
    return buildEnvironment(python);
  } finally {
    releaseLock();
  }
}

function main() {
  if (process.argv.includes("--version")) {
    process.stdout.write(`${require("../package.json").version}\n`);
    return;
  }

  /* postinstall: build the environment now, so the first MCP start is fast.
     Never fail the install here - the launcher reports the real problem. */
  if (process.argv.includes("--setup")) {
    if (ensureEnvironment(true)) say("trademcp: environment ready.");
    else say("trademcp: could not prepare the environment. The server will report why on start.");
    return;
  }

  if (process.argv.includes("--selftest")) {
    if (!ensureEnvironment(true)) {
      say("trademcp: selftest failed - no environment.");
      process.exit(1);
    }
    const probe = spawnSync(venvPython(), ["-c", "import trademcp; print(trademcp.__name__)"], {
      encoding: "utf8",
      env: { ...process.env, PYTHONPATH: SRC_DIR },
    });
    say(probe.status === 0 ? `ok: ${probe.stdout.trim()}` : `failed: ${probe.stderr.trim()}`);
    process.exit(probe.status === 0 ? 0 : 1);
  }

  if (!ensureEnvironment(false)) process.exit(1);

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
