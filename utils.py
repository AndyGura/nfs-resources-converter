def my_import(name):
    components = name.split('.')
    mod = __import__(components[0])
    for comp in components[1:]:
        mod = getattr(mod, comp)
    return mod


def format_exception(ex):
    # return f'{ex.__class__.__name__}: {str(ex)}'
    return str(ex)
