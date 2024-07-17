import base64
import hashlib
import secrets
import requests
from urllib.parse import urlencode
from http.server import HTTPServer, BaseHTTPRequestHandler
import webbrowser
import json
import os
import tkinter as tk
from tkinter import simpledialog

# Global variables
client_id = 'b20f0802c77540a0963048cc394ec998'
redirect_uri = 'http://localhost:8080/callback'
scope ='user-read-playback-state user-read-email user-read-private'
token_url = 'https://accounts.spotify.com/api/token'
api_url = 'https://api.spotify.com/v1/me'

# Constants
VERBOSE_MODE = False  # If true, prints specific logs in the code (for debugging)

def init():
    global code_verifier, code_challenge, auth_url, authorization_code, token_response
    resp = load_from_cache()
    if resp is None:
        code_verifier = generate_code_verifier()
        code_challenge = generate_code_challenge(code_verifier)
        auth_url = get_authorization_url()
        authorization_code = get_auth_code()
        token_response = get_access_token()

def generate_code_verifier(length=128):
    possible = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-._~'
    return ''.join(secrets.choice(possible) for _ in range(length))

def generate_code_challenge(code_verifier):
    code_verifier_bytes = code_verifier.encode('ascii')
    sha256_digest = hashlib.sha256(code_verifier_bytes).digest()
    base64_digest = base64.urlsafe_b64encode(sha256_digest).rstrip(b'=')
    return base64_digest.decode('ascii')

def get_authorization_url():
    global client_id, redirect_uri, scope, code_challenge
    params = {
        'client_id': client_id,
        'response_type': 'code',
        'redirect_uri': redirect_uri,
        'scope': scope,
        'code_challenge_method': 'S256',
        'code_challenge': code_challenge
    }
    return f'https://accounts.spotify.com/authorize?{urlencode(params)}'

def get_access_token():
    global client_id, authorization_code, redirect_uri, code_verifier, token_url, access_token, refresh_token, sp_dc
    payload = {
        'client_id': client_id,
        'grant_type': 'authorization_code',
        'code': authorization_code,
        'redirect_uri': redirect_uri,
        'code_verifier': code_verifier
    }
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded'
    }
    response = requests.post(token_url, data=payload, headers=headers)
    response_data = response.json()

    if response.status_code != 200:
        return None
    
    access_token = response_data.get('access_token')
    refresh_token = response_data.get('refresh_token')
    
    save_to_cache({
        'access_token': access_token,
        'refresh_token': refresh_token,
        'sp_dc': sp_dc
    })
    
    return response_data

def refresh_access_token():
    global client_id, token_url, access_token, refresh_token
    payload = {
        'client_id': client_id,
        'grant_type': 'refresh_token',
        'refresh_token': refresh_token,
    }
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded'
    }
    response = requests.post(token_url, data=payload, headers=headers)
    data = response.json()
    
    access_token = data.get('access_token')
    refresh_token = data.get('refresh_token')
    
    save_to_cache({
        'access_token': access_token,
        'refresh_token': refresh_token,
        'sp_dc': sp_dc
    })
    
    return data

def get_currently_playing(method='GET', params=None):
    try:
        global access_token, api_url
        endpoint = api_url + '/player/currently-playing'
        headers = {
            'Authorization': f'Bearer {access_token}'
        }
        if method == 'GET':
            response = requests.get(endpoint, headers=headers, params=params)
        elif method == 'POST':
            response = requests.post(endpoint, headers=headers, data=params)
            
        if response.status_code == 204:
            print("No content - Spotify is not open or no track is playing.") if VERBOSE_MODE else None
            return None

        if response.status_code != 200:
            print(f"Error: {response.status_code}") if VERBOSE_MODE else None
            refresh_access_token()
            return None

        try:
            response_data = response.json()
        except ValueError:
            print("Response content is not valid JSON") if VERBOSE_MODE else None
            return None
            
        return response_data
    except Exception as e:
        print(f'Exception in get_currently_playing:\n{e}') if VERBOSE_MODE else None

def get_auth_code():
    class AuthRequestHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path.startswith('/callback'):
                query = self.path.split('?')[1]
                params = dict(param.split('=') for param in query.split('&'))
                self.server.auth_code = params.get('code')
                self.send_response(200)
                self.send_header('Content-type', 'text/html')
                self.end_headers()
                self.wfile.write(b'Authentication successful. You can close this window.')
            else:
                self.send_response(404)
                self.end_headers()

    global auth_url, sp_dc
    # Start a simple HTTP server to listen for the callback
    server_address = ('', 8080)
    httpd = HTTPServer(server_address, AuthRequestHandler)

    # Open the authorization URL in the default web browser
    webbrowser.open(auth_url)

    # Serve until we get the authorization code
    httpd.handle_request()
    
    # Open a Tkinter window to ask for the sp_dc cookie
    root = tk.Tk()
    root.withdraw()  # Hide the main window
    sp_dc = simpledialog.askstring("Input", "Please enter the 'sp_dc' cookie value from your browser:")
    root.destroy()
    
    auth_code = httpd.auth_code
    return auth_code

def save_to_cache(data, filename='cache.json'):
    with open(filename, 'w') as cache_file:
        json.dump(data, cache_file, indent=4)

def load_from_cache(filename='cache.json'):
    global access_token, refresh_token, sp_dc
    if not os.path.exists(filename):
        return None
    with open(filename, 'r') as cache_file:
        data =  json.load(cache_file)
        access_token = data['access_token']
        refresh_token = data['refresh_token']
        sp_dc = data['sp_dc']
        return data

def get_sp_dc():
    global sp_dc
    return sp_dc

# Global variables
access_token = ''
refresh_token = ''
sp_dc = ''
code_verifier = ''
code_challenge = ''
auth_url = ''
authorization_code = ''
token_response = ''

# init()
# me_response = get_currently_playing()
# print(me_response)