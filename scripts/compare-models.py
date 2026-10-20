"""Measure compressed ONNX masks against FP32 (consistency, not ground-truth accuracy)."""
import argparse, json, time
from pathlib import Path
import cv2
import numpy as np
import onnxruntime as ort


def preprocess(image):
    h,w=image.shape[:2]; r=min(640/w,640/h);nw,nh=round(w*r),round(h*r)
    x,y=(640-nw)//2,(640-nh)//2
    canvas=np.full((640,640,3),114,np.uint8);canvas[y:y+nh,x:x+nw]=cv2.resize(image,(nw,nh))
    return canvas[:,:,::-1].transpose(2,0,1)[None].astype(np.float32)/255


def decode(outputs, conf=.3):
    det,proto=outputs; rows=det[0].T;rows=rows[rows[:,4]>=conf]
    order=np.argsort(-rows[:,4]);keep=[]
    while len(order) and len(keep)<30:
        i=order[0];keep.append(i);rest=order[1:]
        if not len(rest):break
        b=rows[i,:4];a=rows[rest,:4]
        tl=np.maximum(b[:2]-b[2:]/2,a[:,:2]-a[:,2:]/2);br=np.minimum(b[:2]+b[2:]/2,a[:,:2]+a[:,2:]/2)
        intersection=np.prod(np.maximum(0,br-tl),axis=1);iou=intersection/(b[2]*b[3]+a[:,2]*a[:,3]-intersection)
        order=rest[iou<.45]
    result=[]
    yy,xx=np.mgrid[:160,:160];xx=(xx+.5)*4;yy=(yy+.5)*4
    for i in keep:
        row=rows[i];logits=row[5:]@proto[0].reshape(32,-1);mask=logits.reshape(160,160)>0
        x,y,w,h=row[:4];mask&=(xx>=x-w/2)&(xx<x+w/2)&(yy>=y-h/2)&(yy<y+h/2)
        if mask.sum()<3:continue
        result.append({'score':float(row[4]),'box':row[:4].tolist(),'mask':mask})
    return result


def consistency(base,other):
    used=set();values=[]
    for a in base:
        best=-1;value=0
        for i,b in enumerate(other):
            if i in used:continue
            inter=np.count_nonzero(a['mask']&b['mask']);union=np.count_nonzero(a['mask']|b['mask']);v=inter/max(1,union)
            if v>value:best=i;value=v
        if best>=0:used.add(best)
        values.append(value)
    return {'mask_iou_mean':float(np.mean(values)) if values else None,'mask_iou_min':float(min(values)) if values else None,'matched_over_0_5':int(sum(v>.5 for v in values))}

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('fp32',type=Path);ap.add_argument('compressed',type=Path);ap.add_argument('photos',type=Path);ap.add_argument('output',type=Path);a=ap.parse_args()
    a.output.mkdir(parents=True,exist_ok=True);report={'definition':'IoU vs FP32 output at confidence .30; not annotated ground truth','models':{},'photos':{}}
    images={p.stem:cv2.imread(str(p)) for p in sorted(a.photos.glob('*.jpg'))};baseline={}
    paths=[a.fp32]+sorted(a.compressed.glob('*.onnx'))
    for path in paths:
        model=path.stem;report['models'][model]={'bytes':path.stat().st_size}
        try:
            opts=ort.SessionOptions();opts.intra_op_num_threads=4;opts.inter_op_num_threads=1
            session=ort.InferenceSession(str(path),opts,providers=['CPUExecutionProvider'])
            for name,image in images.items():
                t=time.perf_counter();outputs=session.run(None,{session.get_inputs()[0].name:preprocess(image)});ms=round((time.perf_counter()-t)*1000)
                det=decode(outputs);info={'nails':len(det),'ms_cpu':ms,'scores':[round(d['score'],4) for d in det]}
                if model=='nails-fp32':baseline[name]=det
                else:info.update(consistency(baseline[name],det))
                report['photos'].setdefault(name,{})[model]=info
                # Save outputs for independent JS decoder/letterbox checks.
                if model=='nails-weight-int8':
                    for i,o in enumerate(outputs):np.save(a.output/f'{name}-output{i}.npy',o)
            del session
        except Exception as e:report['models'][model]['error']=str(e)
        print(model,json.dumps(report['models'][model]),flush=True)
    (a.output/'model-comparison.json').write_text(json.dumps(report,indent=2))
    print(json.dumps(report,indent=2))
