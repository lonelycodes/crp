import scrapy
import cgi
from multiprocessing import Process, Queue
from scrapy.exceptions import CloseSpider
from scrapy.spiders import CrawlSpider, Rule
from scrapy.linkextractors import LinkExtractor
from scrapy.crawler import CrawlerProcess
from scrapy.crawler import CrawlerRunner
from scrapy.settings import Settings
from multiprocessing import Process, Queue
from twisted.internet import reactor
from lxml import etree

previews = []
class PreviewSpider(CrawlSpider):
    name = 'preview_spider'
#    allowed_domains = []
#    start_urls = []
    IGNORED_EXTENSIONS = [
        # images
        'mng', 'pct', 'bmp', 'gif', 'jpg', 'jpeg', 'png', 'pst', 'psp', 'tif',
        'tiff', 'ai', 'drw', 'dxf', 'eps', 'ps', 'svg',

        # audio
        'mp3', 'wma', 'ogg', 'wav', 'ra', 'aac', 'mid', 'au', 'aiff',

        # video
        '3gp', 'asf', 'asx', 'avi', 'mov', 'mp4', 'mpg', 'qt', 'rm', 'swf', 'wmv',
        'm4a',

        # office suites
        'xls', 'xlsx', 'ppt', 'pptx', 'pps', 'doc', 'docx', 'odt', 'ods', 'odg',
        'odp',

        # other
        'css', 'exe', 'bin', 'rss', 'zip', 'rar', 'pdf', 'js'
    ]
    rules = [scrapy.spiders.Rule(scrapy.linkextractors.lxmlhtml.LxmlLinkExtractor(
        deny_extensions=IGNORED_EXTENSIONS), callback='parse_item', follow=True)]

    def __init__(self, dname='', *args, **kwargs):
        super(PreviewSpider, self).__init__(*args, **kwargs)
        print('domain: ' + dname)
        self.count = 0
        self.allowed_domains = [dname]
        self.start_urls = ['http://www.' + dname]


    def parse_item(self, response):
        previews.append(response.body)

def get_preview(domain_name, num=10):
    def f(q):
        try:
            runner = CrawlerRunner({
                'USER_AGENT': 'Mozilla/4.0 (compatible; MSIE 7.0; Windows NT 5.1)',
                'CLOSESPIDER_PAGECOUNT': 10
            })
            d = runner.crawl(PreviewSpider, dname=domain_name)
            d.addBoth(lambda _: reactor.stop())
            reactor.run()
            q.put(previews[0:num])
        except Exception as e:
            q.put(e)
    q = Queue()
    p = Process(target=f, args=(q,))
    p.start()
    result = q.get()
    p.join()
    return result
