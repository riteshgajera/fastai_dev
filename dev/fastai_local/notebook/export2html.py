#AUTOGENERATED! DO NOT EDIT! File to edit: dev/99a_export2html.ipynb (unless otherwise specified).

__all__ = ['remove_widget_state', 'hide_cells', 'remove_hidden', 'add_show_docs', 'remove_fake_headers', 'remove_empty',
           'get_metadata', 'ExecuteShowDocPreprocessor', 'execute_nb', 'convert_nb', 'convert_all']

from ..core import *

from ..test import *

from ..imports import *

from .export import *

import nbformat
from nbconvert.preprocessors import ExecutePreprocessor, Preprocessor
from nbconvert import HTMLExporter
from nbformat.sign import NotebookNotary
from traitlets.config import Config

def remove_widget_state(cell):
    "Remove widgets in the output of `cells`"
    if cell['cell_type'] == 'code' and 'outputs' in cell:
        cell['outputs'] = [l for l in cell['outputs']
                           if not ('data' in l and 'application/vnd.jupyter.widget-view+json' in l.data)]
    return cell

def hide_cells(cell):
    "Hide `cell` that need to be hidden"
    if check_re(cell, r's*show_doc\(|^\s*#\s*(export)\s+'):
        cell['metadata'] = {'hide_input': True}
    return cell

def remove_hidden(cells):
    res = []
    pat = re.compile(r'^\s*#\s*(hide|default_exp)\s+')
    for cell in cells:
        if cell['cell_type']=='markdown' or re.search(pat, cell['source']) is None:
            res.append(cell)
    return res

def _show_doc_cell(name):
    return {'cell_type': 'code',
            'execution_count': None,
            'metadata': {},
            'outputs': [],
            'source': f"show_doc({name})"}

def add_show_docs(cells):
    "Add `show_doc` for each exported function or class"
    res = []
    for cell in cells:
        res.append(cell)
        if check_re(cell, r'^\s*#\s*exports?\s*'):
            names = func_class_names(cell['source'])
            for n in names: res.append(_show_doc_cell(n))
    return res

def remove_fake_headers(cells):
    "Remove in `cells` the fake header"
    res = []
    pat = re.compile(r'#+.*-$')
    for cell in cells:
        if cell['cell_type']=='code' or re.search(pat, cell['source']) is None:
            res.append(cell)
    return res

def remove_empty(cells):
    "Remove in `cells` the empty cells"
    return [c for c in cells if len(c['source']) >0]

def get_metadata(cells):
    "Find the cell with title and summary in `cells`."
    pat = re.compile('^\s*#\s*([^\n]*)\n*>\s*([^\n]*)')
    for i,cell in enumerate(cells):
        if cell['cell_type'] == 'markdown':
            match = re.match(pat, cell['source'])
            if match:
                cells.pop(i)
                return {'keywords': 'fastai',
                        'summary' : match.groups()[1],
                        'title'   : match.groups()[0]}
    return {'keywords': 'fastai',
            'summary' : 'summary',
            'title'   : 'Title'}

class ExecuteShowDocPreprocessor(ExecutePreprocessor):
    "An `ExecutePreprocessor` that only executes `show_doc` and `import` cells"
    def preprocess_cell(self, cell, resources, index):
        pat = re.compile(r"from (fastai_local[\.\w_]*)|show_doc\(([\w\.]*)|^\s*#\s*exports?\s*")
        if 'source' in cell and cell.cell_type == "code":
            if re.search(pat, cell['source']):
                return super().preprocess_cell(cell, resources, index)
        return cell, resources

def execute_nb(nb, metadata=None, show_doc_only=True):
    "Execute `nb` (or only the `show_doc` cells) with `metadata`"
    ep_cls = ExecuteShowDocPreprocessor if show_doc_only else ExecutePreprocessor
    ep = ep_cls(timeout=600, kernel_name='python3')
    metadata = metadata or {}
    pnb = nbformat.from_dict(nb)
    ep.preprocess(pnb, metadata)
    return pnb

def _exporter():
    exporter = HTMLExporter(Config())
    exporter.exclude_input_prompt=True
    exporter.exclude_output_prompt=True
    exporter.template_file = 'jekyll.tpl'
    exporter.template_path.append(str((Path('fastai_local')/'notebook').absolute()))
    return exporter

process_cells = [remove_fake_headers, add_show_docs, remove_hidden, remove_empty]
process_cell  = [hide_cells, remove_widget_state]

def convert_nb(fname, dest_path='docs'):
    "Convert a notebook `fname` to html file in `dest_path`."
    fname = Path(fname).absolute()
    nb = read_nb(fname)
    nb['cells'] = compose(*process_cells)(nb['cells'])
    nb['cells'] = [compose(*process_cell)(c) for c in nb['cells']]
    fname = Path(fname).absolute()
    dest_name = '_'.join(fname.with_suffix('.html').name.split('_')[1:])
    meta_jekyll = get_metadata(nb['cells'])
    meta_jekyll['nb_path'] = f'{fname.parent.name}/{fname.name}'
    nb = execute_nb(nb)
    with open(f'{dest_path}/{dest_name}','w') as f:
        f.write(_exporter().from_notebook_node(nb, resources=meta_jekyll)[0])

def convert_all(path='.', dest_path='docs', force_all=False):
    "Convert all notebooks in `path` to html files in `dest_path`."
    path = Path(path)
    changed_cnt = 0
    for fname in path.glob("*.ipynb"):
        # only rebuild modified files
        if fname.name.startswith('_'): continue
        fname_out = Path(dest_path)/'_'.join(fname.with_suffix('.html').name.split('_')[1:])
        if not force_all and fname_out.exists() and os.path.getmtime(fname) < os.path.getmtime(fname_out):
            continue
        print(f"converting: {fname} => {fname_out}")
        changed_cnt += 1
        try: convert_nb(fname, dest_path=dest_path)
        except: print("Failed")
    if changed_cnt==0: print("No notebooks were modified")