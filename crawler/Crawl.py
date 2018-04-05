# -*- coding: utf-8 -*-
import ast
import datetime
import sys,imp
import scrapy
import cgi
from database.database import db_session
from database.models import Text, Source
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
from textblob import TextBlob
from langdetect import detect
from nltk.tokenize import word_tokenize

stored = [] # ugly af

class MainSpider(CrawlSpider):
    name = 'main_spider'
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


    def __init__(self, xp, f, util, *args, **kwargs):
        super(MainSpider, self).__init__(*args, **kwargs)
        self.count = 0
        self.allowed_domains = [util['dname']]
        self.start_urls = ['http://www.' + util['dname']]
        self.xp = xp
        self.f = f
        self.util = util
        

    def parse_item(self, response):
        text = {'source': self.util['src_id'], 'url': response.url, 'title': "", 'lead': "", 'content': "", 'date': "", 'author': "", 'keywords': "", "lang": "", "ftype": "", "num_token": 0}
        for key in self.xp.keys():
            if self.xp[key] != "":
                r = response.xpath(self.xp[key])
                if len(r.extract()) >= 1:
                    text[key] = r.extract()[0]
            if key == 'content':
                text[key] = " ".join(r.extract()).replace(u'\xa0', u' ').replace(u'\xe4', u'ä')
        d = False
        for s in stored:
            if s['content'] == text['content']:
                return
        text['num_token'] = len(text['content'].split(' '))
        text['lang'] = detect(text['content'])
        stored.append(text)


def crawl_scrape(src_id):
    source = db_session.query(Source).filter(Source.id==src_id).first()
    xp = {}
    f = {}
    util={}
    util['src_id'] = src_id
    util['dname'] = source.domain
    xp['title'] = str(source.xp_title)
    xp['lead'] = source.xp_lead
    xp['content'] = source.xp_content
    xp['date'] = source.xp_date
    xp['author'] = source.xp_author
    xp['keywords'] = source.xp_keywords
    f['title'] = source.f_title
    f['lead'] = source.f_lead
    f['content'] = source.f_content
    f['date'] = source.f_date
    f['author'] = source.f_author
    f['keywords'] = source.f_keywords
    source.crawling = True
    db_session.add(source)
    db_session.commit()

    proc = CrawlerProcess({
                'USER_AGENT': 'Mozilla/4.0 (compatible; MSIE 7.0; Windows NT 5.1)',
                'CLOSESPIDER_PAGECOUNT': 20
    })

    proc.crawl(MainSpider, xp, f, util)
    proc.start(stop_after_crawl=True)
    #d.addBoth(lambda _: reactor.stop())
    #reactor.run()
    current_texts = db_session.query(Text).filter(Text.src_id==src_id).all()
    
    c = 0
    for t in stored:
        duplicate = False
        for at in current_texts:
            if at.content==t['content']:
                duplicate = True
        if not duplicate:
            c += 1
            db_session.add(Text(src_id=t['source'], url=t['url'], title=t['title'], lead=t['lead'], content=t['content'], date=t['date'], author=t['author'], keywords=t['keywords'], lang=t['lang'], num_token=t['num_token']))
    source.num_files_html += c
    source.crawling = False
    db_session.add(source)
    db_session.commit()
    return stored
