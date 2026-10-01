from time import time

def timer(func):
    ''' Decorator to measure the execution time of a function '''
    
    def wrapper(*args, **kwargs):
        start = time()
        result = func(*args, **kwargs)
        end = time()
        
        if isinstance(result, tuple):
            return end - start, *result
        
        return end - start, result
    
    return wrapper
