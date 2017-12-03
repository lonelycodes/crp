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

stored = []
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

    def __init__(self, dname='', xp_title='', xp_lead='', xp_content='', xp_date='', xp_author='', xp_keywords='', f_title='', f_lead='', f_content='', f_date='', f_author='', f_keywords='', *args, **kwargs):
        super(MainSpider, self).__init__(*args, **kwargs)
        self.count = 0
        self.allowed_domains = [dname]
        self.start_urls = ['http://www.' + dname]
        self.srcname = dname.split('.')[0]
        self.xp = {}
        self.f = {}
        self.xp['title'] = xp_title
        self.xp['lead'] = xp_lead
        self.xp['content'] = xp_content
        self.xp['date'] = xp_date
        self.xp['author'] = xp_author
        self.xp['keywords'] = xp_keywords
        self.f['title'] = f_title
        self.f['lead'] = f_lead
        self.f['content'] = f_content
        self.f['date'] = f_date
        self.f['author'] = f_author
        self.f['keywords'] = f_keywords


    def parse_item(self, response):
        text = {'source': self.srcname, 'url': response.url, 'title': "", 'lead': "", 'content': "", 'date': "", 'author': "", 'keywords': "", "lang": "", "ftype": "", "num_token": 0}
        for key in self.xp.keys():
            if self.xp[key] != "":
                r = response.xpath(self.xp[key])
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

def crawl_scrape(domain_name):
    a = db_session.query(Source).filter(Source.name==domain_name.split('.')[0]).first()
    xptitle = str(a.xp_title)
    xplead = a.xp_lead
    xpcontent = a.xp_content
    xpdate = a.xp_date
    xpauthor = a.xp_author
    xpkeywords = a.xp_keywords
    ftitle = a.f_title
    flead = a.f_lead
    fcontent = a.f_content
    fdate = a.f_date
    fauthor = a.f_author
    fkeywords = a.f_keywords
    a.crawling = True
    db_session.add(a)
    db_session.commit()
    proc= CrawlerProcess({
                'USER_AGENT': 'Mozilla/4.0 (compatible; MSIE 7.0; Windows NT 5.1)',
                'CLOSESPIDER_PAGECOUNT': 20
    })

    proc.crawl(MainSpider, dname=domain_name, xp_title=xptitle, xp_lead=xplead, xp_content=xpcontent, xp_date=xpdate, xp_author=xpauthor, xp_keywords=xpkeywords, f_title=ftitle, f_lead=flead, f_content=fcontent, f_date=fdate, f_author=fauthor, f_keywords=fkeywords)
    proc.start(stop_after_crawl=True)
    #d.addBoth(lambda _: reactor.stop())
    #reactor.run()
    all_texts = db_session.query(Text).filter(Text.source==domain_name.split('.')[0]).all()
    c = 0
    for t in stored:
        duplicate = False
        for at in all_texts:
            if at.content==t['content']:
                duplicate = True
        if not duplicate:
            c += 1
            db_session.add(Text(source=t['source'], url=t['url'], title=t['title'], lead=t['lead'], content=t['content'], date=t['date'], author=t['author'], keywords=t['keywords'], lang=t['lang'], num_token=t['num_token']))
    a.num_files_html += c
    a.crawling = False
    db_session.add(a)
    db_session.commit()
    return stored
