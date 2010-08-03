import mc
import sys
import signal
import mythtv
import mythboxee

# DEBUG #
#mc.GetApp().GetLocalConfig().SetValue("dbconn", "")
# DEBUG #

# Activate Loading Window
mc.ActivateWindow(14001)

# Lets go ahead and launch the app
mythboxee.Launch()

