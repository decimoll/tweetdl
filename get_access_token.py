#https://sleepless-se.net/2018/11/17/hwo-to-get-tweepy-accesstoken-on-python3/
#apiであなたのデータにアクセスしてよいかっていふよくある画面を出してアクセストークンを得る

import tweepy
import webbrowser
import urllib
import json

with open('./conf.json', 'r') as j:
    json_load = json.load(j)
    CONSUMER_KEY = json_load['api_key']
    CONSUMER_SECRET = json_load['api_secret_key']

def get_oauth_token(url:str)->str:
    querys = urllib.parse.urlparse(url).query
    querys_dict = urllib.parse.parse_qs(querys)
    return querys_dict["oauth_token"][0]

if __name__ == '__main__':

    auth = tweepy.OAuthHandler(CONSUMER_KEY, CONSUMER_SECRET)

    try:
        redirect_url = auth.get_authorization_url()
        print ("Redirect URL:", redirect_url)
    except tweepy.TweepError:
        print( "Error! Failed to get request token.")


    oauth_token = get_oauth_token(redirect_url)
    print("oauth_token:", oauth_token)
    auth.request_token['oauth_token'] = oauth_token

    # Please confirm at twitter after login.
    webbrowser.open(redirect_url)

    verifier = input("You can check Verifier on url parameter. Please input Verifier:")
    auth.request_token['oauth_token_secret'] = verifier

    try:
        auth.get_access_token(verifier)
    except tweepy.TweepError:
        print('Error! Failed to get access token.')

    print("access token key:", auth.access_token)
    print("access token secret:", auth.access_token_secret)

    with open("auth_info.text", mode="w") as file:
        text = "key:{}\nsecret:{}".format(auth.access_token, auth.access_token_secret)
        file.write(text)

    print("DONE")
