import requests
from requests.auth import HTTPBasicAuth
import base64, json
import webbrowser
import re
from secrets import *

class SpotifyClient():

    def __init__(self, client_id, client_secret, scope, redirect_uri):

        self.client_id = client_id 
        self.client_secret = client_secret 
        self.scope = scope
        self.redirect_uri = redirect_uri
        self.init_auth_header()
        self.get_token(self.authenticate_oauth())

    def init_auth_header(self):
        auth_header = {}
        message = f'{CLIENT_ID}:{CLIENT_SECRET}'
        message_bytes = message.encode("ascii")
        base64_bytes = base64.b64encode(message_bytes)
        base64_message = base64_bytes.decode('ascii')

        auth_header['Authorization'] = 'Basic ' + base64_message

        self.auth_header = auth_header

    def authenticate_oauth(self):
        
        auth_url = 'https://accounts.spotify.com/authorize'

        auth_data = {}
        auth_data['response_type'] = 'code'
        auth_data['client_id'] = CLIENT_ID
        auth_data['redirect_uri'] = redirect_uri
        auth_data['scope'] = scope

        res = requests.get(auth_url, headers=self.auth_header, params=auth_data)

        print(f'Please authorize: {res.url}\n')
        webbrowser.open(res.url)
        uri = input("Paste redirect URI here: ")

        code = re.findall(r'code=(.*)', uri)[0]

        return code

    def get_token(self, code):

        auth_url = 'https://accounts.spotify.com/api/token'

        auth_data = {}
        auth_data['code'] = code
        auth_data['client_id'] = self.client_id
        auth_data['grant_type'] = 'authorization_code'
        auth_data['redirect_uri'] = redirect_uri

        res = requests.post(auth_url, headers=self.auth_header, data=auth_data)

        res_json = res.json()
        access_token = '' if res.status_code != 200 else res_json['access_token']
        refresh_token = '' if res.status_code != 200 else res_json['refresh_token']

        if res.status_code == 200:
            self.access_token = access_token
            self.refresh_token = refresh_token

        else:
            print("ERROR; REFRESHING TOKEN")
            self.refresh_token()
            self.get_token(code)
        
    def refresh_token(self):

        auth_url = 'https://accounts.spotify.com/api/token'

        auth_data = {}
        auth_data['grant_type'] = 'refresh_token'
        auth_data['refresh_token'] = self.refresh_token

        res = requests.post(auth_url, headers=self.auth_header, data=auth_data)

        return res.status_code

    def _get_api_response(self, url, params={}):
        
        auth_header = {}
        auth_header['Authorization'] = 'Bearer ' + self.access_token

        res = requests.get(url, headers=auth_header, params=params)

        return res.json()

    def _post_to_api(self, url, body={}):
        
        auth_header = {}
        auth_header['Authorization'] = 'Bearer ' + self.access_token

        res = requests.post(url, headers=auth_header, data=body)

        return res.json()

    def get_user_id(self):

        url = 'https://api.spotify.com/v1/me'
        return self._get_api_response(url)['id']

    def get_user_playlists(self, id):
        
        url = f'https://api.spotify.com/v1/users/{id}/playlists'
        playlists = []

        end = False
        n = 0
        while not end:

            response = self._get_api_response(url, {'limit': 50})

            if response:
                n += len(response['items'])
                print(f"Collected {n} playlists")
                items = response['items']
                pl_list = [{'name': r['name'], 'id': r['id']} for r in items]
                playlists.extend(pl_list)
                url = response['next']

            if not response['next']:
                end = True

        return playlists

    def _get_tracks(self, url):

        tracks = []
        end = False
        n = 0
        while not end:

            response = self._get_api_response(url, {'limit': 50})

            if response:
                n += len(response['items'])
                print(f"Collected {n} tracks")
                items = response['items']
                trks_list = [{'name': r['track']['name'], 'uri': r['track']['uri']} for r in items]
                tracks.extend(trks_list)
                url = response['next']

            if not response['next']:
                end = True

        return tracks

    def get_saved_tracks(self):

        url = f'https://api.spotify.com/v1/me/tracks'
        return self._get_tracks(url)

    def get_playlist_tracks(self, id):

        url = f'https://api.spotify.com/v1/playlists/{id}/tracks'
        return self._get_tracks(url)


    def _check_if_playlist_exists(self, name, user_id):

        existing_playlists = self.get_user_playlists(user_id)
        names = [p['name'] for p in existing_playlists]
        if name in names:
            return existing_playlists[names.index(name)]['id']

        return None

    def create_playlist(self, user_id, name, desc, public=True):

        if playlist_id := self._check_if_playlist_exists(name, user_id):
            print("PLAYLIST ALREADY EXISTS...")
            print("Skipping creation")
            return playlist_id

        url = f'https://api.spotify.com/v1/users/{user_id}/playlists'
        pub = 'true' if public else 'false'

        body = {}
        body['name'] = name
        body['public'] = pub
        body['description'] = desc

        auth_header = {}
        auth_header['Authorization'] = 'Bearer ' + self.access_token

        res = requests.post(url, headers=auth_header, data=json.dumps(body))

        breakpoint()
        res_json = res.json()
        if res.status_code == 201:
            print(f"PLAYLIST {name} SUCCESSFULLY CREATED")
            playlist_id = res_json["id"]
            return playlist_id

        print(f"ERROR CREATING PLAYLIST")
        return -1

    def add_song_to_playlist(self, song_uris, playlist_id):

        url = f'https://api.spotify.com/v1/playlists/{playlist_id}/tracks'

        body = {}
        body['uris'] = song_uris

        res = self._post_to_api(url, body=json.dumps(body))

        print(f"ADDED {len(song_uris)} TO PLAYLIST")


    def add_liked_songs_to_playlist(self):

        user_id = self.get_user_id()
        playlists = self.get_user_playlists(user_id)
        saved_tracks = self.get_saved_tracks()

        name = "Liked Songs but public"
        desc = "Yes, this took me more time to automate than it would if I had done it manually"
        playlist_id = self.create_playlist(user_id, name, desc, public=True)

        playlist_tracks = self.get_playlist_tracks(playlist_id)

        saved_uris = {t['uri'] for t in saved_tracks}
        playlist_uris = {t['uri'] for t in playlist_tracks}

        uris_to_add = list(saved_uris - playlist_uris)

        chunks = [uris_to_add[i:i+100] for i in range(0, len(uris_to_add), 100)]

        for uris in chunks:
            self.add_song_to_playlist(uris, playlist_id)


if __name__ == "__main__":

    scope = 'user-library-read playlist-modify-public'
    redirect_uri = 'http://localhost:8888/callback'

    sp = SpotifyClient(CLIENT_ID, CLIENT_SECRET, scope, redirect_uri)

    sp.add_liked_songs_to_playlist()