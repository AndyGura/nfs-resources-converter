// Sends uncaught errors, unhandled promise rejections, scripts / stylesheets that fail to load and console.error calls
// to the Python log (nfs-resources-converter-logs.log), where every line gets a "[JS]" prefix. index.html loads it
// right after eel.js and before the Angular bundle, so it also reports a bundle that fails to load or to run.
(function () {
  'use strict';

  // An error thrown every frame (render loop) must not push the Python log out of the rotated log files.
  var MAX_MESSAGES = 200;
  var sentCount = 0;
  var sentMessages = {};
  var originalConsoleError = console.error;

  function describe(value) {
    if (value instanceof Error) {
      // Chromium's stack starts with "Name: message", WebKit's has the frames only.
      var header = value.name + ': ' + value.message;
      if (!value.stack) {
        return header;
      }
      return value.stack.indexOf(value.message) !== -1 ? value.stack : header + '\n' + value.stack;
    }
    if (typeof value === 'string') {
      return value;
    }
    try {
      return JSON.stringify(value);
    } catch (e) {
      return String(value);
    }
  }

  function send(level, message) {
    if (sentCount > MAX_MESSAGES || sentMessages[message]) {
      return;
    }
    sentMessages[message] = true;
    sentCount++;
    if (sentCount > MAX_MESSAGES) {
      level = 'warning';
      message = 'Logged ' + MAX_MESSAGES + ' JavaScript errors, not logging the next ones';
    }
    try {
      var result = window.eel.log_frontend_message(level, message)();
      if (result && typeof result.catch === 'function') {
        result.catch(function () {});
      }
    } catch (e) {
      // No bridge to Python: nowhere to report to.
    }
  }

  // Capture phase: load errors of <script> / <link> elements don't bubble up to window.
  window.addEventListener(
    'error',
    function (event) {
      var target = event.target;
      if (target && (target.tagName === 'SCRIPT' || target.tagName === 'LINK')) {
        send('error', 'Failed to load ' + target.tagName.toLowerCase() + ' ' + (target.src || target.href));
        return;
      }
      if (target !== window) {
        return;
      }
      if (event.error) {
        send('error', 'Uncaught ' + describe(event.error));
      } else {
        send(
          'error',
          'Uncaught ' + event.message + ' (' + event.filename + ':' + event.lineno + ':' + event.colno + ')',
        );
      }
    },
    true,
  );

  window.addEventListener('unhandledrejection', function (event) {
    send('error', 'Unhandled promise rejection: ' + describe(event.reason));
  });

  // Angular's ErrorHandler reports the errors it catches with console.error.
  console.error = function () {
    send('error', 'console.error: ' + Array.prototype.map.call(arguments, describe).join(' '));
    return originalConsoleError.apply(console, arguments);
  };
})();
