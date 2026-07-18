import logging
import os
import sys
import threading
from logging.handlers import RotatingFileHandler
from config import LOG_FILE_PATH

class LoggerWriter:
    _local = threading.local()

    def __init__(self, level, original_stream=None):
        self.level = level
        self.original_stream = original_stream
        self.buffer = []

    def write(self, message):
        if message:
            # Prevent recursion if logging calls write to redirected stdout/stderr
            if getattr(self._local, 'is_logging', False):
                if self.original_stream and self.original_stream is not sys.stdout and self.original_stream is not sys.stderr:
                    try:
                        self.original_stream.write(message)
                    except (AttributeError, IOError):
                        pass
                return

            self._local.is_logging = True
            try:
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
            finally:
                self._local.is_logging = False

    def flush(self):
        if getattr(self._local, 'is_logging', False):
            return
        if self.buffer:
            self._local.is_logging = True
            try:
                self.level("".join(self.buffer))
                self.buffer = []
            finally:
                self._local.is_logging = False

is_frozen = getattr(sys, 'frozen', False)
is_windows = sys.platform.startswith('win')
is_windows_built_app = is_frozen and is_windows

_file_handler = None
if is_windows_built_app:
    _original_stdout = None
    _original_stderr = None
else:
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
            # Create a rotating file handler (1MB limit, 5 backups)
            # Use a simpler FileHandler for worker processes to avoid rotation conflicts on Windows
            import multiprocessing
            is_main_process = multiprocessing.current_process().name == 'MainProcess'
            
            if is_main_process:
                _file_handler = RotatingFileHandler(
                    LOG_FILE_PATH,
                    maxBytes=1024 * 1024,
                    backupCount=5,
                    encoding='utf-8'
                )
            else:
                _file_handler = logging.FileHandler(
                    LOG_FILE_PATH,
                    encoding='utf-8'
                )
                
            _file_handler.setFormatter(logging.Formatter('%(asctime)s - %(process)d - %(levelname)s - %(message)s'))
            
            # Configure root logger
            root_logger.setLevel(logging.INFO)
            root_logger.addHandler(_file_handler)
            
            if is_main_process:
                logging.info(f"Logging initialized for main process (PID: {os.getpid()})")
            else:
                logging.info(f"Logging initialized for worker process (PID: {os.getpid()})")
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
    
    # Determine whether to add a console handler:
    # - If we are launched via python command (not frozen), we always want to see all logs in the console.
    # - If we are frozen (built app) on Windows, we should NEVER write to the console as it breaks.
    # - For other frozen apps, we only write to the console if redirection is not requested.
    should_add_console = (not redirect_stdout and not is_windows_built_app) or (not is_frozen)
    
    if should_add_console:
        if _original_stdout is not None:
            console_handler = logging.StreamHandler(_original_stdout)
            console_handler.setFormatter(logging.Formatter('%(levelname)s: %(message)s'))
            root_logger.addHandler(console_handler)
    
    # Redirect sys.stdout/stderr to root logger
    # Note: we use the root logger directly to avoid recursion issues with specialized loggers
    # and to ensure everything is captured.
    sys.stdout = LoggerWriter(logging.info, _original_stdout)
    sys.stderr = LoggerWriter(logging.error, _original_stderr)

def is_stdout_redirected():
    """Returns True if stdout redirection is enabled."""
    return _redirect_stdout_enabled

def run_command_and_log(command, capture_output=True, **kwargs):
    """
    Runs a command and logs its output to the logging system by writing to sys.stdout.
    This ensures that the output is captured by the LoggerWriter if redirection is active,
    or printed to the console otherwise.
    
    Args:
        command: The command to run (list or string).
        capture_output: If True, stdout and stderr will be captured and logged.
                        If False, they will be redirected to DEVNULL.
        **kwargs: Additional arguments for subprocess.Popen/run.
    """
    import subprocess
    shell = isinstance(command, str)
    if capture_output:
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            shell=shell,
            bufsize=1,
            universal_newlines=True,
            **kwargs
        )
        if process.stdout:
            for line in process.stdout:
                sys.stdout.write(line)
        return process.wait()
    else:
        return subprocess.run(
            command,
            shell=shell,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            **kwargs
        ).returncode
