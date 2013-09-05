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


app = webapp2.WSGIApplication([
    ('/', MainHandler),
    ('/testformresponse', TestFormHandler),
    ('/testdateform', TestDateFormHandler),
    ('/successfuldate', SuccessfulDateHandler),
    ('/rot13', Rot13Handler)
], debug=True)
