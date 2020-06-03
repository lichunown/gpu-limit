import os
import inspect
import traceback

from inspect import _empty as inspect_empty

'''
param_info={
    'args': False,
    'kwargs':False,
    'params':[
        {
            'name': 'a',
            'type': 'int',
            'has_default': False,
        }    
    ],    
}
'''

def get_function_info(function):
    data = {'args': False, 'kwargs':False, 'params':[]}
    sig = inspect.signature(function)
    for param in sig.parameters.values():
        if param.kind == param.VAR_POSITIONAL:
            data['args'] = True
            continue
        if param.kind == param.VAR_KEYWORD:
            data['kwargs'] = True
            continue
        data['params'].append(
                {
                    'name': param.name,
                    'type': param.annotation,
                    'has_default': False if param.default is inspect_empty else True,
                }
            )
    return data


def parse_input_cmds(args):
    params = []
    opts = {}
    while args:
        if not args[0].startswith('-'):
            params.append(args[0])
        
        elif args[0].startswith('--'):
            arg = args[0]
            if '=' in arg:
                v = arg.split('=')
                opts[v[0]] = '='.join(v[1:])
            else:
                opts[arg] = True
        
        elif args[0].startswith('-'):
            keys = args[0].lstrip('-')
            if len(keys) > 1:
                for k in keys:
                    opts[f'-{k}'] = True
            else:
                if len(args) > 1 and not args[1].startswith('-'):
                    opts[f'-{keys}'] = args[1]
                    args = args[1:]
                else:
                    opts[f'-{keys}'] = True
        args = args[1:]
    return params, opts
