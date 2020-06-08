import os
import inspect
import traceback
import copy

from .cmd_utils import parse_input_cmds, get_function_info, inspect_empty


class ParseBase(object):
    def __init__(self):
        pass
    #     self._help_msg = None
    #     self.help = help
        
    # @property
    # def help_msg(self):
    #     if self._help_msg is not None:
    #         return self._help_msg
    #     else:
    #         return self._create_help()
    
    # @help_msg.setter
    # def help_msg(self, v):
    #     self._help_msg = v
        
    # def _create_help(self):
    #     raise NotImplementedError()
        
    
        
class ParseFunction(ParseBase):
    def __init__(self, function, opt_map:dict={}, param_map:dict={}, debug=True, help=None):

        self.function = function
        self.debug = debug
        self.help = help
        
        self.func_info = get_function_info(self.function)
        self.opt_map = {}
        
        self._init_func_info()
        
    @property
    def help_msg(self):
        if self.help == 'auto':
            return self._create_auto_help()
        elif self.help == '__doc__':
            return self.function.__doc__
        else:
            return self.help
        
    def func_str(self):
        params_info = ['{}:{}'.format(param['name'],param['type']) for param in self.func_info['params']]
        if self.func_info['args']:
            params_info.append('*args')
        if self.func_info['kwargs']:
            params_info.append('**kwargs')
        params_info = ','.join(params_info)
        return f'{self.function.__name__}({params_info})'
    
    def _create_auto_help(self):
        return self.func_str()
    
    def _init_func_info(self):
        for param in self.func_info['params']:
            if param['type'] == inspect_empty:
                param['type'] = str
                
    def add_opt(self, opt, name):
        self.opt_map[opt] = name

    def add_opts(self, opt_map):
        for opt, name in opt_map.items():
            self.add_opt(opt, name)
            
    def set_param_type(self, param_name, dtype=str):
        for param in self.func_info['params']:
            if param['name'] == param_name:
                param['type'] = dtype
                return
        raise ValueError(f'param name {param_name} not in function {self.function.__name__}.')
        
    def set_params_type(self, param_map):
        for param_name, dtype in param_map.items():
            self.set_param_type(param_name, dtype)
           
    def _check_and_change_opts(self, opts):
        param_names = [param['name'] for param in self.func_info['params']]
        param_name_value_map = {}
        err = ''
        for k, v in opts.items():
            if self.opt_map.get(k):
                param_name_value_map[self.opt_map.get(k)] = v
            elif (k.startswith('--') and k[2:] in param_names) or self.func_info['kwargs']:
                param_name_value_map[k[2:]] = v
            else:
                err += f'opt `{k}` can not identify'
        
        name_type_dict = dict([(param['name'], param['type']) for param in self.func_info['params']])
        for name, value in param_name_value_map.items():
            if name in name_type_dict:
                r, v = self._change_value_type(value, name_type_dict[name])
                if r:
                    err += 'param `{}` have type `{}`, but you input `{}` can not transform.'.format(name, 
                                                                                                 name_type_dict[name], 
                                                                                                 value)
                else:
                    param_name_value_map[name] = v
        return err, param_name_value_map
        
    def _change_value_type(self, value, type):
        err = False
        try:
            value = type(value)
        except ValueError as e:
            err = True
        return err, value
    
    def _check_input_args(self, param_value, param_name_value_map):
        minimal_num_inputs = sum([param['name'] not in param_name_value_map and not param['has_default']
                                  for param in self.func_info['params']])
        if len(param_value) < minimal_num_inputs:
            return 'inputs is not enough', None

        if (not self.func_info['args']) and len(param_value) > minimal_num_inputs:
            return 'inputs too many', None
        
        err = ''
        for i in range(len(param_value)):
            if i >= len(self.func_info['params']): # args
                break
            r, v = self._change_value_type(param_value[i], self.func_info['params'][i]['type'])
            if r:
                err += 'param `{}` have type `{}`, but you input `{}` can not transform.'.format(self.func_info["params"][i]["name"], 
                                                                                                 self.func_info['params'][i]['type'], 
                                                                                                 param_value[i])
            param_value[i] = v
            
        return err, param_value
            
    def safety_call(self, *args, **kwargs):
        try:
            result = self.function(*args, **kwargs)
        except Exception:
            if self.debug:
                msg = traceback.format_exc()
                return msg
            else:
                return f'Error: undefined input.'
        return result
            
    def call(self, args):
        param_value, opts = parse_input_cmds(args)
        msg, param_name_value_map = self._check_and_change_opts(opts)
        if msg:
            
            return msg
        msg, param_value = self._check_input_args(param_value, param_name_value_map)
        if msg:
            return msg
        return self.safety_call(*param_value, **param_name_value_map)
    
    def __call__(self, args):
        if self.help is not None and '--help' in args or ('-h' in args and '-h' not in self.opt_map):
            return self.help_msg
        return self.call(args)
        
    def __repr__(self):
        return f'ParseFunction({self.func_str()})'
    
    def __str__(self):
        return self.__repr__()
    
    
class ParseModule(ParseBase):
    def __init__(self, debug=True, help=None):
        super().__init__()
        self.debug = debug
        self.help = help
        self.cmd_map = {}
        
    @property
    def help_msg(self):
        if self.help == 'auto':
            return self._create_auto_help()
        else:
            return self.help
        
    def add_sub_parse(self, cmd, cmd_parse):
        self.cmd_map[cmd] = cmd_parse

    def sub_module(self, cmd, opt_map={}, param_map:dict={}, debug=True, help='__doc__'):
        def decorator(func):
            self.cmd_map[cmd] = ParseFunction(func, opt_map, param_map, debug, help)
            return func
        return decorator

    def _create_auto_help(self):
        msg = 'Modules:\n'
        for parse_name, parse in self.cmd_map.items():
            sub_help = parse.help_msg.strip().split("\n")[0]
            msg += f'{parse_name}                        {sub_help}\n'
        return msg
    
    def __call__(self, cmds):
        if len(cmds) < 1:
            return self.help_msg
        if self.help is not None and '--help' == cmds[0] or ('-h' == cmds[0] and '-h' not in self.cmd_map):
            return self.help_msg
        if cmds[0] in self.cmd_map:
            return self.cmd_map[cmds[0]](cmds[1:])
        else:
            return f'args {cmds[0]} not defined.'
    
    def __repr__(self):
        return f'ParseModule({str(self.cmd_map)})'
    
    def __str__(self):
        return self.__repr__()
    

if __name__ == '__main__':
    import sys

    def foo(a:int, b:int, **kwargs):
        print(type(a), type(b))
        print(a, b, kwargs)

    parse = ParseModule()
    parse.add_sub_parse('foo', ParseFunction(foo))
    print(parse(sys.argv[1:]))
