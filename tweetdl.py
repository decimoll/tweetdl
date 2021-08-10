import tweepy
import json
import time
import argparse
import sys
import os
import pprint
import urllib.error
import urllib.request

os.getcwd()
with open(os.path.dirname(os.path.abspath(__file__)) + '/conf.json', 'r') as j:
    json_load = json.load(j)
    CONSUMER_KEY = json_load['api_key']
    CONSUMER_SECRET = json_load['api_secret_key']
    ACCESS_TOKEN = json_load['access_token']
    ACCESS_TOKEN_SECRET = json_load['access_token_secret']
    USER_ID = json_load['user_id']
    ROOT_DIR = json_load['root_dir']
    WAIT = json_load['wait']

FIFTEEN_MINUTES = 20 * 60

# 禁則文字の処理
def replace_prohibited_chars(s):
    pc = [['/', '／'], [':', '：'], ['.', '．'], ['*', '＊'], ['<', '＜'], ['>', '＞'], ['|', '｜'], ['?', '？'], ['\"', '”'], ['\0', ''], ['\n', ' ']]
    r = s
    for c in pc:
        r = r.replace(c[0], c[1])
    return r

# https://qiita.com/lamrongol/items/3f14634594d388c96c03
# ↑のコードを一部改変
limit_handled_count = 0;

def limit_handled(cursor):
    global limit_handled_count
    while True:
        try:
            yield cursor.next()
        except tweepy.error.TweepError:
            if limit_handled_count < 3:
                print('Twitter rate limit 15 minutes wait...')
                limit_handled_count += 1
                time.sleep(FIFTEEN_MINUTES)
            else:
                print('Rate limit 4 times.')
                exit(1)
        except StopIteration:
            print("fetch end")
            return None

# fetch_*も真似した
def fetch_favs(api):
    favs_statuses = []
    print('start fetching favs')
    for status in limit_handled(tweepy.Cursor(api.favorites, id=USER_ID, tweet_mode='extended').items()):
        json_result = status._json
        print(json_result['full_text'])
        favs_statuses.append(json_result)
        time.sleep(WAIT)
    return favs_statuses

def fetch_retweets(api):
    retweeted_statuses = []
    print('start fetching retweets')
    for status in limit_handled(tweepy.Cursor(api.user_timeline, id=USER_ID, tweet_mode='extended').items()):
        json_result = status._json
        if 'retweeted_status' in json_result:
            print(json_result['retweeted_status']['full_text'])
            retweeted_statuses.append(json_result['retweeted_status'])
        time.sleep(WAIT)
    return retweeted_statuses

def dl_images(rs, out_dir, file_stem):
    count = 0
    for m in rs['extended_entities']['media']:
        url = m['media_url_https'] + ':large'
        extension = '.' + os.path.basename(m['media_url_https']).split('.')[-1]
        file_name = file_stem + '_' + str(count) + extension
        file_path = out_dir + file_name
        if not args.duplicate and os.path.isfile(file_path):
            print(file_path + ' already exists.')
            return 0
        try:
            with urllib.request.urlopen(url) as web_file, open(file_path, 'wb') as local_file:
                local_file.write(web_file.read())

            print(file_path)
        except urllib.error.URLError as e:
            print(e)
            return 1
        count += 1
    return 0

def dl_gif(rs, out_dir, file_stem):
    if dl_video(rs, out_dir, file_stem) == 1:
        return 1
    return 0

def dl_video(rs, out_dir, file_stem):
    urls = []
    bitrates = []
    for v in rs['extended_entities']['media'][0]['video_info']['variants']:
        if 'bitrate' in v:
            urls.append(v['url'])
            bitrates.append(v['bitrate'])
    url = urls[bitrates.index(max(bitrates))]
    file_name = file_stem + '.mp4'
    file_path = out_dir + file_name
    if not args.duplicate and os.path.isfile(file_path):
        print(file_path + ' already exists.')
        return 0
    try:
        with urllib.request.urlopen(url) as web_file, open(file_path, 'wb') as local_file:
            local_file.write(web_file.read())
        print(file_path)
    except urllib.error.URLError as e:
        print(e)
        return 1
    return 0

def dl_text(rs, out_dir, file_stem):
    file_name = file_stem + '.json'
    file_path = out_dir + file_name
    if not args.duplicate and os.path.isfile(file_path):
        print(file_path + ' already exists.')
        return 0
    with open(file_path, 'w')  as j:
        json.dump(rs, j, indent=2, ensure_ascii=False)
    return 0

def download(api, rs):
    #print(rs['full_text'])
    user_id = rs['user']['id_str']
    dir_name = replace_prohibited_chars(rs['user']['name'] + '_@' + rs['user']['screen_name'] + '_' + user_id)
    out_dir = ROOT_DIR + dir_name + '/'
    files = os.listdir(ROOT_DIR)
    dirs = [f for f in files if os.path.isdir(os.path.join(ROOT_DIR, f))]
    for d in dirs:
        # 名前が變はってもユーザIDは變はらないと思ふからIDでフォルダを検索
        if user_id == d.split('_')[-1]:
            # フォルダ名のユーザ名が現在のユーザ名と異なるならば
            if d != dir_name:
                os.rename(ROOT_DIR + d, ROOT_DIR + dir_name)
            break
    os.makedirs(out_dir, exist_ok=True)
    WORD_COUNT = 16 # ファイル名に使う本文の先頭文字数
    file_stem = replace_prohibited_chars(rs['full_text'][:WORD_COUNT] + '_' + rs['id_str'])
    print(file_stem)
    dl_text(rs, out_dir, file_stem)
    if 'extended_entities' in rs:
        tweet_type = rs['extended_entities']['media'][0]['type']
        if tweet_type == 'photo':
            if dl_images(rs, out_dir, file_stem) == 1:
                return 1
        elif tweet_type == 'animated_gif':
            if dl_gif(rs, out_dir, file_stem) == 1:
                return 1
        elif tweet_type == 'video':
            if dl_video(rs, out_dir, file_stem) == 1:
                return 1
        else:
            print('unknown type: ' + tweet_type)
            return 1
    return 0


###__MAIN__###
parser = argparse.ArgumentParser(prog='tweetdl', 
        usage='tweetdl.py [-h] [--id] [-f] [-n] [-o OUT_DIR] [-d]', 
        description='Download tweets.')
parser.add_argument('--id', type=int, nargs='*', help='some tweets')
parser.add_argument('-f', '--favorites', action='store_true', help='All my favorites')
parser.add_argument('-o', '--outdir', default=ROOT_DIR, help='Output dir')
parser.add_argument('-n', '--normal', action='store_true', help='Normal mode. Download my retweets and unretweet.')
parser.add_argument('-d', '--duplicate', action='store_true', help='Ignore duplicate')
args = parser.parse_args()

if len(sys.argv) == 1:
    parser.print_help()
    exit(0)

auth = tweepy.OAuthHandler(CONSUMER_KEY, CONSUMER_SECRET)
auth.set_access_token(ACCESS_TOKEN, ACCESS_TOKEN_SECRET)
api = tweepy.API(auth)

ROOT_DIR = args.outdir

if args.id != None:
    for ids in args.id:
        if ids > 0:
            tweet = api.get_status(id=ids, tweet_mode='extended')._json
            print(tweet)
            download(api, tweet)
        else:
            print('ERROR: tweet id must be larger than 0.')

if args.favorites:
    favs_statuses = fetch_favs(api)
    for f in favs_statuses:
        download(api, f)
    
if args.normal:
    retweeted_statuses = fetch_retweets(api)
    for r in retweeted_statuses:
        a = download(api, r)
        #print(a)
        if a == 0:
            api.unretweet(r['id'])


