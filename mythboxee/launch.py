import mc
config = mc.GetApp().GetLocalConfig()
http = mc.Http()

#Debug Code
#config.SetValue("verified", "")
#config.SetValue("server", "")

server = config.GetValue("server")
verified = config.GetValue("verified")

def GetServer():
		config = mc.GetApp().GetLocalConfig()
		server = config.GetValue("server")
		response = mc.ShowDialogKeyboard("Enter Full URL to MythBoxee Script", server, False)
		if not response and not server:
			GetServer()
		elif response:
			config.SetValue("server", response)


def VerifyServer():
		data = http.Get(config.GetValue("server") + "?type=verify")
		if http.GetHttpResponseCode() != 200:
			mc.ShowDialogOk("Error", "Unable to connect MythBoxee Script on MythBackend")
			GetServer()
			VerifyServer()
		else:
			config.SetValue("verified", "1")

while not server and not verified:
	if not server:
		GetServer()
		server = config.GetValue("server")
	if not verified:
		VerifyServer()
		verified = config.GetValue("verified")

# If server is set, and at this point it has been verified
# then launch the application
if verified:
	mc.ActivateWindow(14000)