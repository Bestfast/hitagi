import concurrent.futures
import json
from PIL import Image
import io
import os

base_url = "https://danbooru.donmai.us"
api_key = None

try:
    JSONDecodeError = json.JSONDecodeError
except AttributeError:
    JSONDecodeError = ValueError


def main(tg):
    global api_key
    if tg.inline_query:
        api_key = tg.config['DANBOORU']['api_key']
        page = int(tg.inline_query['offset']) if tg.inline_query['offset'] else 1
        query = "rating:s" if tg.inline_query['matched_regex'] == inline_arguments[
            0] else tg.inline_query['match'][1]
        query = query.split(',')
        result = get_post(tg.http, query, page)
        if result:
            executor = concurrent.futures.ThreadPoolExecutor(max_workers=8)
            futures = [executor.submit(create_box, tg, pic) for pic in result]
            concurrent.futures.wait(futures)
            offset = page + 1 if len(result) == 40 else ''
            response = [box.result() for box in futures]
            tg.answer_inline_query([box for box in response if box],
                                   cache_time=86400,
                                   next_offset=offset)
        else:
            tg.answer_inline_query([], cache_time=0)
    elif tg.message['pm_parameter']:
        id = tg.message['pm_parameter'].replace('danbooru', '')
        photo = return_photo(tg.http, id)
        if photo:
            photo_name = "{}.png".format(id)
            file_obj = io.BytesIO()
            photo.save(file_obj, format='PNG')
            file_obj.seek(0)
            tg.send_document((photo_name, file_obj.read()))
        else:
            tg.send_message("Sorry I was unable to retrieve this photo :(")
    elif tg.message:
        keyboard = [[{'text': "Go Inline", 'switch_inline_query': "pic "}]]
        message_text = "Searching for anime pictures is an inline only feature."
        tg.send_message(message_text, reply_markup=tg.inline_keyboard_markup(keyboard))


def create_box(tg, pic):
    try:
        image_url = base_url + pic['file_url']
    except KeyError:
        return
    thumb_url = base_url + pic['preview_file_url']
    keyboard = [[]]
    if 'source' in pic:
        keyboard[0].append({'text': "Source", 'url': pic['source']})
    pm_parameter = tg.pm_parameter("danbooru" + str(pic['id']))
    keyboard[0].append({'text': "Download", 'url': pm_parameter})
    width = pic['image_width']
    height = pic['image_height']
    return tg.inline_query_result_photo(
        image_url,
        thumb_url,
        photo_width=width,
        photo_height=height,
        reply_markup=tg.inline_keyboard_markup(keyboard))


def get_post(http, tags, page):
    tags[-1] = get_tags(http, tags[-1])
    tags = ','.join(tags)
    fields = {
        'api_key': api_key,
        'limit': 40,
        'tags': tags.replace(' ', '_') + ' rating:safe',
        'page': page
    }
    request = http.request('GET', base_url + '/posts.json', fields=fields)
    if request.status == 200:
        try:
            return json.loads(request.data.decode('UTF-8'))
        except JSONDecodeError:
            return
    else:
        return


def get_tags(http, query):
    url = base_url + "/tags/autocomplete.json?search[name_matches]={}*".format(
        query)
    request = http.request('GET', url)
    if request.status == 200:
        try:
            result = json.loads(request.data.decode('UTF-8'))
            if result:
                return result[0]['name']
            return query
        except JSONDecodeError:
            return query
    else:
        return query
        
def return_photo(http, id):
    file_path = "data/files/danbooru/{}.png".format(id)
    try:
        return Image.open(file_path)
    except FileNotFoundError:
        pass
    url = base_url + "/posts/{}.json"
    request = http.request('GET', url.format(id))
    if request.status == 200:
        try:
            result = json.loads(request.data.decode('UTF-8'))
        except JSONDecodeError:
            return
        image = download_photo(http, result['large_file_url'])
        if image:
            try:
                image.save(file_path)
            except FileNotFoundError:
                os.makedirs('data/files/danbooru')
            return Image

def download_photo(http, url):
    request = http.request('GET', base_url + url)
    if request.status == 200:
        image_obj = io.BytesIO(request.data)
        return Image.open(image_obj)


parameters = {
    'name': "Danbooru",
    'short_description':
    "Search for anime art inline using animepic <search_term>",
    'long_description':
    "This is an inline only function which allows you to search Danbooru for anime art. Simply "
    "initiate an inline query from any chat and type in <code>pic &lt;search_term&gt;</code>.",
    'inline_only': True
}

arguments = {
    'text': [
        "^/pic$"
    ]
}

inline_arguments = ['^/?(danbooru|animepic|pic)$', '^/?(danbooru|animepic) (.*)']
