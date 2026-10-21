/* Development-only pinned reference runner. Workflow: README.md. */
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const math = require('mathjs');
if (process.argv.length !== 4) throw Error('Usage: node generate.cjs INPUT.json OUTPUT.json');
const input = path.resolve(process.argv[2]), output = path.resolve(process.argv[3]);
console.error('Input file: ' + input);
console.error('Output file: ' + output);
console.error('[Reference 1/3] Checking pinned runtime and trusted fixtures');
if (math.version !== '15.2.0') throw Error('Reference runtime must be mathjs 15.2.0');
const cases = JSON.parse(fs.readFileSync(input, 'utf8'));
const scopes = [{a:80,b:60,c:0}, {a:-2.5,b:0,c:3}, {a:.1,b:.2,c:.3}];
const results = [];
for (const [index, test] of cases.entries()) {
  for (const scores of scopes) {
    const source = test.syntax === 'navigator' ? test.expression.toLowerCase() : test.expression;
    let result;
    try {
      const value = math.evaluate(source, scores);
      if (typeof value === 'boolean') result = {kind:'finite', value:Number(value)};
      else if (typeof value === 'number' && Number.isFinite(value) && Math.abs(value) <= 1e300)
        result = {kind:'finite', value};
      else result = {kind:'outside', type:math.typeOf(value)};
    } catch (error) { result = {kind:'error', message:error.message}; }
    results.push({...test, scores, result});
  }
  if ((index+1)%20 === 0 || index+1 === cases.length)
    console.error('[Reference 2/3] Evaluated ' + (index+1) + '/' + cases.length + ' expressions');
}
const report = {
  runtime:'mathjs', version:math.version,
  navigator:'https://github.com/mitre-attack/attack-navigator/tree/v5.3.2',
  pipeline:'Navigator lowercases the complete expression before math.evaluate; studio root cases use raw mathjs.',
  upstream: [
    {url:'https://raw.githubusercontent.com/mitre-attack/attack-navigator/v5.3.2/nav-app/package.json',
     sha256:'3e24d79d482f628d7ab706afae6d56e52b3c2f695acd4280604193c4d89ae3c9'},
    {url:'https://raw.githubusercontent.com/mitre-attack/attack-navigator/v5.3.2/nav-app/src/app/services/viewmodels.service.ts',
     sha256:'b973f8ef52435c256f30b32766f4a40811ddf32ea35eced03b172df8e85576e9'}],
  inputSHA256:crypto.createHash('sha256').update(fs.readFileSync(input)).digest('hex'),
  config:math.config(), results
};
fs.writeFileSync(output, JSON.stringify(report,null,2)+'\n');
console.error('[Reference 3/3] Published ' + results.length + ' reference cells');
