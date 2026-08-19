from .._json import error_envelope

NO_TOKEN = error_envelope(
    "not_configured", "No Simplesat API key. Send the X-Simplesat-Api-Key header.", False
)
