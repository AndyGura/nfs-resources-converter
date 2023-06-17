def escape_chars(path: str) -> str:
    return (path
            .replace('<', '--lt--')
            .replace('>', '--gt--'))


def unescape_chars(path: str) -> str:
    return (path
            .replace('--lt--', '<')
            .replace('--gt--', '>'))
