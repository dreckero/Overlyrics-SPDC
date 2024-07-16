import os.path
import pathlib

full_path = os.path.realpath(__file__)
LYRICS_FOLDER = str(pathlib.Path(__file__).parent.resolve()) + "\\lyrics"

def SaveLyrics(sp_song_id, lyrics_text):
    full_file_path = LYRICS_FOLDER + "\\" + sp_song_id + ".lrc"
    #checks if folder exists
    if(os.path.isdir(LYRICS_FOLDER) == False):
        os.mkdir(LYRICS_FOLDER)
    #checks if song exists 
    if(os.path.isfile(full_file_path) == False):
        #song doesn't exists. We create the song.
        f = open(full_file_path, "a", encoding='utf-8')
        f.write(lyrics_text)
        f.close()
    else:
        return False
    return True

def SearchLyricsOnFolder(sp_song_id):
    full_file_path = LYRICS_FOLDER + "\\" + sp_song_id + ".lrc"
    if(os.path.isfile(full_file_path)):
        #song exists. we return the content from the file
        f = open(full_file_path, "r")
        return {
            'lyrics': f.read(),
            'result': True
        }
    else:
        #song doesn't exists. We return nothing
        return {
            'lyrics': '',
            'result': False
        }
    