#AUTOGENERATED! DO NOT EDIT! File to edit: dev/07_vision_core.ipynb (unless otherwise specified).

__all__ = ['Image', 'ToTensor', 'imagenet_stats', 'cifar_stats', 'mnist_stats', 'size', 'n_px', 'shape', 'aspect',
           'load_image', 'PILBase', 'PILImage', 'PILImageBW', 'PILMask', 'TensorPoint', 'get_annotations', 'BBox',
           'TensorBBox', 'image2byte', 'encodes', 'encodes', 'encodes', 'PointScaler', 'BBoxScaler', 'BBoxCategorize',
           'bb_pad', 'subplots', 'show_batch', 'show_results', 'show_results', 'show_results']

#Cell
from ..torch_basics import *
from ..test import *
from ..data.all import *

from PIL import Image

#Cell
imagenet_stats = ([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
cifar_stats    = ([0.491, 0.482, 0.447], [0.247, 0.243, 0.261])
mnist_stats    = ([0.131], [0.308])

#Cell
_old_sz = Image.Image.size.fget
@patch_property
def size(x:Image.Image): return Tuple(_old_sz(x))

#Cell
@patch_property
def n_px(x: Image.Image): return x.size[0] * x.size[1]

#Cell
@patch_property
def shape(x: Image.Image): return x.size[1],x.size[0]

#Cell
@patch_property
def aspect(x: Image.Image): return x.size[0]/x.size[1]

#Cell
@patch
def reshape(x: Image.Image, h, w, resample=0):
    "`resize` `x` to `(w,h)`"
    return x.resize((w,h), resample=resample)

#Cell
@patch
def resize_max(x: Image.Image, resample=0, max_px=None, max_h=None, max_w=None):
    "`resize` `x` to `max_px`, or `max_h`, or `max_w`"
    h,w = x.shape
    if max_px and x.n_px>max_px: h,w = Tuple(h,w).mul(math.sqrt(max_px/x.n_px))
    if max_h and h>max_h: h,w = (max_h    ,max_h*w/h)
    if max_w and w>max_w: h,w = (max_w*h/w,max_w    )
    return x.reshape(round(h), round(w), resample=resample)

#Cell
def load_image(fn, mode=None, **kwargs):
    "Open and load a `PIL.Image` and convert to `mode`"
    im = Image.open(fn, **kwargs)
    im.load()
    im = im._new(im.im)
    return im.convert(mode) if mode else im

#Cell
class PILBase(Image.Image, metaclass=BypassNewMeta):
    _bypass_type=Image.Image
    default_batch_tfms = ByteToFloatTensor
    _show_args = {'cmap':'viridis'}
    _open_args = {'mode': 'RGB'}
    @classmethod
    def create(cls, fn, **kwargs)->None:
        "Open an `Image` from path `fn`"
        if isinstance(fn,Tensor): fn = fn.numpy()
        if isinstance(fn,ndarray): return cls(Image.fromarray(fn))
        return cls(load_image(fn, **merge(cls._open_args, kwargs)))

    def show(self, ctx=None, **kwargs):
        "Show image using `merge(self._show_args, kwargs)`"
        return show_image(self, ctx=ctx, **merge(self._show_args, kwargs))

#Cell
class PILImage(PILBase): pass

#Cell
class PILImageBW(PILImage): _show_args,_open_args = {'cmap':'Greys'},{'mode': 'L'}

#Cell
class PILMask(PILBase): _open_args,_show_args = {'mode':'L'},{'alpha':0.5, 'cmap':'tab20'}

#Cell
class TensorPoint(TensorBase):
    "Basic type for points in an image"
    _show_args = dict(s=10, marker='.', c='r')

    @classmethod
    def create(cls, t)->None:
        "Convert an array or a list of points `t` to a `Tensor`"
        return cls(tensor(t).view(-1, 2).float())

    def show(self, ctx=None, **kwargs):
        if 'figsize' in kwargs: del kwargs['figsize']
        ctx.scatter(self[:, 0], self[:, 1], **{**self._show_args, **kwargs})
        return ctx

#Cell
def get_annotations(fname, prefix=None):
    "Open a COCO style json in `fname` and returns the lists of filenames (with maybe `prefix`) and labelled bboxes."
    annot_dict = json.load(open(fname))
    id2images, id2bboxes, id2cats = {}, collections.defaultdict(list), collections.defaultdict(list)
    classes = {o['id']:o['name'] for o in annot_dict['categories']}
    for o in annot_dict['annotations']:
        bb = o['bbox']
        id2bboxes[o['image_id']].append([bb[0],bb[1], bb[0]+bb[2], bb[1]+bb[3]])
        id2cats[o['image_id']].append(classes[o['category_id']])
    id2images = {o['id']:ifnone(prefix, '') + o['file_name'] for o in annot_dict['images'] if o['id'] in id2bboxes}
    ids = list(id2images.keys())
    return [id2images[k] for k in ids], [(id2bboxes[k], id2cats[k]) for k in ids]

#Cell
from matplotlib import patches, patheffects

def _draw_outline(o, lw):
    o.set_path_effects([patheffects.Stroke(linewidth=lw, foreground='black'), patheffects.Normal()])

def _draw_rect(ax, b, color='white', text=None, text_size=14, hw=True, rev=False):
    lx,ly,w,h = b
    if rev: lx,ly,w,h = ly,lx,h,w
    if not hw: w,h = w-lx,h-ly
    patch = ax.add_patch(patches.Rectangle((lx,ly), w, h, fill=False, edgecolor=color, lw=2))
    _draw_outline(patch, 4)
    if text is not None:
        patch = ax.text(lx,ly, text, verticalalignment='top', color=color, fontsize=text_size, weight='bold')
        _draw_outline(patch,1)

#Cell
class BBox(Tuple):
    "Basic type for a list of bounding boxes in an image"
    def show(self, ctx=None, **kwargs):
        for b,l in zip(self.bbox, self.lbl):
            if l != '#bg': _draw_rect(ctx, b, hw=False, text=l)
        return ctx
    @classmethod
    def create(cls, x): return cls(x)

    bbox,lbl = add_props(lambda i,self: self[i])

#Cell
class TensorBBox(Tuple):
    "Basic type for a tensor of bounding boxes in an image"
    @classmethod
    def create(cls, x): return cls(tensor(x[0]).view(-1, 4).float(), x[1])

    bbox,lbl = add_props(lambda i,self: self[i])

#Cell
def image2byte(img):
    "Transform image to byte tensor in `c*h*w` dim order."
    res = torch.ByteTensor(torch.ByteStorage.from_buffer(img.tobytes()))
    w,h = img.size
    return res.view(h,w,-1).permute(2,0,1)

#Cell
@ToTensor
def encodes(self, o:PILImage): return TensorImage(image2byte(o))
@ToTensor
def encodes(self, o:PILImageBW): return TensorImageBW(image2byte(o))
@ToTensor
def encodes(self, o:PILMask):  return TensorMask(image2byte(o)[0])

#Cell
def _scale_pnts(x, y, do_scale=True,y_first=False):
    if y_first: y = y.flip(1)
    sz = [x.shape[-1], x.shape[-2]] if isinstance(x, Tensor) else x.size
    return y * 2/tensor(sz).float() - 1 if do_scale else y

def _unscale_pnts(x, y):
    sz = [x.shape[-1], x.shape[-2]] if isinstance(x, Tensor) else x.size
    return (y+1) * tensor(sz).float()/2

#Cell
#TODO: Transform on a whole tuple lose types, see if we can simplify that?
class PointScaler(ItemTransform):
    "Scale a tensor representing points"
    def __init__(self, do_scale=True, y_first=False): self.do_scale,self.y_first = do_scale,y_first
    def encodes(self, o): return (o[0],TensorPoint(_scale_pnts(*o, self.do_scale, self.y_first)))
    def decodes(self, o): return (o[0],TensorPoint(_unscale_pnts(*o)))

TensorPoint.default_item_tfms = PointScaler

#Cell
class BBoxScaler(PointScaler):
    "Scale a tensor representing bounding boxes"
    def encodes(self, o):
        x,y = o
        scaled_bb = _scale_pnts(x, y.bbox.view(-1,2), self.do_scale, self.y_first)
        return (x,TensorBBox((scaled_bb.view(-1,4),y.lbl)))

    def decodes(self, o):
        x,y = o
        scaled_bb = _unscale_pnts(x, y.bbox.view(-1,2))
        return (x, TensorBBox((scaled_bb.view(-1,4), y.lbl)))

#Cell
class BBoxCategorize(Transform):
    "Reversible transform of category string to `vocab` id"
    order,state_args=1,'vocab'
    def __init__(self, vocab=None):
        self.vocab = vocab
        self.o2i = None if vocab is None else {v:k for k,v in enumerate(vocab)}

    def setups(self, dsrc):
        if not dsrc: return
        vals = set()
        for bb in dsrc: vals = vals.union(set(bb.lbl))
        self.vocab,self.otoi = uniqueify(list(vals), sort=True, bidir=True, start='#bg')

    def encodes(self, o:BBox):
        return TensorBBox.create((o.bbox,tensor([self.otoi[o_] for o_ in o.lbl if o_ in self.otoi])))
    def decodes(self, o:TensorBBox):
        return BBox((o.bbox,[self.vocab[i_] for i_ in o.lbl]))

BBox.default_type_tfms,BBox.default_item_tfms = BBoxCategorize,BBoxScaler

#Cell
#TODO tests
def bb_pad(samples, pad_idx=0):
    "Function that collect `samples` of labelled bboxes and adds padding with `pad_idx`."
    max_len = max([len(s[1][1]) for s in samples])
    def _f(img,bbox,lbl):
        bbox = torch.cat([bbox,bbox.new_zeros(max_len-bbox.shape[0], 4)])
        lbl  = torch.cat([lbl, lbl .new_zeros(max_len-lbl .shape[0])+pad_idx])
        return img,TensorBBox((bbox,lbl))
    return [_f(x,*y) for x,y in samples]

#Cell
@delegates(plt.subplots, keep=True)
def subplots(nrows=1, ncols=1, **kwargs):
    fig,ax = plt.subplots(nrows,ncols,**kwargs)
    if nrows*ncols==1: ax = array([ax])
    return fig,ax

#Cell
def _get_grid(n, rows=None, cols=None, add_vert=0, figsize=None, double=False):
    rows = rows or int(np.ceil(math.sqrt(n)))
    cols = cols or int(np.ceil(n/rows))
    if double: cols*=2 ; n*=2
    figsize = (cols*3, rows*3+add_vert) if figsize is None else figsize
    _,axs = subplots(rows, cols, figsize=figsize)
    axs = axs.flatten()
    for ax in axs[n:]: ax.set_axis_off()
    return axs

#Cell
@typedispatch
def show_batch(x:TensorImage, y, its, ctxs=None, max_n=10, rows=None, cols=None, figsize=None, **kwargs):
    if ctxs is None: ctxs = _get_grid(min(len(its), max_n), rows=rows, cols=cols, figsize=figsize)
    ctxs = default_show_batch(x, y, its, ctxs=ctxs, max_n=max_n, **kwargs)
    return ctxs

#Cell
@typedispatch
def show_results(x:TensorImage, y, its, ctxs=None, max_n=10, rows=None, cols=None, figsize=None, **kwargs):
    if ctxs is None: ctxs = _get_grid(min(len(its), max_n), rows=rows, cols=cols, add_vert=1, figsize=figsize)
    ctxs = default_show_results(x, y, its, ctxs=ctxs, max_n=max_n, **kwargs)
    return ctxs

#Cell
@typedispatch
def show_results(x:TensorImage, y:TensorCategory, its, ctxs=None, max_n=10, rows=None, cols=None, figsize=None, **kwargs):
    if ctxs is None: ctxs = _get_grid(min(len(its), max_n), rows=rows, cols=cols, add_vert=1, figsize=figsize)
    for i in range(2):
        ctxs = [b.show(ctx=c, **kwargs) for b,c,_ in zip(its.itemgot(i),ctxs,range(max_n))]
    ctxs = [r.show(ctx=c, color='green' if b==r else 'red', **kwargs)
            for b,r,c,_ in zip(its.itemgot(1),its.itemgot(2),ctxs,range(max_n))]
    return ctxs

#Cell
@typedispatch
def show_results(x:TensorImage, y:TensorImageBase, its, ctxs=None, max_n=10, rows=None, cols=None, figsize=None, **kwargs):
    if ctxs is None: ctxs = _get_grid(min(len(its), max_n), rows=rows, cols=cols, add_vert=1, figsize=figsize, double=True)
    for i in range(2):
        ctxs[::2] = [b.show(ctx=c, **kwargs) for b,c,_ in zip(its.itemgot(i),ctxs[::2],range(max_n))]
    for i in [0,2]:
        ctxs[1::2] = [b.show(ctx=c, **kwargs) for b,c,_ in zip(its.itemgot(i),ctxs[1::2],range(max_n))]
    return ctxs