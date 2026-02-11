"""
Asistente de Corrección Narrativa - TFM

Herramienta offline de análisis narrativo para correctores profesionales.
"""

# Version: try importlib.metadata first, then fallback to hardcoded version
# IMPORTANT: This fallback is critical for embedded Python where the package
# is not installed via pip, so importlib.metadata.version() fails.
_FALLBACK_VERSION = "0.8.6"

try:
    from importlib.metadata import version
    __version__ = version("narrative-assistant")
except Exception:
    # Fallback for embedded Python or development environments
    # where the package is not installed via pip
    __version__ = _FALLBACK_VERSION

__author__ = "Pau Ubach"


# Configure SSL to use certifi certificates (needed for macOS embedded Python)
def _configure_ssl_certificates():
    """Configure SSL to use certifi certificates if available."""
    try:
        import ssl

        import certifi

        # Create a default SSL context with certifi certificates
        ssl_context = ssl.create_default_context(cafile=certifi.where())

        # Monkey-patch urllib to use our SSL context
        import urllib.request

        # Store original opener
        _original_urlopen = urllib.request.urlopen

        def _patched_urlopen(url, data=None, timeout=None, **kwargs):
            """Patched urlopen that uses certifi SSL context."""
            if timeout is None:
                timeout = 30
            # Only add context if not already provided and URL is HTTPS
            if "context" not in kwargs:
                url_str = url if isinstance(url, str) else url.full_url
                if url_str.startswith("https://"):
                    kwargs["context"] = ssl_context
            return _original_urlopen(url, data=data, timeout=timeout, **kwargs)

        urllib.request.urlopen = _patched_urlopen

        # Also fix urlretrieve
        _original_urlretrieve = urllib.request.urlretrieve

        def _patched_urlretrieve(url, filename=None, reporthook=None, data=None):
            """Patched urlretrieve that uses certifi SSL context."""
            # urlretrieve doesn't support context directly, so we use a custom opener
            opener = urllib.request.build_opener(urllib.request.HTTPSHandler(context=ssl_context))
            urllib.request.install_opener(opener)
            return _original_urlretrieve(url, filename, reporthook, data)

        urllib.request.urlretrieve = _patched_urlretrieve

    except ImportError:
        # certifi not available, SSL will use system certificates
        pass
    except Exception:
        # Don't fail if SSL configuration fails
        pass


# Configure SSL on import
_configure_ssl_certificates()
