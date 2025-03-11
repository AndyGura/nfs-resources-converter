# TODO probably we can create a dedicated class for that and do it in a more easy way
def add_doc_numbers(a, b):
    if a == '?' or b == '?':
        return '?'
    try:
        return str(int(a) + int(b))
    except ValueError:
        if a == '0':
            return b
        elif b == '0':
            return a
        elif '..' in b or '..' in a:
            [mnld, mxld] = a.split('..') if ('..' in a) else [a, a]
            [mnsd, mxsd] = b.split('..') if ('..' in b) else [b, b]
            return f'{add_doc_numbers(mnld, mnsd)}..{add_doc_numbers(mxld, mxsd)}'
        else:
            return f'{a} + {b}'

def multiply_doc_numbers(a, b):
    if a == '?' or b == '?':
        return '?'
    try:
        return str(int(a) * int(b))
    except ValueError:
        if a == '1':
            return b
        elif b == '1':
            return a
        elif '..' in b or '..' in a:
            [mnld, mxld] = a.split('..') if ('..' in a) else [a, a]
            [mnsd, mxsd] = b.split('..') if ('..' in b) else [b, b]
            return f'{multiply_doc_numbers(mnld, mnsd)}..{multiply_doc_numbers(mxld, mxsd)}'
        else:
            if '+' in str(a) or '-' in str(a):
                a = f'({a})'
            if '+' in str(b) or '-' in str(b):
                b = f'({b})'
            return f'{a}*{b}'
