from syrics.api import Spotify
from syrics.core import *

token_url = "https://open.spotify.com/get_access_token?reason=transport&productType=web_player"
lyrics_url = "https://spclient.wg.spotify.com/color-lyrics/v2/track/"
sp_dc = "SPOTIFY_COOKIE_HERE"

sp = Spotify(sp_dc)

def GetLyricsOfCurrentSong():
    try:
        sp = Spotify(sp_dc)
        lyrics =  sp.get_lyrics(sp.get_current_song()['item']['id'])
        return format_lrc_local(lyrics, sp.get_current_song()['item'])
    except Exception as e:
        return ''
    
def GetLyricsOfId(id):
    try:
        lyrics =  sp.get_lyrics(id)
        #print(lyrics)
        #print(format_lrc_local(lyrics, sp.get_current_song()['item']))
        return format_lrc_local(lyrics, sp.get_current_song()['item'])
    except Exception as e:
        return ''


def format_lrc_local(lyrics_json, track_data):
    try:
        lyrics = lyrics_json
        minutes, seconds = divmod(int(track_data["duration_ms"]) / 1000, 60)
        lrc = [
            f'[ti:{track_data["name"]}]',
            '[al:{'+track_data["album"]['name']+'}]',
            '[ar:{'+track_data["artists"][0]['name']+'}]',
            f'[length: {minutes:0>2.0f}:{seconds:05.2f}]',
        ]
        for lines in lyrics_json['lyrics']['lines']:
            if lyrics_json['lyrics']['syncType'] == 'UNSYNCED':
                lrc.append(lines['words'])
            else:
                duration = int(lines['startTimeMs'])
                minutes, seconds = divmod(duration / 1000, 60)
                lrc.append(f'[{minutes:0>2.0f}:{seconds:05.2f}] {lines["words"]}')
        return '\n'.join(lrc)
    except Exception as e: 
        return None

#GetLyricsOfId("5KIYVXGdws1ZhZYNJHo0st")