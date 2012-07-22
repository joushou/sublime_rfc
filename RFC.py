import sublime,sublime_plugin
import urllib2,functools,threading,xml.sax,xml.sax.handler,os

def main_thread(callback, *args, **kwargs):
	sublime.set_timeout(functools.partial(callback, *args, **kwargs), 0)

class RfcHandler(xml.sax.handler.ContentHandler):
	def __init__(self):
		self.isrfcentry 	= False
		self.isdocid 		= False
		self.istitle 		= False
		self.isdate 		= False
		self.isdatemonth 	= False
		self.isdateyear 	= False
		self.isformat 		= False
		self.isformatfile 	= False
		self.isformatchar 	= False
		self.isformatpage 	= False
		self.level 			= 0
		self.temptitle 		= ""
		self.tempid 		= ""
		self.tempdatemonth 	= ""
		self.tempdateyear 	= ""
		self.tempformatfile = ""
		self.tempformatchar = ""
		self.tempformatpage = ""
		self.list 			= []

	def startElement(self,name,attrs):
		if name == "rfc-entry" and self.level == 1:
			self.isrfcentry = True
		elif self.isrfcentry and self.level == 2 and name == "title":
			self.temptitle = ""
			self.istitle = True
		elif self.isrfcentry and self.level == 2 and name == "doc-id":
			self.tempid = ""
			self.isdocid = True
		elif self.isrfcentry and self.level == 2 and name == "date":
			self.isdate = True
		elif self.isrfcentry and self.level == 3 and self.isdate and name == "month":
			self.tempdatemonth = ""
			self.isdatemonth = True
		elif self.isrfcentry and self.level == 3 and self.isdate and name == "year":
			self.tempdateyear = ""
			self.isdateyear = True
		elif self.isrfcentry and self.level == 2 and name == "format":
			self.isformat = True
		elif self.isrfcentry and self.isformat and self.level == 3 and name == "file-format":
			self.tempformatfile = ", Format: "
			self.isformatfile = True
		elif self.isrfcentry and self.isformat and self.level == 3 and name == "char-count":
			self.tempformatchar = ", "
			self.isformatchar = True
		elif self.isrfcentry and self.isformat and self.level == 3 and name == "page-count":
			self.tempformatpage = ", "
			self.isformatpage = True

		self.level += 1



	def endElement(self,name):
		if self.isrfcentry and self.level == 2 and name == "rfc-entry":
			self.isrfcentry = False
			if self.tempformatpage == "":
				temp = [self.temptitle, self.tempid, self.tempdatemonth+" "+self.tempdateyear+self.tempformatfile+self.tempformatchar]
			else:
				temp = [self.temptitle, self.tempid, self.tempdatemonth+" "+self.tempdateyear+self.tempformatfile+self.tempformatpage]
			self.list.append(temp)
			self.tempformatfile = ""
			self.tempformatchar = ""
			self.tempformatpage = ""
		elif self.isrfcentry and name == "title":
			self.istitle = False
		elif self.isrfcentry and name == "doc-id":
			self.isdocid = False
		elif self.isrfcentry and name == "date":
			self.isdate = False
		elif self.isrfcentry and self.isdate and name == "month":
			self.isdatemonth = False
		elif self.isrfcentry and self.isdate and name == "year":
			self.isdateyear = False
		elif self.isrfcentry and name == "format":
			self.isformat = False
		elif self.isrfcentry and self.isformat and name == "file-format":
			self.isformatfile = False
		elif self.isrfcentry and self.isformat and name == "char-count":
			self.isformatchar = False
			self.tempformatchar += " characters"
		elif self.isrfcentry and self.isformat and name == "page-count":
			self.isformatpage = False
			self.tempformatpage += " page(s)"

		self.level -= 1

	def characters(self,ch):
		if self.isrfcentry and self.istitle:
			self.temptitle += ch
		elif self.isrfcentry and self.isdocid:
			self.tempid += ch
		elif self.isrfcentry and self.isdate and self.isdatemonth:
			self.tempdatemonth += ch
		elif self.isrfcentry and self.isdate and self.isdateyear:
			self.tempdateyear += ch
		elif self.isrfcentry and self.isformat and self.isformatfile:
			self.tempformatfile += ch
		elif self.isrfcentry and self.isformat and self.isformatchar:
			self.tempformatchar += ch
		elif self.isrfcentry and self.isformat and self.isformatpage:
			self.tempformatpage += ch

	def getList(self):
		return self.list

class RfcLister(threading.Thread):
	def __init__(self,callback):
		threading.Thread.__init__(self)
		self.callback = callback

	def run(self):
		parser = xml.sax.make_parser()
		contentHandler = RfcHandler()
		parser.setContentHandler(contentHandler)
		parser.parse(open("/Volumes/Scratchpad/Library/Application Support/Sublime Text 2/Packages/User/rfc-index.xml"))
		main_thread(self.callback, contentHandler.getList())


class RfcCommand(sublime_plugin.WindowCommand):
	def lcallback(self, a):
		self.rfcs = a
		self.window.show_quick_panel(a, self.download)

	def dlcallback(self, response):
		edit = self.wnd.begin_edit()
		reg = sublime.Region(0,self.wnd.size())
		self.wnd.erase(edit,reg)
		self.wnd.insert(edit, 0, response)
		self.wnd.end_edit(edit)

	def download(self, rfc):
		if rfc == -1:
			return
		self.wnd = self.window.new_file()
		self.wnd.set_scratch(True)
		self.wnd.set_name(("%s" % self.rfcs[rfc][0]))
		edit = self.wnd.begin_edit()
		self.wnd.insert(edit, 0, ("Loading %s (%s)...\n" % (self.rfcs[rfc][1], self.rfcs[rfc][0])))
		self.wnd.end_edit(edit)
		URL = "http://www.ietf.org/rfc/%s.txt" % self.rfcs[rfc][1].lower()
		self.dlthread = WebDownloader(URL, self.dlcallback)
		self.dlthread.start()

	def run(self):
		print len(self.window.folders())
		self.lthread = RfcLister(self.lcallback)
		self.lthread.start()

class WebDownloader(threading.Thread):
	def __init__(self,url,callback):
		threading.Thread.__init__(self)
		self.url = url
		self.callback = callback

	def run(self):
		try:
			response = urllib2.urlopen(self.url).read()
		except Exception:
			response = ""
		main_thread(self.callback,response)
