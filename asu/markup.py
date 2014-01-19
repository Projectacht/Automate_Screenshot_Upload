def to_url(page_url, thumbnail_url):
    return page_url


def to_html(page_url, thumbnail_url):
    return "<a href=\"{}\"><img src=\"{}\" /></a>".format(page_url,
                                                          thumbnail_url)


def to_bbcode(page_url, thumbnail_url):
    return "[URL={}][IMG]{}[/IMG][/URL]".format(page_url, thumbnail_url)
