# -*- coding: utf-8 -*-


import concurrent.futures
import html
import json
import time

import _mysql_exceptions

base_url = "https://anilist.co/api/"
client_id = None
client_secret = None
token = None
youtube = "https://www.youtube.com/watch?v={}"


def main(tg):
    global client_id, client_secret, token
    try:
        client_id = tg.config['ANILIST']['client_id']
        client_secret = tg.config['ANILIST']['client_secret']
    except KeyError:
        return
    if client_id and client_secret:
        token = client_credentials(tg)
        if token:
            if tg.message:
                handle_message(tg)
            elif tg.inline_query:
                handle_inline_query(tg)
        elif tg.message:
            tg.send_message("It seems that Anilist is down right now :(")
        elif tg.inline_query:
            tg.answer_inline_query([], cache_time=0)


def handle_message(tg):
    tg.send_chat_action('typing')
    if tg.message['flagged_message']:
        match = tg.plugin_data
    else:
        match = tg.message['matched_regex']
    if match in arguments['text'][0:2]:
        return_anime_result(tg)
    elif match in arguments['text'][2:4]:
        return_character_result(tg)
    elif match in arguments['text'][4:6]:
        return_manga_result(tg)


def handle_inline_query(tg):
    executor = concurrent.futures.ThreadPoolExecutor(max_workers=8)
    if tg.inline_query['offset']:
        query_start, query_end = [int(x) for x in tg.inline_query['offset'].split(',')]
    else:
        query_start, query_end = 0, 8
    if tg.inline_query['matched_regex'] == inline_arguments[2]:
        search_results = search('character/search/{}', tg.http, tg.inline_query['match'])
        if search_results:
            futures = [executor.submit(create_character_box, tg, character) for character
                       in search_results[query_start:query_end]]
    elif tg.inline_query['matched_regex'] == inline_arguments[3]:
        search_results = search('manga/search/{}', tg.http, tg.inline_query['match'])
        if search_results:
            futures = [executor.submit(create_manga_box, tg, manga) for manga in search_results[query_start:query_end]]
    else:
        if tg.inline_query['matched_regex'] == inline_arguments[1]:
            search_results = search('anime/search/{}', tg.http, tg.inline_query['match'])
        else:
            url = base_url + 'browse/anime'
            fields = {'year': 2016, 'season': "spring", 'access_token': token, 'status': "Currently Airing",
                      'type': "TV", 'sort': "popularity-desc"}
            post = tg.http.request('GET', url, fields=fields)
            search_results = json.loads(post.data.decode('UTF-8'))
        if search_results:
            futures = [executor.submit(create_anime_box, tg, anime) for anime in search_results[query_start:query_end]]
    if search_results:
        concurrent.futures.wait(futures)
        offset = '{},{}'.format(query_end, query_end + 8) if len(search_results) > query_end else ""
        tg.answer_inline_query([box.result() for box in futures], cache_time=259200, next_offset=offset)
    else:
        tg.answer_inline_query(list(), cache_time=259200)


def return_anime_result(tg):
    if tg.message['matched_regex'] == arguments['text'][0]:
        tg.send_message("Which anime should I look for?", flag_message={'plugin_data': arguments['text'][0]})
        return
    elif tg.message['flagged_message']:
        if 'text' in tg.message:
            query = tg.message['text']
        else:
            tg.send_message("I can only search for anime using text :(")
            return
    else:
        query = tg.message['match']
    search_results = search('anime/search/{}', tg.http, query)
    if search_results == int:
        tg.send_message("Anilist seems to be down right now :(")
    elif search_results:
        anime_id = search_results[0]['id']
        tg.send_message(**anime_model(tg, anime_id))
    else:
        tg.send_message("I couldn't find any results :(")


def return_manga_result(tg):
    if tg.message['matched_regex'] == arguments['text'][4]:
        tg.send_message("Which manga should I look for?", flag_message={'plugin_data': arguments['text'][4]})
        return
    elif tg.message['flagged_message']:
        if 'text' in tg.message:
            query = tg.message['text']
        else:
            tg.send_message("I can only search for manga using text :(")
            return
    else:
        query = tg.message['match']
    search_results = search('manga/search/{}', tg.http, query)
    if search_results == int:
        tg.send_message("Anilist seems to be down right now :(")
    elif search_results:
        manga_id = search_results[0]['id']
        tg.send_message(**manga_model(tg, manga_id))
    else:
        tg.send_message("I couldn't find any results :(")


def return_character_result(tg):
    if tg.message['matched_regex'] == arguments['text'][2]:
        tg.send_message("Which character should I look for?", flag_message={'plugin_data': arguments['text'][2]})
        return
    elif tg.message['flagged_message']:
        if 'text' in tg.message:
            query = tg.message['text']
        else:
            tg.send_message("I can only search for characters using text :(")
            return
    else:
        query = tg.message['match']
    search_results = search('character/search/{}', tg.http, query)
    if search_results == int:
        tg.send_message("Anilist seems to be down right now :(")
    elif search_results:
        character_id = search_results[0]['id']
        tg.send_message(**character_model(tg, character_id))
    else:
        tg.send_message("I couldn't find any results :(")


def create_anime_box(tg, anime):
    message = anime_model(tg, anime['id'])
    message_content = tg.input_text_message_content(message['text'], parse_mode="markdown")
    description = "{} - {}".format(anime['title_japanese'], anime['airing_status'].title())
    box = tg.inline_query_result_article(anime['title_romaji'], message_content, reply_markup=message['reply_markup'],
                                         thumb_url=anime['image_url_lge'], description=description)
    return box


def create_character_box(tg, character):
    message, big_model = character_model(tg, character['id'], True)
    message_content = tg.input_text_message_content(message['text'], parse_mode="markdown")
    title = "{} {}".format(character['name_first'], character['name_last'])
    box = tg.inline_query_result_article(title, message_content, reply_markup=message['reply_markup'],
                                         thumb_url=character['image_url_lge'], description=big_model['name_japanese'])
    return box


def create_manga_box(tg, manga):
    message = manga_model(tg, manga['id'])
    message_content = tg.input_text_message_content(message['text'], parse_mode="markdown")
    box = tg.inline_query_result_article(manga['title_romaji'], message_content, reply_markup=message['reply_markup'],
                                         thumb_url=manga['image_url_lge'], description=manga['title_japanese'])
    return box


def anime_model(tg, anime_id):
    anime = get_model('anime/{}', tg.http, anime_id)
    if anime:
        message = "*{}* - {}".format(anime['title_romaji'], anime['title_japanese'])
        if anime['airing_status'] == "currently airing":
            message += '\n*Airs in {}*'

        if 'image_url_banner' in anime and anime['image_url_banner']:
            message += '[​]({})'.format(anime['image_url_banner'])
        elif 'image_url_lge' in anime and anime['image_url_lge']:
            message += '[​]({})'.format(anime['image_url_lge'])

        message += "\n\n*Type:* {}".format(anime['type'])
        message += "\n*Status:* {}".format(anime['airing_status'].title())
        if anime['airing_status'] == "currently airing":
            episodes, hours = parse_date(anime)
            message = message.format(hours)
            message += "\n*Episode Count:* {}/{}".format(episodes - 1, anime['total_episodes'])
        else:
            message += "\n*Episode Count:* {}".format(anime['total_episodes'])
        message += "\n*Score:* {}".format(anime['average_score'])
        message += "\n*Genres:* {}".format(', '.join(anime['genres']))

        if anime['description']:
            message += "\n\n{}".format(clean_description(anime['description']))

        anime_url = "https://www.anilist.co/anime/{}".format(anime['id'])
        keyboard = [[{'text': 'Full Anime Page', 'url': anime_url}]]
        if anime['youtube_id']:
            youtube_url = "https://www.youtube.com/watch?v={}".format(anime['youtube_id'])
            keyboard[0].append({'text': "Youtube Trailer", 'url': youtube_url})

        return {'text': message, 'reply_markup': tg.inline_keyboard_markup(keyboard), 'parse_mode': "markdown"}
    return {'text': "Anilist seems to be down :("}


def character_model(tg, character_id, inline=False):
    character = get_model('character/{}', tg.http, character_id)
    if character:
        message = "*{} {}*".format(character['name_first'], character['name_last'])

        if character['name_alt']:
            message += "\n*Aliases:* {}".format(character['name_alt'])

        if 'image_url_banner' in character and character['image_url_banner']:
            message += '[​]({})'.format(character['image_url_banner'])
        elif 'image_url_lge' in character and character['image_url_lge']:
            message += '[​]({})'.format(character['image_url_lge'])

        if character['info']:
            message += "\n\n{}".format(clean_description(character['info']))

        character_page = "http://anilist.co/character/{}".format(character['id'])
        keyboard = [[{'text': "Full Character Page", 'url': character_page}]]

        msg_contents = {'text': message, 'reply_markup': tg.inline_keyboard_markup(keyboard), 'parse_mode': "markdown"}
        if inline:
            return msg_contents, character
        else:
            return msg_contents
    return {'text': "Anilist seems to be down :("}


def manga_model(tg, manga_id):
    manga = get_model('manga/{}', tg.http, manga_id)
    if manga:
        message = "*{}* - {}".format(manga['title_romaji'], manga['title_japanese'])

        if 'image_url_banner' in manga and manga['image_url_banner']:
            message += '[​]({})'.format(manga['image_url_banner'])
        elif 'image_url_lge' in manga and manga['image_url_lge']:
            message += '[​]({})'.format(manga['image_url_lge'])

        message += "\n*Type:* {}".format(manga['type'])
        message += "\n*Status:* {}".format(manga['publishing_status'].title())

        if manga['total_chapters']:
            message += "\n*Chapter Count:* {}".format(manga['total_chapters'])
        if manga['total_volumes']:
            message += "\n*Volume Count:* {}".format(manga['total_volumes'])

        message += "\n*Score:* {}".format(manga['average_score'])
        message += "\n*Genres: {}*".format(', '.join(manga['genres']))
        if manga['description']:
            message += "\n\n{}".format(clean_description(manga['description']))

        manga_page = "http://anilist.co/manga/{}".format(manga['id'])
        keyboard = [[{'text': "Full Manga Page", 'url': manga_page}]]
        return {'text': message, 'reply_markup': tg.inline_keyboard_markup(keyboard), 'parse_mode': "markdown"}
    return {'text': "Anilist seems to be down :("}


def search(method, http, query):
    url = base_url + method.format(query)
    post = http.request('GET', url, fields={'access_token': token})
    if post.status == 200:
        try:
            return json.loads(post.data.decode('UTF-8'))
        except json.decoder.JSONDecodeError:
            return
    return


def get_model(method, http, query_id):
    url = base_url + method.format(query_id)
    post = http.request('GET', url, fields={'access_token': token})
    if post.status == 200:
        try:
            return json.loads(post.data.decode('UTF-8'))
        except json.decoder.JSONDecodeError:
            return
    return


def client_credentials(tg):
    try:
        tg.database.query('SELECT access_token FROM anilist_tokens WHERE grant_type="client_credentials" '
                          'AND expires > FROM_UNIXTIME({})'.format(int(time.time() - 60, )))
        query = tg.database.store_result()
        rows = query.fetch_row()
        if rows:
            return rows[0][0]
    except _mysql_exceptions.ProgrammingError:
        tg.cursor.execute("CREATE TABLE anilist_tokens(access_token VARCHAR(64) NOT NULL, token_type VARCHAR(64), "
                          "expires DATETIME, refresh_token VARCHAR(64), grant_type VARCHAR(64), user_id BIGINT)")
    url = base_url + "auth/access_token"
    headers = {
        'grant_type': "client_credentials",
        'client_id': client_id,
        'client_secret': client_secret
    }
    post = tg.http.request_encode_body('POST', url, fields=headers)
    try:
        result = json.loads(post.data.decode('UTF-8'))
    except json.decoder.JSONDecodeError:
        return post.status
    tg.cursor.execute('DELETE FROM anilist_tokens WHERE grant_type="client_credentials"')
    tg.cursor.execute("INSERT INTO anilist_tokens(access_token, token_type, expires, grant_type) VALUES(%s, %s, "
                      "FROM_UNIXTIME(%s), %s);",
                      (result['access_token'], result['token_type'], result['expires'], "client_credentials"))
    return result['access_token']


def clean_description(description):
    if description:
        description = description[:description.rfind('\n')].replace('<br>', '')
        if len(description) > 300:
            description = description[:250] + "...."
        return html.unescape(description).replace('`', '\'')


def parse_date(anime):
    try:
        next_episode = anime['airing']['next_episode']
    except TypeError:
        return 0, "Unknown"
    time_left = int(anime['airing']['countdown'])
    if time_left < 240:
        time_statement = "A few minutes"
    elif time_left < 3600:
        time_statement = "{} minutes".format(int(time_left / 60))
    elif 86399 > time_left > 3600:
        time_statement = "{} hours".format(int(time_left / 3600))
    else:
        time_statement = "{} days".format(int(time_left / 86400))
    return next_episode, time_statement


parameters = {
    'name': "Anilist",
    'short_description': "Search for anime, characters, and manga.",
    'long_description': "Search anilist using /anime, /character, and /manga for information like rating, summary, and "
                        "episode count. You can also use this command inline from within any chat.",
    'permissions': True
}

arguments = {
    'text': [
        "^/anime$", "^/anime (.*)",
        "^/character$", "^/character (.*)",
        "^/manga$", "^/manga (.*)",
    ]
}

inline_arguments = [
    '^/?anime$', '^/?anime (.*)',
    '^/?character (.*)', '^/?manga (.*)'
]
