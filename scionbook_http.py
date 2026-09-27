"""Shared service identity and supported English Lodestone endpoint.

The NA host is deliberate; localized markup is not supported. See README.
Credentials belong only on individual Lodestone requests, never in these defaults.
"""
LODESTONE = "https://na.finalfantasyxiv.com/lodestone"
USER_AGENT = "Scionbook/1.0"
HTTP_HEADERS = {"User-Agent": USER_AGENT, "Accept-Language": "en-US,en;q=0.9"}
LODESTONE_HEADERS = {
    **HTTP_HEADERS,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Cache-Control": "no-cache, no-store, max-age=0",
    "Pragma": "no-cache",
}
