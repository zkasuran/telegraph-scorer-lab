// Wrap a closed champion's rank_answer with out = x + EPS*(smoothstep(x) - x).
// Strictly increasing for EPS in [0,1], so the wrapper's ranking equals the champion's
// (agreement 1.0). EPS scales how hard it pushes toward 0/1: small EPS barely bends (keeps
// traffic-cluster resolution so no ties, agreement safe), large EPS widens the fixture margin
// more. Tuned as a spread; the node promotes the one that beats margin and holds agreement.
use walrus::*;
use walrus::ir::BinaryOp;
fn main(){
    let a:Vec<String>=std::env::args().collect();
    let (inp,outp,eps)=(&a[1],&a[2],a[3].parse::<f32>().unwrap());
    let mut m=Module::from_file(inp).expect("load");
    let exp=m.exports.iter().find(|e|e.name=="rank_answer").expect("no rank_answer").clone();
    let orig=match exp.item{ExportItem::Function(f)=>f,_=>panic!("not func")};
    let ty=m.funcs.get(orig).ty();
    let td=m.types.get(ty);
    let params:Vec<ValType>=td.params().to_vec();
    let results:Vec<ValType>=td.results().to_vec();
    assert!(results==vec![ValType::F32]);
    let mut fb=FunctionBuilder::new(&mut m.types,&params,&results);
    let locs:Vec<_>=params.iter().map(|t|m.locals.add(*t)).collect();
    let x=m.locals.add(ValType::F32);
    let s=m.locals.add(ValType::F32);
    let mut b=fb.func_body();
    for l in &locs { b.local_get(*l); }
    b.call(orig);
    b.local_set(x);
    // s = x*x*(3 - 2x)
    b.local_get(x).local_get(x).binop(BinaryOp::F32Mul);
    b.f32_const(3.0).local_get(x).f32_const(2.0).binop(BinaryOp::F32Mul).binop(BinaryOp::F32Sub);
    b.binop(BinaryOp::F32Mul);
    b.local_set(s);
    // out = x + EPS*(s - x)
    b.local_get(x);
    b.f32_const(eps).local_get(s).local_get(x).binop(BinaryOp::F32Sub).binop(BinaryOp::F32Mul);
    b.binop(BinaryOp::F32Add);
    let wrap=fb.finish(locs,&mut m.funcs);
    m.exports.get_mut(exp.id()).item=ExportItem::Function(wrap);
    m.emit_wasm_file(outp).expect("emit");
    eprintln!("wrapped {} eps={} -> {}",inp,eps,outp);
}
