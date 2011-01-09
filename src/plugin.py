from Plugins.Plugin import PluginDescriptor
from Components.NimManager import nimmanager
from Components.ActionMap import ActionMap
from Components.Sources.ServiceEvent import ServiceEvent
from Components.ServiceEventTracker import ServiceEventTracker
from Components.Label import Label
from Components.Button import Button
from Components.ProgressBar import ProgressBar
from Screens.Screen import Screen
from ServiceReference import ServiceReference
from enigma import eTimer, eDVBDB, eServiceCenter, eServiceReference, iPlayableService, iFrontendInformation
from about import LCNScannerAbout
import lcn_scanner
import time

class LCNScannerPlugin(Screen):
	skin = """
		<screen position="80,100" size="560,400" title="SIFTeam - LCN Scanner">
			<widget name="progress" position="10,10" size="540,20" borderWidth="1" />
			<widget name="log" position="10,40" size="540,300" font="Regular;18" />
			<widget name="key_red" position="0,360" size="140,40" valign="center" halign="center" zPosition="5" transparent="1" foregroundColor="white" font="Regular;18"/>
			<widget name="key_green" position="140,360" size="140,40" valign="center" halign="center" zPosition="5" transparent="1" foregroundColor="white" font="Regular;18"/>
			<widget name="key_yellow" position="280,360" size="140,40" valign="center" halign="center" zPosition="5" transparent="1" foregroundColor="white" font="Regular;18"/>
			<widget name="key_blue" position="420,360" size="140,40" valign="center" halign="center" zPosition="5" transparent="1" foregroundColor="white" font="Regular;18"/>
			<ePixmap name="red" pixmap="skin_default/buttons/red.png" position="0,360" size="140,40" zPosition="4" transparent="1" alphatest="on"/>
			<ePixmap name="green" pixmap="skin_default/buttons/green.png" position="140,360" size="140,40" zPosition="4" transparent="1" alphatest="on"/>
			<ePixmap name="yellow" pixmap="skin_default/buttons/yellow.png" position="280,360" size="140,40" zPosition="4" transparent="1" alphatest="on"/>
			<ePixmap name="blue" pixmap="skin_default/buttons/blue.png" position="420,360" size="140,40" zPosition="4" transparent="1" alphatest="on"/>
		</screen>"""
	
	service_types_tv = '1:7:1:0:0:0:0:0:0:0:(type == 1) || (type == 17) || (type == 22) || (type == 25) || (type == 134) || (type == 195)'
	service_types_radio = '1:7:2:0:0:0:0:0:0:0:(type == 2) || (type == 10)'
	FLAG_SERVICE_NEW_FOUND = 64

	def __init__(self, session, args = None):
		Screen.__init__(self, session)
		self.session = session
		self.slist = []
		self.slistall = []
		self.sindex = -1
		self.enablezap = False
		self.timeout = eTimer()
		self.timeout.callback.append(self.doZap)
		self.zaptimer = eTimer()
		self.zaptimer.callback.append(self.doZap)
		self.oldref = self.session.nav.getCurrentlyPlayingServiceReference()
		self.lcnlist = []
		self.textlog = ""
		self.isscanning = 0
		
		self["key_red"] = Button(_("Exit"))
		self["key_green"] = Button(_("Scan"))
		self["key_yellow"] = Button(_("About"))
		self["key_blue"] = Button("")
		self["log"] = Label("")
		self["progress"] = ProgressBar()
		self["actions"] = ActionMap(["SetupActions", "ColorActions"],
		{
			"green": self.doScan,
			"yellow": self.about,
			"red": self.quit,
			"cancel": self.quit
		}, -2)		
		self.__event_tracker = ServiceEventTracker(screen=self, eventmap=
		{
			iPlayableService.evTunedIn: self.afterZap,
		})
		
	def about(self):
		self.session.open(LCNScannerAbout)
		
	def addLog(self, text):
		self.textlog = text + "\n" + self.textlog
		self["log"].text = self.textlog;
	
	def addInBouquets(self):
		f = open('/etc/enigma2/bouquets.tv', 'r')
		ret = f.read().split("\n")
		f.close()

		i = 0
		while i < len(ret):
			if ret[i].find("userbouquet.terrestrial_lcn.tv") >= 0:
				return
			i += 1

		f = open('/etc/enigma2/bouquets.tv', 'w')
		f.write(ret[0]+"\n")
		f.write('#SERVICE 1:7:1:0:0:0:0:0:0:0:FROM BOUQUET "userbouquet.terrestrial_lcn.tv" ORDER BY bouquet\n')
		i = 1
		while i < len(ret):
			f.write(ret[i]+"\n")
			i += 1

	def afterZap(self):
		if self.enablezap:
			self.timeout.stop()
			self.enablezap = False
			if self.sindex < len(self.slist):
				lcn = lcn_scanner.get_lcn()
				
				db = 0
				service = self.session.nav.getCurrentService()
				feinfo = service and service.frontendInfo()
				if feinfo != None:
					db = feinfo.getFrontendInfo(iFrontendInformation.signalQualitydB)
				print "Signal quality (db): %d" % db
				count = 0
				while lcn != None:
					i = 0
					newlcn = lcn.lcn
					while i < len(self.lcnlist):
						if self.lcnlist[i][0] == lcn.lcn:
							if self.lcnlist[i][4] < db:
								self.lcnlist[i][0] += 16384
							else:
								newlcn += 16384
							break
						i += 1
					self.lcnlist.append((newlcn, lcn.nid, lcn.tsid, lcn.sid, db))
					lcn = lcn.next
					count += 1

				lcn_scanner.lcn_entry_clean(lcn)
				self.addLog("Found %d services" % count)
				self.zaptimer.start(100, 1)

	def doZap(self):
		if len(self.slist) > 0:
			self["progress"].setValue((100/len(self.slist))*self.sindex)
		self.timeout.stop()
		self.sindex += 1
		if self.sindex < len(self.slist):
			tmp = self.slist[self.sindex].split(":")
			self.addLog("Scanning transponder 0x%s..." % tmp[4])
			self.enablezap = True
			self.session.nav.playService(eServiceReference(self.slist[self.sindex]), False)
			self.timeout.start(5000, 1)
		else:
			self["progress"].setValue(100)
			self.addLog("Completed")
			lcn_scanner.demuxer_close()
			self.lcnlist = sorted(self.lcnlist, key=lambda lcn: lcn[0])
			db = eDVBDB.getInstance()
			f = open('/etc/enigma2/userbouquet.terrestrial_lcn.tv', 'w')
			f.write("#NAME Terrestrial LCN\n")
			i = 0
			duplicates = 0
			while i < len(self.lcnlist):
				if self.lcnlist[i][0] >= 16384 and duplicates == 0:
					f.write("#DESCRIPTION ---------- Duplicates ----------\n")
					duplicates = 1
			
				refstr = "1:0:1:%x:%x:%x:eeee0000:0:0:0:" % (self.lcnlist[i][3], self.lcnlist[i][2], self.lcnlist[i][1])
				if eServiceReference(refstr).toString() in self.slistall:
					f.write("#SERVICE %s\n" % refstr)
				i += 1
			f.close()
			self.addInBouquets()
			eDVBDB.getInstance().reloadBouquets()
			self.isscanning = 0
			
	def doScan(self):
		if self.isscanning == 1:
			return
			
		self.isscanning = 1
		refstr = '%s ORDER BY name'%(self.service_types_tv)
		ref = eServiceReference(refstr)
		serviceHandler = eServiceCenter.getInstance()
		servicelist = serviceHandler.list(ref)
		self.lcnlist = []
		self.slist = []
		self.slistall = []
		self.sindex = -1
		tsidtmp = []
		self.textlog = ""
		self["progress"].setValue(0)
		if not servicelist is None:
			while True:
				service = servicelist.getNext()
				if not service.valid(): #check if end of list
					break
					
				unsigned_orbpos = service.getUnsignedData(4) >> 16
				if unsigned_orbpos == 0xEEEE: #Terrestrial
					refstr = service.toString()
					self.slistall.append(refstr)
					tmp = refstr.split(":")
					if len(tmp) == 11:
						tsid = tmp[4]
						if not tsid in tsidtmp:
							self.slist.append(refstr)
							tsidtmp.append(tsid)
							
		lcn_scanner.demuxer_open()
		self.doZap()
	def quit(self):
		self.timeout.stop()
		self.timeout.stop()
		self.close()
		
def LCNScannerMain(session, **kwargs):
	session.open(LCNScannerPlugin)
	
def LCNScannerSetup(menuid, **kwargs):
	if menuid == "setup":
		return [("LCN Scanner", LCNScannerMain, "lcnscanner", None)]
	else:
		return []

def Plugins(**kwargs):
	return PluginDescriptor(name="LCN Scanner", description=_("LCN scanner for DVB-T services"), where = PluginDescriptor.WHERE_MENU, fnc=LCNScannerSetup)
