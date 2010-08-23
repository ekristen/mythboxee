import mc
import time

# DEBUG #
#mc.GetApp().GetLocalConfig().SetValue("dbconn", "")
# DEBUG #

# We'll use this to determine when to reload data.
mc.GetApp().GetLocalConfig().SetValue("LastRunTime", str(time.time()))
mc.GetApp().GetLocalConfig().SetValue("CurrentShowItemID", "0")

# Activate Loading Window
mc.ActivateWindow(14001)
