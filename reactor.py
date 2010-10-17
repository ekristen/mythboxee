import threading

class Reactor(threading.Thread):
	def __init__(self):
		print "reactor.init"
		self._stopEvent = threading.Event()
		self._sleepPeriod = 4
		threading.Thread.__init__(self, name="Reactor")

	def __del__(self):
		print "reactor.del"

	def run(self):
		print "reactor.run"
		print "%s starts" % (self.getName(),)
		while not self._stopEvent.isSet():
			threads = threading.enumerate
			## Do Stuff Here
			self._stopEvent.wait(self._sleepPeriod)

	def stop(self,timeout=None):
		self._stopEvent.set()
		threading.Thread.join(self,timeout)