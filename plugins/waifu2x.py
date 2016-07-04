# -*- coding: utf-8 -*-

from PIL import Image
import io

post_url = "http://waifu2x.udp.jp/api"


def main(tg):
    if 'reply_to_message' in tg.message and 'document' in tg.message[
            'reply_to_message']:
        document = tg.message['reply_to_message']['document']
    elif 'document' in tg.message:
        document = tg.message['document']
    else:
        tg.send_message(
            "Reply to an image with /waifu2x or use it as a caption to upscale")
        return
    mime_type = document['mime_type']
    if 'image' not in mime_type:
        tg.send_message("I can only upscale images :(")
    elif 'gif' in mime_type:
        tg.send_message("I can't upscale gifs :(")
    format = mime_type.replace('image/', '')
    photo_id = document['file_id']
    tg.send_chat_action("upload_photo")
    document_obj = tg.get_file(photo_id)
    file_path = tg.download_file(document_obj)
    file = Image.open(file_path)
    file = check_size(file)
    if file:
        file = create_image_obj(file, format)
        name = "{}.{}".format(photo_id, format)
        fields = {'file': (name, file.read()), 'noise': 2, 'scale': 2}
        x = tg.http.request('POST', post_url, fields=fields)
        tg.send_document((name, x.data))
    else:
        tg.send_message("This image is too big for me to waifu2x :(")


def check_size(image):
    if image.size[0] < 1280 and image.size[1] < 1280:
        return image
    if image.size[0] > 2560 or image.size[1] > 2560:
        return None
    else:
        largest = image.size[0] if image.size[0] > image.size[
            1] else image.size[1]
        scale = 1279 / largest
        new_dimensions = (int(image.size[0] * scale), int(image.size[1] *
                                                          scale))
        return image.resize(new_dimensions, Image.LANCZOS)


def create_image_obj(image, format):
    compressed_image = io.BytesIO()
    image.save(compressed_image, format=format)
    compressed_image.seek(0)
    return compressed_image


parameters = {
    'name': "Waifu2x",
    'short_description': "Upscale images!",
    'permissions': '11'
}

arguments = {'text': ["^/waifu2x"], 'caption': ["^/waifu2x"]}
