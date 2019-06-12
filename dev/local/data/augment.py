#AUTOGENERATED! DO NOT EDIT! File to edit: dev/08_augmentation.ipynb (unless otherwise specified).

__all__ = ['flip_affine', 'mask_tensor']

from ..imports import *
from ..test import *
from ..core import *
from .pipeline import *
from .source import *
from .core import *
from ..vision.core import *
from .external import *

import math
from torch import stack, zeros_like as t0, ones_like as t1
from torch.distributions.bernoulli import Bernoulli

def flip_affine(x, p=0.5):
    "Flip as an affine transform"
    mask = -2*x.new_empty(x.size(0)).bernoulli_(p)+1
    return stack([stack([mask,     t0(mask), t0(mask)], dim=1),
                  stack([t0(mask), t1(mask), t0(mask)], dim=1),
                  stack([t0(mask), t0(mask), t1(mask)], dim=1)], dim=1)

def mask_tensor(x, p=0.5, neutral=0.):
    "Mask elements of `x` with probability `p` by replacing them with `neutral`"
    if p==1.: return x
    if neutral != 0: x.add_(-neutral)
    mask = x.new_empty(*x.size()).bernoulli_(p)
    x.mul_(mask)
    return x.add_(neutral) if neutral != 0 else x