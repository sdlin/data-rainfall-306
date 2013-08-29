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
import webapp2

root_get_response = """
Welcome to data-rainfall-306!
<br>
<form method="post" action="/testformresponse">
<input name="q">
<input type="submit" value="submit something awesome">
</form>
"""

testform_get_response = """
This is the get response for testform.  
<br>
Not too interesting is it?  Try a post response...
"""

testdateform_get_response = """
<form method="post">
	What is your birthday?
	<br>
	<label> Month
		<input type="text" name="month" value=%(month)s>
	</label>
	<label> Day
		<input type="text" name="day" value=%(day)s>
	</label>
	<label> Year
		<input type="text" name="year" value=%(year)s>
	</label>
	<div style="color: red">%(error)s</div>
	<br>
	<br>
	<input type="submit">
</form>
"""

def valid_month(monthstring):
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

def valid_day(daystring):
	if daystring.isdigit():
		dayint = int(daystring)
		if dayint > 0 and dayint <= 31:
			return dayint

def valid_year(yearstring):
	if yearstring.isdigit():
		yearint = int(yearstring)
		if yearint > 0:
			return yearint
	
def escape_html(s):
		for (i, o) in (("&", "&amp;"),
					   (">", "&gt;"),
					   ("<", "&lt;"),
					   ('"', "&quot;"),
					   ("'", "&apos;")):
			s = s.replace(i, o)
		return s

def valid_date(input_month, input_day, input_year):
		month = valid_month(input_month)
		day = valid_day(input_day)
		year = valid_year(input_year)
		return month, day, year

class MainHandler(webapp2.RequestHandler):
    def get(self):
        self.response.write(root_get_response)

class TestFormHandler(webapp2.RequestHandler):
	def get(self):
		self.response.write(testform_get_response)
	def post(self):
		self.response.headers['Content-Type'] = 'text/plain'
		self.response.write(self.request)

class TestDateFormHandler(webapp2.RequestHandler):
	def write_form(self, error="", month="January", day="1", year="1900"):
		self.response.out.write(testdateform_get_response % {"error":escape_html(error), 
															 "month":escape_html(month),
															 "day":escape_html(day), 
															 "year":escape_html(year)})
	
	def get(self):
		self.write_form()
	
	def post(self):
		input_month = self.request.get('month')
		input_day = self.request.get('day')
		input_year = self.request.get('year')
		month, day, year = valid_date(input_month, input_day, input_year)

		if not (month and day and year):
			self.write_form("That's not a valid date", input_month, input_day, input_year)
		else:
			self.redirect("/successfuldate?m=%(month)s&d=%(day)s&y=%(year)s" 
															%{"month":month,
															  "day":day, 
															  "year":year})

class SuccessfulDateHandler(webapp2.RequestHandler):
	def get(self):
		input_month = self.request.get('m')
		input_day = self.request.get('d')
		input_year = self.request.get('y')
		month, day, year = valid_date(input_month, input_day, input_year)

		if not (month and day and year):
			response = "whatevs"
		else:
			response = "%(month)s %(day)s, %(year)s is a great day!" % {"month":month,
															 			"day":day, 
															 			"year":year}
		self.response.out.write(response)

class Rot13Handler(webapp2.RequestHandler):
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
			safetext = escape_html(text)
			self.response.out.write("""Rot13<br><form method="post">
				<textarea name="text" rows="18" cols="80">%s</textarea>
				<br><input type="submit" value="rot13"></form>""" % safetext)

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
