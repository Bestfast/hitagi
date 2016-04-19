def main(tg_api):  # This is where plugin_handler will send msg
    tg_api.send_chat_action('typing')
    if 'reply_to_message' in tg_api.msg:
        tg_api.send_message(tg_api.msg['reply_to_message']['text'])
    elif len(tg_api.msg['match']) > 1:
        tg_api.send_message(tg_api.msg['match'][1])
    else:
        tg_api.send_message("What do I echo?")


plugin_info = {
    'name': "Echo Plugin",
    'Info': "Echo plugin demonstrates how plugins work!",
    'Usage': [
        "/echo"
    ],
    'arguments': {
        'text': [
            "^[/]echo$",
            "^[/](echo) (.*)"
        ]
    }
}
