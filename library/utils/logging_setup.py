import logging
import sys
from logging.handlers import RotatingFileHandler
from config import LOG_FILE_PATH

class LoggerWriter:
    def __init__(self, level):
        self.level = level
        self.buffer = []

    def write(self, message):
        if message:
            # Add to buffer and split by newlines, keeping the ends to know if we have a full line
            lines = ( "".join(self.buffer) + message ).splitlines(keepends=True)
            self.buffer = []
            for line in lines:
                if line.endswith('\n') or line.endswith('\r'):
                    # Log full lines without the trailing newline, but preserving leading spaces
                    self.level(line.rstrip('\n\r'))
                else:
                    # Keep partial line in buffer
                    self.buffer.append(line)

    def flush(self):
        if self.buffer:
            self.level("".join(self.buffer))
            self.buffer = []

_file_handler = None
_original_stdout = sys.stdout
_original_stderr = sys.stderr
_redirect_stdout_enabled = False

def setup_logging(redirect_stdout=False):
    """
    Setup logging to a file with rotation and optional stdout/stderr redirection.
    
    Args:
        redirect_stdout: If True, sys.stdout and sys.stderr will be redirected to the logger
                         and console output will be suppressed.
    """
    global _file_handler, _original_stdout, _original_stderr, _redirect_stdout_enabled
    _redirect_stdout_enabled = redirect_stdout
    root_logger = logging.getLogger()
    
    if _file_handler is None:
        try:
            # Create a rotating file handler (50MB limit, 5 backups)
            _file_handler = RotatingFileHandler(
                LOG_FILE_PATH,
                maxBytes=50 * 1024 * 1024,
                backupCount=5,
                encoding='utf-8'
            )
            _file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
            
            # Configure root logger
            root_logger.setLevel(logging.INFO)
            root_logger.addHandler(_file_handler)
        except Exception as e:
            # Fallback to basic logging if file handler fails
            logging.basicConfig(level=logging.INFO)
            logging.error(f"Failed to setup file logging: {e}")
            return

    # Handle stdout/stderr redirection
    # We always redirect to capture prints in the log file
    
    # Remove all existing StreamHandlers to avoid duplicates or loops
    for handler in root_logger.handlers[:]:
        if isinstance(handler, logging.StreamHandler) and not isinstance(handler, logging.FileHandler):
            root_logger.removeHandler(handler)
    
    if not redirect_stdout:
        # If not suppressing, add a StreamHandler that writes to the ORIGINAL stdout
        console_handler = logging.StreamHandler(_original_stdout)
        console_handler.setFormatter(logging.Formatter('%(levelname)s: %(message)s'))
        root_logger.addHandler(console_handler)
    
    # Redirect sys.stdout/stderr to root logger
    # Note: we use the root logger directly to avoid recursion issues with specialized loggers
    # and to ensure everything is captured.
    sys.stdout = LoggerWriter(logging.info)
    sys.stderr = LoggerWriter(logging.error)

def is_stdout_redirected():
    """Returns True if stdout redirection is enabled."""
    return _redirect_stdout_enabled
