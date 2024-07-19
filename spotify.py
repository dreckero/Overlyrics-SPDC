from syrics.api import Spotify
from syrics.core import *
from apicallspotify import *

token_url = "https://open.spotify.com/get_access_token?reason=transport&productType=web_player"
lyrics_url = "https://spclient.wg.spotify.com/color-lyrics/v2/track/"

def GetLyricsOfCurrentSong(item):
    try:
        # sp = Spotify(get_sp_dc())
        # lyrics =  sp.get_lyrics(item['id'])
        lyrics = get_lyrics_syrics(item['id'])
        return format_lrc_local(lyrics, item)
    except Exception as e:
        # sp = Spotify(get_sp_dc())
        return None

def format_lrc_local(lyrics_json, track_data):
    try:
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