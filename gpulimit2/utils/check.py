# -*- coding: utf-8 -*-


def check_input(input_types, extra_args=(), extra_kwargs={}):
    '''
    Example:
        
        input_types = (('1', int), ('start', str))
    '''
    err_msg = ''
    result_input = []
    for value, dtype in input_types:
        try:
            result_input.append(dtype(value))
        except Exception as e:
            result_input.append(None)
            err_msg += f'[error]: input {value} is not type `{dtype.__name__}`.\n'
    for v in extra_args:
        err_msg += f'[error]: can not identify param `{v}`.\n'
    for k, v in extra_kwargs.items():
        err_msg += f'[error]: can not identify param `{k}={v}`.\n'
            
    return result_input, err_msg

