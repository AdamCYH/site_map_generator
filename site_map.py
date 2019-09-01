import collections
import json
import re
import ssl
import sys
from multiprocessing.pool import ThreadPool
from urllib.error import URLError
from urllib.request import urlopen, HTTPError

from bs4 import BeautifulSoup

url_pattern = re.compile("^https?://.*$")


class SiteMap:
    def __init__(self, starting_url, max_depth=10, max_thread=2):

        # used to store path that has been visited
        self.visited = set()
        self.json_site_map = []
        # a deque to run bfs search, append initial url to the queue.
        self.q = collections.deque()
        self.starting_url = starting_url
        self.max_depth = max_depth
        self.max_thread = max_thread
        self.domain_pattern = None

    def build_site_map(self):
        """
        This function is used to build site map with breadth first search.
        :return: Json string that contains list of map, which including page_urls, links, and images
        """
        # Urllib.request requires url to start with http:// or https://.
        if not self.validate_url(self.starting_url):
            print("[Error] Invalid url. Make sure it starts with http:// or https://")
            return {"error": "[Error] Invalid url. Make sure it starts with http:// or https://"}

        self.domain_pattern = re.compile(".*\." + self.find_domain(self.starting_url) + "\..*")

        # depth should be smller than required max_depth/
        depth = 0
        # append initial url to the q
        self.q.append(self.starting_url)
        # Create a domain pattern for domain only search

        # keep searching until q is empty or max_depth reaches.
        while self.q and depth < self.max_depth:
            # get current queue size, so we can do search by level.
            q_size = len(self.q)
            urls = []
            for i in range(q_size):
                # pop urls from head of the queue
                urls.append(self.q.popleft())

            # make the Pool of workers
            pool = ThreadPool(self.max_thread)

            # open the urls in their own threads
            # and return the results
            pool.map(self.process_url, urls)

            # close the pool and wait for the work to finish
            pool.close()
            pool.join()

            # increment depth since the whole level is searched.
            depth += 1
        print(json.dumps(self.json_site_map))
        return json.dumps(self.json_site_map)

    def process_url(self, curr_url):
        # check if url is visited or not
        if curr_url not in self.visited:
            url_list, img_list = self.get_contents(curr_url)
            curr_json = {"page_url": curr_url,
                         "links": url_list,
                         "images": img_list}
            # extend the whole url list to the queue for next level of search
            if type(url_list) is not str:
                self.q.extend(url_list)
            # append search result of current object to the site_map
            self.json_site_map.append(curr_json)
            # add to visited set so no repeated search
            self.visited.add(curr_url)

    def get_contents(self, url):
        """
        This function scraps the website and return list of urls and images that belong to the target domain
        GIF is also treated as an image
        :return: url list and image list
        """
        print("Opening URL: " + url)
        # Try to open the site with url,
        # validate if content type is plain text so we can scrap
        # if it is application, we dont want to read it.
        try:
            html = urlopen(url, context=ssl._create_unverified_context())
            if html.info().get_content_type() != "text/html":
                print("[Error]Not a site")
                return "Not a site", "N/A"
        except HTTPError as e:
            if e.code == 404:
                print("[Error]404 site not found")
                return "404 site not found", "N/A"
            else:
                print("[Error]Unknown error::: " + e.reason)
                return "Unknown error" + e.reason, "N/A"
        except UnicodeError:
            print("[Error]Unicode error::: ")
            return "Unicode error", "N/A"
        except ValueError:
            print("[Error]URL error")
            return "URL error", "N/A"
        except URLError as urle:
            print("[Error]invalid url")
            return "invalid url", "N/A"

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
                    if self.domain_pattern.match(found_url):
                        # check if it is valid url, if not we append the url and hope it will work.
                        # TODO this might not work, it should be improved.
                        if found_url[:2] == "//":
                            url_list.add("http:" + found_url)
                        elif found_url[:4] == "http":
                            url_list.add(found_url)
                        else:
                            url_list.add(url + found_url)
                except TypeError:
                    continue
            else:
                # try to get src of the image
                img_url = line.get("src")
                try:
                    if self.domain_pattern.match(img_url):
                        img_list.add(img_url)
                except TypeError:
                    continue
        return list(url_list), list(img_list)

    @staticmethod
    def validate_url(url):
        """
        This function validates url
        :param url: root url that is inputed by the user.
        :return: boolean whether or not it starts with http:// or https://
        """
        if url_pattern.match(url):
            return True
        return False

    @staticmethod
    def find_domain(url):
        """
        The function finds the domain if the input is a full url.
        :param url:
        :return:
        """
        return re.split('http://|https://|\\.', url)[-2]


if __name__ == '__main__':
    print("Starting program")
    url = sys.argv[1]
    max_depth = int(sys.argv[2])
    max_thread = int(sys.argv[3])
    site_map_request = SiteMap(url, max_depth, max_thread)
    # site_map_request = SiteMap("https://www.mozilla.org", 3, 8)
    site_map_request.build_site_map()

