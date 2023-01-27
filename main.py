import requests
import webbrowser
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlencode
import base64
import time
import threading
import sys

# Deezer constants ###########################################################
APP_ID = ''
APP_SECRET = ''
BASE_URL_DEEZER = 'https://api.deezer.com'
AUTH_URL_DEEZER = 'https://connect.deezer.com/oauth/auth.php?'
TOKEN_URL_DEEZER = 'https://connect.deezer.com/oauth/access_token.php?'

# Spotify constants ##########################################################
CLIENT_ID = ""
CLIENT_SECRET = ""
OAUTH_URL_SPOTIFY = "https://accounts.spotify.com/authorize"
AUTH_URL_SPOTIFY = 'https://accounts.spotify.com/api/token'
BASE_URL_SPOTIFY = 'https://api.spotify.com/v1/'

# Server constants ###########################################################
REDIRECT_URI = ''
HOST = ""
PORT = 0

# Parameters ##########################################################
spotify_playlist = ""
deezer_playlist = ""
playlistType = "public"
mode = 0
globalHeadersDeezer = {}
globalHeadersSpotify = {}

def command_arguments():
    global spotify_playlist
    global deezer_playlist
    global playlistType
    global mode

    if sys.argv[1] == "--help":
        print(f"Usage: {sys.argv[0]} -sP <SpotifyPlaylist> -dP <DeezerPlaylist> -m <mode> [-t <type>]")
        print("-sP,\t\t Spotify Playlist ID")
        print("-dP,\t\t Deezer Playlist ID")
        print("-m, \t\t Mode (1- Spotify to Deezer, 2- Deezer to Spotify")
        print("-t, \t\t Playlist type (\'public\' or \'private\')")
        quit()

    elif len(sys.argv) != 7 and len(sys.argv) != 9:
        print(len(sys.argv))
        raise SystemExit(f"{sys.argv[0]}: try \'{sys.argv[0]} --help\' for more information")

    else:
        for i, arg in enumerate(sys.argv):
            try:
                if arg == "-sP":
                    if sys.argv[i+1][0] == "-":
                        raise SystemExit(f"Invalid argument: {sys.argv[i+1]}")
                    spotify_playlist = sys.argv[i+1]
                elif arg == "-dP":
                    if sys.argv[i+1][0] == "-":
                        raise SystemExit(f"Invalid argument: {sys.argv[i+1]}")
                    deezer_playlist = sys.argv[i+1]
                elif arg == "-t":
                    if sys.argv[i+1][0] == "-":
                        raise SystemExit(f"Invalid argument: {sys.argv[i+1]}")
                    playlistType = sys.argv[i+1]
                elif arg == "-m":
                    if sys.argv[i+1][0] == "-":
                        raise SystemExit(f"Invalid argument: {sys.argv[i+1]}")
                    mode = int(sys.argv[i+1])
                elif arg[0] == "-":
                    print(f"Invalid argument: {sys.argv[i]}")
                    raise SystemExit(f"{sys.argv[0]}: try \'{sys.argv[0]} --help\' for more information")

            except:
                raise SystemExit(f"{sys.argv[0]}: try \'{sys.argv[0]} --help\' for more information")


# create server
class Server(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "application/json")
        self.end_headers()
        if 'deezer' in self.path:
            print("Deezer request")
            code = self.path.strip('/callback/deezer?code=')
            deezer_token = requestTokenDeezer(code)
            if deezer_token != -1:
                global globalHeadersDeezer
                globalHeadersDeezer = {
                    "access_token": deezer_token
                }
            else:
                shutThread.start()

        elif 'favicon' in self.path:
            pass

        else:
            print("Spotify request")
            code = self.path.strip('/callback?code=')
            spotify_token = requestTokenSpotify(code)
            global globalHeadersSpotify
            globalHeadersSpotify = {
                'Authorization': 'Bearer {token}'.format(token=spotify_token)
            }


        if globalHeadersSpotify != {} and globalHeadersDeezer != {}:
            if mode == "1":
                spotifyToDeezer(spotify_playlist, deezer_playlist)
            else:
                deezerToSpotify(spotify_playlist, deezer_playlist)

            shutThread.start()
            print("server shutdown")

server = HTTPServer((HOST, PORT), Server)
shutThread = threading.Thread(target=server.shutdown, daemon=True)

# popups for auth
def getCodeDeezer():
    perms = 'manage_library'
    webbrowser.open(AUTH_URL_DEEZER + 'app_id=' + APP_ID + '&redirect_uri=' + REDIRECT_URI + '/deezer' + '&perms=' + perms)

def getCodeSpotify(type):
    auth_headers = {
        "client_id": CLIENT_ID,
        "response_type": "code",
        "redirect_uri": REDIRECT_URI,
        "scope": "playlist-modify-" + type
    }
    webbrowser.open("https://accounts.spotify.com/authorize?" + urlencode(auth_headers))

# token requests
def requestTokenDeezer(code):
    try:
        print("making deezer request")
        access_token = requests.post(TOKEN_URL_DEEZER + "app_id={}&secret={}&code={}&output=json".format(APP_ID, APP_SECRET, code)).json()['access_token']
        headers = {
            "access_token": access_token
        }
        return access_token
    except requests.exceptions.JSONDecodeError:
        print("error in deezer request, try again later")
        return -1

def requestTokenSpotify(code):
    print("making spotify request")
    token_data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": "http://localhost:7777/callback"
    }
    encoded_credentials = base64.b64encode(CLIENT_ID.encode() + b':' + CLIENT_SECRET.encode()).decode("utf-8")
    token_headers = {
        "Authorization": "Basic " + encoded_credentials,
        "Content-Type": "application/x-www-form-urlencoded"
    }

    access_token = requests.post("https://accounts.spotify.com/api/token", data=token_data, headers=token_headers)
    access_token = access_token.json()['access_token']

    return access_token

# Search functions
def searchSpotify(headers, name, artist):
    data = {
        'q': '%artist:' + artist + '%track:' + name,
        'type': 'track',
        'limit': 1
    }
    search = requests.get(BASE_URL_SPOTIFY + 'search?', params=data, headers=headers).json()
    try:
        return search['tracks']['items'][0]['uri']
    except IndexError:
        return -1

def searchDeezer(headers, name, artist):
    params = {
        'q': 'artist:\"' + artist + '\"track:\"' + name + '\"'
    }
    search = requests.get(BASE_URL_DEEZER + '/search?', params=params, headers=headers).json()
    try:
        return search['data'][0]['id']
    except IndexError:
        return -1

# Add functions
def addSpotify(headers, playlist, uri):
    add = requests.post(BASE_URL_SPOTIFY + "playlists/" + playlist + "/tracks?uris=" + uri, headers=headers).json()
    try:
        error_code = add['error']
    except KeyError:
        error_code = 201

    return error_code # If added successfully returns code 201

def addDeezer(headers, playlist, songID):
    songs = songID
    access_token = headers['access_token']
    add = requests.post("https://api.deezer.com/playlist/{}/tracks?songs={}&access_token=".format(playlist, songs) + str(access_token))
    return add # If added successfully returns true


# Get tracks
def tracksSpotify(headers, playlistID):
    playlist = requests.get(BASE_URL_SPOTIFY + "playlists/" + str(playlistID), headers=headers).json()
    return playlist['tracks']


def tracksDeezer(headers, playlistID):
    tracks = requests.get(BASE_URL_DEEZER + "/playlist/" + str(playlistID) + "/tracks", headers=headers).json()
    return tracks


def spotifyToDeezer(playlistSpotify, playlistDeezer):
    print("adding tracks from spotify to deezer")
    tracks = tracksSpotify(globalHeadersSpotify, playlistSpotify)
    for i in range(tracks['total']):
        songID = searchDeezer(globalHeadersDeezer, tracks['items'][i]['track']['name'], tracks['items'][i]['track']['artists'][0]['name'])
        if songID != -1:
            added = addDeezer(globalHeadersDeezer, playlistDeezer, songID)
            if added.json():
                print("added " + tracks['items'][i]['track']['name'] + " to playlist")

    print("done")

def deezerToSpotify(playlistSpotify, playlistDeezer):
    print("adding tracks from deezer to spotify")
    tracks = tracksDeezer(globalHeadersDeezer, playlistDeezer)
    for i in range(tracks['total']):
        uri = searchSpotify(globalHeadersSpotify, tracks['data'][i]['title'], tracks['data'][i]['artist']['name'])
        if uri != -1:
            added = addSpotify(globalHeadersSpotify, playlistSpotify, uri)
            if added == 201:
                print("added " + tracks['data'][i]['title'] + " to playlist")
            else:
                print(added)
    print("done")


if __name__ == "__main__":  
    getCodeSpotify(playlistType)
    getCodeDeezer()
    server.serve_forever()
    time.sleep(1)
    server.server_close()
