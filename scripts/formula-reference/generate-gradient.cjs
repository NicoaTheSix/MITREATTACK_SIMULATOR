/* Execute reviewed official service + real Gradient class in development. Flow: README.md. */
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto');
const ts=require('typescript'), math=require('mathjs');
if(process.argv.length!==6)throw Error('Usage: node generate-gradient.cjs CASES SERVICE.ts GRADIENT.ts OUTPUT');
const [input,servicePath,gradientPath,output]=process.argv.slice(2).map(p=>path.resolve(p));
for(const p of [input,servicePath,gradientPath])console.error('Input file: '+p);
console.error('Output file: '+output);
console.error('[Gradient reference 1/3] Verify pinned runtimes and upstream bytes');
const packageVersion=name=>JSON.parse(fs.readFileSync(path.join(__dirname,'node_modules',name,'package.json'),'utf8')).version;
const versions={mathjs:math.version,typescript:ts.version,
 tinycolor2:packageVersion('tinycolor2'),tinygradient:packageVersion('tinygradient')};
if(JSON.stringify(Object.values(versions))!==JSON.stringify(['15.2.0','5.8.3','1.6.0','2.0.1']))throw Error('Reference dependency pin mismatch');
const hash=bytes=>crypto.createHash('sha256').update(bytes).digest('hex');
const service=fs.readFileSync(servicePath),gradient=fs.readFileSync(gradientPath);
if(hash(service)!=='b973f8ef52435c256f30b32766f4a40811ddf32ea35eced03b172df8e85576e9' ||
 hash(gradient)!=='4e48d69a52ffaa221a8aaeedba7c1b3d31948ff14e4af5e0fd15e4e9b0650ec3')throw Error('Upstream bytes differ from reviewed v5.3.2');
function compile(source){
 const result=ts.transpileModule(source,{compilerOptions:{target:ts.ScriptTarget.ES2020,
  module:ts.ModuleKind.CommonJS,esModuleInterop:true},reportDiagnostics:true});
 if(result.diagnostics.some(d=>d.category===ts.DiagnosticCategory.Error))throw Error('Invalid reference TypeScript');
 return result.outputText;
}
const gradientModule={};
new Function('require','exports',compile(gradient.toString('utf8')))(require,gradientModule);
const Gradient=gradientModule.Gradient;
class TechniqueVM {constructor(id){this.technique_tactic_union_id=id;this.score='';this.enabled=true;this.color='';}}
class ViewModel {
 constructor(){this.techniqueVMs=new Map();this.gradient=new Gradient();this.initializeScoresTo='';}
 hasTechniqueVM_id(id){return this.techniqueVMs.has(id);}
 getTechniqueVM_id(id){return this.techniqueVMs.get(id);}
 updateGradient(){this.gradient.updateGradient();}
}
const method='public layerOperation('+service.toString('utf8').split('public layerOperation(')[1].split('return newViewModel;')[0]+'return newViewModel;\n}';
const wrapper='export class ReferenceService {viewModels=[];dataService=null;getNonce(){return 0;}\n'+method+'\n}';
const serviceModule={};
new Function('exports','ViewModel','TechniqueVM','Gradient','evaluate','isBoolean','isNumber',compile(wrapper))(
 serviceModule,ViewModel,TechniqueVM,Gradient,math.evaluate,v=>typeof v==='boolean',v=>typeof v==='number');
// Only these two hash-pinned official sources are executed, never application input code.
const fixture=JSON.parse(fs.readFileSync(input,'utf8')),results=[];
for(const [index,test] of fixture.cases.entries()){
 const sources=test.sources.map(source=>{
  const vm=new ViewModel();
  if(source.gradient)vm.gradient.deserialize(JSON.stringify(source.gradient));
  for(const cell of fixture.matrix)vm.techniqueVMs.set(cell.techniqueID+'^'+cell.tactic,new TechniqueVM(cell.techniqueID+'^'+cell.tactic));
  for(const row of source.rows)for(const cell of fixture.matrix){
   if(cell.techniqueID!==row.techniqueID || ('tactic' in row && row.tactic!==cell.tactic))continue;
   const id=cell.techniqueID+'^'+cell.tactic,tvm=new TechniqueVM(id);
   if('score' in row)tvm.score=String(row.score);
   if('enabled' in row)tvm.enabled=row.enabled;
   if('color' in row)tvm.color=row.color;
   vm.techniqueVMs.set(id,tvm);
  }
  return vm;
 });
 const variables=new Map();
 for(const name of test.expression.toLowerCase().match(/\b[a-z]\b/g)||[]){
  const vm=sources[name.charCodeAt(0)-97];if(!vm)throw Error('Unavailable source '+name);variables.set(name,vm);
 }
 const settings={scoreExpression:test.expression,domain:'fixture'};
 for(const [field,key] of Object.entries({gradient:'gradientVM',enabled:'enabledVM',color:'coloringVM'})){
  const alias=test.inheritance[field];if(alias)settings[key]=sources[alias.charCodeAt(0)-97];
 }
 const result=new serviceModule.ReferenceService().layerOperation(variables,'Reference',settings);
 const cells=fixture.matrix.map(cell=>{
  const tvm=result.techniqueVMs.get(cell.techniqueID+'^'+cell.tactic)||{score:result.initializeScoresTo,enabled:true,color:''};
  const score=tvm.score===''?null:Number(tvm.score);
  if(score!==null && (!Number.isFinite(score)||Math.abs(score)>1e300))throw Error('Out-of-bound fixture');
  return {...cell,score,enabled:tvm.enabled,color:tvm.color,
   officialRGB:result.gradient.getHexColor(tvm.score)||null};
 });
 results.push({name:test.name,gradient:JSON.parse(result.gradient.serialize()),cells});
 console.error('[Gradient reference 2/3] '+(index+1)+'/'+fixture.cases.length+' '+test.name);
}
fs.writeFileSync(output,JSON.stringify({versions,inputSHA256:hash(fs.readFileSync(input)),
 upstream:[{path:'nav-app/src/app/services/viewmodels.service.ts',sha256:hash(service)},
 {path:'nav-app/src/app/classes/gradient.ts',sha256:hash(gradient)}],
 navigator:'https://github.com/mitre-attack/attack-navigator/tree/v5.3.2',
 method:'Exact layerOperation and Gradient class transpiled by TypeScript; minimal score/enabled ViewModel/TechniqueVM stubs.',
 renderer:'officialRGB is the actual 100-sample RGB renderer output; native continuous RGBA rendering is separately tested, not asserted pixel-identical.',
 results},null,2)+'\n');
console.error('[Gradient reference 3/3] Published '+results.length+' gradients / '+results.length*fixture.matrix.length+' cells');
