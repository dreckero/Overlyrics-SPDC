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
scope ='user-read-playback-state user-read-email user-read-private user-modify-playback-state'
token_url = 'https://accounts.spotify.com/api/token'
api_url = 'https://api.spotify.com/v1/me'

# Constants
VERBOSE_MODE = False  # If true, prints specific logs in the code (for debugging)

def init():
    resp = load_from_cache()
    #if file does not existe generates cache file
    if resp is None:
        generateCacheFile()
    else:
        _access_token = resp.get('access_token')
        _refresh_token = resp.get('refresh_token')
        #if file exists but tokens doesn't then updates cache file
        if _access_token is None or _refresh_token is None:
            generateCacheFile()

def generateCacheFile():
    global code_verifier, code_challenge, auth_url, authorization_code, token_response
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
    
    save_cache()
    
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
    
    save_cache()
    
    return data

def request_to_spotify(method, url, headers, params=None):
    try:
        global access_token, api_url
        
        endpoint = api_url + url
        
        if method == 'GET':
            response = requests.get(endpoint, headers=headers, params=params)
        elif method == 'POST':
            response = requests.post(endpoint, headers=headers, data=params)
        elif method == 'PUT':
            response = requests.put(endpoint, headers=headers, json=params)
            
        if response.status_code == 204:
            print("No content - Spotify is not open or no track is playing.") if VERBOSE_MODE else None
            return None

        if response.status_code == 429:
            print("Too many requests.") if VERBOSE_MODE else None
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
        print(f'Exception in request_to_spotify:\n{e}') if VERBOSE_MODE else None

def get_currently_playing():
    try:
        global progress_ms
        headers = {
            'Authorization': f'Bearer {access_token}'
        }
        response_data = request_to_spotify('GET', '/player/currently-playing', headers)
        if response_data:
            progress_ms = response_data.get('progress_ms')
        get_devices()
        # print('get_currently_playing')
        return response_data
    except Exception as e:
        print(f'Exception in get_currently_playing:\n{e}') if VERBOSE_MODE else None
        
def get_devices():
    try:
        global device_id
        headers = {
            'Authorization': f'Bearer {access_token}'
        }
        response_data = request_to_spotify('GET', '/player/devices', headers)
        for d in response_data.get('devices'):
            if d.get('is_active'):
                device_id = d.get('id')
        return response_data
    except Exception as e:
        print(f'Exception in get_devices:\n{e}') if VERBOSE_MODE else None
        
def start_resume_playback():
    try:
        global progress_ms, device_id
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }
        data = {
            "position_ms": progress_ms
        }
        url = '/player/play'
        if device_id:
            url = url + f'?device_id={device_id}'
        
        response_data = request_to_spotify('PUT', url, headers, data)
        return response_data
    except Exception as e:
        print(f'Exception in get_currently_playing:\n{e}') if VERBOSE_MODE else None
        
def pause_playback():
    try:
        headers = {
            'Authorization': f'Bearer {access_token}'
        }
        response_data = request_to_spotify('PUT', '/player/pause', headers)
        return response_data
    except Exception as e:
        print(f'Exception in get_currently_playing:\n{e}') if VERBOSE_MODE else None

def next_playback():
    try:
        headers = {
            'Authorization': f'Bearer {access_token}'
        }
        response_data = request_to_spotify('POST', '/player/next', headers)
        return response_data
    except Exception as e:
        print(f'Exception in get_currently_playing:\n{e}') if VERBOSE_MODE else None

def back_playback():
    try:
        headers = {
            'Authorization': f'Bearer {access_token}'
        }
        response_data = request_to_spotify('POST', '/player/previous', headers)
        return response_data
    except Exception as e:
        print(f'Exception in get_currently_playing:\n{e}') if VERBOSE_MODE else None

def volume_playback(volume):
    try:
        headers = {
            'Authorization': f'Bearer {access_token}'
        }
        url = '/player/volume'
        if device_id:
            url = url + f'?volume_percent={volume}&device_id={device_id}'
        response_data = request_to_spotify('PUT', url, headers)
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
    
    ask_sp_dc()
    
    auth_code = httpd.auth_code
    return auth_code

def save_to_cache(data, filename='cache.json'):
    with open(filename, 'w') as cache_file:
        json.dump(data, cache_file, indent=4)

def save_cache():
    global access_token, refresh_token, sp_dc
    save_to_cache({
        'access_token': access_token,
        'refresh_token': refresh_token,
        'sp_dc': sp_dc
    })

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

def set_progress_ms(ms):
    global progress_ms
    progress_ms = 0
    
def get_progress_ms():
    global progress_ms
    return progress_ms

def ask_sp_dc():
    global sp_dc
    # Open a Tkinter window to ask for the sp_dc cookie
    root = tk.Tk()
    root.withdraw()  # Hide the main window
    sp_dc = simpledialog.askstring("Input", "Please enter the 'sp_dc' cookie value from your browser:")
    save_cache()
    root.destroy()

def get_lyrics(track_id):
    headers = {
        'authorization': f'Bearer {access_token}',
        'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/101.0.4951.41 Safari/537.36',
        'app-platform': 'WebPlayer'
    }
    params = {
        'format': 'json',
        'market': 'from_token',
    }
    response = requests.get(f'https://spclient.wg.spotify.com/color-lyrics/v2/track/{track_id}', headers=headers, json=params)
    try:
        response_data = response.json()
    except ValueError:
        print("Response content is not valid JSON") if VERBOSE_MODE else None
        return None
    print(response_data)
    return response_data

# -----------------------------------------------

def init_syrics():
    global session, sp_dc
    session = requests.Session()
    session.cookies.set('sp_dc', sp_dc)
    session.headers['User-Agent'] = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/101.0.4951.41 Safari/537.36'
    session.headers['app-platform'] = 'WebPlayer'
    login_syrics()
        
def login_syrics():
        try:
            global session
            req = session.get('https://open.spotify.com/get_access_token?reason=transport&productType=web_player', allow_redirects=False)
            req_json = req.json()
            token = req_json.get('accessToken')
            session.headers['authorization'] = f"Bearer {token}"
        except Exception as e:
            print(f'Exception in login_syrics:\n{e}') if VERBOSE_MODE else None
        
def get_lyrics_syrics(track_id: str):
    global session
    init_syrics()
    params = 'format=json&market=from_token'
    req = session.get(f'https://spclient.wg.spotify.com/color-lyrics/v2/track/{track_id}', params=params)
    
    if req.status_code == 200:
        return req.json()
    elif req.status_code == 401:
        print('sp_dc invalid!')
    else:
        None
    
# -----------------------------------------------

# Global variables
access_token = ''
refresh_token = ''
sp_dc = ''
code_verifier = ''
code_challenge = ''
auth_url = ''
authorization_code = ''
token_response = ''
device_id = ''
progress_ms = 0
session = None

# init()
# me_response = get_currently_playing()
# print(me_response)