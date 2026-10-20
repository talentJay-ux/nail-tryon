/* Shared, dependency-free YOLOv8-seg decoder. Embedded into index.html by build.mjs. */
function decodeNails(det, proto, meta, confidence = .3) {
  const [batch, channels, count] = det.dims;
  const [pb, masks, ph, pw] = proto.dims;
  if (batch !== 1 || pb !== 1 || channels !== 5 + masks || masks !== 32)
    throw new Error('不支持的指甲模型输出');
  const d = det.data, p = proto.data, candidates = [];
  const {width, height, resizedW, resizedH, padX, padY, size = 640} = meta;
  const sx = width / resizedW, sy = height / resizedH;
  for (let i = 0; i < count; i++) {
    const score = d[4 * count + i];
    if (!Number.isFinite(score) || score < confidence) continue;
    const cx = d[i], cy = d[count + i], w = d[2 * count + i], h = d[3 * count + i];
    if (!(w > 0 && h > 0)) continue;
    const x1 = Math.max(padX, cx - w / 2), y1 = Math.max(padY, cy - h / 2);
    const x2 = Math.min(padX + resizedW, cx + w / 2), y2 = Math.min(padY + resizedH, cy + h / 2);
    if (x2 - x1 < 2 || y2 - y1 < 2) continue;
    candidates.push({id:i, score, x1, y1, x2, y2});
  }
  candidates.sort((a,b) => b.score - a.score);
  const keep = [], iou = (a,b) => {
    const intersection = Math.max(0,Math.min(a.x2,b.x2)-Math.max(a.x1,b.x1)) *
      Math.max(0,Math.min(a.y2,b.y2)-Math.max(a.y1,b.y1));
    return intersection / ((a.x2-a.x1)*(a.y2-a.y1)+(b.x2-b.x1)*(b.y2-b.y1)-intersection || 1);
  };
  // Bound work on very noisy images; never restrict detection to one or two hands.
  for (const c of candidates.slice(0,1000)) {
    if (keep.every(k => iou(c,k) < .45)) keep.push(c);
    if (keep.length === 30) break;
  }
  const out = [], plane = pw * ph;
  for (const b of keep) {
    const px1 = Math.max(0,Math.floor(b.x1 * pw / size)-1);
    const py1 = Math.max(0,Math.floor(b.y1 * ph / size)-1);
    const px2 = Math.min(pw,Math.ceil(b.x2 * pw / size)+1);
    const py2 = Math.min(ph,Math.ceil(b.y2 * ph / size)+1);
    const mw = px2-px1, mh = py2-py1, alpha = new Uint8Array(mw*mh);
    const points = [];
    for (let y=0;y<mh;y++) for (let x=0;x<mw;x++) {
      const px=px1+x, py=py1+y, nx=(px+.5)*size/pw, ny=(py+.5)*size/ph;
      if (nx<b.x1 || nx>=b.x2 || ny<b.y1 || ny>=b.y2) continue;
      let logit=0;
      for (let c=0;c<masks;c++) logit += d[(5+c)*count+b.id] * p[c*plane+py*pw+px];
      const probability=1/(1+Math.exp(-logit));
      alpha[y*mw+x]=Math.round(probability*255);
      if (probability>.5) points.push((nx-padX)*sx,(ny-padY)*sy);
    }
    if (points.length<6) continue;
    let mx=0,my=0;
    for(let j=0;j<points.length;j+=2){mx+=points[j];my+=points[j+1]}
    mx/=points.length/2;my/=points.length/2;
    let xx=0,xy=0,yy=0;
    for(let j=0;j<points.length;j+=2){const x=points[j]-mx,y=points[j+1]-my;xx+=x*x;xy+=x*y;yy+=y*y}
    const theta=.5*Math.atan2(2*xy,xx-yy), ux=Math.cos(theta),uy=Math.sin(theta);
    let lo=Infinity,hi=-Infinity,left=Infinity,right=-Infinity;
    for(let j=0;j<points.length;j+=2){
      const x=points[j]-mx,y=points[j+1]-my,along=x*ux+y*uy,across=x*uy-y*ux;
      lo=Math.min(lo,along);hi=Math.max(hi,along);left=Math.min(left,across);right=Math.max(right,across);
    }
    // Include the outer half of each prototype pixel in the PCA frame.
    const halfAlong=(Math.abs(ux)*sx*size/pw+Math.abs(uy)*sy*size/ph)/2;
    const halfAcross=(Math.abs(uy)*sx*size/pw+Math.abs(ux)*sy*size/ph)/2;
    lo-=halfAlong;hi+=halfAlong;left-=halfAcross;right+=halfAcross;
    out.push({...b,mx,my,ux,uy,lo,hi,left,right,mw,mh,alpha,
      rx:(px1*size/pw-padX)*sx,ry:(py1*size/ph-padY)*sy,
      rw:mw*size/pw*sx,rh:mh*size/ph*sy,
      box:[(b.x1-padX)*sx,(b.y1-padY)*sy,(b.x2-padX)*sx,(b.y2-padY)*sy]});
  }
  return out;
}
if(typeof module!=='undefined') module.exports={decodeNails};
