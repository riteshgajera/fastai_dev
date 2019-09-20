#AUTOGENERATED! DO NOT EDIT! File to edit: dev/03_data_pipeline.ipynb (unless otherwise specified).

__all__ = ['get_func', 'Func', 'Sig', 'compose_tfms', 'batch_to_samples', 'mk_transform', 'Pipeline', 'TfmdBase',
           'TfmdList', 'TfmdDS']

#Cell
from ..torch_basics import *
from ..test import *
from .transform import *
from ..notebook.showdoc import show_doc

#Cell
def get_func(t, name, *args, **kwargs):
    "Get the `t.name` (potentially partial-ized with `args` and `kwargs`) or `noop` if not defined"
    f = getattr(t, name, noop)
    return f if not (args or kwargs) else partial(f, *args, **kwargs)

#Cell
class Func():
    "Basic wrapper around a `name` with `args` and `kwargs` to call on a given type"
    def __init__(self, name, *args, **kwargs): self.name,self.args,self.kwargs = name,args,kwargs
    def __repr__(self): return f'sig: {self.name}({self.args}, {self.kwargs})'
    def _get(self, t): return get_func(t, self.name, *self.args, **self.kwargs)
    def __call__(self,t): return L(t).mapped(self._get) if is_listy(t) else self._get(t)

#Cell
class _Sig():
    def __getattr__(self,k):
        def _inner(*args, **kwargs): return Func(k, *args, **kwargs)
        return _inner

Sig = _Sig()

#Cell
def compose_tfms(x, tfms, is_enc=True, reverse=False, **kwargs):
    "Apply all `func_nm` attribute of `tfms` on `x`, maybe in `reverse` order"
    if reverse: tfms = reversed(tfms)
    for f in tfms:
        if not is_enc: f = f.decode
        x = f(x, **kwargs)
    return x

#Cell
def batch_to_samples(b, max_n=10):
    "'Transposes' a batch to (at most `max_n`) samples"
    if isinstance(b, Tensor): return b[:max_n]
    else:
        res = L(b).mapped(partial(batch_to_samples,max_n=max_n))
        return L(retain_types(res.zipped(), [b]))

#Cell
def mk_transform(f, as_item=True):
    "Convert function `f` to `Transform` if it isn't already one"
    f = instantiate(f)
    return f if isinstance(f,Transform) else Transform(f, as_item=as_item)

#Cell
class Pipeline:
    "A pipeline of composed (for encode/decode) transforms, setup with types"
    def __init__(self, funcs=None, as_item=False, filt=None):
        if isinstance(funcs, Pipeline): funcs = funcs.fs
        elif isinstance(funcs, Transform): funcs = [funcs]
        self.filt,self.default = filt,None
        self.fs = L(ifnone(funcs,[noop])).mapped(mk_transform).sorted(key='order')
        self.set_as_item(as_item)
        for f in self.fs:
            name = camel2snake(type(f).__name__)
            a = getattr(self,name,None)
            if a is not None: f = L(a)+f
            setattr(self, name, f)

    def set_as_item(self, as_item):
        self.as_item = as_item
        for f in self.fs: f.as_item = as_item

    def setup(self, items=None):
        self.items = items
        tfms,self.fs = self.fs,L()
        for t in tfms: self.add(t,items)

    def add(self,t, items=None):
        t.setup(items)
        self.fs.append(t)

    def __call__(self, o): return compose_tfms(o, tfms=self.fs, filt=self.filt)
    def decode  (self, o): return compose_tfms(o, tfms=self.fs, is_enc=False, reverse=True, filt=self.filt)
    def __repr__(self): return f"Pipeline: {self.fs}"
    def __getitem__(self,i): return self.fs[i]
    def decode_batch(self, b, max_n=10): return batch_to_samples(b, max_n=max_n).mapped(self.decode)
    def __setstate__(self,data): self.__dict__.update(data)

    def __getattr__(self,k):
        if k.startswith('_') or k=='fs': raise AttributeError(k)
        res = [t for t in self.fs.attrgot(k) if t is not None]
        if not res: raise AttributeError(k)
        return res[0] if len(res)==1 else L(res)

    def show(self, o, ctx=None, **kwargs):
        for f in reversed(self.fs):
            res = self._show(o, ctx, **kwargs)
            if res is not None: return res
            o = f.decode(o, filt=self.filt)
        return self._show(o, ctx, **kwargs)

    def _show(self, o, ctx, **kwargs):
        o1 = [o] if self.as_item or not is_listy(o) else o
        if not all(hasattr(o_, 'show') for o_ in o1): return
        for o_ in o1: ctx = o_.show(ctx=ctx, **kwargs)
        return ifnone(ctx,1)

#Cell
class TfmdBase(L):
    "Base class for transformed lists"
    _after_item = None
    def __getitem__(self, idx):
        res = super().__getitem__(idx)
        if self._after_item is None: return res
        if isinstance(idx,int): return self._after_item(res)
        return res.mapped(self._after_item)

    def __iter__(self): return (self[i] for i in range(len(self)))
    def subset(self, idxs): return self._new(super()._gets(idxs))
    def decode_at(self, idx): return self.decode(self[idx])
    def show_at(self, idx, **kwargs): return self.show(self[idx], **kwargs)

#Cell
class TfmdList(TfmdBase):
    "A `Pipeline` of `tfms` applied to a collection of `items`"
    def __init__(self, items, tfms, do_setup=True, as_item=True, use_list=None, filt=None):
        super().__init__(items, use_list=use_list)
        if isinstance(tfms,TfmdList): tfms = tfms.tfms
        if isinstance(tfms,Pipeline): do_setup=False
        self.tfms = Pipeline(tfms, as_item=as_item, filt=filt)
        if do_setup: self.setup()

    def _new(self, items, *args, **kwargs): return super()._new(items, tfms=self.tfms, do_setup=False, filt=self.filt)
    def _after_item(self, o): return self.tfms(o)
    def __repr__(self): return f"{self.__class__.__name__}: {self.items}\ntfms - {self.tfms.fs}"

    # Delegating to `self.tfms`
    def show(self, o, **kwargs): return self.tfms.show(o, **kwargs)
    def setup(self): self.tfms.setup(self)
    def decode(self, x, **kwargs): return self.tfms.decode(x, **kwargs)
    def __call__(self, x, **kwargs): return self.tfms.__call__(x, **kwargs)

    @property
    def filt(self): return self.tfms.filt
    @filt.setter
    def filt(self,v): self.tfms.filt = v

#Cell
@docs
class TfmdDS(TfmdBase):
    "A dataset that creates a tuple from each `tfms`, passed thru `ds_tfms`"
    def __init__(self, items, tfms=None, do_setup=True, use_list=None, filt=None):
        super().__init__(items, use_list=use_list)
        if tfms is None: tms = [None]
        self.tls = [TfmdList(items, t, do_setup=do_setup, filt=filt, use_list=use_list) for t in L(tfms)]

    def _after_item(self, it): return tuple(tl.tfms(it) for tl in self.tls)
    def __repr__(self): return coll_repr(self)
    def decode(self, o): return tuple(it.decode(o_) for o_,it in zip(o,self.tls))
    def show(self, o, ctx=None, **kwargs):
        for o_,it in zip(o,self.tls): ctx = it.show(o_, ctx=ctx, **kwargs)
        return ctx

    @property
    def filt(self): return self.tls[0].filt
    @filt.setter
    def filt(self,v):
        for tl in self.tls: tl.filt = v

    _docs=dict(
        decode="Compose `decode` of all `tuple_tfms` then all `tfms` on `i`",
        show="Show item `o` in `ctx`")