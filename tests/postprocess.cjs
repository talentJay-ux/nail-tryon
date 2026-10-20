const assert=require('node:assert/strict');
const fs=require('node:fs');
const {decodeNails}=require('../scripts/postprocess.js');
function tensor(rows){
  const data=new Float32Array(37*rows.length);
  rows.forEach((row,i)=>row.forEach((v,c)=>data[c*rows.length+i]=v));
  return {dims:[1,37,rows.length],data};
}
const row=(cx,cy,w,h,score,co=1)=>[cx,cy,w,h,score,co,...Array(31).fill(0)];
const data=new Float32Array(32*160*160);data.fill(12,0,160*160);
const proto={dims:[1,32,160,160],data};
const meta={width:1200,height:800,resizedW:640,resizedH:427,padX:0,padY:106};
const decoded=decodeNails(tensor([row(160,240,80,120,.9),row(162,241,80,120,.8),row(480,280,60,80,.85),row(320,300,100,100,.29)]),proto,meta);
assert.equal(decoded.length,2,'class confidence filtering and instance NMS');
assert.ok(Math.abs(decoded[0].mx-300)<4,'letterbox x mapped to original');
assert.ok(Math.abs(decoded[0].my-(240-106)*800/427)<4,'asymmetric letterbox padding removed');
assert.ok(Math.abs(decoded[0].uy)>.99,'PCA follows long mask axis');
for(const n of decoded) for(let y=0;y<n.mh;y++)for(let x=0;x<n.mw;x++)if(n.alpha[y*n.mw+x]){
 const nx=n.rx+(x+.5)*n.rw/n.mw,ny=n.ry+(y+.5)*n.rh/n.mh;
 assert.ok(nx>=n.box[0]&&nx<n.box[2]&&ny>=n.box[1]&&ny<n.box[3],'mask cropped inside detection, not prototype background');
}
assert.equal(decodeNails(tensor([row(160,240,80,120,.9,-1)]),proto,meta).length,0,'negative mask logits pass through sigmoid, no phantom nails');
assert.equal(decodeNails(tensor([]),proto,meta).length,0,'empty detection is valid');
assert.throws(()=>decodeNails({dims:[1,38,1],data:[]},proto,meta),/模型输出/);
const inline=fs.readFileSync(require('node:path').join(__dirname,'../index.html'),'utf8').match(/\/\* BEGIN DECODER \*\/\n([\s\S]*?)\/\* END DECODER \*\//)[1].trim();
const source=fs.readFileSync(require('node:path').join(__dirname,'../scripts/postprocess.js'),'utf8').replace(/\nif\(typeof module[^\n]+\n?$/,'').trim();
assert.equal(inline,source,'the tested decoder is exactly the decoder shipped to the Worker');
console.log('PASS: confidence, NMS, mask coefficients/sigmoid/crop, letterbox, PCA, empty results, embedded source');
