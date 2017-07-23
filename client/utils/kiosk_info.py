import codecs


def get_file_content(file_path):
    try:
        with codecs.open(file_path, 'r', "utf-8") as f:
            return f.read().strip()
    except IOError:
        return ''


def get_kiosk_home():
    return get_file_content("/home/mm/.kioskconfig/kiosk_home")


def get_kiosk_id():
    return get_file_content(get_kiosk_home() + ".kioskconfig/kiosk_id")
