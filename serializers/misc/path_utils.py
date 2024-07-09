def escape_chars(path: str) -> str:
    return (path
            .replace('<', '--lt--')
            .replace('>', '--gt--')
            .replace('\\', '--bs--'))


def unescape_chars(path: str) -> str:
    return (path
            .replace('--lt--', '<')
            .replace('--gt--', '>')
            .replace('--bs--', '\\'))
