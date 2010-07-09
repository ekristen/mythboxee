import mc
import mythboxee

# Get Access to the Apps Local Config
config = mc.GetApp().GetLocalConfig()

# For Debugging
#config.SetValue("verified", "")
#config.SetValue("server", "")

# Pull out some of the variables we need
server = config.GetValue("server")
verified = config.GetValue("verified")

# If the server hasn't been defined, we need to get it.
if not server:
	mythboxee.GetServer()

# If server is set, and at this point it has been verified
# then launch the application
if config.GetValue("verified") == "1":
	mc.ActivateWindow(14000)

	# Load all the show data from the MythTV Backend Server
	mythboxee.LoadShows()
else:
	mc.ShowDialogOk("MythBoxee Error", "You must enter the full path to the MythBoxee script or MythBoxee was unable to verify the URL provided.")