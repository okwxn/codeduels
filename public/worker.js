importScripts('https://cdn.jsdelivr.net/pyodide/v0.26.4/full/pyodide.js');

const ready = (async () => {
  const [py, harness] = await Promise.all([
    loadPyodide(),
    fetch('/judge/harness.py').then((r) => r.text()),
  ]);
  py.runPython(harness); // defines run_judge_json in the Pyodide globals
  return py;
})();

onmessage = async (e) => {
  const { code, entry, tests, checker } = e.data;
  try {
    const py = await ready;
    const run = py.globals.get('run_judge_json');
    try {
      postMessage(JSON.parse(run(code, entry, JSON.stringify(tests), checker || '')));
    } finally {
      run.destroy();
    }
  } catch (err) {
    postMessage({ error: String(err).slice(-400) });
  }
};