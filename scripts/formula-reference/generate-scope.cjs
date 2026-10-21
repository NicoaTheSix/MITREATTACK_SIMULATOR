/* Run the pinned official layerOperation with minimal data-model stubs. Flow: README.md. */
const fs=require('node:fs'), path=require('node:path'), crypto=require('node:crypto');
const math=require('mathjs');
if(process.argv.length!==5) throw Error('Usage: node generate-scope.cjs CASES.json OFFICIAL_SERVICE.ts OUTPUT.json');
const [input,upstream,output]=process.argv.slice(2).map(p=>path.resolve(p));
console.error('Input file: '+input); console.error('Input file: '+upstream); console.error('Output file: '+output);
console.error('[Scope reference 1/3] Verify pinned runtime and official method');
if(math.version!=='15.2.0') throw Error('Expected mathjs 15.2.0');
const raw=fs.readFileSync(upstream);
const hash=crypto.createHash('sha256').update(raw).digest('hex');
if(hash!=='b973f8ef52435c256f30b32766f4a40811ddf32ea35eced03b172df8e85576e9')
  throw Error('Official source does not match the reviewed v5.3.2 service');
let method=raw.toString('utf8').split('    public layerOperation(')[1];
method='function layerOperation('+method.split('return newViewModel;')[0]+'return newViewModel;\n}';
method=method.replace('scoreVariables: Map<string, ViewModel>, layerName: string, opSettings: any): ViewModel',
                      'scoreVariables, layerName, opSettings)')
 .replace('new Set<string>()','new Set()')
 .replace('let scoreValue: number;','let scoreValue;')
 .replace('function inherit(inheritVM: ViewModel, fieldName: string)','function inherit(inheritVM, fieldName)');
class TechniqueVM {constructor(id){this.technique_tactic_union_id=id; this.score='';this.enabled=true;}}
class ViewModel {
 constructor(){this.techniqueVMs=new Map();this.gradient={setGradientPreset(){}};this.initializeScoresTo='';}
 hasTechniqueVM_id(id){return this.techniqueVMs.has(id);}
 getTechniqueVM_id(id){return this.techniqueVMs.get(id);}
 updateGradient(){}
}
const operation=new Function('ViewModel','TechniqueVM','Gradient','evaluate','isBoolean','isNumber',
  method+';return layerOperation;')(ViewModel,TechniqueVM,function(){},math.evaluate,
  v=>typeof v==='boolean',v=>typeof v==='number');
// Only the hash-pinned, reviewed official source above is executed, never app input code.
const fixture=JSON.parse(fs.readFileSync(input,'utf8'));
const results=[];
for(const [index,test] of fixture.cases.entries()){
 const sources=test.sources.map(source=>{
  const vm=new ViewModel();
  for(const cell of fixture.matrix) vm.techniqueVMs.set(cell.techniqueID+'^'+cell.tactic,new TechniqueVM(cell.techniqueID+'^'+cell.tactic));
  for(const row of source.rows){
   for(const cell of fixture.matrix){
    if(cell.techniqueID!==row.techniqueID || (row.tactic && row.tactic!==cell.tactic))continue;
    const id=cell.techniqueID+'^'+cell.tactic, tvm=new TechniqueVM(id);
    if('score' in row) tvm.score=String(row.score);
    if('enabled' in row) tvm.enabled=row.enabled;
    vm.techniqueVMs.set(id,tvm);
   }
  }
  return vm;
 });
 const variables=new Map();
 for(const name of test.expression.toLowerCase().match(/\b[a-z]\b/g)||[]){
  const vm=sources[name.charCodeAt(0)-97];
  if(!vm)throw Error('Fixture references unavailable source '+name);
  variables.set(name,vm);
 }
 const result=operation.call({getNonce:()=>0,dataService:null,viewModels:[]},variables,'Reference',{scoreExpression:test.expression,domain:'fixture'});
 const cells=fixture.matrix.map(cell=>{
  const id=cell.techniqueID+'^'+cell.tactic;
  const tvm=result.techniqueVMs.get(id)||{score:result.initializeScoresTo,enabled:true};
  const score=tvm.score===''?null:Number(tvm.score);
  if(score!==null && (!Number.isFinite(score)||Math.abs(score)>1e300))throw Error('Fixture outside finite subset');
  return {...cell,score,enabled:tvm.enabled};
 });
 results.push({name:test.name,cells});
 console.error('[Scope reference 2/3] '+(index+1)+'/'+fixture.cases.length+' '+test.name);
}
fs.writeFileSync(output,JSON.stringify({runtime:'mathjs',version:math.version,
 serviceURL:'https://raw.githubusercontent.com/mitre-attack/attack-navigator/v5.3.2/nav-app/src/app/services/viewmodels.service.ts',
 serviceSHA256:hash,inputSHA256:crypto.createHash('sha256').update(fs.readFileSync(input)).digest('hex'),
 contextSources:[
  {path:'nav-app/src/app/classes/view-model.ts',sha256:'baa172f70e3a5b481870d6e75f3f98e09c3be4d0c8d3b970cffb2bcb85ba109c'},
  {path:'nav-app/src/app/classes/technique-vm.ts',sha256:'aea171b201e287efdf92233902ffeb2321a090c2862d4bc6cb308c4579062030'},
  {path:'nav-app/src/app/tabs/tabs.component.ts',sha256:'b5ff7b9830fd200c0cef9ab50060644b1b036fad6eab995d46238afb15dad55a'}],
 method:'Exact layerOperation with TypeScript annotations removed; score/enabled model stubs, post-load constant initialization.',
 results},null,2)+'\n');
console.error('[Scope reference 3/3] Published '+results.length*fixture.matrix.length+' reference cells');
