import mc
config = mc.GetApp().GetLocalConfig()
http = mc.Http()

# For Debugging
#config.SetValue("verified", "")
#config.SetValue("server", "")

server = config.GetValue("server")
verified = config.GetValue("verified")

def GetServer():
		config = mc.GetApp().GetLocalConfig()
		server = config.GetValue("server")
		response = mc.ShowDialogKeyboard("Enter Full URL to MythBoxee Script", server, False)
		if VerifyServer(response) == True:
			config.SetValue("server", response)

def VerifyServer(url):
		data = http.Get(url + "?type=verify")
		if http.GetHttpResponseCode() == 200:
			config.SetValue("verified", "1")
			return True
		else:
			return False

if not server:
	GetServer()

# If server is set, and at this point it has been verified
# then launch the application
if config.GetValue("verified") == "1":
	mc.ActivateWindow(14000)
else:
	mc.ShowDialogOk("MythBoxee Error", "You must enter the full path to the MythBoxee script or MythBoxee was unable to verify the URL provided.")