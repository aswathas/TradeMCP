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
 *
 * Modes:
 *
 *     (none)          run the server on stdio
 *     --version       print the package version
 *     --setup         build the Python environment and exit
 *     --selftest      import check only (no session)
 *     --smoke         a real MCP session: initialize + tools/list
 *     --smoke-client  the same session, driven by the Python MCP client
 *
 * The smoke modes need no network for the session itself; add --smoke-call to
 * also call a tool, which does.
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
/* mcp is capped below the next major on purpose: the server imports the
   version-specific path `mcp.server.mcpserver`, and a future major that
   renames it would break every fresh install. */
const DEPS = ["mcp>=2.3,<3", "httpx>=0.27"];
const MIN_PYTHON = [3, 11];

/* A setup lock older than this counts as abandoned. The first-run build takes
   about half a minute, so five minutes means the owner is gone (killed
   mid-build) or wedged. */
const LOCK_STALE_MS = 5 * 60 * 1000;
/* How long a launcher waits for another process to finish the build. */
const LOCK_WAIT_MS = 10 * 60 * 1000;

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

/* Is the process behind a lock still running? On Windows `process.kill(pid, 0)`
   throws ESRCH for a PID that does not exist and EPERM for a PID owned by
   another user - which still means the process is alive. */
function processAlive(pid) {
  if (!Number.isInteger(pid) || pid <= 0) return false;
  try {
    process.kill(pid, 0);
    return true;
  } catch (error) {
    return error.code === "EPERM";
  }
}

function readLock() {
  let content;
  let stat;
  try {
    content = fs.readFileSync(LOCK_FILE, "utf8");
    stat = fs.statSync(LOCK_FILE);
  } catch {
    return { state: "gone" };
  }
  let owner = null;
  try {
    owner = JSON.parse(content);
  } catch {
    owner = null;
  }
  return { state: "held", owner, mtimeMs: stat.mtimeMs };
}

/* A lock is stale when the process that took it is gone, or when it is older
   than LOCK_STALE_MS - a killed first-run build leaves the file behind with
   no stamp, and without this check the launcher would block for ten minutes
   on every later run. */
function lockIsStale(lock) {
  if (lock.state === "gone") return false;
  const startedAt = lock.owner && Number.isFinite(lock.owner.ts) ? lock.owner.ts : lock.mtimeMs;
  const age = Date.now() - startedAt;
  if (lock.owner && Number.isInteger(lock.owner.pid) && !processAlive(lock.owner.pid)) return true;
  return age > LOCK_STALE_MS;
}

function clearStaleLock() {
  try {
    fs.unlinkSync(LOCK_FILE);
    return true;
  } catch {
    return false;
  }
}

/* Two `npx` invocations can race on the first run. One takes the lock and
   builds the environment; the other waits for the stamp. The lock records the
   owning PID and a timestamp so an abandoned lock can be reclaimed instead of
   blocking the launcher forever. */
function takeLock() {
  fs.mkdirSync(CACHE_DIR, { recursive: true });
  const deadline = Date.now() + LOCK_WAIT_MS;
  while (Date.now() < deadline) {
    try {
      const handle = fs.openSync(LOCK_FILE, "wx");
      try {
        fs.writeSync(handle, JSON.stringify({ pid: process.pid, ts: Date.now() }));
      } finally {
        fs.closeSync(handle);
      }
      return true;
    } catch (error) {
      if (error.code !== "EEXIST") {
        /* Not a lock conflict (permissions, read-only home, ...). Nothing we
           can do about it here - the caller reports the failure. */
        return false;
      }
      const lock = readLock();
      if (lockIsStale(lock)) {
        say("trademcp: found an abandoned setup lock - clearing it and continuing.");
        clearStaleLock();
        continue;
      }
      if (fs.existsSync(STAMP_FILE)) return false;
      sleep(1000);
    }
  }
  return false;
}

/* Only release the lock if it is still ours - a lock that was reclaimed from
   a stale owner belongs to somebody else now. */
function releaseLock() {
  const lock = readLock();
  if (lock.state === "held" && lock.owner && lock.owner.pid !== process.pid) return;
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

/* --- MCP session smoke test ------------------------------------------------
 *
 * A real client session over stdio: initialize -> notifications/initialized
 * -> tools/list, and optionally one tools/call.
 *
 * The tool call needs the network (it hits the quote provider), so it is
 * OPTIONAL and off by default. The session shape - initialize plus a
 * non-empty tool list - is what the test asserts, and that needs no network.
 * Pass --smoke-call (or set TRADEMCP_SMOKE_CALL=1) to include the call.
 */
const SMOKE_TIMEOUT_MS = 60 * 1000;

function runSmoke(callTool) {
  return new Promise((resolve) => {
    /* Start the server the way an MCP client does: through this launcher. */
    const child = spawn(process.execPath, [__filename], {
      env: { ...process.env },
      stdio: ["pipe", "pipe", "pipe"],
    });

    const pending = new Map();
    let nextId = 1;
    let buffer = "";
    let settled = false;

    const timer = setTimeout(() => {
      fail(`timed out after ${SMOKE_TIMEOUT_MS}ms waiting for the server`);
    }, SMOKE_TIMEOUT_MS);

    function finish(code, message) {
      if (settled) return;
      settled = true;
      clearTimeout(timer);
      if (message) say(message);
      try {
        child.stdin.end();
      } catch {
        /* the pipe may already be gone */
      }
      try {
        child.kill();
      } catch {
        /* already dead */
      }
      resolve(code);
    }

    function fail(reason) {
      finish(1, `trademcp: smoke test failed - ${reason}`);
    }

    function pass(summary) {
      finish(0, `trademcp: smoke test ok - ${summary}`);
    }

    function send(message) {
      try {
        child.stdin.write(`${JSON.stringify(message)}\n`);
      } catch {
        /* the server closed the pipe - the exit handler reports it */
      }
    }

    function request(method, params) {
      const id = nextId++;
      return new Promise((resolveRequest, rejectRequest) => {
        pending.set(id, { resolveRequest, rejectRequest });
        send({ jsonrpc: "2.0", id, method, params: params || {} });
      });
    }

    child.stdout.on("data", (chunk) => {
      buffer += chunk.toString("utf8");
      let newline = buffer.indexOf("\n");
      while (newline >= 0) {
        const line = buffer.slice(0, newline).trim();
        buffer = buffer.slice(newline + 1);
        newline = buffer.indexOf("\n");
        if (!line) continue;
        let message;
        try {
          message = JSON.parse(line);
        } catch {
          continue; /* not protocol traffic */
        }
        if (message.id === undefined || !pending.has(message.id)) continue;
        const { resolveRequest, rejectRequest } = pending.get(message.id);
        pending.delete(message.id);
        if (message.error) rejectRequest(new Error(message.error.message || "JSON-RPC error"));
        else resolveRequest(message.result);
      }
    });

    child.stderr.on("data", (chunk) => process.stderr.write(chunk));
    child.stdin.on("error", () => {
      /* the server may close stdin before we finish; the exit handler reports it */
    });
    child.on("error", (error) => fail(`could not start the server: ${error.message}`));
    child.on("exit", (code) => {
      if (!settled) fail(`the server exited early with code ${code}`);
    });

    (async () => {
      try {
        const init = await request("initialize", {
          protocolVersion: "2025-06-18",
          capabilities: {},
          clientInfo: { name: "trademcp-smoke", version: "0.1.0" },
        });
        const info = init && init.serverInfo;
        if (!info || info.name !== "trademcp") {
          throw new Error(`unexpected server handshake: ${JSON.stringify(info)}`);
        }

        send({ jsonrpc: "2.0", method: "notifications/initialized", params: {} });

        const listing = await request("tools/list");
        const tools = (listing && listing.tools) || [];
        if (!tools.length) throw new Error("the server listed no tools");
        if (!tools.some((tool) => tool.name === "trademcp_get_quote")) {
          throw new Error("trademcp_get_quote is missing from the tool list");
        }

        if (callTool) {
          const result = await request("tools/call", {
            name: "trademcp_get_quote",
            arguments: { symbol: "RELIANCE" },
          });
          const text = result && result.content && result.content[0] && result.content[0].text;
          if (!text || String(text).startsWith("Error:")) {
            throw new Error(`the tool call failed: ${String(text).slice(0, 200)}`);
          }
        }

        pass(`${info.name} v${info.version}, ${tools.length} tools over stdio`);
      } catch (error) {
        fail(error.message);
      }
    })();
  });
}

/* Runs the Python-client smoke script (scripts/smoke_npx.py) inside the
   launcher's virtualenv. It is a repo-only script, not part of the
   published package. */
function runSmokeClient(callTool) {
  const script = path.join(PKG_ROOT, "scripts", "smoke_npx.py");
  if (!fs.existsSync(script)) {
    say(`trademcp: ${script} is not in this install - nothing to smoke test.`);
    return 1;
  }
  const probe = spawnSync(venvPython(), callTool ? [script, "--call"] : [script], {
    stdio: "inherit",
    env: { ...process.env, PYTHONPATH: SRC_DIR },
  });
  return probe.status === null || probe.status !== 0 ? 1 : 0;
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

  /* A real MCP session over stdio: initialize, initialized, tools/list. */
  if (process.argv.includes("--smoke")) {
    if (!ensureEnvironment(true)) {
      say("trademcp: smoke test failed - no environment.");
      process.exit(1);
    }
    const callTool =
      process.argv.includes("--smoke-call") || process.env.TRADEMCP_SMOKE_CALL === "1";
    runSmoke(callTool).then((code) => process.exit(code));
    return;
  }

  /* The same session, driven by the official Python MCP client. */
  if (process.argv.includes("--smoke-client")) {
    if (!ensureEnvironment(true)) {
      say("trademcp: smoke test failed - no environment.");
      process.exit(1);
    }
    const callTool =
      process.argv.includes("--smoke-call") || process.env.TRADEMCP_SMOKE_CALL === "1";
    process.exit(runSmokeClient(callTool));
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
