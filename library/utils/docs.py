# TODO probably we can create a dedicated class for that and do it in a more easy way
def add_doc_numbers(a, b):
    if a == '?' or b == '?':
        return '?'
    try:
        return str(int(a) + int(b))
    except ValueError:
        if a == '0':
            return b
        if b == '0':
            return a
        if a.isdigit() or b.isdigit():
            expression = a if b.isdigit() else b
            integer = int(b if b.isdigit() else a)
            items = expression.split(' + ')
            for i, item in enumerate(items):
                if item.isdigit():
                    items[i] = str(int(item) + integer)
                    return ' + '.join(items)
        if '..' in b or '..' in a:
            [mnld, mxld] = a.split('..') if ('..' in a) else [a, a]
            [mnsd, mxsd] = b.split('..') if ('..' in b) else [b, b]
            return f'{add_doc_numbers(mnld, mnsd)}..{add_doc_numbers(mxld, mxsd)}'
        else:
            return f'{a} + {b}'

def needs_parentheses(a):
    if a.isdigit():
        return False
    if '+' in a or '-' in a or '>>' in a or '<<' in a:
        return True
    return False

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
            if needs_parentheses(a):
                a = f'({a})'
            if needs_parentheses(b):
                b = f'({b})'
            return f'{a}*{b}'
