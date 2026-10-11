"""One-time Pinterest login (run on your own computer, signed in as the DebtLab Pinterest business account).

1. developers.pinterest.com -> My apps -> Connect app. Redirect URI: http://localhost:8085/
2. PINTEREST_APP_ID=... PINTEREST_APP_SECRET=... python tools/pinterest/auth_setup.py
3. Approve in the browser. The script prints the refresh token and your boards.
4. GitHub repo -> Settings -> Secrets: PINTEREST_APP_ID, PINTEREST_APP_SECRET, PINTEREST_REFRESH_TOKEN
   and Variables: PINTEREST_BOARD_ID
The refresh token lasts about a year; run this again when posting starts failing with 401.
"""
import os
import urllib.parse
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer

import requests

REDIRECT = "http://localhost:8085/"
APP_ID, SECRET = os.environ["PINTEREST_APP_ID"], os.environ["PINTEREST_APP_SECRET"]
code = {}


class H(BaseHTTPRequestHandler):
    def do_GET(self):
        q = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
        code["v"] = q.get("code", [""])[0]
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Done. You can close this tab.")

    def log_message(self, *a):
        pass


url = "https://www.pinterest.com/oauth/?" + urllib.parse.urlencode(
    {"client_id": APP_ID, "redirect_uri": REDIRECT, "response_type": "code", "scope": "boards:read,pins:read,pins:write,user_accounts:read"}
)
print("Opening:", url)
webbrowser.open(url)
srv = HTTPServer(("localhost", 8085), H)
while not code.get("v"):
    srv.handle_request()

tok = requests.post(
    "https://api.pinterest.com/v5/oauth/token",
    auth=(APP_ID, SECRET),
    data={"grant_type": "authorization_code", "code": code["v"], "redirect_uri": REDIRECT},
    timeout=30,
).json()
print("\nPINTEREST_REFRESH_TOKEN =", tok.get("refresh_token"))
boards = requests.get("https://api.pinterest.com/v5/boards", headers={"Authorization": f"Bearer {tok['access_token']}"}, timeout=30).json()
print("\nBoards (use the id as PINTEREST_BOARD_ID):")
for b in boards.get("items", []):
    print(f"  {b['id']}  {b['name']}")
