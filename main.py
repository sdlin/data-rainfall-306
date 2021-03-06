#!/usr/bin/env python
#
# Copyright 2007 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
import os
import webapp2
import jinja2
import re
import string
import hashlib
import random
import urllib2
from xml.dom import minidom
import json
import time
import logging

from google.appengine.ext import db
from google.appengine.api import memcache

JINJA_ENVIRONMENT = jinja2.Environment(
	autoescape=True,
    loader=jinja2.FileSystemLoader(os.path.dirname(__file__)),
    extensions=['jinja2.ext.autoescape'])

class BaseHandler(webapp2.RequestHandler):
	def write(self, *a, **kw):
		self.response.out.write(*a, **kw)

	def render_str(self, template, **params):
		t = JINJA_ENVIRONMENT.get_template(template)
		return t.render(params)

	def render(self, template, **kw):
		self.write(self.render_str(template, **kw))

	def getcookie(self, cookiename):
		return self.request.cookies.get(cookiename)

class MainHandler(BaseHandler):
    def get(self):
        self.render("index.html")

class TestFormHandler(BaseHandler):
	def get(self):
		self.write("Not too interesting is it?  Try a post response...")
	def post(self):
		self.response.headers['Content-Type'] = 'text/plain'
		self.write(self.request)

class TestDateFormHandler_Helpers(BaseHandler):
	def valid_month(self, monthstring):
		months = ['January',
	          'February',
	          'March',
	          'April',
	          'May',
	          'June',
	          'July',
	          'August',
	          'September',
	          'October',
	          'November',
	          'December']
		if monthstring.capitalize() in months:
			return monthstring.capitalize()

	def valid_day(self, daystring):
		if daystring.isdigit():
			dayint = int(daystring)
			if dayint > 0 and dayint <= 31:
				return dayint

	def valid_year(self, yearstring):
		if yearstring.isdigit():
			yearint = int(yearstring)
			if yearint > 0:
				return yearint

	def valid_date(self, input_month, input_day, input_year):
			month = self.valid_month(input_month)
			day = self.valid_day(input_day)
			year = self.valid_year(input_year)
			return month, day, year

class TestDateFormHandler(TestDateFormHandler_Helpers):
	def write_form(self, error="", month="January", day="1", year="1900"):
		self.render("testdateform.html", error=error, month=month, day=day, year=year)
	
	def get(self):
		self.write_form()
	
	def post(self):
		input_month = self.request.get('month')
		input_day = self.request.get('day')
		input_year = self.request.get('year')
		month, day, year = self.valid_date(input_month, input_day, input_year)

		if not (month and day and year):
			self.write_form("That's not a valid date", input_month, input_day, input_year)
		else:
			self.redirect("/successfuldate?m=%(month)s&d=%(day)s&y=%(year)s" 
															%{"month":month,
															  "day":day, 
															  "year":year})

class SuccessfulDateHandler(TestDateFormHandler_Helpers):
	def get(self):
		input_month = self.request.get('m')
		input_day = self.request.get('d')
		input_year = self.request.get('y')
		month, day, year = self.valid_date(input_month, input_day, input_year)

		if not (month and day and year):
			response = "whatevs"
		else:
			response = "%(month)s %(day)s, %(year)s is a great day!" % {"month":month,
															 			"day":day, 
															 			"year":year}
		self.write(response)

class Rot13Handler(BaseHandler):
	def Rot13(self, s):
		anum = ord('a')
		znum = ord('z')
		Anum = ord('A')
		Znum = ord('Z')
		i = 0
		for l in s:
			lnum = ord(l)
			if lnum >= anum and lnum <= znum:
				newlord = ord(l)+13
				if newlord >= znum+1:
					newl = chr(anum + newlord % (znum+1))
				else:
					newl = chr(newlord)
				s = s[0:i] + newl + s[i+1:]
			elif lnum >= Anum and lnum <= Znum:
				newlord = ord(l)+13
				if newlord >= Znum+1:
					newl = chr(Anum + newlord % (Znum+1))
				else:
					newl = chr(newlord)
				s = s[0:i] + newl + s[i+1:]
			i += 1
		return s

	def write_page(self, text="Type something in here and try out the Rot13 Cipher!"):
		self.render("Rot13.html", text=text)

	def get(self):
		self.write_page()

	def post(self):
		mytext = self.request.get("text")
		self.write_page(self.Rot13(mytext))

def get_coords(ip):
	IPurl = 'http://api.hostip.info/?ip='
	url = IPurl + ip
	content = None
	try:
		content = urllib2.urlopen(url).read()
	except:
		return
	if content:
	    d = minidom.parseString(content)
	    coords = d.getElementsByTagName('gml:coordinates')
	    if coords:
	        lon, lat =  coords[0].childNodes[0].nodeValue.split(',')
	        return db.GeoPt(lat, lon)

def gmaps_img(points):
    GMAPS_URL = "http://maps.googleapis.com/maps/api/staticmap?size=380x280&sensor=false&"
    getparams = '&'.join('markers=%s,%s' % (p.lat,p.lon) for p in points)
    return GMAPS_URL + getparams

class Art(db.Model):
	title = db.StringProperty(required = True)
	arttext = db.TextProperty(required = True)
	date_created = db.DateTimeProperty(auto_now_add = True)
	coords = db.GeoPtProperty()

class AsciiArtHandler(BaseHandler):
	def render_front(self, title="", arttext="", error=""):
		arts = db.GqlQuery("SELECT * FROM Art "
						   "ORDER BY date_created DESC ")
		arts = list(arts)
		points = filter(None, (a.coords for a in arts))
		img_url = None
		if points:
			img_url = gmaps_img(points)

		self.render("asciiart.html", title=title, arttext=arttext, error=error, arts=arts, mapsurl=img_url)

	
	def get(self):
		self.render_front()

	def post(self):
		title = self.request.get("title")
		arttext = self.request.get("arttext")

		if title and arttext:
			a = Art(title=title, arttext=arttext)
			coords = get_coords(self.request.remote_addr)
			if coords:
				a.coords = coords
			a.put()
			self.redirect("/asciiart")
		else:
			error = "title and artwork required."
			self.render_front(title=title, arttext=arttext, error=error)

class Blog(db.Model):
	title = db.StringProperty(required = True)
	entrytext = db.TextProperty(required = True)
	date_created = db.DateTimeProperty(auto_now_add = True)

def EntriesToDict(e):
	d = []
	for b in e:
		d.append(BlogToDict(b))
	return d

def BlogToDict(b):
	return {"content":b.entrytext, "subject":b.title, "created":str(b.date_created)}

LAST_QUERY_TIME = 0
PERMALINK_QUERY_TIMES = {}

def GetBlogEntries():
	global LAST_QUERY_TIME
	entries = memcache.get('all_blogs')
	if not entries:
		entries = db.GqlQuery("SELECT * FROM Blog "
						   	"ORDER BY date_created DESC ")
		memcache.add('all_blogs', entries)
		LAST_QUERY_TIME = int(time.strftime('%s',time.gmtime()))
	return entries

class BlogHandler(BaseHandler):
	def get(self):
		entries = GetBlogEntries()
		self.render("blog_list.html", blogentries=entries, time=int(time.strftime('%s',time.gmtime()))-LAST_QUERY_TIME)

class BlogHandlerJson(BaseHandler):
	def get(self):
		entries = GetBlogEntries()
		self.response.out.headers['Content-Type'] = 'application/json'
		self.write(json.dumps(EntriesToDict(entries)))

class BlogNewPostHandler(BaseHandler):
	def render_front(self, title="", entrytext="", error=""):
		self.render("blognewpost.html", title=title, entrytext=entrytext, error=error)

	def get(self):
		self.render_front()

	def post(self):
		title = self.request.get("subject")
		entrytext = self.request.get("content")

		if title and entrytext:
			b = Blog(title=title, entrytext=entrytext)
			b.put()
			memcache.delete('all_blogs')
			self.redirect("/blog/%d" % b.key().id())
		else:
			error = "title and blog text required."
			self.render_front(title=title, entrytext=entrytext, error=error)

class BlogPermalinkHandler(BaseHandler):
	def get(self, blog_id):
		global PERMALINK_QUERY_TIMES	
		b = memcache.get(blog_id)
		if not b:
			b = Blog.get_by_id(int(blog_id))
			memcache.add(blog_id,b)
			PERMALINK_QUERY_TIMES[blog_id] = int(time.strftime('%s',time.gmtime()))
		if b:
			timediff = int(time.strftime('%s',time.gmtime())) - PERMALINK_QUERY_TIMES[blog_id]
			self.render("blogpermalink.html", date=b.date_created, title=b.title, entrytext=b.entrytext, time=timediff)
		else:
			self.redirect("/blog")

class BlogPermalinkHandlerJson(BaseHandler):
	def get(self, blog_id,jsonext):
		if jsonext == '.json':
			b = Blog.get_by_id(int(blog_id))
			if b:
				self.response.out.headers['Content-Type'] = 'application/json'
				self.write(json.dumps(BlogToDict(b)))
			else:
				self.redirect("/blog")
		else:
			self.redirect("/blog")			

def VerifyEmail(e):
	email_re = re.compile(r"(^[-!#$%&'*+/=?^_`{}|~0-9A-Z]+(\.[-!#$%&'*+/=?^_`{}|~0-9A-Z]+)*"r'|^"([\001-\010\013\014\016-\037!#-\[\]-\177]|\\[\001-011\013\014\016-\177])*"'r')@(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?$', re.IGNORECASE)
	return email_re.match(e)

class User(db.Model):
	username = db.StringProperty(required = True)
	email = db.StringProperty(required = False)
	saltyhash = db.StringProperty(required = True)
	date_created = db.DateTimeProperty(auto_now_add = True)

def MakeSalt(length=10):
	return ''.join(random.choice(string.letters) for x in xrange(length))

def MakeSaltyHash(pw, salt=None):
	if not salt:
		salt = MakeSalt()
	return MakeHash(pw + salt)+ '|' + salt

def MakeHash(s):
	return hashlib.sha256(s).hexdigest()

def VerifyCookie(c):
	try:
		return c == MakeSaltyHash(COOKIESECRET, c.split('|')[1])
	except:
		return False

COOKIESECRET = 'chocolatechip'

class SignupHandler(BaseHandler):
	def render_front(self, username="", email="", error=""):
		self.render("signup.html", prefix="blog", username=username, email=email, error=error)

	def get(self):
		self.render_front()

	def post(self):
		username = self.request.get("username")
		password = self.request.get("password")
		verify = self.request.get("verify")
		email = self.request.get("email")
		q = User.all()
		q.filter("username =", username)
		qresult = q.get()

		if qresult:
			error = "Username Taken."
		elif not username:
			error = "Username Required."
		elif email and not VerifyEmail(email):
			error = "Invalid Email."
		elif not password or (password != verify):
			error = "Check Password."
		else:
			saltyhash = MakeSaltyHash(password)
			u = User(username=username, saltyhash=saltyhash, email=email)
			u.put()
			usercookie = MakeSaltyHash(COOKIESECRET, str(u.key().id()))
			self.response.headers.add_header('Set-Cookie', 'user=%s' % usercookie)
			self.redirect("/blog/welcomeuser")
			return

		self.render_front(username=username, email=email, error=error)


class WelcomeHandler(BaseHandler):
	def get(self):
		usercookie = self.getcookie('user')
		if not VerifyCookie(usercookie):
			self.redirect("/blog/signup")
			return
		uid = usercookie.split('|')[1]
		u = User.get_by_id(int(uid))
		if u:
			self.write('Welcome back, %s!' % u.username)
		else:
			self.write('you rascal...')

class LoginHandler(BaseHandler):
	def render_front(self, username="", error=""):
		self.render("login.html", prefix="blog", username=username, error=error)

	def get(self):
		self.render_front()

	def post(self):
		username = self.request.get("username")
		password = self.request.get("password")
		q = User.all()
		q.filter("username =", username)
		qresult = q.get()
		if qresult:
			salt = qresult.saltyhash.split('|')[1]
			if qresult.saltyhash == MakeSaltyHash(password, salt):
				usercookie = MakeSaltyHash(COOKIESECRET, str(qresult.key().id()))
				self.response.headers.add_header('Set-Cookie', 'user=%s' % usercookie)
				self.redirect("/blog/welcomeuser")
				return
		self.render_front(username=username, error="invalid login")

class LogoutHandler(BaseHandler):
	def get(self):
		self.response.headers.add_header('Set-Cookie', 'user=;Expires=Thu, 01-Jan-1970 00:00:00 GMT')
		self.redirect('/signup')

class FlushHandler(BaseHandler):
	def get(self):
		memcache.flush_all()
		self.redirect('/blog')		

DEFAULTWIKITEXT = "this is the best wiki in the world"

class WikiBaseHandler(BaseHandler):
	def LoggedIn(self):
		usercookie = self.getcookie('user')
		if VerifyCookie(usercookie):
			uid = usercookie.split('|')[1]
			return User.get_by_id(int(uid))
		else:
			return False

	def Logout(self):
		self.response.headers.add_header('Set-Cookie', 'user=;Expires=Thu, 01-Jan-1970 00:00:00 GMT')

	def SetCookie(self, usercookie):
		self.response.headers.add_header('Set-Cookie', 'user=%s' % usercookie)

	def GetUser(self, username):
		q = User.all()
		q.filter("username =", username)
		return q.get()

	def GetWikiModel(self, title):
		q = WikiModel.all()
		q.filter("title =", str(title))
		return q.get()

class WikiModel(db.Model):
	title = db.StringProperty(required = True)
	wikitext = db.TextProperty(required = False)
	date_created = db.DateTimeProperty(auto_now_add = True)

class WikiSignupHandler(WikiBaseHandler):
	def render_front(self, username="", email="", error=""):
		self.render("signup.html", prefix="wiki", username=username, email=email, error=error)

	def get(self):
		self.render_front()

	def post(self):
		username = self.request.get("username")
		password = self.request.get("password")
		verify = self.request.get("verify")
		email = self.request.get("email")
		qresult = self.GetUser(username)

		if qresult:
			error = "Username Taken."
		elif not username:
			error = "Username Required."
		elif email and not VerifyEmail(email):
			error = "Invalid Email."
		elif not password or (password != verify):
			error = "Check Password."
		else:
			saltyhash = MakeSaltyHash(password)
			u = User(username=username, saltyhash=saltyhash, email=email)
			u.put()
			usercookie = MakeSaltyHash(COOKIESECRET, str(u.key().id()))
			self.SetCookie(usercookie)
			self.redirect("/wiki/")
			return

		self.render_front(username=username, email=email, error=error)

class WikiLoginHandler(WikiBaseHandler):
	def render_front(self, username="", error=""):
		self.render("login.html", prefix="wiki", username=username, error=error)

	def get(self):
		self.render_front()

	def post(self):
		username = self.request.get("username")
		password = self.request.get("password")
		qresult = self.GetUser(username)
		if qresult:
			salt = qresult.saltyhash.split('|')[1]
			if qresult.saltyhash == MakeSaltyHash(password, salt):
				usercookie = MakeSaltyHash(COOKIESECRET, str(qresult.key().id()))
				self.SetCookie(usercookie)
				self.redirect("/wiki/")
				return
		self.render_front(username=username, error="invalid login")

class WikiLogoutHandler(WikiBaseHandler):
	def get(self):
		self.Logout()
		self.redirect('/wiki/')

class WikiEditPageHandler(WikiBaseHandler):
	def get(self, pagetitle):
		w = self.GetWikiModel(pagetitle)
		if self.LoggedIn():
			if w:
				self.render("wikiedit.html", user=self.LoggedIn(), title=w.title, wikitext=w.wikitext)
			else:
				p = WikiModel(title=pagetitle, wikitext=DEFAULTWIKITEXT)
				p.put()
				self.render("wikiedit.html", user=self.LoggedIn(), title=pagetitle, wikitext=DEFAULTWIKITEXT)
		else:
			self.redirect('../login')

	def post(self, pagetitle):
		if self.LoggedIn():
			wikitext = self.request.get("wikitext")
			w = self.GetWikiModel(pagetitle)
			if w:
				w.wikitext = wikitext
				w.put()
			else:
				p = WikiModel(title=pagetitle, wikitext=wikitext)
				p.put()
			self.redirect('../%s' % pagetitle[1:])
		else:
			self.redirect('../login')			


class WikiPageHandler(WikiBaseHandler):
	def get(self, pagetitle):
		w = self.GetWikiModel(pagetitle)
		if w:
			self.render("wikipage.html", user=self.LoggedIn(), title=w.title, wikitext=w.wikitext)
		else:
			self.redirect('/wiki/_edit/' + pagetitle[1:])

class WikiRedirectHandler(WikiBaseHandler):
	def get(self):
		self.redirect('/wiki/')

class AltCodeHandler(BaseHandler):
	def AltCipher(self, s):
		alt_to_abc = {u'\u00e5':'a',u'\u222b':'b',u'\u00e7':'c',u'\u2202':'d',u'\u00b4':'e',u'\u0192':'f',u'\u00a9':'g',u'\u02d9':'h',u'\u02c6':'i',u'\u2206':'j',u'\u02da':'k',u'\u00ac':'l',u'\u00b5':'m',u'\u02dc':'n',u'\u00f8':'o',u'\u03c0':'p',u'\u0153':'q',u'\u00ae':'r',u'\u00df':'s',u'\u2020':'t',u'\u00a8':'u',u'\u221a':'v',u'\u2211':'w',u'\u2248':'x',u'\u00a5':'y',u'\u03a9':'z'}
		abc_to_alt = {'a':u'\u00e5','b':u'\u222b','c':u'\u00e7','d':u'\u2202','e':u'\u00b4','f':u'\u0192','g':u'\u00a9','h':u'\u02d9','i':u'\u02c6','j':u'\u2206','k':u'\u02da','l':u'\u00ac','m':u'\u00b5','n':u'\u02dc','o':u'\u00f8','p':u'\u03c0','q':u'\u0153','r':u'\u00ae','s':u'\u00df','t':u'\u2020','u':u'\u00a8','v':u'\u221a','w':u'\u2211','x':u'\u2248','y':u'\u00a5','z':u'\u03a9'}
		output = ''
		for l in s:
			if l in alt_to_abc:
				output += alt_to_abc[l]
			elif l.lower() in abc_to_alt:
					output += abc_to_alt[l.lower()]
			else:
				output += l
		return output

	def write_page(self, text=u'\u2020\u00a5\u03c0\u00b4 \u00e5\u00ac\u2020 \u00e7\u00f8\u2202\u00b4.'):
		self.render("altcodes.html", text=text)

	def get(self):
		self.write_page()

	def post(self):
		mytext = self.request.get("text")
		self.write_page(self.AltCipher(mytext))

PAGE_RE = r'(/(?:[a-zA-Z0-9_-]+)*)'
app = webapp2.WSGIApplication([
    ('/', MainHandler),
    ('/testformresponse', TestFormHandler),
    ('/testdateform', TestDateFormHandler),
    ('/successfuldate', SuccessfulDateHandler),
    ('/rot13', Rot13Handler),
    ('/asciiart', AsciiArtHandler),
    ('/blog', BlogHandler),
    ('/blog/.json', BlogHandlerJson),
    ('/blog/newpost', BlogNewPostHandler),
    (r'/blog/([0-9]+)', BlogPermalinkHandler),
    (r'/blog/([0-9]+)(\.json)', BlogPermalinkHandlerJson),
    ('/blog/signup', SignupHandler),
    ('/blog/welcomeuser', WelcomeHandler),
    ('/blog/login', LoginHandler),
    ('/blog/logout', LogoutHandler),
    ('/blog/flush',FlushHandler),
    ('/wiki/signup', WikiSignupHandler),
    ('/wiki/login', WikiLoginHandler),
    ('/wiki/logout', WikiLogoutHandler),
    ('/wiki/_edit' + PAGE_RE, WikiEditPageHandler),
    ('/wiki' + PAGE_RE, WikiPageHandler),
    ('/wiki' + PAGE_RE + '/', WikiPageHandler),
    ('/wiki', WikiRedirectHandler),
    ('/altcodes', AltCodeHandler)
], debug=True)
