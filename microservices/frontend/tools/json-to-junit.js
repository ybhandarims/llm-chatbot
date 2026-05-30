const fs = require('fs');
const path = require('path');

function safeGetTests(obj) {
  if (!obj) return [];
  if (Array.isArray(obj)) return obj;
  if (Array.isArray(obj.tests)) return obj.tests;
  if (Array.isArray(obj.suites)) return obj.suites;
  // fallback: attempt to collect from properties
  return [];
}

function escapeXml(s) {
  return String(s)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/\"/g, '&quot;')
    .replace(/'/g, '&apos;');
}

function toJUnit(jsonPath, outPath) {
  if (!fs.existsSync(jsonPath)) {
    console.error('JSON report not found:', jsonPath);
    process.exitCode = 1;
    return;
  }
  const raw = fs.readFileSync(jsonPath, 'utf8');
  let obj;
  try {
    obj = JSON.parse(raw);
  } catch (e) {
    console.error('Failed to parse JSON report:', e.message);
    process.exitCode = 1;
    return;
  }

  const tests = safeGetTests(obj);
  // Some Node JSON reporter outputs an object with "tests" containing test objects
  // We will fallback to searching for any nodes with a "name" and "status" property.
  let entries = tests.filter(t => t && (t.name || t.title));
  if (entries.length === 0) {
    // attempt to find tests in nested structures
    const all = [];
    function walk(o) {
      if (!o || typeof o !== 'object') return;
      if (o.name && o.status) {
        all.push(o);
      }
      for (const k of Object.keys(o)) walk(o[k]);
    }
    walk(obj);
    entries = all;
  }

  // If still empty, create a single test summary
  if (entries.length === 0) {
    const passed = obj && obj.pass || 0;
    const failed = obj && obj.fail || 0;
    const total = (passed || 0) + (failed || 0);
    const xml = `<?xml version="1.0" encoding="UTF-8"?>\n<testsuites>\n  <testsuite name="node-tests" tests="${total}" failures="${failed}">\n    <testcase classname="node" name="summary"/>\n  </testsuite>\n</testsuites>`;
    fs.mkdirSync(path.dirname(outPath), { recursive: true });
    fs.writeFileSync(outPath, xml, 'utf8');
    console.log('Wrote JUnit XML summary to', outPath);
    return;
  }

  let failures = 0;
  let xml = '<?xml version="1.0" encoding="UTF-8"?>\n<testsuites>\n';
  xml += `  <testsuite name="node-tests" tests="${entries.length}" failures="0">\n`;

  for (const e of entries) {
    const name = e.name || e.title || 'unnamed';
    const status = e.status || (e.ok ? 'pass' : 'fail');
    const duration = e.duration != null ? Number(e.duration) : 0;
    xml += `    <testcase classname="node" name="${escapeXml(name)}" time="${(duration/1000).toFixed(3)}">`;
    if (status !== 'pass' && status !== 'ok' && status !== 'success') {
      failures += 1;
      const msg = e.error && (e.error.message || e.error) || (e.reason || 'failed');
      xml += `\n      <failure>${escapeXml(msg)}</failure>\n    `;
    }
    xml += `</testcase>\n`;
  }

  // close testsuite, update failures
  xml = xml.replace('failures="0"', `failures="${failures}"`);
  xml += '  </testsuite>\n</testsuites>\n';

  fs.mkdirSync(path.dirname(outPath), { recursive: true });
  fs.writeFileSync(outPath, xml, 'utf8');
  console.log('Wrote JUnit XML to', outPath, ' (failures=', failures, ')');
}

if (require.main === module) {
  const args = process.argv.slice(2);
  const jsonPath = args[0] || path.join(process.cwd(), 'reports', 'frontend-tests.json');
  const outPath = args[1] || path.join(process.cwd(), 'reports', 'frontend-tests.xml');
  toJUnit(jsonPath, outPath);
}

module.exports = { toJUnit };
