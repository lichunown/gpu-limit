# -*- coding: utf-8 -*-
import threading


def asyn(func):
    def wrapper(*args, **kwargs):
        t = threading.Thread(target=func, args=args, kwargs=kwargs)
        return t.start()
    return wrapper


if __name__ == '__main__':
    import time
    
    @asyn
    def foo(t, a, b):
        time.sleep(t)
        print(f'{a} + {b} = {a+b}')
    
    foo(2,1,1)
    print('start foo1')
    foo(1,2,2)
    print('start foo2')
    foo(0,3,3)
    print('start foo3')
