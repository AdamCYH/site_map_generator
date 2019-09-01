import collections
import json
import re
import ssl
import sys
from multiprocessing.pool import ThreadPool
from urllib.request import urlopen, HTTPError

from bs4 import BeautifulSoup

"""
Many global variable is initiated for easy multi threading purpose.
although they look ugly.
"""
url_pattern = re.compile("^https?://.*$")
# used to store path that has been visited
visited = None
json_site_map = None
domain_pattern = None
# a deque to run bfs search, append initial url to the queue.
q = None


def build_site_map(starting_url, max_depth=10, max_thread=2):
    """
    This function is used to build site map with breadth first search.

    :param max_thread: maximun thread that will be used to process site_map
    :param starting_url: starting point of the search
    :param max_depth: max depth of levels that the function will search
    :return: Json string that contains list of map, which including page_urls, links, and images
    """
    # Urllib.request requires url to start with http:// or https://.
    if not validate_url(starting_url):
        print("[Error] Invalid url. Make sure it starts with http:// or https://")
        return {"error": "[Error] Invalid url. Make sure it starts with http:// or https://"}

    global json_site_map
    global visited
    global domain_pattern
    global q
    json_site_map = []
    visited = set()
    domain_pattern = None
    q = collections.deque()

    # depth should be smller than required max_depth/
    depth = 0
    # append initial url to the q
    q.append(starting_url)
    # Create a domain pattern for domain only search
    domain_pattern = re.compile(".*\." + find_domain(starting_url) + "\..*")
    # keep searching until q is empty or max_depth reaches.
    while q and depth < max_depth:
        # get current queue size, so we can do search by level.
        q_size = len(q)
        urls = []
        for i in range(q_size):
            # pop urls from head of the queue
            urls.append(q.popleft())

        # make the Pool of workers
        pool = ThreadPool(max_thread)

        # open the urls in their own threads
        # and return the results
        pool.map(process_url, urls)

        # close the pool and wait for the work to finish
        pool.close()
        pool.join()

        # increment depth since the whole level is searched.
        depth += 1
    print(json.dumps(json_site_map))
    return json.dumps(json_site_map)


def validate_url(url):
    """
    This function validates url
    :param url: root url that is inputed by the user.
    :return: boolean whether or not it starts with http:// or https://
    """
    if url_pattern.match(url):
        return True
    return False


def find_domain(url):
    """
    The function finds the domain if the input is a full url.
    :param url:
    :return:
    """
    return re.split('http://|https://|\\.', url)[-2]


def process_url(curr_url):
    global visited
    global json_site_map
    global domain_pattern
    global q
    # check if url is visited or not
    if curr_url not in visited:
        url_list, img_list = getContents(curr_url, domain_pattern)
        curr_json = {"page_url": curr_url,
                     "links": url_list,
                     "images": img_list}
        # extend the whole url list to the queue for next level of search
        q.extend(url_list)
        # append search result of current object to the site_map
        json_site_map.append(curr_json)
        # add to visited set so no repeated search
        visited.add(curr_url)


def getContents(url, domain_pattern):
    """
    This function scraps the website and return list of urls and images that belong to the target domain
    GIF is also treated as an image
    :param url: the site url that is currently being searched
    :param domain_pattern: domain pattern that checks if the url belongs to target domain
    :return: url list and image list
    """
    print("Opening URL: " + url)
    # Try to open the site with url,
    # validate if content type is plain text so we can scrap
    # if it is application, we dont want to read it.
    try:
        html = urlopen(url, context=ssl._create_unverified_context())
        if html.info().get_content_type() != "text/html":
            print("Not a site")
            return "Not a site", "N/A"
    except HTTPError as e:
        if e.code == 404:
            print("404 site not found")
            return "404 site not found", "N/A"
        else:
            print("Unknown error::: " + e.reason)
            return "Unknown error" + e.reason, "N/A"
    except UnicodeError:
        print("Unicode error::: ")
        return "Unicode error", "N/A"
    except ValueError:
        print("URL error")
        return "URL error", "N/A"


    print("Reading contents...")
    soup = BeautifulSoup(html.read(), "html.parser")
    url_list = set()
    img_list = set()
    # find all a and img tag which may contain url and img source
    for line in soup.find_all(["a", "img"]):
        if line.name == "a":
            found_url = line.get("href")
            # people use # as href holder, which we want to skip
            # it may not contains href, which we also skip
            if found_url is "#" or found_url is None:
                continue
            try:
                found_url = found_url.split("?")[0]
                # check if it belongs to target domain
                if domain_pattern.match(found_url):
                    # check if it is valid url, if not we append the url and hope it will work.
                    # TODO this might not work, it should be improved.
                    if not url_pattern.match(found_url):
                        url_list.add(url + found_url)
                    else:
                        url_list.add(found_url)
            except TypeError:
                continue
        else:
            # try to get src of the image
            img_url = line.get("src")
            try:
                if domain_pattern.match(img_url):
                    img_list.add(img_url)
            except TypeError:
                continue
    return list(url_list), list(img_list)


if __name__ == '__main__':
    print("Starting program")
    url = sys.argv[1]
    max_depth = int(sys.argv[2])
    max_thread = int(sys.argv[3])
    build_site_map(url, max_depth, max_thread)
    # build_site_map("https://www.mozilla.org", 2, 4)
