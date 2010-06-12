import mc
config = mc.GetApp().GetLocalConfig()
http = mc.Http()

def GetServer():
		config = mc.GetApp().GetLocalConfig()
		server = config.GetValue("server")
		response = mc.ShowDialogKeyboard("Enter Full URL to Boxee Script (ie http://192.168.1.210/boxee.php)", server, False)
		if not response and not server:
			GetServer()
		elif response:
			config.SetValue("server", response)

# Check to see if the server variable has been set
# if it has not then ask for input from user
if not server:
	GetServer()

# Verify that the script has been installed at the location
# specifed by the user
data = http.Get(config.GetValue("server") + "?type=verify")
if http.GetHttpResponseCode() != 200:
	mc.ShowDialogOk("Error", "Unable to connect MythBoxee Script on MythBackend")
	GetServer()

# If server is set, and at this point it has been verified
# then launch the application
if server:	
	mc.ActivateWindow(14000)